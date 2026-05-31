"""LogDiver — HiveMind's log specialist (Elastic, thinking_level=low)."""

from __future__ import annotations

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.genai import types
from pydantic import BaseModel, Field

from hivemind.memory import Severity

load_dotenv()


class LogQuery(BaseModel):
    """What you hand LogDiver: a focused log search."""
    channel_id: str
    query: str
    services: list[str] = Field(default_factory=list)
    time_window_minutes: int = Field(default=60, ge=1)


class LogTriageReport(BaseModel):
    """What LogDiver returns: what the logs actually show."""
    summary: str
    error_count: int = Field(ge=0)
    notable_errors: list[str] = Field(default_factory=list)
    suspected_culprit: str | None = None
    severity_estimate: Severity = "sev3"


log_diver = Agent(
    name="log_diver",
    model="gemini-3.5-flash",
    instruction=(
        "You are LogDiver, HiveMind's log specialist. Given a focused query, you "
        "dig through service logs to surface the relevant error patterns, stack "
        "traces, and timestamps. You report only what the logs actually show — "
        "counts, the most suspicious lines, and a first-pass severity. You stay "
        "fast and literal: you do not theorize about root cause, you hand the raw "
        "evidence back to the Detective."
    ),
    output_schema=LogTriageReport,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    ),
    tools=[],
)