#!/usr/bin/env python3
"""End-to-end smoke test for CustomerLiaison against live BigQuery (via its read tool)
and the Fivetran MCP.

Sends one incident — payment-service is down — and checks CustomerLiaison computes the
REAL blast radius from the `customer_usage` table Fivetran synced from the Google Sheet.
Ground truth (from scripts/seed_customer_usage.csv, services_used containing payment-service):
  - 7 customers: CUST-001 / 002 / 004 / 006 / 008 / 011 / 012
  - $21,397 / month revenue at risk

Asserts the ground truth (not the agent's say-so):
  (a) it actually queried BigQuery (query_customer_data was called) — else it's hallucinating
  (b) customers_affected == 7
  (c) revenue_at_risk_usd ~= 21,397

Prereq:
  - pip install google-cloud-bigquery   (the read tool)
  - gcloud ADC set up (you already have it)
  - the Fivetran sync of customer_usage has COMPLETED (data is in BigQuery)
  - uvx available (for the Fivetran MCP)

Run:  python scripts/test_customer_liaison.py
"""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Project root on sys.path so this runs directly (mirrors pyproject pytest pythonpath=["."]).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.customer_liaison import (  # noqa: E402
    CustomerContextQuery,
    CustomerImpactReport,
    customer_liaison,
)

load_dotenv()

APP_NAME = "test-customer-liaison"
USER_ID = "demo"
OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"

# Ground truth from the seed sheet (customers whose services_used contains payment-service).
EXPECTED_CUSTOMERS = 7
EXPECTED_REVENUE = 21397


async def main() -> int:
    payload = CustomerContextQuery(
        channel_id="inc-pay-001",
        affected_services=["payment-service"],
        severity="sev1",
        incident_id="INC-PAY-001",
    )
    print(f"\n{'=' * 70}\nCUSTOMERLIAISON — blast radius for {payload.affected_services}\n{'=' * 70}")

    session_service = InMemorySessionService()
    runner = Runner(agent=customer_liaison, app_name=APP_NAME, session_service=session_service)
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role="user", parts=[types.Part(text=payload.model_dump_json())])

    tool_calls: list[str] = []
    final_text = ""
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=message
    ):
        for call in event.get_function_calls() or []:
            tool_calls.append(call.name)
            print(f"  CALL   {call.name}  {str(dict(call.args or {}))[:200]}")
        for resp in event.get_function_responses() or []:
            print(f"  RESULT {resp.name}")
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)

    print(f"\n  tool calls ({len(tool_calls)}): {tool_calls}")
    report: CustomerImpactReport | None = None
    try:
        report = CustomerImpactReport.model_validate_json(final_text)
        print(report.model_dump_json(indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"  ! final response was not a valid CustomerImpactReport: {e}")
        print(f"  raw: {final_text[:800]}")

    print(f"\n{'=' * 70}")
    if report is None:
        print(f"  {FAIL}  no valid CustomerImpactReport returned.")
        return 1
    # Anti-hallucination: the numbers must come from a real BigQuery query.
    if "query_customer_data" not in tool_calls:
        print(f"  {FAIL}  never called query_customer_data — the numbers are hallucinated, "
              "not pulled from BigQuery.")
        return 1
    print(f"  {OK}  queried BigQuery via query_customer_data.")
    if report.customers_affected != EXPECTED_CUSTOMERS:
        print(f"  {FAIL}  customers_affected={report.customers_affected}, expected "
              f"{EXPECTED_CUSTOMERS} (is the Fivetran sync finished + data in BigQuery?).")
        return 1
    print(f"  {OK}  customers_affected == {EXPECTED_CUSTOMERS}.")
    rev = report.revenue_at_risk_usd or 0
    if abs(rev - EXPECTED_REVENUE) > 50:
        print(f"  {FAIL}  revenue_at_risk_usd={rev}, expected ~{EXPECTED_REVENUE}.")
        return 1
    print(f"  {OK}  revenue_at_risk_usd ~= {rev} (expected {EXPECTED_REVENUE}).")
    print(f"\n  PASS — CustomerLiaison computed the real blast radius from live BigQuery data.")
    print(f"  segments: {report.affected_segments}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
