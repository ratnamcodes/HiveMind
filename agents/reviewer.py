"""Reviewer — HiveMind's critic (Arize, thinking_level=high).

Its input is the *output* of any other agent, so it imports their output
schemas and judges them against the rubric.
"""

from __future__ import annotations

from typing import Literal

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.genai import types
from pydantic import BaseModel, Field

from agents.code_arch import CodeFinding
from agents.customer_liaison import CustomerImpactReport
from agents.detective import InvestigationFinding
from agents.log_diver import LogTriageReport
from agents.scribe import StoredIncident

load_dotenv()

# An agent output is ANY ONE of these five shapes.
AgentOutput = (
    InvestigationFinding
    | LogTriageReport
    | CodeFinding
    | CustomerImpactReport
    | StoredIncident
)


class AnyAgentOutput(BaseModel):
    """Wraps one specialist's output together with who produced it."""
    producer: Literal["Detective", "LogDiver", "CodeArch", "CustomerLiaison", "Scribe"]
    output: AgentOutput


class CriticVerdict(BaseModel):
    """What Reviewer returns: a grounded verdict on another agent's output."""
    verdict: Literal["approve", "revise", "escalate"]
    rubric_line: str
    offending_fragment: str | None = None
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


reviewer = Agent(
    name="reviewer",
    model="gemini-3.5-flash",
    instruction=(
        "You are Reviewer, the critic of HiveMind. You score every agent output "
        "against the rubric and reject anything ungrounded, contradicted by "
        "evidence, or below the quality bar. Your verdict is one of {approve, "
        "revise, escalate}. You always cite the specific rubric line and the "
        "offending fragment."
    ),
    output_schema=CriticVerdict,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
    tools=[],
)