#!/usr/bin/env python3
"""Seed 10 fake human corrections, run the flywheel loop once, print which rubric won.

The corrections are realistic critic-MISSES — agent outputs a human flagged as
should-have-been-rejected (hallucinated files/links, ungrounded claims, wrong service,
non-minimal fixes). The flywheel drafts a new critic rubric from them, runs the
experiment (which rubric catches more of these misses), and promotes the winner.

Run:  .venv/bin/python scripts/run_flywheel_demo.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/Users/ratnam/hivemind/.env")

from flywheel.loop import run_loop  # noqa: E402

FAKE_CORRECTIONS = [
    {"agent": "detective", "rejected_output": "Root cause: probably the database. Confidence 0.9.", "human_reason": "ungrounded — no DQL evidence pulled; vague 'probably'", "preferred_output": "Root cause: payment-service retry.timeout_seconds=1 (from DQL logs)."},
    {"agent": "code_arch", "rejected_output": "Patched src/server/db.go to add an index.", "human_reason": "hallucinated file — src/server/db.go doesn't exist in the repo", "preferred_output": "Patched payment-service/config.yaml timeout 1->5."},
    {"agent": "customer_liaison", "rejected_output": "About a few hundred customers affected.", "human_reason": "an estimate, not from the data-warehouse query", "preferred_output": "7 customers (from Fivetran -> BigQuery)."},
    {"agent": "detective", "rejected_output": "Latency is high. Look into it.", "human_reason": "no hypothesis, no confidence, not actionable", "preferred_output": "Hypothesis: retry timeout too low; confidence 0.82."},
    {"agent": "code_arch", "rejected_output": "Opened MR https://gitlab.com/fake/-/merge_requests/999.", "human_reason": "hallucinated MR link — iid not returned by a tool", "preferred_output": "Opened MR !1 with the real iid."},
    {"agent": "reviewer", "rejected_output": "approve", "human_reason": "approved despite CodeArch patching a non-existent file", "preferred_output": "revise — the fix targets a file not in the repo."},
    {"agent": "log_diver", "rejected_output": "Saw some errors in the logs.", "human_reason": "no counts, no representative messages, ungrounded", "preferred_output": "1,204 ERROR logs 'deadline exceeded' post-deploy."},
    {"agent": "detective", "rejected_output": "Root cause: the checkout UI rendering.", "human_reason": "wrong service — alert + data implicate payments", "preferred_output": "payment-service retry timeout."},
    {"agent": "customer_liaison", "rejected_output": "No customers affected.", "human_reason": "contradicted by the warehouse query (7 affected)", "preferred_output": "7 customers affected."},
    {"agent": "code_arch", "rejected_output": "Rewrote the entire payment-service module.", "human_reason": "not minimal — should be a one-line timeout change", "preferred_output": "Minimal diff: timeout_seconds 1 -> 5."},
]


async def main() -> int:
    print(f"seeding {len(FAKE_CORRECTIONS)} fake human corrections; running the flywheel once...\n")
    result = await run_loop(FAKE_CORRECTIONS)
    print(json.dumps(result, indent=2, default=str))
    s = result.get("scores", {})
    n = result.get("n_corrections", 0)
    print("\n" + "=" * 60)
    print(
        f"WINNER: {result.get('winner')}  "
        f"(old caught {s.get('old', {}).get('caught')}/{n}, "
        f"new caught {s.get('new', {}).get('caught')}/{n})"
    )
    print(f"promoted to production: {result.get('promoted')}  |  logged to Mongo: {result.get('logged')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
