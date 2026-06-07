#!/usr/bin/env python3
"""Fire one synthetic incident through the Generator→Evaluator harness (T19 demo).

Prints each iteration's verdict + the Evaluator's feedback diff, then the final status and
the MongoDB `harness_runs` documents. This is T18's flywheel reframed as a harness loop:
the crew generates, the EXTERNAL Evaluator judges, and feedback drives the retry.

⚠️  LIVE: each iteration is a full orchestrator run (opens a real MR) + a Vertex Gemini
    evaluation. It usually PASSes on iteration 1.

Run:  .venv/bin/python scripts/run_harness_demo.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from harness import loop  # noqa: E402

ALERT = {
    "incident_id": "INC-harness-demo",
    "channel_id": "harness-demo",
    "user_id": "hivemind",
    "alert": (
        "Checkout latency p99 doubled to 1.8s after the 14:05 payment-service deploy; "
        "suspect an over-aggressive retry timeout."
    ),
    "affected_services": ["checkout", "payments"],
    "severity": "sev2",
}


async def main() -> int:
    print("firing one incident through the Generator->Evaluator harness...\n")
    result = await loop.run(ALERT)

    for it in result["iterations"]:
        print(f"--- iteration {it['iteration']}: {it['verdict']} ---")
        if it.get("failed_contract_clauses"):
            print("   failed clauses:", it["failed_contract_clauses"])
        if it.get("one_paragraph_diff"):
            print("   diff:", it["one_paragraph_diff"][:300])

    print("\n" + "=" * 60)
    print(f"FINAL: {result['status'].upper()}  (incident {result['incident_id']})")
    fb = result.get("final_feedback") or {}
    print("evidence trace links:", fb.get("evidence_trace_links"))

    try:
        from hivemind.mongo_client import close_mongo, get_db

        docs = await get_db().harness_runs.find(
            {"incident_id": result["incident_id"]}
        ).to_list(length=20)
        await close_mongo()
        print(f"\nMongoDB harness_runs ({len(docs)} docs for this incident):")
        print(json.dumps(docs, indent=2, default=str)[:1600])
    except Exception as e:  # noqa: BLE001
        print("could not read harness_runs:", e)

    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
