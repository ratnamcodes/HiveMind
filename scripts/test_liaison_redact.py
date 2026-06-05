#!/usr/bin/env python3
"""Depth play C — GDPR PII redaction (REAL write).

Sends an incident whose context says the report will be posted to a PUBLIC GitLab MR, so
CustomerLiaison must redact PII first. Asserts the agent actually fired the redaction write
surface (modify_connection_column_config / delete_multiple_columns_connection_config) against
the customer connector.

This is a real, reversible column-config change (applies on the connector's next sync).
Prereqs: same as test_customer_liaison.py (bigquery client, gcloud ADC, uvx, data synced).

Run:  python scripts/test_liaison_redact.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from agents.customer_liaison import (  # noqa: E402
    CustomerContextQuery,
    CustomerImpactReport,
    customer_liaison,
)

load_dotenv()
OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"
REDACT_TOOLS = {"modify_connection_column_config", "delete_multiple_columns_connection_config"}


async def main() -> int:
    payload = CustomerContextQuery(
        channel_id="inc-gdpr-001",
        affected_services=["payment-service"],
        severity="sev1",
        incident_id="INC-GDPR-001",
        context=(
            "This impact report will be posted to a PUBLIC GitLab merge request. Before "
            "reporting, REDACT personal data: hash the customer_id column on the customer "
            "data connector so customer identifiers are never exposed publicly."
        ),
    )
    print(f"\n{'=' * 70}\nDEPTH PLAY C — PII redaction\n{'=' * 70}")

    ss = InMemorySessionService()
    runner = Runner(agent=customer_liaison, app_name="test-liaison-redact", session_service=ss)
    session = await ss.create_session(app_name="test-liaison-redact", user_id="demo")
    msg = types.Content(role="user", parts=[types.Part(text=payload.model_dump_json())])

    tool_calls: list[str] = []
    final_text = ""
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=msg
    ):
        for call in event.get_function_calls() or []:
            tool_calls.append(call.name)
            print(f"  CALL   {call.name}  {str(dict(call.args or {}))[:160]}")
            if call.name in REDACT_TOOLS:
                print(f"\033[95m  🔒 PII redaction applied: {dict(call.args or {})}\033[0m")
        for resp in event.get_function_responses() or []:
            print(f"  RESULT {resp.name}")
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)

    print(f"\n  tool calls: {tool_calls}")
    try:
        print(CustomerImpactReport.model_validate_json(final_text).model_dump_json(indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"  ! not a valid CustomerImpactReport: {e}\n  raw: {final_text[:600]}")

    print(f"\n{'=' * 70}")
    if not (REDACT_TOOLS & set(tool_calls)):
        print(f"  {FAIL}  agent never called a redaction tool — PII would leak.")
        return 1
    print(f"  {OK}  redaction write surface exercised (modify/delete column config fired).")
    print(f"  {OK}  PASS — CustomerLiaison redacted PII mid-incident.")
    print("  (note: the column-config change is reversible in the Fivetran UI; applies next sync.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
