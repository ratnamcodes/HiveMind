"""Scribe condenses a finished incident into its archival record."""

from __future__ import annotations

from datetime import datetime

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.genai import types
from pydantic import BaseModel, Field

from hivemind.memory import Severity

load_dotenv()


class IncidentSummary(BaseModel):
    """What you hand Scribe: a finished incident to archive."""
    channel_id: str
    title: str
    narrative: str
    services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"
    started_at: datetime
    resolved_at: datetime | None = None
    mr_url: str | None = None
    participants: list[str] = Field(default_factory=list)


class StoredIncident(BaseModel):
    """What Scribe returns: the archival record (mirrors hivemind.memory.Incident)."""
    incident_id: str
    title: str
    summary: str
    services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"
    stored: bool = False


scribe = Agent(
    name="scribe",
    model="gemini-3.5-flash",
    instruction=(
        "You are Scribe, HiveMind's record-keeper. You take a finished incident "
        "and produce a clean, self-contained archival record. You condense the "
        "narrative into a single embeddable summary and fill every field "
        "precisely. You add nothing new — you only organize and record what you "
        "are given."
    ),
    output_schema=StoredIncident,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
    ),
    tools=[],
)