#!/usr/bin/env python3
"""Seed ALL partners for ONE scenario, coherently, from scripts/scenarios.py.

  .venv/bin/python scripts/seed_scenario.py S2

Applies, for the chosen scenario:
  - Dynatrace Grail logs  (Detective)  — baseline -> deploy marker -> degradation, naming the culprit
  - Elastic logs           (LogDiver)  — the culprit service's error burst + correlated symptoms
  - Elastic deploy registry(LogDiver)  — the culprit deploy as the most-recent row (LookupJoin blame)
  - Atlas prior incident   (Scribe)    — only if the scenario has one (S3 'we've seen this before')
  - BigQuery store_sales   (Liaison)   — only if the scenario needs it (S3)

So Detective, LogDiver and CodeArch all converge on the SAME root cause + the SAME repo file,
and the Reviewer approves instead of escalating on a contradiction.
"""
from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scripts.scenarios import get  # noqa: E402

G, R, Y, D, X = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
LOG_INDEX = "hivemind-logs-000001"
DEP_INDEX = "hivemind-deploys-000001"
DEP_ALIAS = "hivemind-deploys"
OTHER_SERVICES = ["cart", "inventory", "auth-service", "api-gateway", "notifications", "search"]


def _iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------- Dynatrace
def seed_dynatrace(scn: dict) -> None:
    env_url = os.environ["DT_ENVIRONMENT"]
    token = os.environ["DT_API_TOKEN"]
    base = env_url.rstrip("/").replace(".apps.dynatrace.com", ".live.dynatrace.com")
    dt = scn["dynatrace"]
    svc, src, dep = dt["service_name"], dt["log_source"], dt["deploy"]
    now = datetime.now(timezone.utc)
    logs: list[dict] = []

    def add(mins, sev, content, **attrs):
        logs.append({"timestamp": _iso(now - timedelta(minutes=mins)), "severity": sev,
                     "content": content, "service.name": svc, "log.source": src, **attrs})

    # baseline -> deploy -> degradation. We ingest the current scenario's logs at HIGH volume
    # and very recent timestamps so THIS story dominates Detective's Grail query — Grail ingest
    # is append-only, so prior scenarios' logs linger in the window and would otherwise muddle
    # the diagnosis (observed: a stale 'payment-service' story hijacking a fraud incident).
    for i, m in enumerate(range(45, 26, -3)):
        add(m, "INFO", dt["baseline"].replace("${amt}", str(150 + (i % 3) * 30)))
    # Repeat the deploy marker so the implicated release is unmissable.
    for m in (25, 24, 23):
        add(m, "INFO", f"Deploy {svc} {dep['version']} rolled out (commit {dep['commit']}) — {dep['summary']}",
            **{"deployment.version": dep["version"], "deployment.commit": dep["commit"]})
    deg = dt["degradation"]
    k = 0
    for m in range(24, 0, -1):       # every minute in the last 24m
        for _ in range(3):           # 3 lines/min -> ~72 dominant degradation logs
            sev, msg = deg[k % len(deg)]
            add(m, sev, msg, **{"deployment.version": dep["version"]})
            k += 1

    r = requests.post(f"{base}/api/v2/logs/ingest",
                      headers={"Authorization": f"Api-Token {token}", "Content-Type": "application/json"},
                      json=logs, timeout=30)
    ok = r.status_code in (200, 204)
    print(f"  {G if ok else R}Dynatrace{X}: ingested {len(logs)} {svc} logs (HTTP {r.status_code})")


# ---------------------------------------------------------------- Elastic
def _es():
    from elasticsearch import Elasticsearch
    return Elasticsearch(cloud_id=os.environ["ELASTIC_CLOUD_ID"], api_key=os.environ["ELASTIC_ADMIN_API_KEY"])


def seed_elastic_logs(scn: dict, n: int = 5000) -> None:
    from elasticsearch import helpers
    es = _es()
    el = scn["elastic"]
    culprit, corr = el["incident_service"], el["corr_service"]
    inc_msgs, corr_msgs = el["incident_msgs"], el["corr_msgs"]
    now = datetime.now(timezone.utc)
    info = ["request completed in {ms}ms", "health check ok", "GET /api/v1/{svc} 200 in {ms}ms"]
    warn = ["high latency {ms}ms on {svc}", "connection pool at 70% on {svc}"]
    err = ["503 from upstream {svc}", "unhandled exception in {svc}"]

    def doc(ts, service, level, message):
        return {"_index": LOG_INDEX, "_source": {
            "@timestamp": ts.isoformat(), "service": service, "level": level, "message": message,
            "message_embedding": message, "trace_id": uuid.uuid4().hex,
            "kube_pod": f"{service}-{uuid.uuid4().hex[:6]}", "kube_namespace": "prod"}}

    def gen():
        for _ in range(n):
            ts = now - timedelta(seconds=random.randint(0, 6 * 3600))
            recent = ts > now - timedelta(minutes=30)
            roll = random.random()
            if recent and roll < 0.40:
                yield doc(ts, culprit, "ERROR", random.choice(inc_msgs))
            elif recent and roll < 0.52:
                yield doc(ts, corr, random.choice(["WARN", "ERROR"]), random.choice(corr_msgs))
            else:
                svc = random.choice(OTHER_SERVICES + [culprit, corr])
                r = random.random()
                lvl, pool = ("INFO", info) if r < 0.8 else (("WARN", warn) if r < 0.93 else ("ERROR", err))
                yield doc(ts, svc, lvl, random.choice(pool).format(ms=random.randint(5, 800), svc=svc))

    es.options(ignore_status=404).indices.delete(index=LOG_INDEX)
    es.options(request_timeout=120).indices.create(index=LOG_INDEX, mappings={"properties": {
        "@timestamp": {"type": "date"}, "service": {"type": "keyword"}, "level": {"type": "keyword"},
        "message": {"type": "text"}, "message_embedding": {"type": "semantic_text"},
        "trace_id": {"type": "keyword"}, "kube_pod": {"type": "keyword"}, "kube_namespace": {"type": "keyword"}}})
    ok, _ = helpers.bulk(es.options(request_timeout=120), gen(), chunk_size=100)
    es.indices.refresh(index=LOG_INDEX)
    print(f"  {G}Elastic logs{X}: {ok} docs; culprit='{culprit}' corr='{corr}'")


def seed_elastic_deploys(scn: dict) -> None:
    from elasticsearch import helpers
    es = _es()
    now = datetime.now(timezone.utc)
    row = scn["elastic"]["deploy_row"]
    others = [
        ("checkout", "v2.8.0", "a1b9f3c", 240, "prod", "rivera", "add structured request logging"),
        ("payment-service", "v2.4.0", "a1b2c30", 600, "prod", "okoro", "baseline retry policy"),
        ("auth-service", "v5.1.0", "0fa7731", 2880, "prod", "rivera", "rotate JWT keys"),
        ("search", "v6.3.1", "fd5e210", 8640, "prod", "singh", "reindex synonyms"),
    ]
    deploys = [(row["service"], row["version"], row["commit"], row["minutes_ago"], row["environment"],
                row["deployed_by"], row["summary"])] + [o for o in others if o[0] != row["service"]]
    es.options(ignore_status=404).indices.delete(index=DEP_INDEX)
    es.indices.create(index=DEP_INDEX, settings={"index": {"mode": "lookup"}}, aliases={DEP_ALIAS: {}},
                      mappings={"properties": {"service": {"type": "keyword"}, "version": {"type": "keyword"},
                                "commit_sha": {"type": "keyword"}, "deployed_at": {"type": "date"},
                                "environment": {"type": "keyword"}, "deployed_by": {"type": "keyword"},
                                "summary": {"type": "text"}}})
    actions = [{"_index": DEP_INDEX, "_source": {"service": s, "version": v, "commit_sha": c,
                "deployed_at": (now - timedelta(minutes=m)).isoformat(), "environment": e,
                "deployed_by": by, "summary": sm}} for (s, v, c, m, e, by, sm) in deploys]
    ok, _ = helpers.bulk(es.options(request_timeout=60), actions)
    es.indices.refresh(index=DEP_INDEX)
    print(f"  {G}Elastic deploys{X}: {ok} rows; culprit deploy = {row['service']} {row['version']} ({row['minutes_ago']}m ago)")


# ---------------------------------------------------------------- Atlas + BigQuery
def seed_atlas_prior(scn: dict) -> None:
    prior = scn.get("atlas_prior_incident")
    if not prior:
        return
    import asyncio
    from hivemind.memory import ColdMemory, Incident

    async def _store():
        inc = Incident(id=prior["id"], title=prior["title"], summary=prior["summary"],
                       services=prior["services"], severity=prior["severity"],
                       started_at=datetime.now(timezone.utc) - timedelta(days=212),
                       mr_url=None, participants=["detective", "log_diver", "code_arch"])
        await ColdMemory().store_incident(inc)
    asyncio.run(_store())
    print(f"  {G}Atlas{X}: seeded prior incident '{prior['id']}' for Scribe recall")


def seed_bq_store_sales(scn: dict) -> None:
    if not scn["bigquery"].get("store_sales"):
        return
    try:
        from google.cloud import bigquery
    except ImportError:
        print(f"  {Y}BigQuery store_sales skipped (bigquery not installed){X}")
        return
    proj = os.environ.get("GOOGLE_CLOUD_PROJECT", "hivemind-hackathon")
    client = bigquery.Client(project=proj)
    table_id = f"{proj}.google_sheets.store_sales"
    schema = [bigquery.SchemaField(n, t) for n, t in
              [("region", "STRING"), ("store_id", "STRING"), ("week", "STRING"),
               ("revenue", "FLOAT"), ("footfall", "INTEGER")]]
    # build 2 weeks for 5 regions; midwest-mall drops 22% this week, footfall flat
    regions = {"northeast-metro": 1.0, "south-coast": 1.0, "west-bay": 1.0, "pacific-nw": 1.0, "midwest-mall": 0.78}
    rows = []
    for region, factor in regions.items():
        base_rev = 120000.0
        rows.append({"region": region, "store_id": f"{region}-01", "week": "2026-W22",
                     "revenue": round(base_rev, 2), "footfall": 14000})
        rows.append({"region": region, "store_id": f"{region}-01", "week": "2026-W23",
                     "revenue": round(base_rev * factor, 2), "footfall": 13950})
    client.delete_table(table_id, not_found_ok=True)
    table = client.create_table(bigquery.Table(table_id, schema=schema))
    client.insert_rows(table, rows)
    print(f"  {G}BigQuery{X}: store_sales table ({len(rows)} rows); midwest-mall -22% WoW, footfall flat")


def main() -> int:
    if len(sys.argv) < 2:
        from scripts.scenarios import SCENARIOS
        print("usage: seed_scenario.py <S1|S2|S3|S4|S5>")
        for s in SCENARIOS:
            print(f"   {s['id']}  {s['title']}  -> fixes {s['code_target']}")
        return 1
    scn = get(sys.argv[1])
    print(f"\n{D}seeding {scn['id']} — {scn['title']}  (fix lands on {scn['code_target']}){X}")
    seed_dynatrace(scn)
    seed_elastic_logs(scn)
    seed_elastic_deploys(scn)
    seed_atlas_prior(scn)
    seed_bq_store_sales(scn)
    print(f"{G}done.{X} Grail needs ~30-60s to index; then fire the scenario.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
