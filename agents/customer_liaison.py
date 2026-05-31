"""CustomerLiaison — HiveMind's voice of the customer (Fivetran, thinking_level=low)."""

from __future__ import annotations

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.genai import types
from pydantic import BaseModel, Field

from hivemind.memory import Severity

load_dotenv()


class CustomerContextQuery(BaseModel):
    """What you hand CustomerLiaison: which services are hit, and how badly."""
    channel_id: str
    affected_services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"


class CustomerImpactReport(BaseModel):
    """What CustomerLiaison returns: business-level blast radius."""
    customers_affected: int = Field(ge=0)
    impact_summary: str
    affected_segments: list[str] = Field(default_factory=list)
    revenue_at_risk_usd: float | None = Field(default=None, ge=0.0)
    suggested_comms: str | None = None


customer_liaison = Agent(
    name="customer_liaison",
    model="gemini-3.5-flash",
    instruction=(
        "You are CustomerLiaison, HiveMind's voice of the customer. Given an "
        "incident's affected services, you assess who is impacted and how badly, "
        "in plain business terms. You quantify the blast radius — affected "
        "segments, account counts, and revenue at risk — and draft clear "
        "external-facing comms. You stay factual and concise: you never minimize "
        "or exaggerate the impact."
    ),
    output_schema=CustomerImpactReport,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    ),
    tools=[],
)