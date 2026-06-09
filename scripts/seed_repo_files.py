#!/usr/bin/env python3
"""Seed the GitLab target repo into a realistic multi-service monorepo.

Each scenario in the redesign needs CodeArch to fix a GENUINELY DIFFERENT real file (this
is what kills the "one bug, three skins" gimmick). This pushes 5 service config files, each
carrying ONE planted, inline-commented bug that the matching scenario's seeded telemetry
points at — so CodeArch (grounded by fetch_repo_tree) reads the right file and opens a
different MR every time. payment-service/config.yaml (the original) is left as-is.

Files pushed (path -> scenario):
  ticketing-service/pricing-rules.yaml   S1  group_stage_toronto.price = 0   (tickets sold free)
  fraud-rules/velocity.yaml              S2  max_txn_per_min = 2             (false declines)
  inventory-service/sync-config.yaml     S3  midwest-mall dropped from regions (silent stockouts)
  pos-gateway/capacity.yaml              S4  pool=20 / timeout=1000ms        (POS fails under surge)
  data-policy/pii-allowlist.yaml         S5  email/customer_id un-gated      (compliance MR target)

Idempotent: one commit with per-file create-or-update actions. Authored by the human token
(GITLAB_TOKEN) so the bot's only commits remain the fixes.

Run:  .venv/bin/python scripts/seed_repo_files.py
"""
from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")
TOKEN = os.getenv("GITLAB_TOKEN")
PROJ = os.getenv("GITLAB_TARGET_PROJECT", "")
PID = urllib.parse.quote(PROJ, safe="")
H = {"PRIVATE-TOKEN": TOKEN}

FILES: dict[str, str] = {
    "README.md": """# acme-commerce — monorepo

The platform behind Acme's ticketing, payments, fraud, in-store POS, inventory and data
pipeline. Services own a config file under their directory. Production telemetry flows to
Dynatrace + Elastic; customer/revenue data lands in BigQuery via Fivetran.

| Service | Path | Owns |
| --- | --- | --- |
| ticketing-service | `ticketing-service/pricing-rules.yaml` | event/tier pricing |
| payment-service | `payment-service/config.yaml` | payment retry/timeout policy |
| fraud-decision | `fraud-rules/velocity.yaml` | real-time fraud/velocity rules |
| inventory-service | `inventory-service/sync-config.yaml` | shelf↔system stock sync |
| pos-gateway | `pos-gateway/capacity.yaml` | in-store tap-to-pay capacity |
| data-policy | `data-policy/pii-allowlist.yaml` | columns allowed to leave the warehouse |

> Changes are reviewed as merge requests. HiveMind's CodeArch agent files fixes here as
> `@HiveMind-bot`; a human approves before merge.
""",

    "ticketing-service/pricing-rules.yaml": """# ticketing-service — tier & per-match pricing (FIFA 2026)
# Owner: ticketing-platform   Deploy: v3.1.0 (tier remap for the group stage on-sale)
service: ticketing-service
currency: USD

tiers:
  category_1: 450
  category_2: 280
  category_3: 150
  hospitality: 2200

# Per-match overrides. price is the amount charged at checkout (USD).
match_overrides:
  group_stage_toronto:
    tier: category_3
    price: 0          # TODO verify — comp tier? (set during the v3.1.0 remap)
  group_stage_la:
    tier: category_3
    price: 150
  group_stage_nyc:
    tier: category_2
    price: 280

# Safety floor: reject any order whose applied price is below this.
# min_price_usd: 25   # FIXME: no floor configured — a 0/null override charges $0 with no error
""",

    "fraud-rules/velocity.yaml": """# fraud-decision — real-time velocity / decline policy
# Owner: risk-platform   Deploy: v5.2 ("tightened for World Cup surge")
service: fraud-decision

rules:
  velocity:
    max_txn_per_min: 2     # tightened for WC surge (was 5) — too strict: trips legit cardholders
    window_seconds: 60
    action: decline        # a declined txn returns HTTP 200 + reason code (no error is logged)
  amount_ceiling_usd: 5000

# whitelist_enterprise: false   # enterprise accounts are still subject to the 2/min cap
""",

    "inventory-service/sync-config.yaml": """# inventory-service — shelf<->system stock reconciliation
# Owner: supply-chain   Deploy: v2.0 (scoped the sync to a region allowlist to cut load)
service: inventory-service

sync:
  interval_minutes: 15
  reconcile: true          # if a region is not reconciled, popular SKUs read "in stock" and never reorder
  region_batch_size: 50
  # v2.0 scoped reconciliation to these regions to cut load.
  # FIXME: is this allowlist complete? A region missing here NEVER reconciles -> silent stockouts.
  regions:
    - northeast-metro
    - south-coast
    - west-bay
    - pacific-nw
    # midwest-mall is NOT in this list since v2.0
""",

    "pos-gateway/capacity.yaml": """# pos-gateway — in-store tap-to-pay gateway capacity
# Owner: in-store-payments   Deploy: v4.4 ("trim idle resources")
service: pos-gateway

capacity:
  connection_pool_size: 20      # trimmed from 200 to cut idle conns — starves under match-day surge
  request_timeout_ms: 1000      # 1s — aborts valid taps once the pool saturates
  max_retries: 3                # retries pile onto the exhausted pool (retry storm)
# autoscale_min_replicas: 2     # no surge headroom configured
""",

    "data-policy/pii-allowlist.yaml": """# data-policy — which warehouse columns may leave toward PUBLIC destinations.
# Enforced by CI (data-policy-check): anything NOT allow-listed must be hashed/redacted at the
# Fivetran layer before export. Compliance: GDPR Art. 5 (minimization) / 25 / 32.
version: 1

allowlist:
  customer_usage:
    - plan
    - monthly_revenue
    - services_used

# pii_columns:            # FIXME: declare + enforce. email / customer_id are currently UN-GATED
#   - customer_id         #        and can flow to public destinations un-redacted.
#   - email
""",
}


def _exists(path: str) -> bool:
    fp = urllib.parse.quote(path, safe="")
    r = requests.get(f"{BASE}/api/v4/projects/{PID}/repository/files/{fp}?ref=main", headers=H, timeout=15)
    return r.status_code == 200


def main() -> int:
    if not (TOKEN and PROJ):
        print("FAIL: GITLAB_TOKEN / GITLAB_TARGET_PROJECT missing")
        return 1
    actions = []
    for path, content in FILES.items():
        actions.append({
            "action": "update" if _exists(path) else "create",
            "file_path": path,
            "content": content,
        })
    payload = {
        "branch": "main",
        "commit_message": "chore: seed acme-commerce monorepo services (ticketing/fraud/inventory/pos/data-policy)",
        "actions": actions,
    }
    r = requests.post(f"{BASE}/api/v4/projects/{PID}/repository/commits", headers=H, json=payload, timeout=30)
    if r.status_code in (200, 201):
        c = r.json()
        print(f"OK: committed {len(actions)} files -> {c.get('short_id')} {c.get('title','')[:60]}")
        for a in actions:
            print(f"   {a['action']:6} {a['file_path']}")
        return 0
    print(f"FAIL: HTTP {r.status_code} — {r.text[:300]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
