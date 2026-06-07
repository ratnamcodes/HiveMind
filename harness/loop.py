"""Generator→Evaluator loop (T19).

The **Generator** is the orchestrator (the crew); the **Evaluator** is the external
`harness/evaluator.py`. Each iteration: run the crew → grade it externally → on PASS, done;
on FAIL, feed the Evaluator's `feedback.json` back into the crew (as `evaluator_feedback`,
plus appended to the alert so the agents actually see what to fix) and re-run. Hard cap
`MAX_ITERS`, then escalate to a human — never loop forever. Every iteration is logged as a
structured event to MongoDB `harness_runs`.

Each iteration runs on a FRESH orchestrator thread (incident_id stays stable so the MR
branch + the Evaluator's lookups are consistent across retries).
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from harness import evaluator  # noqa: E402
from orchestrator.graph import OrchestratorRunner  # noqa: E402

MAX_ITERS = 5


async def _log_harness_run(event: dict) -> bool:
    try:
        from hivemind.mongo_client import close_mongo, get_db

        await get_db().harness_runs.insert_one(dict(event))
        await close_mongo()
        return True
    except Exception:  # noqa: BLE001
        return False


async def run(alert_payload: dict, max_iters: int = MAX_ITERS) -> dict:
    incident_id = alert_payload.get("incident_id") or f"INC-{uuid.uuid4().hex[:8]}"
    base = {**alert_payload, "incident_id": incident_id}
    base_alert = base.get("alert", "")
    contract = evaluator.default_contract(incident_id, base.get("severity", "sev2"))

    iterations: list[dict] = []
    feedback: dict | None = None

    for i in range(1, max_iters + 1):
        payload = dict(base)
        payload["thread_id"] = f"{incident_id}-iter{i}"  # fresh run each iteration
        if feedback:
            # The verdict travels as a FILE-derived field, never as agent-to-agent chat.
            payload["evaluator_feedback"] = feedback
            payload["alert"] = (
                base_alert
                + "\n\nPRIOR EVALUATOR FEEDBACK (must fix this iteration): "
                + "; ".join(feedback.get("failed_contract_clauses", []))
                + " — "
                + feedback.get("one_paragraph_diff", "")
            )

        out, state = await OrchestratorRunner().run_full(payload)
        feedback = await evaluator.evaluate(incident_id, contract, out.output, state)

        event = {
            "incident_id": incident_id,
            "iteration": i,
            "verdict": feedback["verdict"],
            "failed_contract_clauses": feedback["failed_contract_clauses"],
            "evidence_trace_links": feedback["evidence_trace_links"],
            "one_paragraph_diff": feedback["one_paragraph_diff"],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        await _log_harness_run(event)
        iterations.append(event)

        if feedback["verdict"] == "PASS":
            return {
                "incident_id": incident_id, "status": "passed",
                "iterations": iterations, "final_feedback": feedback,
            }

    # Hard cap reached — escalate to a human; never loop forever. (Inside the graph this
    # would be a LangGraph interrupt(); the harness drives the graph from outside, so the
    # loop stops and flags for human pickup.)
    esc = {
        "incident_id": incident_id, "iteration": max_iters, "verdict": "ESCALATED",
        "note": "max iterations reached without PASS — escalated to a human (LangGraph interrupt point)",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    await _log_harness_run(esc)
    iterations.append(esc)
    return {
        "incident_id": incident_id, "status": "escalated",
        "iterations": iterations, "final_feedback": feedback,
    }
