"""CodeArch — HiveMind's code archaeologist (GitLab, thinking_level=high)."""

from __future__ import annotations

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()


class CodeSearchRequest(BaseModel):
    """What you hand CodeArch: a suspected fault to trace through code."""
    channel_id: str
    question: str
    repos: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)


class CodeFinding(BaseModel):
    """What CodeArch returns: the code most likely responsible."""
    explanation: str
    suspect_files: list[str] = Field(default_factory=list)
    suspect_commits: list[str] = Field(default_factory=list)
    suggested_fix: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


code_arch = Agent(
    name="code_arch",
    model="gemini-3.5-flash",
    instruction=(
        "You are CodeArch, HiveMind's code archaeologist. Given a suspected fault "
        "area, you trace it through the codebase and recent changes to find the "
        "files, commits, or merge requests most likely responsible. You reason "
        "carefully about how a specific change could produce the observed behavior. "
        "You return concrete file paths and a suggested fix only when the evidence "
        "supports it, and you report your confidence honestly."
    ),
    output_schema=CodeFinding,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
    tools=[],
)