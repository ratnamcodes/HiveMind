#!/usr/bin/env python3
"""Drive the HiveMind war-room in a REAL browser through a full incident — including the
human-in-the-loop approval — and record video + screenshots. This is the demoable artifact.

Flow (scenario-aware, reads scripts/scenarios.py):
  1. predict the incident channel id, open it in the browser, and let /ws connect FIRST
     (so the pinned brief + every event is captured live, not missed),
  2. fire the signed Dynatrace alert (optionally --hitl so the run pauses for a human),
  3. watch the brief card, the six agents stream their reasoning + tool calls, and the
     business impact ($ at risk, named customers, PII redaction),
  4. when the approval card appears, CLICK "Approve & ship" — the run resumes and ships,
  5. capture the resolved card + the real MR link.

Run:
    .venv/bin/python scripts/record_demo.py --scenario S2 --hitl --max-seconds 600
Outputs: scripts/demo_recording/<scenario>/  (war-room-demo.webm + NN-*.png)
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from scripts.scenarios import get  # noqa: E402

import redis as redislib  # noqa: E402
from hivemind import events  # noqa: E402

SECRET = os.getenv("DT_WEBHOOK_SECRET") or os.getenv("HMAC_SECRET", "")
API = os.getenv("DEMO_API_URL", "http://127.0.0.1:8000")
WEB = os.getenv("DEMO_WEB_URL", "http://localhost:3000")
R = redislib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="S2")
    ap.add_argument("--hitl", action="store_true")
    ap.add_argument("--user", default="hivemind")
    ap.add_argument("--max-seconds", type=float, default=600.0)
    ap.add_argument("--headless", default="true")
    args = ap.parse_args()

    scn = get(args.scenario)
    # Drive Detective/LogDiver/CodeArch on the UNIQUE cause service (its own Grail logs) so a
    # back-to-back recording of other scenarios doesn't contaminate the diagnosis; Liaison grounds
    # customer impact on the customer-FACING service.
    svc = scn["dynatrace"]["service_name"]
    customer_service = scn["alert"]["service"]
    sev, title = scn["alert"]["severity"], scn["alert"]["title"]
    liaison_ctx = scn.get("liaison_context", "")
    out = ROOT / "scripts" / "demo_recording" / scn["id"]
    out.mkdir(parents=True, exist_ok=True)
    for f in list(out.glob("*.png")) + list(out.glob("*.webm")):
        f.unlink()

    problem_id = f"P-{uuid.uuid4().hex[:6]}"
    channel_id = f"inc-{svc}-{problem_id}".lower()
    chan = events.channel_name(args.user)
    shots: list[str] = []

    def numsub() -> int:
        s = R.execute_command("PUBSUB", "NUMSUB", chan)
        return int(s[1]) if len(s) > 1 else 0

    print(f"recording {scn['id']} ({scn['domain']}) hitl={args.hitl} -> {out}")
    print(f"  channel: {channel_id}  | fix should land on {scn['code_target']}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=(args.headless.lower() != "false"))
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  record_video_dir=str(out),
                                  record_video_size={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: print("  PAGEERROR", str(e)[:200]))

        def shot(name: str) -> None:
            pg.screenshot(path=str(out / name))
            shots.append(name)
            print(f"  📸 {name}")

        # 1) Open the (empty) incident channel FIRST and wait for OUR /ws to subscribe.
        base = numsub()
        pg.goto(f"{WEB}/c/{channel_id}", wait_until="networkidle", timeout=30000)
        for _ in range(40):
            if numsub() > base:
                break
            pg.wait_for_timeout(500)
        pg.wait_for_timeout(800)
        shot("01-channel-open.png")

        # 2) Fire the signed alert.
        body = {"problem_id": problem_id, "service": svc, "severity": sev, "title": title,
                "code_target": scn["code_target"], "customer_service": customer_service}
        if liaison_ctx:
            body["liaison_context"] = liaison_ctx
        if args.hitl:
            body["hitl"] = True
        raw = json.dumps(body).encode()
        sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
        r = requests.post(f"{API}/api/incoming/dynatrace?user={args.user}", data=raw,
                          headers={"Content-Type": "application/json", "X-DT-Signature": sig}, timeout=20)
        print(f"  🚨 fired -> HTTP {r.status_code}")
        pg.wait_for_timeout(2500)
        shot("02-brief.png")

        # 3) Watch the run; screenshot periodically; handle the approval card; stop on resolve.
        deadline = time.time() + args.max_seconds
        next_shot = time.time() + 30
        seq = 3
        approved = False
        resolved = False
        while time.time() < deadline:
            pg.wait_for_timeout(1500)
            low = pg.inner_text("body").lower()

            if args.hitl and not approved and ("paused — your call" in low or "approve & ship" in low):
                shot(f"{seq:02d}-approval-card.png"); seq += 1
                btn = pg.get_by_role("button", name="Approve & ship")
                try:
                    btn.first.click(timeout=4000)
                    approved = True
                    print("  👤 clicked Approve & ship")
                    pg.wait_for_timeout(1500)
                    shot(f"{seq:02d}-approved.png"); seq += 1
                except Exception as e:  # noqa: BLE001
                    print("  (approve click failed:", str(e)[:80], ")")

            if "incident resolved" in low or "incident escalated" in low:
                resolved = True
                break

            if time.time() >= next_shot:
                shot(f"{seq:02d}-streaming.png"); seq += 1
                next_shot = time.time() + 35

        pg.wait_for_timeout(2000)
        shot(f"{seq:02d}-final.png")
        pg.wait_for_timeout(1500)
        ctx.close()
        video = pg.video.path() if pg.video else None
        browser.close()

    print(f"\n=== done === approved={approved} resolved={resolved} shots={len(shots)}")
    if video:
        final = out / "war-room-demo.webm"
        try:
            Path(video).rename(final)
            print(f"  🎬 {final}")
        except Exception:  # noqa: BLE001
            print(f"  🎬 {video}")
    return 0 if (resolved and (approved or not args.hitl)) else 2


if __name__ == "__main__":
    raise SystemExit(main())
