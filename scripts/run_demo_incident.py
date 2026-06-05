#!/usr/bin/env python3
"""Fire a hardcoded checkout-latency incident through the HiveMind orchestrator and
print the final output object (T14 demo entry point).

⚠️  LIVE RUN: this drives all six specialists against their real partners and will
    open a REAL merge request in hivemind-target under @hivemind-bot, write an
    incident record to Atlas, and emit a Phoenix incident trace. Not a dry run.

Run:  python scripts/run_demo_incident.py
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys

# Run directly (`python scripts/run_demo_incident.py`) from anywhere: put the repo
# root on sys.path, since running a script from scripts/ only adds scripts/ itself.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/Users/ratnam/hivemind/.env")

from orchestrator.graph import OrchestratorRunner  # noqa: E402

ALERT = {
    "channel_id": "inc-demo",
    "alert": (
        "Checkout latency p99 doubled to 1.8s starting 14:32; error rate normal. "
        "Suspect the 14:05 checkout-service deploy that added a synchronous payments call."
    ),
    "affected_services": ["checkout", "payments"],
    "severity": "sev2",
}


async def main() -> int:
    print("Firing demo incident through the orchestrator (LIVE — opens a real MR)...\n")
    result = await OrchestratorRunner().run(ALERT)
    print("\n" + "=" * 72)
    print("FINAL ORCHESTRATOR OUTPUT")
    print("=" * 72)
    print(json.dumps(result.model_dump(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
