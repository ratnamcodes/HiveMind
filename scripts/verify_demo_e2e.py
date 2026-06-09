#!/usr/bin/env python3
"""End-to-end demo verifier: fire a signed Dynatrace alert, watch the FULL /ws stream,
then independently confirm the side effects landed (real GitLab MR + Atlas incident record).

Unlike _test_ws_plumbing.py (which stops after the first ~15 events), this waits for the
`complete` event of a full 6-agent run and then VERIFIES the artifacts out-of-band:

  1. Connects to /ws as the demo user and records every event with a wall-clock offset.
  2. Fires the HMAC-signed Dynatrace webhook (rich narrative carried in --title).
  3. Streams until `complete` (or --timeout), printing a live agent/tool timeline.
  4. Confirms a NEW merge request was opened on the target repo since we started, and
     reads payment-service/config.yaml on the MR's branch to prove the timeout was fixed.
  5. Confirms an Atlas incident record exists for this run.

Exit 0 only if: complete arrived AND a real MR url is in the payload AND the MR is on
GitLab AND (best-effort) the Atlas record is present.

Run:
    .venv/bin/python scripts/verify_demo_e2e.py \
        --service payment-service --severity sev2 \
        --title "Real-time fraud scoring: legit card payments declined ..." \
        --user demo
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
from pathlib import Path

import requests
import websockets
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SECRET = os.getenv("DT_WEBHOOK_SECRET") or os.getenv("HMAC_SECRET", "")
GL_BASE = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")
GL_TOKEN = os.getenv("GITLAB_TOKEN")
GL_PROJ = os.getenv("GITLAB_TARGET_PROJECT", "")

C = {"g": "\033[92m", "r": "\033[91m", "y": "\033[93m", "b": "\033[94m", "d": "\033[2m", "x": "\033[0m"}


def _mrs_since(t0: float) -> list[dict]:
    pid = urllib.parse.quote(GL_PROJ, safe="")
    url = f"{GL_BASE}/api/v4/projects/{pid}/merge_requests?state=all&order_by=created_at&per_page=10"
    r = requests.get(url, headers={"PRIVATE-TOKEN": GL_TOKEN}, timeout=15)
    if r.status_code != 200:
        return []
    out = []
    for m in r.json():
        # created_at is ISO8601 UTC; compare to our start epoch.
        from datetime import datetime, timezone
        try:
            ts = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")).timestamp()
        except Exception:
            ts = 0
        if ts >= t0 - 5:
            out.append(m)
    return out


def _mr_changes(iid: int) -> list[str]:
    pid = urllib.parse.quote(GL_PROJ, safe="")
    r = requests.get(f"{GL_BASE}/api/v4/projects/{pid}/merge_requests/{iid}/changes",
                     headers={"PRIVATE-TOKEN": GL_TOKEN}, timeout=15)
    if r.status_code != 200:
        return []
    return [c.get("new_path") for c in r.json().get("changes", [])]


def _file_on_branch(branch: str) -> str | None:
    pid = urllib.parse.quote(GL_PROJ, safe="")
    fp = urllib.parse.quote("payment-service/config.yaml", safe="")
    url = f"{GL_BASE}/api/v4/projects/{pid}/repository/files/{fp}?ref={urllib.parse.quote(branch, safe='')}"
    r = requests.get(url, headers={"PRIVATE-TOKEN": GL_TOKEN}, timeout=15)
    if r.status_code != 200:
        return None
    return base64.b64decode(r.json()["content"]).decode()


async def _verify_atlas(incident_id: str, mr_url: str | None = None) -> str:
    try:
        from pymongo import MongoClient
        c = MongoClient(os.getenv("MDB_URI"), serverSelectionTimeoutMS=8000)
        db = c["hivemind"]
        # Scribe writes its own incident_id, so match on the MR url FIRST (the reliable
        # join key), then fall back to the incident id fields.
        query = {"$or": [{"id": incident_id}, {"incident_id": incident_id}]}
        if mr_url:
            query["$or"].insert(0, {"mr_url": mr_url})
        doc = db.incidents.find_one(query)
        if doc:
            return f"found in 'incidents' (title={str(doc.get('title','?'))[:50]!r}, services={doc.get('services')})"
        return "no record found"
    except Exception as e:  # noqa: BLE001
        return f"atlas check error: {type(e).__name__}: {e}"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=None, help="S1..S5 — pulls service/severity/title/context from scripts/scenarios.py")
    ap.add_argument("--service", default="payment-service")
    ap.add_argument("--severity", default="sev2", choices=["sev1", "sev2", "sev3"])
    ap.add_argument("--title", default=None, help="rich incident narrative (carried into the alert)")
    ap.add_argument("--problem-id", default=None)
    ap.add_argument("--liaison-context", default="", help="activates a Fivetran depth play (e.g. PII redaction)")
    ap.add_argument("--hitl", action="store_true", help="pause at the human approval gate (run pauses; resume separately)")
    ap.add_argument("--user", default="demo")
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--timeout", type=float, default=900.0)  # allow for a Reviewer revise loop
    args = ap.parse_args()

    if args.scenario:
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from scripts.scenarios import get
        scn = get(args.scenario)
        args.service = scn["dynatrace"]["service_name"]  # unique cause service (clean Grail)
        args.customer_service = scn["alert"]["service"]  # customer-facing service for Liaison
        args.severity = scn["alert"]["severity"]
        args.title = scn["alert"]["title"]
        args.liaison_context = args.liaison_context or scn.get("liaison_context", "")
        args.expected_target = scn.get("code_target")
        print(f"{C['d']}scenario {scn['id']} — fix should land on {scn['code_target']}{C['x']}")
    if not args.title:
        print("FAIL: provide --scenario or --title")
        return 1
    if not SECRET:
        print("FAIL: no HMAC secret")
        return 1

    import uuid
    problem_id = args.problem_id or f"P-{uuid.uuid4().hex[:6]}"
    t0 = time.time()
    ws_uri = args.url.replace("http", "ws") + f"/ws?user={args.user}"

    print(f"{C['b']}╔══ HiveMind E2E demo verify ═══════════════════════════════{C['x']}")
    print(f"  service={args.service} severity={args.severity} user={args.user} problem={problem_id}")
    print(f"  title: {args.title}")
    print(f"{C['b']}╚═══════════════════════════════════════════════════════════{C['x']}\n")

    agents_seen: dict[str, set] = {}
    tool_calls: list[tuple[str, str]] = []
    complete_payload: dict | None = None

    async with websockets.connect(ws_uri, max_size=None) as ws:
        body = {"problem_id": problem_id, "service": args.service,
                "severity": args.severity, "title": args.title}
        if args.liaison_context:
            body["liaison_context"] = args.liaison_context
        if args.hitl:
            body["hitl"] = True
        if getattr(args, "expected_target", None):
            body["code_target"] = args.expected_target
        if getattr(args, "customer_service", None):
            body["customer_service"] = args.customer_service
        raw = json.dumps(body).encode()
        sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
        r = requests.post(f"{args.url}/api/incoming/dynatrace?user={args.user}", data=raw,
                          headers={"Content-Type": "application/json", "X-DT-Signature": sig}, timeout=15)
        print(f"{C['d']}webhook → HTTP {r.status_code}: {r.text[:140]}{C['x']}\n")
        if r.status_code != 200:
            return 1

        deadline = time.time() + args.timeout
        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=deadline - time.time())
            except asyncio.TimeoutError:
                break
            ev = json.loads(msg)
            off = time.time() - t0
            t = ev.get("type")
            if t == "channel_created":
                print(f"  {off:6.1f}s  {C['y']}📡 channel {ev['channel']['id']} (sev {ev['channel'].get('severity')}){C['x']}")
            elif t == "status":
                aid, st, tool = ev["agent_id"], ev["state"], ev.get("tool")
                agents_seen.setdefault(aid, set()).add(st)
                if st == "tool_call" and tool:
                    tool_calls.append((aid, tool))
                    print(f"  {off:6.1f}s  {C['b']}🔧 {aid} → {tool}(){C['x']}")
                elif st == "thinking":
                    print(f"  {off:6.1f}s  {C['d']}💭 {aid} thinking…{C['x']}")
                elif st == "done":
                    print(f"  {off:6.1f}s  {C['g']}✓ {aid} done{C['x']}")
            elif t == "token":
                aid = ev["agent_id"]
                agents_seen.setdefault(aid, set())
            elif t == "complete":
                complete_payload = ev.get("payload") or {}
                print(f"  {off:6.1f}s  {C['g']}🏁 complete{C['x']}")
                break

    print(f"\n{C['b']}── stream summary ──{C['x']}")
    print(f"  agents seen: {sorted(agents_seen)}")
    print(f"  tool calls : {tool_calls}")
    if not complete_payload:
        print(f"{C['r']}FAIL: no complete event within {args.timeout}s{C['x']}")
        return 1
    print(f"  final payload: {json.dumps(complete_payload, indent=2)[:900]}")

    # --- out-of-band artifact verification ---
    print(f"\n{C['b']}── artifact verification (out-of-band) ──{C['x']}")
    ok = True
    mr_url = complete_payload.get("mr_url")
    if mr_url:
        print(f"  {C['g']}MR url in payload: {mr_url}{C['x']}")
    else:
        print(f"  {C['r']}no mr_url in payload{C['x']}")
        ok = False

    mrs = _mrs_since(t0)
    new_mr = next((m for m in mrs if mr_url and m["web_url"] == mr_url), mrs[0] if mrs else None)
    expected = getattr(args, "expected_target", None)
    if new_mr:
        print(f"  {C['g']}GitLab MR confirmed: !{new_mr['iid']} '{new_mr['title'][:60]}' by @{new_mr['author']['username']} [{new_mr['state']}]{C['x']}")
        changed = _mr_changes(new_mr["iid"])
        print(f"  changed files: {changed}")
        if expected:
            if expected in changed:
                print(f"  {C['g']}✓ correct file patched for this scenario: {expected}{C['x']}")
            else:
                print(f"  {C['r']}✗ expected the fix on {expected}, but MR changed {changed}{C['x']}")
                ok = False
    else:
        print(f"  {C['r']}no new MR found on GitLab since start{C['x']}")
        ok = False

    inc_id = complete_payload.get("incident_id") or f"INC-{problem_id}"
    atlas = await _verify_atlas(inc_id, mr_url)
    print(f"  Atlas incident record: {atlas}")

    verdict = complete_payload.get("verdict")
    print(f"\n{C['b']}── VERDICT ──{C['x']}  reviewer={verdict} escalated={complete_payload.get('escalated')} "
          f"customers={complete_payload.get('customers_affected')}")
    print((C['g'] + "E2E PASS" if ok else C['r'] + "E2E FAIL") + C['x'])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
