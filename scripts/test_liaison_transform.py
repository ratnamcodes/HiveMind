#!/usr/bin/env python3
"""Depth play B — transformation refresh (DECISION-LEVEL).

Sends an incident whose context says the rollups are stale, so CustomerLiaison decides to run
a dbt transformation. Asserts the agent fired run_transformation (its decision to refresh).

NOTE — this is the one write surface that can't fully execute on the course's setup: no dbt
transformation project is configured, so run_transformation will ERROR from the MCP. The test
asserts the AGENTIC DECISION (the agent chose to refresh and called the tool). To make it
fully run end-to-end, first set up a dbt transformation project in Fivetran (connect a dbt
git repo), then this same test will pass on the real run.

Run:  python scripts/test_liaison_transform.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from agents.customer_liaison import CustomerContextQuery, customer_liaison  # noqa: E402

load_dotenv()
OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"
TRANSFORM_TOOLS = {"run_transformation", "create_transformation", "create_transformation_project"}
AUTH = (os.environ.get("FIVETRAN_API_KEY"), os.environ.get("FIVETRAN_API_SECRET"))
BASE = "https://api.fivetran.com/v1"


def _project_ids() -> set:
    r = requests.get(f"{BASE}/transformation-projects", auth=AUTH, timeout=20)
    return {p["id"] for p in r.json().get("data", {}).get("items", [])} if r.status_code == 200 else set()


async def main() -> int:
    before = _project_ids()
    payload = CustomerContextQuery(
        channel_id="inc-xform-001",
        affected_services=["payment-service"],
        severity="sev2",
        incident_id="INC-XFORM-001",
        context=(
            "POLICY for this incident: the customer-impact rollups are STALE (last refreshed "
            ">1h ago) and you must NOT report from stale aggregates. You are REQUIRED to call "
            "run_transformation to refresh them BEFORE you compute or report impact. Do the "
            "refresh first."
        ),
    )
    print(f"\n{'=' * 70}\nDEPTH PLAY B — transformation refresh (decision-level)\n{'=' * 70}")

    ss = InMemorySessionService()
    runner = Runner(agent=customer_liaison, app_name="test-liaison-transform", session_service=ss)
    session = await ss.create_session(app_name="test-liaison-transform", user_id="demo")
    msg = types.Content(role="user", parts=[types.Part(text=payload.model_dump_json())])

    tool_calls: list[str] = []
    try:
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=msg
        ):
            for call in event.get_function_calls() or []:
                tool_calls.append(call.name)
                print(f"  CALL   {call.name}  {str(dict(call.args or {}))[:160]}")
                if call.name in TRANSFORM_TOOLS:
                    print(f"\033[93m  🔄 transformation refresh: {call.name} {dict(call.args or {})}\033[0m")
            for resp in event.get_function_responses() or []:
                print(f"  RESULT {resp.name}")
    except Exception as e:  # noqa: BLE001
        kind = "Gemini 429 rate-limit" if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) else type(e).__name__
        print(f"  (run interrupted mid-flight by {kind} — asserting on what already fired)")

    print(f"\n  tool calls: {tool_calls}")
    try:
        for pid in _project_ids() - before:
            requests.delete(f"{BASE}/transformation-projects/{pid}", auth=AUTH, timeout=20)
            print(f"  (cleaned up transformation project {pid})")
    except Exception as e:  # noqa: BLE001
        print(f"  (cleanup skipped: {e})")
    print(f"\n{'=' * 70}")
    if not (TRANSFORM_TOOLS & set(tool_calls)):
        print(f"  {FAIL}  agent never attempted run_transformation — it didn't decide to refresh.")
        return 1
    print(f"  {OK}  transformation write surface attempted (agent decided to refresh).")
    print(f"  {OK}  PASS (decision-level) — set up a dbt project to make it fully execute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
