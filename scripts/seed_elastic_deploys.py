"""Seed a tiny deployment registry into Elastic for the enrich step.

Creates `hivemind-deploys-000001` as a LOOKUP-mode index (one row per service,
each row = that service's *current* deploy) plus a `hivemind-deploys` alias.
The incident_log_triage workflow can then `LOOKUP JOIN hivemind-deploys ON
service` to blame a specific release for an error spike.

Run once:  python scripts/seed_elastic_deploys.py
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

es = Elasticsearch(
    cloud_id=os.environ["ELASTIC_CLOUD_ID"],
    api_key=os.environ["ELASTIC_ADMIN_API_KEY"],
)

INDEX = "hivemind-deploys-000001"
ALIAS = "hivemind-deploys"

now = datetime.now(timezone.utc)

# One current deployment per service. checkout & payments shipped most recently
# (minutes ago) -> prime suspects when their error rate spikes.
# (service, version, commit_sha, deployed_at, environment, deployed_by, summary)
DEPLOYS = [
    ("checkout",      "v2.8.0",  "a1b9f3c", now - timedelta(minutes=18), "prod",    "rivera", "swap checkout-db connection pool to pgbouncer"),
    ("payments",      "v4.2.1",  "7d2e004", now - timedelta(minutes=42), "prod",    "okoro",  "add retry budget for payment gateway calls"),
    ("cart",          "v1.15.3", "c4419aa", now - timedelta(hours=9),    "prod",    "singh",  "bump cart TTL to 72h"),
    ("inventory",     "v3.0.7",  "e88b120", now - timedelta(hours=26),   "prod",    "chen",   "stock reservation hotfix"),
    ("auth-service",  "v5.1.0",  "0fa7731", now - timedelta(days=2),     "prod",    "rivera", "rotate JWT signing keys"),
    ("api-gateway",   "v2.2.9",  "b3c0d51", now - timedelta(days=3),     "prod",    "okoro",  "raise upstream timeout to 8s"),
    ("notifications", "v1.4.2",  "9912faa", now - timedelta(days=5),     "staging", "chen",   "batch the email digest job"),
    ("search",        "v6.3.1",  "fd5e210", now - timedelta(days=6),     "prod",    "singh",  "reindex search synonyms"),
]


def main() -> None:
    # Clean slate so re-runs don't stack duplicates.
    es.options(ignore_status=404).indices.delete(index=INDEX)
    es.indices.create(
        index=INDEX,
        settings={"index": {"mode": "lookup"}},
        aliases={ALIAS: {}},
        mappings={
            "properties": {
                "service": {"type": "keyword"},
                "version": {"type": "keyword"},
                "commit_sha": {"type": "keyword"},
                "deployed_at": {"type": "date"},
                "environment": {"type": "keyword"},
                "deployed_by": {"type": "keyword"},
                "summary": {"type": "text"},
            }
        },
    )

    actions = [
        {
            "_index": INDEX,
            "_source": {
                "service": service,
                "version": version,
                "commit_sha": commit_sha,
                "deployed_at": deployed_at.isoformat(),
                "environment": environment,
                "deployed_by": deployed_by,
                "summary": summary,
            },
        }
        for (service, version, commit_sha, deployed_at,
             environment, deployed_by, summary) in DEPLOYS
    ]

    success, _ = helpers.bulk(es.options(request_timeout=60), actions)
    es.indices.refresh(index=INDEX)
    print(f"done: indexed {success} deploys into {INDEX} (lookup mode, alias '{ALIAS}')")


if __name__ == "__main__":
    main()
