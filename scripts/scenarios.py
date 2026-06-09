"""HiveMind scenario registry — the single source of truth for the 5 distinct demos.

Each scenario is a coherent cross-system story: the SAME root cause shows up in Dynatrace
Grail (Detective), Elastic logs+deploys (LogDiver), the GitLab monorepo file CodeArch fixes,
and BigQuery customer/revenue impact (Liaison). Driven by:
  - scripts/seed_scenario.py  (applies dynatrace + elastic + atlas seeds per scenario)
  - scripts/demo.py / verify_demo_e2e.py  (fires the alert + verifies the run)

COHERENCE RULES (so a savvy audience can't poke holes):
  - alert.service is what the webhook stamps + what Liaison uses for blast radius, so it must
    be a service present in BigQuery customer_usage (payment-service / checkout) OR have a
    custom table (S1/S3). The CODE fix can still land on a different file: CodeArch picks the
    repo path from the root-cause hypothesis, which the Dynatrace/Elastic seeds make name the
    culprit (e.g. "fraud-rules velocity threshold") -> code_target.
  - dynatrace.degradation lines must NAME the culprit deploy + the exact knob in code_target.
  - elastic.deploy_row must be the most-recent deploy on the noisiest service (LookupJoin blame).
"""
from __future__ import annotations

# Each scenario: metadata + alert + code_target + the seed bundle for each partner.
SCENARIOS: list[dict] = [
    {
        "id": "S1",
        "domain": "2026 World Cup",
        "title": "World Cup on-sale is selling tickets for $0",
        "headline": "312 confirmed orders, $0.00 recognized revenue — no error thrown",
        "alert": {
            "service": "checkout",  # Liaison grounds on checkout customers; fix lands on ticketing file
            "severity": "sev1",
            "title": "World Cup group-stage on-sale (Toronto): 312 orders CONFIRMED in 8 min but recognized revenue is $0.00 — orders succeed, no exception is thrown; finance flagged the $0 gap.",
        },
        "code_target": "ticketing-service/pricing-rules.yaml",
        "dynatrace": {
            "service_name": "ticketing-service",
            "log_source": "ticketing-service",
            "deploy": {"version": "v3.1.0", "commit": "3a1c0de",
                       "summary": "tier remap for the group-stage on-sale (ticketing-service/pricing-rules.yaml)"},
            "degradation": [
                ("ERROR", "entitlement granted with price_applied=0.00 for match=group_stage_toronto (HTTP 200, no exception)"),
                ("ERROR", "order CONFIRMED with recognized_revenue=0.00 — pricing-rules returned $0 for the Toronto tier"),
                ("WARN",  "312 confirmed Toronto orders in 8m, total recognized revenue $0.00 — pricing anomaly, not an outage"),
                ("ERROR", "pricing-rules v3.1.0: match_overrides.group_stage_toronto.price=0 and no min_price_usd floor configured"),
                ("ERROR", "tier map: category_3 should be $150 but group_stage_toronto override charged $0"),
                ("WARN",  "checkout success rate normal; the loss is silent revenue leakage from ticketing-service pricing"),
            ],
            "baseline": "ticketing checkout ok — group_stage order recognized ${amt} (healthy pre-v3.1.0)",
        },
        "elastic": {
            "incident_service": "ticketing-service",
            "incident_msgs": [
                "price_applied=0.00 on confirmed order — group_stage_toronto tier mapped to $0 (pricing-rules v3.1.0)",
                "recognized_revenue=0.00 for a CONFIRMED ticket order — no min_price_usd floor",
                "tier remap v3.1.0 set match_overrides.group_stage_toronto.price=0",
                "ticketing-service: $0 entitlement granted, HTTP 200, zero exceptions",
            ],
            "corr_service": "checkout",
            "corr_msgs": [
                "checkout completed order but ticketing-service recognized $0.00 revenue",
                "checkout success normal; downstream ticketing pricing returned $0",
            ],
            "deploy_row": {"service": "ticketing-service", "version": "v3.1.0", "commit": "3a1c0de",
                           "minutes_ago": 19, "environment": "prod", "deployed_by": "okoro",
                           "summary": "tier remap for group-stage on-sale — introduced group_stage_toronto.price=0"},
        },
        "bigquery": {"services_match": "checkout", "impact_hint": "fans/accounts whose Toronto orders were mispriced to $0"},
        "atlas_prior_incident": None,
        "code_fix": "Restore match_overrides.group_stage_toronto.price from 0 to 150 (category_3) and add a min_price_usd floor.",
        "aha_line": "One alert during the on-sale spike — 90 seconds later the crew found a pricing deploy was giving World Cup tickets away free, named the ~$46,800 on the line, and drafted the fix, then asked a human whether to honor the freebies.",
        "mom_test": "The website was accidentally selling World Cup tickets for $0 and no alarm went off — the sales just went through. The AI crew noticed the money wasn't coming in, found the typo, and asked a person before fixing it.",
        "hitl": ["P1: approve the price-correction MR (or edit the price)", "Business call: honor or void the already-confirmed $0 tickets"],
    },
    {
        "id": "S2",
        "domain": "Financial Services",
        "title": "A 'fraud' decline storm is actually strangling real customers",
        "headline": "Approval rate down 4 pts, declines +38% — every decline is a clean HTTP 200",
        "alert": {
            "service": "payment-service",
            "severity": "sev1",
            "title": "Card-auth approval rate dropped 4 points overnight and declines are up 38% — 3 enterprise customers escalated. Every declined transaction returned HTTP 200 (no error logged); suspected the overnight fraud-rules deploy.",
        },
        "code_target": "fraud-rules/velocity.yaml",
        "dynatrace": {
            "service_name": "fraud-decision",
            "log_source": "fraud-decision",
            "deploy": {"version": "v5.2", "commit": "f9a2b10",
                       "summary": "fraud-rules velocity tightened for the World Cup surge (fraud-rules/velocity.yaml)"},
            "degradation": [
                ("ERROR", "txn DECLINED reason=velocity_exceeded (HTTP 200) — fraud-rules v5.2 max_txn_per_min=2"),
                ("WARN",  "decline volume +38% vs 24h baseline; approval rate 96% -> 92% right after the fraud-rules deploy"),
                ("ERROR", "legit cardholder declined: 3rd txn in 60s tripped velocity rule (threshold was 5, now 2)"),
                ("ERROR", "fraud-rules/velocity.yaml max_txn_per_min lowered 5 -> 2; enterprise accounts not whitelisted"),
                ("WARN",  "no error/exception on declines — they are successful HTTP 200 responses, invisible to error alerts"),
                ("ERROR", "false-decline pattern concentrated on high-frequency enterprise payers"),
            ],
            "baseline": "fraud-decision ok — approval rate ~96%, declines steady (healthy pre-v5.2)",
        },
        "elastic": {
            "incident_service": "fraud-decision",
            "incident_msgs": [
                "DECLINE reason=velocity_exceeded — fraud-rules v5.2 max_txn_per_min=2 (was 5)",
                "legitimate payment declined: velocity threshold too strict after the fraud-rules deploy",
                "approval rate dropped 4 points; declines +38% post fraud-rules v5.2",
                "enterprise account declined on 3rd txn/min — no enterprise whitelist in velocity.yaml",
            ],
            "corr_service": "payment-service",
            "corr_msgs": [
                "payment-service auth declined downstream of fraud-decision velocity rule",
                "payment-service success rate dipping — declines are HTTP 200, not errors",
            ],
            "deploy_row": {"service": "fraud-decision", "version": "v5.2", "commit": "f9a2b10",
                           "minutes_ago": 25, "environment": "prod", "deployed_by": "okoro",
                           "summary": "tightened velocity max_txn_per_min 5 -> 2 for WC surge (false declines)"},
        },
        "bigquery": {"services_match": "payment-service", "impact_hint": "enterprise payers being falsely declined; revenue at risk"},
        "atlas_prior_incident": None,
        "code_fix": "Raise fraud-rules/velocity.yaml max_txn_per_min 2 -> 5 and add whitelist_enterprise: true.",
        "aha_line": "A 'fraud' decline storm was actually the fraud filter strangling real paying customers — the crew named the 4 Enterprise accounts and the $20,600/mo, scrubbed their card data out of the export, and let a human make the fraud-vs-revenue trade-off.",
        "mom_test": "The bank's anti-fraud setting got too strict and blocked real customers' cards. The AI crew worked out which big customers and how much money was walking away, deleted their private card details from the report, and asked a human how much to loosen it.",
        "hitl": ["P2 (marquee): approve GDPR redaction of customer_id/email before the public MR",
                 "P1 (risk call): loosen velocity 2 -> 5? recovers ~$20,600/mo but raises fraud exposure"],
        "liaison_context": "REDACT_PII: the decline-log export references customer_id/email PII and this fix becomes a PUBLIC GitLab MR — redact (hash) the PII columns before synthesis leaks them.",
    },
    {
        "id": "S3",
        "domain": "Brick-and-Mortar Retail",
        "title": "One mall region quietly loses 22% revenue with flat footfall",
        "headline": "Midwest-Mall revenue down 22% WoW, footfall flat, POS uptime normal — nothing is 'down'",
        "alert": {
            "service": "checkout",
            "severity": "sev2",
            "title": "Store region 'Midwest-Mall': revenue down 22% week-over-week while footfall is flat and POS uptime is normal. No exception anywhere — a business mystery, not an outage. Finance asked HiveMind to find out why.",
        },
        "code_target": "inventory-service/sync-config.yaml",
        "dynatrace": {
            "service_name": "inventory-service",
            "log_source": "inventory-sync",
            "deploy": {"version": "v2.0", "commit": "5c7d011",
                       "summary": "inventory sync scoped to a region allowlist to cut load (inventory-service/sync-config.yaml)"},
            "degradation": [
                ("WARN",  "inventory-sync: last successful reconciliation for region=midwest-mall was 31h ago"),
                ("ERROR", "region=midwest-mall not in sync allowlist since v2.0 — shelves never reconcile, popular SKUs read 'in stock' and never reorder"),
                ("WARN",  "phantom stock: midwest-mall SKUs show in-stock in system but are empty on shelf (silent stockouts)"),
                ("ERROR", "inventory-service/sync-config.yaml regions allowlist missing 'midwest-mall' (added region scoping in v2.0)"),
                ("WARN",  "other regions (northeast-metro, south-coast, west-bay, pacific-nw) reconciling normally"),
                ("WARN",  "no outage, no error rate — revenue regression is downstream of un-reordered stockouts"),
            ],
            "baseline": "inventory-sync ok — all regions reconciled within 15m (healthy pre-v2.0 scoping)",
        },
        "elastic": {
            "incident_service": "inventory-service",
            "incident_msgs": [
                "region=midwest-mall excluded from sync allowlist since inventory-service v2.0",
                "midwest-mall last reconcile 31h ago — SKUs not reordered, phantom in-stock",
                "sync-config.yaml regions list does not contain midwest-mall (v2.0 region scoping)",
                "popular SKUs stocked out on shelf but flagged in-stock in system for midwest-mall",
            ],
            "corr_service": "checkout",
            "corr_msgs": [
                "checkout uptime normal in midwest-mall; revenue per visit collapsed (empty shelves)",
                "footfall flat for midwest-mall; basket value down on stocked-out SKUs",
            ],
            "deploy_row": {"service": "inventory-service", "version": "v2.0", "commit": "5c7d011",
                           "minutes_ago": 28, "environment": "prod", "deployed_by": "chen",
                           "summary": "scoped sync to a region allowlist to cut load — dropped midwest-mall"},
        },
        "bigquery": {"services_match": "checkout", "impact_hint": "Midwest-Mall stores losing basket revenue from stockouts",
                     "store_sales": True},
        "atlas_prior_incident": {
            "id": "INC-2025-1108-region-sync",
            "title": "Region-filter typo broke EU-West inventory sync (Nov 2025)",
            "summary": "A v1.7 inventory-sync deploy scoped reconciliation to a region allowlist and a typo'd region code silently excluded EU-West; shelves stopped reordering and revenue dipped ~18% before anyone noticed. Fix: corrected the region code + added a regions completeness assertion. Lesson: never scope a sync to an allowlist without a '*'/completeness guard.",
            "services": ["inventory-service"], "severity": "sev2",
        },
        "code_fix": "Add 'midwest-mall' back to inventory-service/sync-config.yaml regions allowlist (and add a completeness assertion).",
        "aha_line": "No alarm went off — one mall region was quietly making less money while foot traffic stayed normal. The crew proved a broken inventory sync was hiding empty shelves as 'in stock', shipped the one-line fix, and even remembered the last time this exact mistake happened.",
        "mom_test": "One mall's shops were slowly losing sales but the same number of people walked in. The AI crew played detective across the systems, found the warehouse computer had quietly stopped updating that store's shelves — and recognized it had seen this exact bug before.",
        "hitl": ["S2: confirm the diagnosis thread (fix the sync vs look at pricing/staffing)",
                 "P1: approve the sync-config MR; optionally trigger a manual re-sync now"],
    },
    {
        "id": "S4",
        "domain": "2026 World Cup",
        "title": "Match-day POS fails at kickoff — roll back or patch?",
        "headline": "In-store tap-to-pay timing out across tenants at kickoff; $/minute bleeding",
        "alert": {
            "service": "checkout",
            "severity": "sev1",
            "title": "Match-day surge: in-store tap-to-pay timing out across mall tenants as the crowd hits at kickoff — registers retrying and aborting valid taps. Only happens under load (~5x traffic). Revenue bleeding by the minute.",
        },
        "code_target": "pos-gateway/capacity.yaml",
        "dynatrace": {
            "service_name": "pos-gateway",
            "log_source": "pos-gateway",
            "deploy": {"version": "v4.4", "commit": "8b2e077",
                       "summary": "pos-gateway 'trim idle resources' lowered the pool/timeout (pos-gateway/capacity.yaml)"},
            "degradation": [
                ("ERROR", "pos-gateway connection_pool exhausted: max 20 reached under match-day surge (pos-gateway v4.4)"),
                ("ERROR", "tap-to-pay request timed out after 1000ms — pool saturated, valid taps aborted"),
                ("WARN",  "p99 latency spikes ONLY under surge (~5x traffic); off-peak is healthy — load-dependent"),
                ("ERROR", "pos-gateway/capacity.yaml connection_pool_size=20 and request_timeout_ms=1000 are too low for kickoff load"),
                ("WARN",  "retry storm: max_retries=3 piling onto the exhausted pool, amplifying the saturation"),
                ("ERROR", "valid taps declined at the till during the busiest minute — revenue per minute at risk"),
            ],
            "baseline": "pos-gateway ok — pool healthy, p99 ~120ms off-peak (healthy pre-v4.4 surge)",
        },
        "elastic": {
            "incident_service": "pos-gateway",
            "incident_msgs": [
                "connection_pool_size=20 exhausted under surge — pos-gateway v4.4 trimmed it from 200",
                "request_timeout_ms=1000 aborting valid taps when the pool saturates",
                "retry storm on pos-gateway: 3 retries onto an exhausted pool",
                "surge traffic ~5x baseline at kickoff — capacity.yaml has no headroom",
            ],
            "corr_service": "checkout",
            "corr_msgs": [
                "in-store checkout aborts at the till — blocked on pos-gateway timeouts",
                "checkout success collapses only during the surge window",
            ],
            "deploy_row": {"service": "pos-gateway", "version": "v4.4", "commit": "8b2e077",
                           "minutes_ago": 35, "environment": "prod", "deployed_by": "rivera",
                           "summary": "trim idle resources — lowered connection_pool_size 200 -> 20 and timeout to 1s"},
        },
        "bigquery": {"services_match": "checkout", "impact_hint": "$/minute bleeding at the till during the surge"},
        "atlas_prior_incident": None,
        "code_fix": "Patch-forward: raise pos-gateway/capacity.yaml connection_pool_size 20 -> 200 and request_timeout_ms -> 5000. (Or roll back the v4.4 deploy.)",
        "aha_line": "At the busiest minute of match day two AI specialists disagreed — one wanted to roll back, one found the real cap in the config — and a human broke the tie in one click while revenue bled by the minute.",
        "mom_test": "During the World Cup rush the card machines started failing. Two AI experts argued about the fix, the system showed how much money was lost every minute, and a person picked the winner — solved in minutes, not hours.",
        "hitl": ["P3 (marquee): rollback-vs-patch fork, costed live ($/min)",
                 "S2: which specialist to trust (LogDiver blames the surge, CodeArch blames the config)"],
    },
    {
        "id": "S5",
        "domain": "Research/Analysis",
        "title": "Proactive compliance sweep catches PII about to leak",
        "headline": "No alert — a scheduled sweep finds un-redacted customer PII heading to a public destination",
        "alert": {
            "service": "payment-service",
            "severity": "sev3",
            "title": "Scheduled compliance sweep: a new analytics export is syncing raw customer_id/email toward a destination that feeds a public dashboard — un-redacted PII about to leave the warehouse. No incident fired; this is proactive.",
        },
        "code_target": "data-policy/pii-allowlist.yaml",
        "dynatrace": {
            "service_name": "data-pipeline",
            "log_source": "data-policy",
            "deploy": {"version": "sweep", "commit": "00c0de0",
                       "summary": "scheduled data-policy compliance sweep (no deploy)"},
            "degradation": [
                ("WARN",  "data-policy sweep: customer_usage export includes un-gated columns customer_id, email (PII)"),
                ("ERROR", "PII columns customer_id/email are NOT in data-policy/pii-allowlist.yaml and can reach a public destination"),
                ("WARN",  "GDPR exposure: minimization (Art. 5) requires these be hashed/redacted before export"),
                ("WARN",  "no allowlist enforcement (CI check) exists yet for the customer_usage export"),
            ],
            "baseline": "data-policy sweep nominal — allow-listed columns only (healthy)",
        },
        "elastic": {
            "incident_service": "data-pipeline",
            "incident_msgs": [
                "customer_usage export carries customer_id/email un-redacted toward a public destination",
                "pii-allowlist.yaml does not declare PII columns — no CI enforcement",
                "Fivetran connector syncing raw PII columns ahead of a public dashboard feed",
            ],
            "corr_service": "data-policy",
            "corr_msgs": [
                "data-policy-check CI stub missing — nothing blocks PII export",
            ],
            "deploy_row": {"service": "data-pipeline", "version": "v1.3", "commit": "00c0de0",
                           "minutes_ago": 40, "environment": "prod", "deployed_by": "chen",
                           "summary": "added analytics export connector (no PII allowlist enforcement)"},
        },
        "bigquery": {"services_match": "payment-service", "impact_hint": "customers whose PII (email/customer_id) is in the export"},
        "atlas_prior_incident": None,
        "code_fix": "Add the pii_columns (customer_id, email) declaration + a CI data-policy-check stub to data-policy/pii-allowlist.yaml.",
        "aha_line": "Nothing broke — the crew proactively caught customer PII about to leak into a public dataset, redacted it across the live data pipeline, and opened the compliance fix before any regulator could, then required a human to sign off because that's the law.",
        "mom_test": "Before anything went wrong, the AI team went looking for problems, found customers' private emails about to end up somewhere public, hid them everywhere they flowed, and wrote up the fix — but a real person had to approve it, because privacy law requires a human.",
        "hitl": ["P2 (the whole point): human compliance sign-off on the PII redaction",
                 "Approve provisioning the new connector"],
        "liaison_context": "REDACT_PII: scan customer_usage for PII columns (customer_id, email) about to leave the warehouse and redact them via Fivetran before the public export.",
    },
]

BY_ID = {s["id"]: s for s in SCENARIOS}


def get(scenario_id: str) -> dict:
    sid = scenario_id.upper()
    if sid not in BY_ID:
        raise KeyError(f"unknown scenario {scenario_id}; have {list(BY_ID)}")
    return BY_ID[sid]
