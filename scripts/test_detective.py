"""End-to-end smoke test for Detective against the live Dynatrace MCP.

Drives the full investigation loop on one synthetic alert:

    "Checkout latency p99 doubled at 14:32, what's the cause?"

Detective must chain its Dynatrace tools — generate_dql_from_natural_language ->
verify_dql -> execute_dql -> execute_davis_analyzer (or the chat_with_davis_copilot
fallback) -> create_dynatrace_notebook — and return an InvestigationFinding whose
notebook_url is non-null (the archived investigation judges can open).

workflow_public_url stays null here on purpose: publishing the investigation as a
public workflow URL is gated (automation:workflows:* scopes + write-approval) and
is deferred to T11.

Prereq: DT_ENVIRONMENT + DT_PLATFORM_TOKEN in .env (see scripts/verify_keys.py),
and the Dynatrace MCP installed (npm i -g @dynatrace-oss/dynatrace-mcp-server).

Run:  python scripts/test_detective.py
"""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.detective import (
    InvestigationFinding,
    InvestigationRequest,
    detective,
    dynatrace_tools,
)

load_dotenv()

APP_NAME = "test-detective"
USER_ID = "demo"

ALERT = "Checkout latency p99 doubled at 14:32, what's the cause?"

# The tools that make up the depth loop — used only to confirm the MCP exposed
# them before we drive the agent.
LOOP_TOOLS = (
    "generate_dql_from_natural_language",
    "verify_dql",
    "execute_dql",
    "execute_davis_analyzer",
    "create_dynatrace_notebook",
)


async def run_investigation(
    payload: InvestigationRequest,
) -> tuple[list[str], InvestigationFinding | None]:
    print(f"\n{'=' * 70}\nDETECTIVE — Dynatrace investigation loop\n{'=' * 70}")
    print(f"alert: {payload.alert!r}")

    session_service = InMemorySessionService()
    runner = Runner(
        agent=detective, app_name=APP_NAME, session_service=session_service
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
    finding: InvestigationFinding | None = None
    try:
        finding = InvestigationFinding.model_validate_json(final_text)
        print("  final InvestigationFinding:")
        print(finding.model_dump_json(indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"  ! final response was not a valid InvestigationFinding: {e}")
        print(f"  raw: {final_text[:800]}")
    return tool_calls, finding


async def main() -> int:
    # What did the MCP actually hand Detective? Confirms the loop tools are wired.
    try:
        tools = await dynatrace_tools.get_tools()
        names = [t.name for t in tools]
        print("MCP tools available to Detective:")
        for n in names:
            print(" -", n)
        missing = [t for t in LOOP_TOOLS if t not in names]
        if missing:
            print(f" (note: loop tools not exposed: {missing})")
    except Exception as e:  # noqa: BLE001
        print(f"(couldn't list MCP tools up front: {e})")

    tool_calls, finding = await run_investigation(
        InvestigationRequest(
            channel_id="inc-010",
            alert=ALERT,
            affected_services=["checkout"],
        )
    )

    # Pass/fail: the loop must have ACTUALLY run the tools and archived a notebook.
    print(f"\n{'=' * 70}")
    if finding is None:
        print("FAIL: no valid InvestigationFinding returned.")
        return 1
    # Guard against a hallucinated pass. If the MCP fails to connect, the agent
    # makes 0 tool calls but can still fabricate a finding — fake root cause, fake
    # notebook_url and all. Only trust the result if it really used the tools.
    if not tool_calls:
        print("FAIL: agent made 0 tool calls — the MCP never connected, so this "
              "finding is hallucinated (notebook_url is not a real notebook).")
        return 1
    if "create_dynatrace_notebook" not in tool_calls:
        print("FAIL: create_dynatrace_notebook was never called — notebook_url is "
              f"fabricated, not a real notebook ({finding.notebook_url!r}).")
        return 1
    if not finding.notebook_url:
        print("FAIL: notebook_url is null — the loop didn't finish archiving.")
        return 1
    print(f"PASS: investigation archived at {finding.notebook_url}")
    if finding.workflow_public_url:
        print(
            "note: workflow_public_url is set — unexpected for step 10 "
            "(workflow-publish is deferred to T11)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
