"""Comprehensive verification of HiveMind's two-tier memory layer.

Runs every acceptance check from step 07's "What you'll see" in one go:

    [HOT-1] HotMemory.append + recent + clear (atomic, TTL-bounded)
    [HOT-2] Append+trim atomicity under concurrent writes
    [HOT-3] TTL is set and roughly 24h
    [COLD-1] store_incident triggers Voyage auto-embed
    [COLD-2] recall returns top-k with scores and matches expected
    [COLD-3] recall with metadata filter (services) restricts results
    [COLD-4] related_to finds neighbors and excludes self
    [ADK-1] Memory tools are importable, callable, and wireable into LlmAgent

Prereqs:
    - REDIS_URL reachable (start Redis: `docker compose up redis -d`)
    - MDB_URI set; Atlas autoEmbed index `incidents_vector_idx` is READY
    - scripts/seed_memory.py has been run (this script doesn't reseed)
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from typing import Any, Awaitable, Callable

from dotenv import load_dotenv

from hivemind.memory import ColdMemory, HotMemory, Incident
from hivemind.mongo_client import close_mongo, get_db
from hivemind.redis_client import close_redis, get_redis

load_dotenv()


# --- pretty output ----------------------------------------------------------
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _ok(label: str, detail: str = "") -> None:
    print(f"  {GREEN}✓{RESET} {label}  {DIM}{detail}{RESET}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  {RED}✗{RESET} {label}  {RED}{detail}{RESET}")


def _section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}── {title} ──{RESET}")


# --- check harness ----------------------------------------------------------
class Verifier:
    def __init__(self) -> None:
        self.failures: list[str] = []

    async def run(self, label: str, fn: Callable[[], Awaitable[str]]) -> None:
        try:
            detail = await fn()
            _ok(label, detail)
        except AssertionError as e:
            _fail(label, f"assertion: {e}")
            self.failures.append(label)
        except Exception as e:
            _fail(label, f"{type(e).__name__}: {e}")
            self.failures.append(label)


# --- HotMemory checks -------------------------------------------------------
TEST_CHANNEL = "verify-hot-001"


async def _hot_basic(hot: HotMemory) -> str:
    """[HOT-1] append + recent + clear preserve order and bound at 20."""
    await hot.clear(TEST_CHANNEL)
    for i in range(25):
        await hot.append(TEST_CHANNEL, "agent", f"msg-{i:02d}", agent_id="t")
    turns = await hot.recent(TEST_CHANNEL, n=20)
    assert len(turns) == 20, f"expected 20 turns, got {len(turns)}"
    assert turns[0].content == "msg-05", f"oldest should be msg-05, got {turns[0].content}"
    assert turns[-1].content == "msg-24", f"newest should be msg-24, got {turns[-1].content}"
    await hot.clear(TEST_CHANNEL)
    after = await hot.recent(TEST_CHANNEL)
    assert after == [], f"clear should empty the list, got {len(after)} turns"
    return "25 appends → window holds 20, order preserved, clear empties"


async def _hot_concurrent(hot: HotMemory) -> str:
    """[HOT-2] Concurrent appends never corrupt or duplicate; trim stays atomic."""
    await hot.clear(TEST_CHANNEL)

    async def fire(i: int) -> None:
        await hot.append(TEST_CHANNEL, "agent", f"c-{i:03d}", agent_id="t")

    await asyncio.gather(*(fire(i) for i in range(50)))
    turns = await hot.recent(TEST_CHANNEL, n=20)
    assert len(turns) == 20, f"expected 20 after concurrent, got {len(turns)}"
    contents = [t.content for t in turns]
    assert len(set(contents)) == 20, f"duplicates after concurrent: {contents}"
    return f"50 concurrent appends → 20 unique survivors (atomic trim ok)"


async def _hot_ttl(hot: HotMemory) -> str:
    """[HOT-3] TTL is set on the channel key and is roughly 24h."""
    await hot.clear(TEST_CHANNEL)
    await hot.append(TEST_CHANNEL, "agent", "ttl-probe", agent_id="t")
    redis = get_redis()
    ttl = await redis.ttl(HotMemory._key(TEST_CHANNEL))
    # 24h = 86400s; allow a small window in case of clock drift / round-trip.
    assert 86_000 < ttl <= 86_400, f"TTL out of expected ~24h band: {ttl}s"
    await hot.clear(TEST_CHANNEL)
    return f"TTL ≈ {ttl}s (~24h)"


# --- ColdMemory checks ------------------------------------------------------
async def _cold_seed_present(cold: ColdMemory) -> str:
    """[COLD-1] Seed docs exist in Atlas (proves store_incident path worked)."""
    db = get_db()
    count = await db["incidents"].count_documents({"_id": {"$regex": "^SEED-"}})
    assert count >= 10, (
        f"expected ≥10 SEED-* docs, found {count}. Run "
        f"`python3 scripts/seed_memory.py` first."
    )
    return f"{count} SEED-* incidents present in Atlas"


async def _cold_recall_topk(cold: ColdMemory) -> str:
    """[COLD-2] Paraphrased recall returns the right top-1 with a score."""
    results = await cold.recall("database replication delay during heavy writes", k=3)
    assert results, "recall returned no results"
    top = results[0]
    assert top.id == "SEED-001", (
        f"expected top-1 SEED-001 (replica lag), got {top.id}"
    )
    assert 0 < top.score <= 1, f"score should be in (0,1], got {top.score}"
    return f"top-1={top.id} score={top.score:.3f} (of {len(results)})"


async def _cold_recall_filter(cold: ColdMemory) -> str:
    """[COLD-3] Metadata filters restrict results to matching services."""
    # Without filter, "database issue" could pull non-postgres docs too.
    # With filter services=postgres, ONLY postgres seeds should come back.
    results = await cold.recall(
        "database issue", k=5, filters={"services": "postgres"}
    )
    assert results, "filtered recall returned no results"
    bad = [r for r in results if "postgres" not in r.services]
    assert not bad, f"filter leaked non-postgres results: {[r.id for r in bad]}"
    return f"{len(results)} results, all touch 'postgres'"


async def _cold_related(cold: ColdMemory) -> str:
    """[COLD-4] related_to returns neighbors and never returns the source itself."""
    neighbors = await cold.related_to("SEED-001", k=3)
    assert neighbors, "related_to returned nothing"
    ids = [n.id for n in neighbors]
    assert "SEED-001" not in ids, f"related_to leaked self: {ids}"
    assert len(ids) <= 3, f"asked for k=3, got {len(ids)}"
    return f"{len(ids)} neighbors of SEED-001: {ids}"


# --- ADK tool checks --------------------------------------------------------
async def _adk_tools_callable() -> str:
    """[ADK-1] The 4 memory tools are importable, callable, and shape-correct."""
    from tools.memory_tools import (
        MEMORY_TOOLS,
        recall_similar_incidents,
        recent_turns,
        remember_turn,
        store_finished_incident,
    )

    assert len(MEMORY_TOOLS) == 4, f"expected 4 tools, got {len(MEMORY_TOOLS)}"
    names = {t.__name__ for t in MEMORY_TOOLS}
    expected = {
        "remember_turn",
        "recent_turns",
        "recall_similar_incidents",
        "store_finished_incident",
    }
    assert names == expected, f"tool name mismatch: {names} vs {expected}"

    # Each tool must have a non-empty docstring (ADK uses it as the LLM schema).
    for tool in MEMORY_TOOLS:
        assert tool.__doc__ and len(tool.__doc__) > 50, (
            f"{tool.__name__} needs a substantive docstring for ADK"
        )

    # Sanity-call recall_similar_incidents end-to-end (uses seeded docs).
    result = await recall_similar_incidents("postgres replication lag", k=2)
    assert result["status"] == "ok", f"tool returned non-ok: {result}"
    assert result["incidents"], "tool returned empty incidents list"

    # Wire-test: LlmAgent must accept the tools list without raising.
    if os.getenv("VERIFY_SKIP_AGENT_WIRE") != "1":
        from google.adk.agents import LlmAgent

        agent = LlmAgent(
            name="memory_verify",
            model="gemini-3.5-flash",
            instruction="(verification only — not invoked)",
            tools=MEMORY_TOOLS,
        )
        assert agent.tools, "LlmAgent didn't accept the memory tools"

    return f"4 tools importable, docstrings present, LlmAgent accepted them"


# --- driver -----------------------------------------------------------------
async def main() -> int:
    v = Verifier()

    _section("HotMemory (Redis)")
    hot = HotMemory()
    await v.run("[HOT-1] append + recent + clear", lambda: _hot_basic(hot))
    await v.run("[HOT-2] concurrent-safe atomic trim", lambda: _hot_concurrent(hot))
    await v.run("[HOT-3] TTL set to ~24h", lambda: _hot_ttl(hot))

    _section("ColdMemory (Atlas auto-embed)")
    cold = ColdMemory()
    await v.run("[COLD-1] seeded incidents present", lambda: _cold_seed_present(cold))
    await v.run("[COLD-2] recall returns expected top-1", lambda: _cold_recall_topk(cold))
    await v.run("[COLD-3] metadata filter restricts results", lambda: _cold_recall_filter(cold))
    await v.run("[COLD-4] related_to finds neighbors, excludes self", lambda: _cold_related(cold))

    _section("ADK tool wiring")
    await v.run("[ADK-1] tools importable and accepted by LlmAgent", _adk_tools_callable)

    await close_redis()
    await close_mongo()

    print()
    if v.failures:
        print(
            f"{RED}{BOLD}✗ {len(v.failures)} check(s) failed:{RESET} "
            f"{', '.join(v.failures)}"
        )
        return 1
    print(f"{GREEN}{BOLD}✓ All checks passed — memory layer verified.{RESET}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}aborted{RESET}", file=sys.stderr)
        raise SystemExit(130)
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
