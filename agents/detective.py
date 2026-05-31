"""Detective — HiveMind's lead diagnostician (Dynatrace, thinking_level=high)."""

from __future__ import annotations

from typing import Literal

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.genai import types
from pydantic import BaseModel, Field

from hivemind.memory import Severity

load_dotenv()


class InvestigationRequest(BaseModel):
    """What you hand the Detective: an alert to diagnose."""
    channel_id: str
    alert: str
    affected_services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"


class InvestigationFinding(BaseModel):
    """What the Detective returns: a root-cause hypothesis."""
    root_cause_hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    affected_entities: list[str] = Field(default_factory=list)
    supporting_signals: list[str] = Field(default_factory=list)
    handoff_to: Literal["LogDiver", "CodeArch", "CustomerLiaison", "none"] = "none"
    recommended_next_step: str


detective = Agent(
    name="detective",
    model="gemini-3.5-flash",
    instruction=(
        "You are Detective, the lead diagnostician of HiveMind. Given an alert, "
        "your job is to isolate the root cause. You always start broad (entity, "
        "service, timeline) before drilling into specifics. You never speculate — "
        "every claim must be grounded in the evidence you are given. You hand off "
        "to LogDiver, CodeArch, or CustomerLiaison when you've narrowed the cause "
        "to logs, code, or customers respectively."
    ),
    output_schema=InvestigationFinding,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
)