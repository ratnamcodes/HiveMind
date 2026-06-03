"""LogDiver — HiveMind's log specialist (Elastic, thinking_level=low)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.genai import types
from pydantic import BaseModel, Field

from hivemind.limiter import tool_call_budget
from hivemind.memory import Severity

load_dotenv()

# The Elastic Agent Builder MCP, hosted by Kibana. LogDiver authenticates with
# the read-only ELASTIC_API_KEY — it can search logs, never write or delete them.
elastic_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{os.environ['KIBANA_URL']}/api/agent_builder/mcp",
        headers={
            "Authorization": f"ApiKey {os.environ['ELASTIC_API_KEY']}",
            "kbn-xsrf": "true",
        },
    ),
)


class LogQuery(BaseModel):
    """What you hand LogDiver: a focused log search."""
    channel_id: str
    query: str
    # When set, LogDiver can route straight to the incident_log_triage workflow.
    error_signature: str | None = None
    services: list[str] = Field(default_factory=list)
    time_window_minutes: int = Field(default=60, ge=1)


class ErrorGroup(BaseModel):
    """A cluster of errors that share one normalized signature."""
    signature: str
    count: int = Field(ge=0)
    services: list[str] = Field(default_factory=list)
    sample_message: str | None = None


class DeployRef(BaseModel):
    """The deploy blamed for a service's error spike."""
    service: str
    version: str | None = None
    commit_sha: str | None = None
    deployed_at: str | None = None
    deployed_by: str | None = None
    summary: str | None = None


class LogTriageReport(BaseModel):
    """What LogDiver returns: what the logs actually show."""
    summary: str
    error_count: int = Field(ge=0)
    notable_errors: list[str] = Field(default_factory=list)
    suspected_culprit: str | None = None
    severity_estimate: Severity = "sev3"
    # Filled from the incident_log_triage workflow; left empty on the ad-hoc
    # ES|QL path.
    groups: list[ErrorGroup] = Field(default_factory=list)
    anomalous_services: list[str] = Field(default_factory=list)
    top_suspect_deploy: DeployRef | None = None


log_diver = Agent(
    name="log_diver",
    model="gemini-3.5-flash",
    instruction=(
        "You are LogDiver, HiveMind's log specialist. Service logs live in the "
        "Elasticsearch index `hivemind-logs-*` (fields: @timestamp, service, "
        "level, message, message_embedding). Investigate by actually querying "
        "Elastic — never invent log lines or theorize about root cause; hand the "
        "raw evidence back to the Detective.\n\n"
        "Pick one of two paths:\n"
        "1. Triage a known spike: when the query names a clear error signature, "
        "call the `incident_log_triage` workflow ONCE with that error_signature "
        "(plus time_window_minutes, and services_filter if the query is scoped "
        "to specific services). It hybrid-searches the signature, z-scores each "
        "service's error rate against a 24h baseline, dedupes by normalized "
        "signature, and blames the most recent deploy on the noisiest service. "
        "Fill `groups`, `anomalous_services`, and `top_suspect_deploy` from its "
        "result.\n"
        "2. Answer an ad-hoc question: go depth-first — "
        "`platform.core.index_explorer` to confirm the index and fields, then "
        "`platform.core.generate_esql` to draft a query, then "
        "`platform.core.execute_esql` to run it. Use `platform.core.search` for "
        "semantic or keyword lookups of specific lines.\n\n"
        "You have a hard budget of 4 tool calls — spend them deliberately, then "
        "write your report. Always return an error_count, the most suspicious "
        "lines in notable_errors, the noisiest service as suspected_culprit, and "
        "a first-pass severity_estimate. Stay fast and literal."
    ),
    output_schema=LogTriageReport,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    ),
    tools=[elastic_mcp],
    before_tool_callback=tool_call_budget(4),
)