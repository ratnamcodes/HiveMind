"""Each persona boots, takes a real input, and returns output that validates."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents import registry
from agents.code_arch import CodeFinding, CodeSearchRequest, code_arch
from agents.customer_liaison import (
    CustomerContextQuery,
    CustomerImpactReport,
    customer_liaison,
)
from agents.detective import InvestigationFinding, InvestigationRequest, detective
from agents.log_diver import LogQuery, LogTriageReport, log_diver
from agents.reviewer import AnyAgentOutput, CriticVerdict, reviewer
from agents.scribe import IncidentSummary, StoredIncident, scribe

load_dotenv()

APP_NAME = "test-personas"
USER_ID = "test"


async def _run_agent(agent, payload) -> str:
    """Send one typed payload to an agent, return its final text."""
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role="user", parts=[types.Part(text=payload.model_dump_json())])

    final_text = ""
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)
    return final_text


# A real Detective finding, used as the Reviewer's input.
_SAMPLE_FINDING = InvestigationFinding(
    root_cause_hypothesis="A synchronous payments call added in the 14:05 deploy.",
    confidence=0.8,
    affected_entities=["checkout", "payments"],
    supporting_signals=["p99 jumped 200ms->1.8s post-deploy", "error rate normal"],
    handoff_to="CodeArch",
    recommended_next_step="Review the 14:05 diff in checkout-service.",
)

CASES = [
    (
        detective,
        InvestigationRequest(
            channel_id="inc-1",
            alert="Checkout p99 latency spiked to 1.8s after the 14:05 deploy; errors normal.",
            affected_services=["checkout", "payments"],
            severity="sev2",
        ),
        InvestigationFinding,
    ),
    (
        log_diver,
        LogQuery(
            channel_id="inc-1",
            query="payment gateway timeout errors",
            services=["payments"],
            time_window_minutes=30,
        ),
        LogTriageReport,
    ),
    (
        code_arch,
        CodeSearchRequest(
            channel_id="inc-1",
            question="What recent change could slow the checkout->payments call?",
            repos=["checkout-service"],
            symbols=["PaymentClient.charge"],
        ),
        CodeFinding,
    ),
    (
        customer_liaison,
        CustomerContextQuery(
            channel_id="inc-1",
            affected_services=["checkout", "payments"],
            severity="sev2",
        ),
        CustomerImpactReport,
    ),
    (
        scribe,
        IncidentSummary(
            channel_id="inc-1",
            title="Checkout latency regression",
            narrative=(
                "A 14:05 deploy added a synchronous call to payments, raising checkout "
                "p99 from 200ms to 1.8s. Rolled back at 14:40; latency recovered."
            ),
            services=["checkout", "payments"],
            severity="sev2",
            started_at=datetime(2026, 5, 31, 14, 5, tzinfo=timezone.utc),
            resolved_at=datetime(2026, 5, 31, 14, 40, tzinfo=timezone.utc),
            mr_url="https://gitlab.example/checkout-service/-/merge_requests/42",
            participants=["detective", "code_arch"],
        ),
        StoredIncident,
    ),
    (
        reviewer,
        AnyAgentOutput(producer="Detective", output=_SAMPLE_FINDING),
        CriticVerdict,
    ),
]


@pytest.mark.parametrize("agent, payload, schema", CASES, ids=[a.name for a, _, _ in CASES])
async def test_persona_output_validates(agent, payload, schema):
    final_text = await _run_agent(agent, payload)
    assert final_text, f"{agent.name} returned no final text"
    result = schema.model_validate_json(final_text)  # raises if the shape is wrong
    assert isinstance(result, schema)


def test_registry_lists_all_six():
    assert set(registry.list_all()) == {
        "detective", "log_diver", "code_arch",
        "customer_liaison", "scribe", "reviewer",
    }
    assert registry.get("detective") is detective