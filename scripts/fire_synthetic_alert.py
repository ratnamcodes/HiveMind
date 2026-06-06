#!/usr/bin/env python3
"""Fire a synthetic Dynatrace alert at the local webhook to drive a live war-room run.

POSTs a Dynatrace-shaped problem payload (with a valid HMAC signature) to
/api/incoming/dynatrace. The backend validates the signature, materializes an incident
channel, and spawns the orchestrator — watch it stream in the browser (web/ at :3000).

Signature: HMAC-SHA256 over the exact request body, keyed by DT_WEBHOOK_SECRET (falls
back to HMAC_SECRET), sent in the X-DT-Signature header.

Run:
    .venv/bin/python scripts/fire_synthetic_alert.py --service checkout --severity sev2
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import uuid

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

SECRET = os.getenv("DT_WEBHOOK_SECRET") or os.getenv("HMAC_SECRET", "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fire a synthetic Dynatrace alert.")
    ap.add_argument("--service", default="checkout")
    ap.add_argument("--severity", default="sev2", choices=["sev1", "sev2", "sev3"])
    ap.add_argument("--title", default=None)
    ap.add_argument("--problem-id", default=None)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--user", default="hivemind")
    args = ap.parse_args()

    if not SECRET:
        print("FAIL: set DT_WEBHOOK_SECRET (or HMAC_SECRET) in .env")
        return 1

    problem_id = args.problem_id or f"P-{uuid.uuid4().hex[:6]}"
    title = args.title or f"{args.service} p99 latency degraded after deploy"
    body = {
        "problem_id": problem_id,
        "service": args.service,
        "severity": args.severity,
        "title": title,
    }
    # Sign the EXACT bytes we send (re-serializing server-side would change the digest).
    raw = json.dumps(body).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()

    url = f"{args.url.rstrip('/')}/api/incoming/dynatrace?user={args.user}"
    print(f"POST {url}\n  body: {body}")
    try:
        r = requests.post(
            url,
            data=raw,
            headers={"Content-Type": "application/json", "X-DT-Signature": sig},
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"FAIL: request error: {e}")
        return 1

    print(f"  HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code == 200:
        print("\nOK — watch the channel materialize + stream at http://localhost:3000")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
