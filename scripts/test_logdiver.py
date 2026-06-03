"""End-to-end smoke test for LogDiver against the live Elastic Agent Builder MCP.

Runs two scenarios that exercise both of LogDiver's paths:

  Scenario 1 — one-shot workflow: a named error signature ("connection refused
  to checkout-db") should make LogDiver call the `incident_log_triage` workflow
  once and return a populated LogTriageReport (groups / anomalous_services /
  top_suspect_deploy filled from the workflow result).

  Scenario 2 — depth play (for the demo video): an open-ended "how many" question
  should make LogDiver go index_explorer -> generate_esql -> execute_esql.

For each scenario it prints every tool call the agent made and the final typed
report. Needs the workflow registered (elastic/register_tools.py) and the
indices seeded (scripts/seed_elastic_logs.py, scripts/seed_elastic_deploys.py).

Run:  python scripts/test_logdiver.py
"""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.log_diver import LogQuery, LogTriageReport, elastic_mcp, log_diver

load_dotenv()

APP_NAME = "test-logdiver"
USER_ID = "demo"


async def run_scenario(
    label: str, payload: LogQuery
) -> tuple[list[str], LogTriageReport | None]:
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    print(f"query: {payload.query!r}")

    session_service = InMemorySessionService()
    runner = Runner(
        agent=log_diver, app_name=APP_NAME, session_service=session_service
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )
    message = types.Content(
        role="user", parts=[types.Part(text=payload.model_dump_json())]
    )

    tool_calls: list[str] = []
    final_text = ""
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=message
    ):
        for call in event.get_function_calls() or []:
            tool_calls.append(call.name)
            print(f"  CALL   {call.name}  {dict(call.args or {})}")
        for resp in event.get_function_responses() or []:
            print(f"  RESULT {resp.name}")
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)

    print(f"\n  tool calls ({len(tool_calls)}): {tool_calls}")
    report: LogTriageReport | None = None
    try:
        report = LogTriageReport.model_validate_json(final_text)
        print("  final LogTriageReport:")
        print(report.model_dump_json(indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"  ! final response was not a valid LogTriageReport: {e}")
        print(f"  raw: {final_text[:800]}")
    return tool_calls, report


async def main() -> None:
    # What did the MCP actually hand us? Confirms incident_log_triage is wired.
    try:
        tools = await elastic_mcp.get_tools()
        print("MCP tools available to LogDiver:")
        for t in tools:
            print(" -", t.name)
        if not any("incident_log_triage" in t.name for t in tools):
            print(
                " (note: incident_log_triage not exposed yet — "
                "run elastic/register_tools.py first)"
            )
    except Exception as e:  # noqa: BLE001
        print(f"(couldn't list MCP tools up front: {e})")

    # Scenario 1 — named signature -> one-shot incident_log_triage workflow.
    await run_scenario(
        "SCENARIO 1 — one-shot incident_log_triage",
        LogQuery(
            channel_id="inc-001",
            query=(
                "Why is checkout erroring with 'connection refused to "
                "checkout-db' in the last 30 minutes?"
            ),
            error_signature="connection refused to checkout-db",
            services=["checkout"],
            time_window_minutes=30,
        ),
    )

    # Scenario 2 — open-ended count -> generate_esql / execute_esql two-step.
    await run_scenario(
        "SCENARIO 2 — generate_esql / execute_esql depth play",
        LogQuery(
            channel_id="inc-002",
            query=(
                "Which service has logged the most ERRORs in the last hour, "
                "and how many?"
            ),
            time_window_minutes=60,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
