"""Seed synthetic Kubernetes logs into Elastic for LogDiver to search.

Builds the `hivemind-logs-000001` index with a hybrid mapping and fills it
with ~5,000 synthetic log lines, including a deliberate burst of "connection
refused to checkout-db" ERRORs on the `checkout` service in the last 30 minutes
so anomaly detection has a real anomaly to find — one the recent checkout
pgbouncer deploy neatly explains.
"""
from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

es = Elasticsearch(
    cloud_id=os.environ["ELASTIC_CLOUD_ID"],
    api_key=os.environ["ELASTIC_ADMIN_API_KEY"],
)

INDEX = "hivemind-logs-000001"
N_LOGS = 5_000

SERVICES = ["checkout", "payments", "cart", "inventory",
            "auth-service", "api-gateway", "notifications", "search"]
NAMESPACES = ["prod", "prod", "prod", "staging"]  # weighted toward prod

INFO_MSGS = [
    "request completed in {ms}ms",
    "health check ok",
    "cache hit for key user:{n}",
    "processed {n} items from queue",
    "GET /api/v1/{svc} 200 in {ms}ms",
]
WARN_MSGS = [
    "high latency {ms}ms on upstream {svc}",
    "connection pool at 85% capacity",
    "retrying request to {svc} (attempt 2)",
    "deprecated endpoint /v0/{svc} used",
]
ERROR_MSGS = [
    "NullPointerException in {svc}Handler.process",
    "503 Service Unavailable from upstream {svc}",
    "unhandled exception: invalid state",
    "connection timeout to {svc}-db after 5000ms",
]
INCIDENT_SERVICE = "checkout"
INCIDENT_MSGS = [
    "connection refused to checkout-db after 5000ms",
    "could not connect to checkout-db: connection refused",
    "checkout-db pool exhausted: max_client_conn reached (pgbouncer)",
    "circuit breaker OPEN for checkout-db",
    "503 Service Unavailable from checkout-db",
]


def _doc(ts: datetime, service: str, level: str, message: str) -> dict:
    return {
        "@timestamp": ts.isoformat(),
        "service": service,
        "level": level,
        "message": message,
        "message_embedding": message,  # semantic_text auto-embeds this
        "trace_id": uuid.uuid4().hex,
        "kube_pod": f"{service}-{uuid.uuid4().hex[:6]}",
        "kube_namespace": random.choice(NAMESPACES),
    }


def gen_actions():
    now = datetime.now(timezone.utc)
    for _ in range(N_LOGS):
        ts = now - timedelta(seconds=random.randint(0, 6 * 3600))
        recent = ts > now - timedelta(minutes=30)

        if recent and random.random() < 0.4:
            # checkout is melting down in the last half hour
            service, level = INCIDENT_SERVICE, "ERROR"
            message = random.choice(INCIDENT_MSGS)
        else:
            service = random.choice(SERVICES)
            roll = random.random()
            if roll < 0.80:
                level, pool = "INFO", INFO_MSGS
            elif roll < 0.93:
                level, pool = "WARN", WARN_MSGS
            else:
                level, pool = "ERROR", ERROR_MSGS
            message = random.choice(pool).format(
                ms=random.randint(5, 800),
                n=random.randint(1, 9999),
                svc=service,
            )

        yield {"_index": INDEX, "_source": _doc(ts, service, level, message)}


def main() -> None:
    # Clean slate so re-runs don't stack duplicates.
    es.options(ignore_status=404).indices.delete(index=INDEX)
    es.options(request_timeout=120).indices.create(
        index=INDEX,
        mappings={
            "properties": {
                "@timestamp": {"type": "date"},
                "service": {"type": "keyword"},
                "level": {"type": "keyword"},
                "message": {"type": "text"},
                "message_embedding": {"type": "semantic_text"},
                "trace_id": {"type": "keyword"},
                "kube_pod": {"type": "keyword"},
                "kube_namespace": {"type": "keyword"},
            }
        },
    )
    print(f"created {INDEX}; indexing {N_LOGS} logs — ELSER may take a few minutes...")

    success, _ = helpers.bulk(
        es.options(request_timeout=120), gen_actions(), chunk_size=100
    )
    es.indices.refresh(index=INDEX)
    count = es.count(index=INDEX)["count"]
    print(f"done: indexed {success} docs; {count} now searchable in {INDEX}")


if __name__ == "__main__":
    main()
