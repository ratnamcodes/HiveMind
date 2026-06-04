#!/usr/bin/env python3
"""Seed synthetic checkout-service degradation into Dynatrace Grail (logs).

HiveMind step 10 needs *something to investigate*. A fresh Dynatrace trial is
empty, so Detective's `fetch logs | filter contains(content, "checkout")` comes
back with 0 records and the investigation stalls before it can archive anything.
This script ingests ~45 minutes of synthetic checkout logs telling one story: a
deploy (checkout v2.4.1) doubles p99 latency via a slow orders-table query.

Two wiring notes — this is the mirror image of the MCP path:
  * The classic v2 Log Monitoring ingest API lives on the **.live** URL
    (DT_ENVIRONMENT as-is, NOT the .apps form) and authenticates with the
    **classic** DT_API_TOKEN (dt0c01...), NOT the platform token. Same
    `Api-Token` header as verify_keys.py. (SaaS serves this directly — no
    ActiveGate needed — and the logs land in Grail, queryable by the platform
    token's `fetch logs`.)
  * Your DT_API_TOKEN needs the **logs.ingest** scope. If it 403s, add "Ingest
    logs" (logs.ingest) to the token in Dynatrace > Settings > Access tokens.

Timestamps are recent (last ~45 min) on purpose: the ingest APIs reject data
that's too old, and Detective queries relative windows (now()-Nh) anyway, so
recent data is what it actually finds. The "14:32" in the alert is just narrative.

Run from repo root:
    .venv/bin/python scripts/seed_dynatrace.py
Then (after ~30-60s for indexing):
    PYTHONPATH=. .venv/bin/python scripts/test_detective.py
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"

SERVICE = "checkout"
DEPLOY_VERSION = "v2.4.1"
DEPLOY_COMMIT = "a1b2c3d"


def _iso(ts: datetime) -> str:
    """Dynatrace-friendly ISO-8601 UTC with millis, e.g. 2026-06-04T16:30:00.000Z."""
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_logs() -> list[dict]:
    """One coherent incident: healthy baseline -> deploy -> p99 doubles."""
    now = datetime.now(timezone.utc)
    logs: list[dict] = []

    def add(minutes_ago: float, severity: str, content: str, **attrs) -> None:
        logs.append(
            {
                "timestamp": _iso(now - timedelta(minutes=minutes_ago)),
                "severity": severity,
                "content": content,
                "service.name": SERVICE,
                "log.source": "checkout-service",
                **attrs,
            }
        )

    # 1) Healthy baseline (~45..27 min ago): p99 around 240ms.
    for i, m in enumerate(range(45, 26, -3)):
        p99 = 235 + (i % 3) * 8  # 235-251ms
        add(m, "INFO",
            f"checkout request completed ok — p99 latency {p99}ms (baseline healthy)")

    # 2) The deploy that breaks it (~25 min ago).
    add(25, "INFO",
        f"Deploy {SERVICE} {DEPLOY_VERSION} rolled out (commit {DEPLOY_COMMIT})",
        **{"deployment.version": DEPLOY_VERSION, "deployment.commit": DEPLOY_COMMIT})

    # 3) Post-deploy degradation (~24..2 min ago): p99 ~520ms, slow orders query.
    deg = [
        ("ERROR", "checkout p99 latency 520ms — SLO breach (threshold 300ms), ~2x baseline"),
        ("ERROR", "checkout: slow query on orders table took 480ms "
                  "(db.statement: SELECT * FROM orders WHERE customer_id = ?)"),
        ("WARN",  f"checkout latency degraded sharply right after the {DEPLOY_VERSION} deploy"),
        ("ERROR", "checkout p99 latency 535ms — sustained SLO breach"),
        ("ERROR", "checkout: orders-table query 510ms, index appears missing after schema change"),
        ("WARN",  "checkout: request queue backing up, p99 still elevated (~500ms)"),
    ]
    for i, m in enumerate(range(24, 0, -2)):  # 24,22,...,2
        sev, msg = deg[i % len(deg)]
        add(m, sev, msg, **{"deployment.version": DEPLOY_VERSION})

    return logs


def main() -> int:
    env_url = os.environ.get("DT_ENVIRONMENT")
    token = os.environ.get("DT_API_TOKEN")
    if not env_url or not token:
        print(f"{RED}FAIL{RESET}: DT_ENVIRONMENT and DT_API_TOKEN must be set in .env")
        return 2

    # Classic ingest lives on the .live URL — use DT_ENVIRONMENT as-is (NOT .apps).
    base = env_url.rstrip("/").replace(".apps.dynatrace.com", ".live.dynatrace.com")
    url = f"{base}/api/v2/logs/ingest"

    logs = build_logs()
    print(f"{DIM}Ingesting {len(logs)} synthetic {SERVICE} logs -> {url}{RESET}")
    print(f"{DIM}Story: healthy baseline, then {SERVICE} {DEPLOY_VERSION} doubles p99 "
          f"(~240ms -> ~520ms) via a slow orders-table query.{RESET}")

    try:
        r = requests.post(
            url,
            headers={
                "Authorization": f"Api-Token {token}",
                "Content-Type": "application/json",
            },
            json=logs,
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"{RED}FAIL{RESET}: request error: {e}")
        return 1

    if r.status_code in (200, 204):
        print(f"{GREEN}OK{RESET}: ingested {len(logs)} log records into Grail.")
        print(f"{DIM}Give Grail ~30-60s to index, then run:{RESET}")
        print("    PYTHONPATH=. .venv/bin/python scripts/test_detective.py")
        return 0
    if r.status_code in (401, 403):
        print(f"{RED}FAIL{RESET}: HTTP {r.status_code} — DT_API_TOKEN is missing the "
              f"{YELLOW}logs.ingest{RESET} scope (or is invalid).")
        print(f"{DIM}Add 'Ingest logs' (logs.ingest) to the token in Dynatrace > "
              f"Settings > Access tokens, then re-run.{RESET}")
        print(f"{DIM}response: {r.text[:200]}{RESET}")
        return 1
    print(f"{RED}FAIL{RESET}: HTTP {r.status_code} — {r.text[:300]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
