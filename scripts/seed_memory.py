"""Smoke-test HiveMind's ColdMemory end-to-end against Atlas auto-embed.

Inserts 12 synthetic incidents covering varied topics (database, k8s, auth,
networking, edge, checkout, etc.) and then runs 4 deliberately paraphrased
recall queries — none of which share many keywords with the matching
summary. The script passes only if the obvious correct incident comes back
as top-1 for every query.

Idempotent: deletes all SEED-* docs before re-seeding so it can be re-run.

Prereqs:
    - `python scripts/provision_atlas.py` has run successfully
    - The autoEmbed Voyage index on `incidents.summary` is READY
    - REDIS_URL and MDB_URI are set (auto-loaded from .env)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from hivemind.memory import ColdMemory, Incident
from hivemind.mongo_client import close_mongo, get_db

load_dotenv()


# --- ANSI colors (match provision_atlas.py style) ---------------------------
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


NOW = datetime.now(timezone.utc)


def _t(minutes_ago: int) -> datetime:
    return NOW - timedelta(minutes=minutes_ago)


SEED_INCIDENTS: list[Incident] = [
    Incident(
        id="SEED-001",
        title="Postgres replica lag spike",
        summary=(
            "Read replica fell behind the primary by 8 minutes during a "
            "morning bulk import job. Replica caught up after we paused the "
            "ingest. Root cause: ingest write rate exceeded replica apply "
            "throughput."
        ),
        services=["postgres"],
        severity="sev2",
        started_at=_t(120),
        resolved_at=_t(70),
        participants=["db_agent"],
    ),
    Incident(
        id="SEED-002",
        title="Kubernetes pod OOM kill loop",
        summary=(
            "API pods were OOM-killed repeatedly after a deploy. New feature "
            "flag SDK held a larger heap than the previous version. Bumped "
            "memory request from 512Mi to 1Gi and pods stabilized."
        ),
        services=["api-gateway", "k8s"],
        severity="sev1",
        started_at=_t(200),
        resolved_at=_t(160),
        participants=["infra_agent"],
    ),
    Incident(
        id="SEED-003",
        title="Auth service rejected all tokens",
        summary=(
            "JWT signing key was rotated without a grace period, so every "
            "in-flight access token was rejected for 14 minutes. Restored "
            "the old key alongside the new one and scheduled a proper "
            "overlap window for the next rotation."
        ),
        services=["auth"],
        severity="sev1",
        started_at=_t(300),
        resolved_at=_t(240),
        participants=["auth_agent"],
    ),
    Incident(
        id="SEED-004",
        title="Redis connection pool exhausted",
        summary=(
            "Worker pool ran out of Redis connections during a traffic surge. "
            "Workers were leaking connections because a code path bypassed "
            "the context manager. Patched the leak and raised pool size."
        ),
        services=["redis", "workers"],
        severity="sev2",
        started_at=_t(400),
        resolved_at=_t(330),
        participants=["infra_agent", "db_agent"],
    ),
    Incident(
        id="SEED-005",
        title="Cluster DNS resolution failures",
        summary=(
            "CoreDNS pods crashed after a config map rollout. All "
            "inter-service DNS lookups inside the cluster failed for "
            "roughly 9 minutes. Rolled back the config map and bounced the "
            "CoreDNS deployment."
        ),
        services=["k8s", "networking"],
        severity="sev1",
        started_at=_t(500),
        resolved_at=_t(450),
        participants=["infra_agent"],
    ),
    Incident(
        id="SEED-006",
        title="Stripe webhooks timing out",
        summary=(
            "External payment provider webhooks began timing out, delaying "
            "order confirmations for paying customers. Added a circuit "
            "breaker plus exponential-backoff retries for the webhook "
            "handler."
        ),
        services=["payments"],
        severity="sev2",
        started_at=_t(600),
        resolved_at=_t(530),
        participants=["payments_agent"],
    ),
    Incident(
        id="SEED-007",
        title="SSL certificate near expiration",
        summary=(
            "Production TLS cert was 6 hours from expiring; ACME auto-renew "
            "had been failing for a week because the HTTP-01 challenge "
            "couldn't reach the origin. Manually issued a new cert and "
            "fixed the challenge routing."
        ),
        services=["edge", "tls"],
        severity="sev2",
        started_at=_t(700),
        resolved_at=_t(660),
        participants=["infra_agent"],
    ),
    Incident(
        id="SEED-008",
        title="Postgres disk space warning",
        summary=(
            "Primary postgres disk reached 92% capacity because WAL segment "
            "archival had silently stopped. Triggered manual WAL cleanup "
            "and provisioned additional storage as a buffer."
        ),
        services=["postgres"],
        severity="sev2",
        started_at=_t(800),
        resolved_at=_t(740),
        participants=["db_agent"],
    ),
    Incident(
        id="SEED-009",
        title="CDN cache purge automation broken",
        summary=(
            "Cloudflare cache invalidation requests were rejected after the "
            "API token was rotated and not pushed to CI. Updated the token "
            "in the CI vault and re-enabled the purge job."
        ),
        services=["cdn", "edge"],
        severity="sev3",
        started_at=_t(900),
        resolved_at=_t(870),
        participants=["edge_agent"],
    ),
    Incident(
        id="SEED-010",
        title="Celery queue backed up",
        summary=(
            "Background worker queue depth hit 50k jobs after a downstream "
            "API slowed to 8s per call. Scaled the worker pool from 4 to 16 "
            "and added a 3s timeout plus retries on the slow API."
        ),
        services=["workers", "queue"],
        severity="sev2",
        started_at=_t(1000),
        resolved_at=_t(920),
        participants=["infra_agent"],
    ),
    Incident(
        id="SEED-011",
        title="Checkout API timeout under load",
        summary=(
            "Checkout API endpoint started timing out under traffic. p99 "
            "latency jumped from 300ms to 8s after a release introducing "
            "per-line tax calculation, so many cart submissions hit the 5s "
            "gateway timeout. Root cause: an N+1 query against the tax "
            "service. Reverted the release and patched the query to batch "
            "lookups."
        ),
        services=["checkout", "api-gateway"],
        severity="sev1",
        started_at=_t(1100),
        resolved_at=_t(1040),
        participants=["payments_agent", "infra_agent"],
    ),
    Incident(
        id="SEED-012",
        title="Checkout payments timing out at peak",
        summary=(
            "Checkout conversion rate fell 18% during the evening peak "
            "because the payment gateway began returning intermittent 504 "
            "timeouts on the final checkout step. Switched the primary "
            "payment route to the secondary provider and added a circuit "
            "breaker around the timing-out endpoint."
        ),
        services=["checkout", "payments"],
        severity="sev1",
        started_at=_t(1200),
        resolved_at=_t(1110),
        participants=["payments_agent"],
    ),
]


# Each tuple = (query phrased differently from the summary, set of acceptable
# top-1 SEED ids). A set is used because some queries (like "checkout timeout")
# could legitimately match more than one seed and we just need a checkout-y one.
QUERIES: list[tuple[str, set[str]]] = [
    ("database replication delay during heavy writes", {"SEED-001"}),
    ("containers killed because of memory limits after release", {"SEED-002"}),
    ("expired authentication credentials rejected after key change", {"SEED-003"}),
    ("checkout timeout", {"SEED-011", "SEED-012"}),
]


async def _wait_for_indexing(
    collection, expected_ids: list[str], timeout_s: int = 30
) -> bool:
    """Poll until every seeded doc is queryable via $vectorSearch, or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    sentinel = expected_ids[0]
    while asyncio.get_event_loop().time() < deadline:
        cursor = collection.aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": "incidents_vector_idx",
                        "path": "summary",
                        "query": "database",
                        "limit": len(expected_ids) + 5,
                        "numCandidates": 100,
                    }
                },
                {"$match": {"_id": sentinel}},
                {"$limit": 1},
            ]
        )
        async for _ in cursor:
            return True
        await asyncio.sleep(1.5)
    return False


async def main() -> int:
    cold = ColdMemory()
    db = get_db()
    incidents = db["incidents"]

    # Idempotent reseed: drop any prior SEED-* docs.
    deleted = await incidents.delete_many({"_id": {"$regex": "^SEED-"}})
    if deleted.deleted_count:
        print(f"{DIM}Cleared {deleted.deleted_count} prior SEED-* docs.{RESET}")

    print(f"{CYAN}Seeding {len(SEED_INCIDENTS)} synthetic incidents…{RESET}")
    for inc in SEED_INCIDENTS:
        await cold.store_incident(inc)
        print(f"  {DIM}+ {inc.id}  {inc.title}{RESET}")

    print(f"\n{CYAN}Waiting for Voyage embeddings to settle…{RESET}")
    ready = await _wait_for_indexing(incidents, [inc.id for inc in SEED_INCIDENTS])
    if not ready:
        print(
            f"{YELLOW}warning: seeded docs not visible to $vectorSearch within "
            f"the timeout; running queries anyway.{RESET}"
        )
    else:
        print(f"{GREEN}  ✓ indexed{RESET}")

    print(f"\n{CYAN}Running {len(QUERIES)} paraphrased recall queries…{RESET}")
    failures = 0
    for query, expected_ids in QUERIES:
        results = await cold.recall(query, k=3)
        if not results:
            print(f"{RED}  ✗ '{query}' → no results{RESET}")
            failures += 1
            continue
        top = results[0]
        ok = top.id in expected_ids
        marker = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {marker} {BOLD}'{query}'{RESET}")
        print(
            f"      top-1: {top.id}  score={top.score:.4f}  "
            f"{DIM}{top.title}{RESET}"
        )
        if not ok:
            expected_str = (
                next(iter(expected_ids))
                if len(expected_ids) == 1
                else f"one of {sorted(expected_ids)}"
            )
            print(f"      {RED}expected: {expected_str}{RESET}")
            failures += 1
        for r in results[1:]:
            print(
                f"      also:  {r.id}  score={r.score:.4f}  "
                f"{DIM}{r.title}{RESET}"
            )

    await close_mongo()

    if failures:
        print(
            f"\n{RED}{BOLD}{failures} query(ies) failed — recall not behaving as "
            f"expected.{RESET}"
        )
        return 1
    print(
        f"\n{GREEN}{BOLD}All {len(QUERIES)} recall queries returned the expected "
        f"top-1 incident.{RESET}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
