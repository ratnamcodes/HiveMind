"""Detective investigates alerts against Dynatrace and returns a grounded root-cause finding."""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from pydantic import BaseModel, Field

from hivemind.limiter import tool_call_budget
from hivemind.mcp_env import mcp_env
from hivemind.memory import Severity

load_dotenv()


class InvestigationRequest(BaseModel):
    """What you hand the Detective: an alert to diagnose."""
    channel_id: str
    alert: str
    affected_services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"


class Evidence(BaseModel):
    """One piece of evidence behind the hypothesis: a DQL result highlight, a Davis
    analyzer hypothesis (including the runners-up that didn't win), or an anomaly."""
    source: str
    detail: str
    dql: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class InvestigationFinding(BaseModel):
    """What the Detective returns: a root-cause hypothesis, grounded in a Dynatrace
    investigation that's been archived as a notebook."""
    root_cause_hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    implicated_service: str | None = None
    implicated_deploy: str | None = None
    notebook_url: str | None = None
    # Always null today; set when workflow publishing is wired.
    workflow_public_url: str | None = None
    # Routing: which specialist should pick up the investigation next.
    handoff_to: Literal["LogDiver", "CodeArch", "CustomerLiaison", "none"] = "none"
    recommended_next_step: str


# The Dynatrace MCP, launched as a local stdio subprocess via npx. ADK does not
# inherit the shell environment for stdio servers, so DT_* is passed explicitly.
# The server authenticates with a Platform Token (dt0s16…) under DT_PLATFORM_TOKEN,
# not the classic dt0c01 DT_API_TOKEN, and it rejects classic `.live` URLs, so it
# gets the `.apps` platform URL derived from DT_ENVIRONMENT.
dynatrace_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@dynatrace-oss/dynatrace-mcp-server@latest"],
            env=mcp_env(
                DT_ENVIRONMENT=os.environ["DT_ENVIRONMENT"].replace(".live.", ".apps."),
                DT_PLATFORM_TOKEN=os.environ["DT_PLATFORM_TOKEN"],
                DT_MCP_DISABLE_TELEMETRY="true",
            ),
        ),
        # Davis CoPilot tools (nl2dql, analyzers, copilot chat) are LLM-backed and
        # routinely take longer than ADK's default 5s MCP request timeout.
        timeout=60.0,
    ),
    # Only the investigation-loop tools: keeps Detective out of entity/problem
    # explorers that 403 on ungranted scopes, and away from the gated writes
    # (send_email, make_workflow_public, …).
    tool_filter=[
        "generate_dql_from_natural_language",
        "verify_dql",
        "execute_dql",
        "list_davis_analyzers",
        "execute_davis_analyzer",
        "chat_with_davis_copilot",
        "create_dynatrace_notebook",
    ],
)


detective = Agent(
    name="detective",
    model="gemini-3.5-flash",
    instruction=(
        "You are Detective, the lead diagnostician of HiveMind. You investigate "
        "alerts against Dynatrace and never speculate — every claim must be "
        "grounded in data you actually pulled.\n\n"
        "Where the data is: this environment's telemetry lives in LOGS (Grail). "
        "Always investigate via `fetch logs` and filter or search on content "
        "(e.g. `fetch logs | filter contains(content, \"checkout\")`). Do NOT "
        "query the spans or metrics tables — they are not populated here, and "
        "spans will fail authorization and waste your budget.\n\n"
        "Your tools are restricted to exactly this loop — do NOT explore with "
        "anything else first. Run these steps in order:\n"
        "1. generate_dql_from_natural_language — translate the alert into a LOGS "
        "DQL query for the affected service (ask for logs, not spans/metrics).\n"
        "2. verify_dql — sanity-check that query's syntax BEFORE running it, so a "
        "malformed query never spends Grail budget.\n"
        "3. execute_dql — run the verified query against Grail to pull the real "
        "log records.\n"
        "4. execute_davis_analyzer — ONLY after step 3 has returned log records, "
        "run a Davis analyzer over them for root-cause hypotheses. If you're "
        "unsure which analyzer fits, call list_davis_analyzers first; if none "
        "applies, fall back to chat_with_davis_copilot. Never call "
        "list_davis_analyzers or chat_with_davis_copilot before you have pulled "
        "data in step 3.\n"
        "5. create_dynatrace_notebook — as your LAST tool, best-effort archive the "
        "investigation (the question, the DQL, the key results, your conclusion) as "
        "a notebook and put its URL in notebook_url. This is a nice-to-have: attempt "
        "it AT MOST ONCE. If it does not return promptly or it errors, do NOT retry "
        "it and do NOT block on it — immediately write your finding with "
        "notebook_url=null. Your grounded root-cause hypothesis is what matters; "
        "never withhold or delay the finding because the notebook step was slow or "
        "failed.\n\n"
        "Then write your InvestigationFinding:\n"
        "- root_cause_hypothesis + confidence: your single best explanation. If "
        "Davis returned several hypotheses, put the highest-confidence one here "
        "and record the rest in evidence.\n"
        "- evidence: the signals you relied on (DQL result highlights, Davis "
        "hypotheses including runners-up, anomalies), each with its source and, "
        "where relevant, the dql and a confidence.\n"
        "- implicated_service / implicated_deploy: the service and (if you can "
        "tell) the deploy you believe caused this; null if unknown.\n"
        "- notebook_url: the notebook if you created one, else null. Leave "
        "workflow_public_url null — that's handled later in T11.\n"
        "- handoff_to + recommended_next_step: who should pick this up next "
        "(LogDiver for log detail, CodeArch for the code/commit, CustomerLiaison "
        "for customer impact) and the concrete next action.\n\n"
        "You have a hard budget of 10 tool calls — spend them deliberately on the "
        "loop above, then write your finding from what you gathered."
    ),
    output_schema=InvestigationFinding,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
    tools=[dynatrace_tools],
    before_tool_callback=tool_call_budget(10),
)
