#!/usr/bin/env python3
"""Record the REAL HiveMind incident loop end-to-end in a real browser — NO script, NO seed.

Unlike record_demo.py (which fires a seeded scenario alert), this drives the genuinely-real flow:
  1. open the war room and let the /ws stream connect FIRST,
  2. inject a REAL latency regression into the running checkout/payment apps,
  3. the checkout service detects its OWN sustained SLO breach and pages HiveMind (no manual fire),
  4. watch the incident channel auto-appear, click into it, and watch the six agents investigate
     real Dynatrace Grail telemetry (Davis CoPilot DQL + live evidence) and open a real MR,
  5. when the human approval card appears, CLICK "Approve & ship",
  6. capture the recovery proven from real Dynatrace data (Grail + Site Reliability Guardian).

Outputs: scripts/demo_recording/REAL/  (war-room-real-demo.webm + .mp4 + NN-*.png)
Run:  .venv/bin/python scripts/record_real_demo.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import redis as redislib
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from hivemind import events  # noqa: E402

WEB = os.getenv("DEMO_WEB_URL", "http://localhost:3000")
USER = "hivemind"
MAX_SECONDS = float(os.getenv("DEMO_MAX_SECONDS", "480"))
R = redislib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


def main() -> int:
    out = ROOT / "scripts" / "demo_recording" / "REAL"
    out.mkdir(parents=True, exist_ok=True)
    for f in list(out.glob("*.png")) + list(out.glob("*.webm")) + list(out.glob("*.mp4")):
        f.unlink()
    chan = events.channel_name(USER)

    def numsub() -> int:
        s = R.execute_command("PUBSUB", "NUMSUB", chan)
        return int(s[1]) if len(s) > 1 else 0

    # make sure the app starts healthy so the regression is a real state change
    subprocess.run(["bash", str(ROOT / "scripts" / "inject_regression.sh"), "revert"],
                   capture_output=True)
    print(f"recording REAL incident loop -> {out}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  record_video_dir=str(out),
                                  record_video_size={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: print("  PAGEERROR", str(e)[:160]))
        shots: list[str] = []

        def shot(name: str) -> None:
            try:
                pg.screenshot(path=str(out / name)); shots.append(name); print(f"  [shot] {name}")
            except Exception as e:  # noqa: BLE001
                print("  (shot failed", str(e)[:60], ")")

        # 1) Open the war room; wait for OUR /ws to subscribe so nothing is missed.
        base = numsub()
        pg.goto(f"{WEB}/c/ops", wait_until="networkidle", timeout=30000)
        for _ in range(40):
            if numsub() > base:
                break
            pg.wait_for_timeout(500)
        pg.wait_for_timeout(1000)
        shot("01-warroom-idle.png")

        # 2) Subscribe to the event bus so we learn the EXACT id of the real channel this run creates
        #    (robust even if the Davis-problem poller fires a second incident), then inject the REAL
        #    regression — the running app detects its own breach and pages HiveMind (no manual fire).
        pubsub = R.pubsub()
        pubsub.subscribe(chan)
        time.sleep(0.5)
        print("  >>> injecting REAL regression (payment downstream_delay_ms -> 1200)")
        subprocess.run(["bash", str(ROOT / "scripts" / "inject_regression.sh"), "break"],
                       capture_output=True)

        # 3) Capture the channel_created id from the bus, then click into that exact channel (client-side
        #    nav keeps the /ws connection + the events already buffered in the store).
        channel_id = None
        t_end = time.time() + 60
        while time.time() < t_end and not channel_id:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg:
                continue
            try:
                ev = json.loads(msg["data"])
                if ev.get("type") == "channel_created":
                    channel_id = ev["channel"]["id"]
            except Exception:  # noqa: BLE001
                pass
        print(f"  real incident channel: {channel_id}")
        clicked = False
        if channel_id:
            link = pg.locator(f'a[href$="/c/{channel_id}"]')
            for _ in range(30):
                if link.count() > 0:
                    shot("02-incident-appeared.png")
                    try:
                        link.first.click(timeout=4000); clicked = True
                    except Exception:  # noqa: BLE001
                        pass
                    break
                pg.wait_for_timeout(1000)
        print(f"  clicked into real channel: {clicked}")
        pg.wait_for_timeout(2500)
        shot("03-brief.png")

        # 4) Watch the run; screenshot periodically; click Approve when the gate appears; stop on recovery.
        deadline = time.time() + MAX_SECONDS
        next_shot = time.time() + 25
        seq = 4
        approved = recovered = False
        while time.time() < deadline:
            pg.wait_for_timeout(1500)
            try:
                low = pg.inner_text("body").lower()
            except Exception:  # noqa: BLE001
                continue
            if not approved and "approve & ship" in low:
                shot(f"{seq:02d}-approval-gate.png"); seq += 1
                try:
                    pg.get_by_role("button", name="Approve & ship").first.click(timeout=4000)
                    approved = True
                    print("  >>> clicked Approve & ship")
                    pg.wait_for_timeout(1500)
                    shot(f"{seq:02d}-approved.png"); seq += 1
                except Exception as e:  # noqa: BLE001
                    print("  (approve click failed:", str(e)[:70], ")")
            if "confirmed in dynatrace grail" in low or "site reliability guardian" in low or "recovery verified" in low:
                recovered = True
                pg.wait_for_timeout(2500)
                shot(f"{seq:02d}-recovered.png"); seq += 1
                break
            if time.time() >= next_shot:
                shot(f"{seq:02d}-streaming.png"); seq += 1
                next_shot = time.time() + 30

        pg.wait_for_timeout(2500)
        shot(f"{seq:02d}-final.png")
        pg.wait_for_timeout(1500)
        ctx.close()
        video = pg.video.path() if pg.video else None
        browser.close()

    print(f"\n=== done === approved={approved} recovered={recovered} shots={len(shots)}")
    if video:
        webm = out / "war-room-real-demo.webm"
        try:
            Path(video).rename(webm)
        except Exception:  # noqa: BLE001
            webm = Path(video)
        mp4 = out / "war-room-real-demo.mp4"
        try:
            subprocess.run(["ffmpeg", "-y", "-i", str(webm), "-vcodec", "libx264",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)],
                           capture_output=True, check=True)
            print(f"  video: {mp4}")
        except Exception as e:  # noqa: BLE001
            print(f"  video: {webm}  (mp4 convert failed: {str(e)[:60]})")
    return 0 if (approved and recovered) else 2


if __name__ == "__main__":
    raise SystemExit(main())
