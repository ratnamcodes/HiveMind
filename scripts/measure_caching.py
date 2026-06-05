#!/usr/bin/env python3
"""Measure Gemini context caching (T15-A) WITHOUT firing real incidents.

The spec runs the demo 5x — five real MRs — to measure a caching mechanism. That's
needlessly destructive, so this measures the mechanism directly: a synthetic agent with a
>32k-token stable prefix is run N times in ONE persistent session through the App +
ContextCacheConfig from hivemind/caching.py, reading usage_metadata each call.

Why a persistent session: ADK explicit caching only reuses a cache within a session. The
orchestrator uses a fresh session per incident (isolation), so it rides free *implicit*
caching; this script demonstrates the EXPLICIT layer working — call 1 primes the cache,
later calls serve ~the whole stable prefix from cache (the input saving the spec promises),
the win available to any persistent-session path (a chat mode, or the revise loop
re-running an agent).

Run:  python scripts/measure_caching.py
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/Users/ratnam/hivemind/.env")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.apps.app import App  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from hivemind.caching import CACHE_CONFIG  # noqa: E402

N = 4
# A >32k-token stable prefix so explicit caching engages (CACHE_CONFIG min_tokens=32768).
BIG_PREFIX = "You are a diagnostics assistant. " + (
    "Carefully apply each operational guideline when reasoning about an incident. " * 4000
)
AGENT = LlmAgent(name="cache_probe", model="gemini-3.5-flash", instruction=BIG_PREFIX)


async def main() -> int:
    print(f"Running a >32k-token agent {N}x in ONE persistent session...\n")
    app = App(name="measure", root_agent=AGENT, context_cache_config=CACHE_CONFIG)
    ss = InMemorySessionService()
    runner = Runner(app=app, session_service=ss)
    session = await ss.create_session(app_name=app.name, user_id="m")

    print(f"{'call':>4} {'prompt_tok':>11} {'cached_tok':>11} {'from_cache':>11} {'latency_s':>10}")
    for i in range(1, N + 1):
        content = types.Content(
            role="user",
            parts=[types.Part(text=f"Incident #{i}: checkout p99 doubled. One-line guess?")],
        )
        usage, t0 = None, time.perf_counter()
        async for e in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=content
        ):
            if getattr(e, "usage_metadata", None):
                usage = e.usage_metadata
        dt = time.perf_counter() - t0
        prompt = getattr(usage, "prompt_token_count", 0) or 0
        cached = getattr(usage, "cached_content_token_count", 0) or 0
        frac = (cached / prompt * 100) if prompt else 0.0
        print(f"{i:>4} {prompt:>11} {cached:>11} {frac:>10.1f}% {dt:>10.2f}")

    print(
        "\nCall 1 primes the cache (cached=0); calls 2+ serve the stable prefix from cache, "
        "billed at the cache discount.\nThe orchestrator uses fresh per-incident sessions for "
        "isolation (free implicit caching); this is the explicit layer, ready for any "
        "persistent-session path."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
