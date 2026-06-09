#!/usr/bin/env python3
"""HiveMind demo control panel — one tool to drive the hackathon demo.

  python scripts/demo.py list                 # show the themed scenarios
  python scripts/demo.py preflight            # re-seed time-relative data + health check (run before stage)
  python scripts/demo.py fire worldcup        # fire a scenario at the war-room (user=hivemind -> the browser)
  python scripts/demo.py fire finserv --verify  # fire + wait for completion + verify the real MR/Atlas
  python scripts/demo.py mrs                   # list the freshest @HiveMind-bot MRs (grab the iid to click)
  python scripts/demo.py customers             # live BigQuery blast-radius (the $ at risk, by name)
  python scripts/demo.py rigor                 # the 'it grades itself / gets better' evidence (aha #4)

The browser war-room (:3000) subscribes to events for user 'hivemind' (NEXT_PUBLIC_WS_USER),
so `fire` defaults to --user hivemind: the incident channel materializes + streams live in the
browser. `--verify` uses an isolated watcher (so it doesn't matter which user) and asserts the
real side effects landed.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import urllib.parse
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SCENARIOS_PATH = ROOT / "scripts" / "demo_scenarios.json"
SECRET = os.getenv("DT_WEBHOOK_SECRET") or os.getenv("HMAC_SECRET", "")
API = os.getenv("DEMO_API_URL", "http://127.0.0.1:8000")

G, R, Y, B, D, X = "\033[92m", "\033[91m", "\033[93m", "\033[94m", "\033[2m", "\033[0m"


def _load() -> dict:
    return json.loads(SCENARIOS_PATH.read_text())


def _scenario(sid: str) -> dict:
    for s in _load()["scenarios"]:
        if s["id"] == sid:
            return s
    sys.exit(f"{R}unknown scenario '{sid}'. try: {', '.join(s['id'] for s in _load()['scenarios'])}{X}")


def cmd_list(_: argparse.Namespace) -> int:
    data = _load()
    print(f"\n{B}HiveMind demo scenarios{X}  (all route to the one real fix: payment-service timeout 1->5)\n")
    for s in data["scenarios"]:
        print(f"  {G}{s['id']:<9}{X} [{s['severity']}] {B}{s['theme']}{X}")
        print(f"            {s['headline']}")
        print(f"            {D}aha: {s['aha']}{X}\n")
    rb = data["rigor_beat"]
    print(f"  {G}{'rigor':<9}{X} {B}{rb['theme']}{X}")
    print(f"            {D}aha: {rb['aha']}{X}\n")
    print(f"{D}fire one:  python scripts/demo.py fire <id>            (streams to the browser war-room){X}")
    print(f"{D}verify:    python scripts/demo.py fire <id> --verify   (asserts the real MR + Atlas record){X}\n")
    return 0


def cmd_fire(args: argparse.Namespace) -> int:
    s = _scenario(args.id)
    if args.verify:
        # Delegate to the battle-tested end-to-end verifier.
        cmd = [
            sys.executable, "-u", str(ROOT / "scripts" / "verify_demo_e2e.py"),
            "--service", s["service"], "--severity", s["severity"],
            "--user", args.user, "--title", s["title"], "--timeout", str(args.timeout),
        ]
        return subprocess.call(cmd)

    if not SECRET:
        sys.exit(f"{R}no HMAC secret (set HMAC_SECRET in .env){X}")
    problem_id = f"P-{uuid.uuid4().hex[:6]}"
    body = {"problem_id": problem_id, "service": s["service"],
            "severity": s["severity"], "title": s["title"]}
    raw = json.dumps(body).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    url = f"{API}/api/incoming/dynatrace?user={args.user}"
    print(f"\n{B}firing {s['id']} ({s['theme']}, {s['severity']}) -> {url}{X}")
    print(f"{D}{s['title']}{X}\n")
    try:
        r = requests.post(url, data=raw,
                          headers={"Content-Type": "application/json", "X-DT-Signature": sig},
                          timeout=20)
    except requests.RequestException as e:
        sys.exit(f"{R}request error: {e}{X}")
    print(f"  HTTP {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        ch = r.json().get("channel_id")
        print(f"\n{G}OK{X} — watch it stream live at {B}http://localhost:3000/c/{ch}{X}")
        print(f"{D}talking points:{X}")
        for t in s.get("talk", []):
            print(f"  • {t}")
        print(f"\n{D}aha: {s['aha']}{X}\n")
        return 0
    return 1


def cmd_mrs(args: argparse.Namespace) -> int:
    base = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")
    tok = os.getenv("GITLAB_TOKEN")
    proj = os.getenv("GITLAB_TARGET_PROJECT", "")
    pid = urllib.parse.quote(proj, safe="")
    r = requests.get(f"{base}/api/v4/projects/{pid}/merge_requests?state=all&per_page=8&order_by=created_at",
                     headers={"PRIVATE-TOKEN": tok}, timeout=15)
    print(f"\n{B}Recent merge requests on {proj}{X}")
    freshest_open = None
    for m in r.json():
        mark = G if m["state"] == "opened" else D
        if m["state"] == "opened" and freshest_open is None:
            freshest_open = m
        print(f"  {mark}!{m['iid']} [{m['state']}]{X} {m['title'][:58]}  {D}@{m['author']['username']}{X}")
    if freshest_open:
        print(f"\n{G}freshest OPEN MR to click on stage: !{freshest_open['iid']}{X}  {freshest_open['web_url']}")
    return 0


def cmd_customers(_: argparse.Namespace) -> int:
    """Live BigQuery blast-radius via the Liaison's exact read path."""
    try:
        from google.cloud import bigquery
    except ImportError:
        sys.exit(f"{R}google-cloud-bigquery not installed{X}")
    proj = os.getenv("GOOGLE_CLOUD_PROJECT", "hivemind-hackathon")
    client = bigquery.Client(project=proj)
    sql = f"""
      SELECT customer_id, plan, monthly_revenue, services_used
      FROM `{proj}.google_sheets.customer_usage`
      WHERE CONTAINS_SUBSTR(services_used, 'payment-service')
         OR CONTAINS_SUBSTR(services_used, 'checkout')
      ORDER BY monthly_revenue DESC
    """
    rows = list(client.query(sql).result())
    total = sum(r["monthly_revenue"] for r in rows)
    ent = [r for r in rows if r["plan"] == "Enterprise"]
    ent_rev = sum(r["monthly_revenue"] for r in ent)
    print(f"\n{B}Live BigQuery blast radius (payment-service OR checkout){X}")
    print(f"  {G}{len(rows)} customers affected · ${total:,}/mo at risk{X}  (~${total*12:,}/yr)")
    print(f"  {G}{len(ent)} Enterprise accounts = ${ent_rev:,}/mo (the named, high-trust risk){X}\n")
    for r in rows:
        tag = B if r["plan"] == "Enterprise" else D
        print(f"  {tag}{r['customer_id']}  {r['plan']:<11} ${r['monthly_revenue']:>5,}/mo{X}  {r['services_used']}")
    return 0


def cmd_rigor(_: argparse.Namespace) -> int:
    print(f"\n{B}AHA #4 — it's real, not theater: external grading + self-improvement{X}\n")
    # 1) external Evaluator feedback files
    runs_dir = ROOT / "harness" / "runs"
    print(f"{B}1) External Evaluator verdicts (harness/runs/*/feedback.json){X}")
    found = False
    if runs_dir.exists():
        for fb in sorted(runs_dir.glob("*/feedback.json")):
            try:
                d = json.loads(fb.read_text())
            except Exception:
                continue
            found = True
            v = d.get("verdict", "?")
            clauses = d.get("failed_contract_clauses") or d.get("failed_clauses") or []
            col = G if v == "PASS" else (Y if v == "ESCALATED" else R)
            print(f"  {col}{fb.parent.name}: {v}{X}" + (f"  {D}({len(clauses)} failed clauses){X}" if clauses else ""))
            for c in clauses[:3]:
                print(f"      {D}- {c}{X}")
    if not found:
        print(f"  {D}(no feedback.json on disk — run scripts/run_harness_demo.py to generate one){X}")
    # 2) Atlas harness_runs + flywheel_runs
    try:
        from pymongo import MongoClient
        db = MongoClient(os.getenv("MDB_URI"), serverSelectionTimeoutMS=8000)["hivemind"]
        print(f"\n{B}2) Generator->Evaluator loop (Atlas harness_runs){X}")
        agg = {}
        for d in db.harness_runs.find():
            agg[d.get("verdict", "?")] = agg.get(d.get("verdict", "?"), 0) + 1
        print(f"  {D}verdict tally: {agg}{X}")
        print(f"  {G}the loop self-corrects (FAIL->PASS) and gives up safely (FAILx4 -> ESCALATED to a human){X}")
        print(f"\n{B}3) Self-improving flywheel (Atlas flywheel_runs){X}")
        for d in db.flywheel_runs.find():
            sc = d.get("scores", {})
            old, new, n = sc.get("old", {}).get("caught"), sc.get("new", {}).get("caught"), d.get("n_corrections")
            if d.get("winner") and n:
                print(f"  {G}old rubric {old}/{n} -> new rubric {new}/{n}  winner={d.get('winner')} promoted={d.get('promoted')}{X}")
    except Exception as e:  # noqa: BLE001
        print(f"  {D}(Atlas read skipped: {e}){X}")
    print(f"\n{D}honesty: narrate only dated flywheel runs; say 'human-flagged corrections'; Phoenix links are localhost.{X}\n")
    return 0


def cmd_preflight(_: argparse.Namespace) -> int:
    print(f"\n{B}PRE-FLIGHT — re-seed time-relative data + health checks{X}\n")
    seeds = ["seed_dynatrace.py", "seed_elastic_deploys.py", "seed_elastic_logs.py"]
    for sname in seeds:
        print(f"{D}running {sname}…{X}")
        rc = subprocess.call([sys.executable, str(ROOT / "scripts" / sname)],
                             stdout=subprocess.DEVNULL if sname != "seed_elastic_logs.py" else None)
        print(f"  {G if rc == 0 else R}{sname}: {'ok' if rc == 0 else 'FAILED'}{X}")
    # health
    try:
        h = requests.get(f"{API}/healthz", timeout=5).json()
        print(f"\n  {G}backend /healthz: {h}{X}")
    except Exception as e:  # noqa: BLE001
        print(f"\n  {R}backend not reachable at {API}: {e}{X}")
    try:
        code = requests.get("http://localhost:3000/c/ops", timeout=8).status_code
        print(f"  {G if code == 200 else R}war-room :3000/c/ops -> HTTP {code}{X}")
    except Exception as e:  # noqa: BLE001
        print(f"  {R}war-room not reachable: {e}{X}")
    print(f"\n{D}Grail needs ~30-60s to index; then fire a scenario. Tip: `python scripts/demo.py mrs` to grab the iid.{X}\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="HiveMind demo control panel")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("mrs").set_defaults(fn=cmd_mrs)
    sub.add_parser("customers").set_defaults(fn=cmd_customers)
    sub.add_parser("rigor").set_defaults(fn=cmd_rigor)
    sub.add_parser("preflight").set_defaults(fn=cmd_preflight)
    f = sub.add_parser("fire")
    f.add_argument("id")
    f.add_argument("--user", default="hivemind")
    f.add_argument("--verify", action="store_true")
    f.add_argument("--timeout", type=float, default=540.0)
    f.set_defaults(fn=cmd_fire)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
