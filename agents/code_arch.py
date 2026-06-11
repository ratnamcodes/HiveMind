"""CodeArch locates the faulty code, drafts a minimal patch, and lands it as a merge request.

Wires to the community GitLab MCP (@zereight/mcp-gitlab) over stdio, authenticated as
the dedicated bot identity (GITLAB_BOT_TOKEN -> @hivemind-bot), so every branch, merge
request, and comment is attributed to the bot.

ADK treats every {curly} token in an instruction as a session-state variable and raises
KeyError on unknown ones, so the templates below use <angle> tokens as fill-in
placeholders instead.
"""

from __future__ import annotations

import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from pydantic import BaseModel, Field

from hivemind.limiter import tool_call_budget
from hivemind.mcp_env import mcp_env

load_dotenv()

_GITLAB_API_URL = (
    os.environ.get("GITLAB_URL", "https://gitlab.com").rstrip("/") + "/api/v4"
)
_TARGET_PROJECT = os.environ.get("GITLAB_TARGET_PROJECT", "")


def fetch_repo_tree(max_files: int = 200) -> list[str]:
    """List the target repo's files via the GitLab REST tree API (recursive).

    The orchestrator injects this before the LLM runs so CodeArch reads paths
    that exist instead of guessing (guessed paths just return "File not found").
    The REST endpoint works where the MCP's get_repository_tree returns
    "Repository or path not found". Returns [] on any error; the agent still has
    get_repository_tree as a fallback.
    """
    token = os.environ.get("GITLAB_BOT_TOKEN") or os.environ.get("GITLAB_TOKEN")
    if not token or not _TARGET_PROJECT:
        return []
    pid = quote(_TARGET_PROJECT, safe="")
    try:
        r = requests.get(
            f"{_GITLAB_API_URL}/projects/{pid}/repository/tree",
            headers={"PRIVATE-TOKEN": token},
            params={"recursive": "true", "per_page": max_files},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return [item["path"] for item in r.json() if item.get("type") == "blob"]
    except requests.RequestException:
        return []


class CodeSearchRequest(BaseModel):
    """What you hand CodeArch: a diagnosed incident to fix, plus the observability
    trail to cite back. The diagnosis fields + URLs come from Detective / Reviewer /
    memory; CodeArch fills in the code half (suspect file, patch, rationale)."""

    channel_id: str
    question: str  # the suspected fault to fix, in plain language
    # incident + diagnosis context (from Detective)
    incident_id: str = "INC-0000"
    short_title: str = ""
    root_cause_hypothesis: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # observability chain to stamp into the MR and closing note
    arize_trace_url: str | None = None
    dynatrace_notebook_url: str | None = None
    workflow_public_url: str | None = None
    mongo_doc_id: str | None = None
    # optional targeting hints
    repos: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    # Files that exist in the target repo, injected by the node via the GitLab
    # REST tree API; CodeArch picks paths from here instead of guessing.
    repo_tree: list[str] = Field(default_factory=list)


class CodeFinding(BaseModel):
    """What CodeArch returns: the drafted fix and the MR it landed under the bot
    identity, with the observability note confirmed posted."""

    explanation: str
    suspect_files: list[str] = Field(default_factory=list)
    suspect_commits: list[str] = Field(default_factory=list)
    suggested_fix: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    # the landed MR (authored by @hivemind-bot)
    source_branch: str | None = None
    merge_request_iid: int | None = None
    merge_request_url: str | None = None
    observability_note_posted: bool = False
    pipeline_status: str | None = None


# Community GitLab MCP (@zereight/mcp-gitlab), launched as a local stdio subprocess
# via npx. ADK does not inherit the shell env for stdio servers, so the GitLab vars
# are passed explicitly. Authenticates as @hivemind-bot via GITLAB_BOT_TOKEN.
gitlab_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@zereight/mcp-gitlab"],
            env=mcp_env(
                GITLAB_PERSONAL_ACCESS_TOKEN=os.environ["GITLAB_BOT_TOKEN"],
                GITLAB_API_URL=_GITLAB_API_URL,
                # Default project so the agent never has to pass (or mis-pass)
                # project_id itself.
                GITLAB_PROJECT_ID=_TARGET_PROJECT,
                USE_PIPELINE="true",
                GITLAB_READ_ONLY_MODE="false",
            ),
        ),
        # GitLab API calls (file reads, MR create) can exceed ADK's default 5s
        # MCP request timeout.
        timeout=60.0,
    ),
    # Only the fix-loop tools: keeps CodeArch out of the destructive surface
    # (no delete_*, no force-push).
    tool_filter=[
        "get_repository_tree",  # fallback listing when repo_tree injection is empty
        # This server build may not expose a search tool; the loop falls back to
        # get_file_contents.
        "search_project_code",
        "search_code",
        "get_file_contents",  # read / browse to the candidate file
        "create_branch",  # branch for the patch
        "create_or_update_file",  # commit the minimal patch
        "create_merge_request",  # open the MR under the bot identity
        "create_note",  # post the observability-chain note
        "get_merge_request",  # read the MR back to confirm its iid/url
        "list_pipeline_jobs",  # bonus: watch the MR's pipeline
        "retry_pipeline_job",  # bonus: retry a failed job once
    ],
)


_INSTRUCTION = """You are CodeArch, HiveMind's code archaeologist and fix author. You act \
through the dedicated bot identity @hivemind-bot — every branch, merge request, and \
comment you create is attributed to the bot, never to a human. That attribution is the \
whole point: it makes an AI-authored change's provenance unambiguous.

You receive ONE incident as JSON with these fields: channel_id, question, incident_id, \
short_title, root_cause_hypothesis, confidence, repo_tree, arize_trace_url, dynatrace_notebook_url, \
workflow_public_url, mongo_doc_id. In the two templates below, each angle-bracketed token \
like <incident_id> is a PLACEHOLDER: replace it with that field's value from the incident \
JSON (verbatim — never invent a URL or id), and leave NO angle brackets in your output. \
<hypothesis> means root_cause_hypothesis. The diff/why/tests tokens you fill from your \
own analysis.

The repository you file against is: __TARGET_PROJECT__
Its default (target) branch is: main

Run this loop IN ORDER. Do not wander off it.

1. Ground yourself in the repository FIRST. The incident JSON includes a `repo_tree` \
field: the EXACT list of files that exist in the repo, fetched for you. Read it and pick \
the SINGLE path most relevant to the incident — match on the affected service and the \
root-cause hypothesis. NEVER pick a path that is not in repo_tree (no inventing go.mod, \
package.json, or checkout-service/… — guessing returns "File not found" and wastes your \
budget). Then call get_file_contents on that REAL path to read the current code before \
changing it. Inline comments flagging a bad value (e.g. a number marked "too low") point \
you straight to the fix. (repo_tree is authoritative; if it is somehow empty you MAY call \
get_repository_tree to list the files, but normally you do not need any listing tool.)
2. Draft a MINIMAL patch — the smallest change that fixes the root cause and nothing \
else. Work out the full new contents of that one file. (If the file genuinely does not \
exist, create the corrected file instead, and say so in the MR.)
3. Land it as a merge request, in three calls:
   a. create_branch — create branch hivemind-bot/fix-<incident_id> off main.
   b. create_or_update_file — commit your patched file contents to that branch, with a \
commit message referencing the incident.
   c. create_merge_request — open an MR in __TARGET_PROJECT__ from \
hivemind-bot/fix-<incident_id> into main. Title: "fix(<short_title>): <incident_id>". The \
description MUST be EXACTLY this template, placeholders filled:

🤖 **Auto-drafted by HiveMind Detective + CodeArch**

**Incident:** <incident_id> — <short_title>
**Root cause hypothesis (Davis):** <hypothesis>
**Confidence:** <confidence>
**Dynatrace notebook:** <dynatrace_notebook_url>
**Dynatrace workflow (public):** <workflow_public_url>

## Proposed change
<one or two sentence rationale for the diff>

## Why
<why this fix addresses the root cause>

## Tests
<what test coverage exists or should be added>

---
Reviewed by Reviewer agent (Arize trace: <arize_trace_url>)

4. create_note — post a FOLLOW-UP comment on the MR you just created (use its iid). The \
note body MUST be EXACTLY:

🔍 Full observability chain:
- Arize trace: <arize_trace_url>
- Dynatrace investigation notebook: <dynatrace_notebook_url>
- Dynatrace public workflow: <workflow_public_url>
- MongoDB incident record: incidents/<mongo_doc_id>

This note is the cross-partner closing-the-loop moment — it links the code change back to \
the trace, the diagnosis, and the incident record. It is MANDATORY; post it even if some \
URLs are null (write the value you were given).

BONUS (only if a pipeline runs on the new MR): call list_pipeline_jobs for the MR's \
pipeline. If a job failed, call retry_pipeline_job ONCE, then report the final status. \
Never retry more than once.

Then write your CodeFinding:
- explanation: what was wrong and what you changed.
- suspect_files: the file(s) you identified / changed.
- suggested_fix: a one-line summary of the patch.
- confidence: how sure you are this fixes it (0 to 1, honest).
- source_branch: hivemind-bot/fix-<incident_id>.
- merge_request_iid + merge_request_url: from the MR you created.
- observability_note_posted: true only if create_note succeeded.
- pipeline_status: the pipeline outcome if you checked one, else null.

You have a hard budget of 15 tool calls — spend them on the loop above.
""".replace("__TARGET_PROJECT__", _TARGET_PROJECT)


code_arch = Agent(
    name="code_arch",
    model="gemini-3.5-flash",
    instruction=_INSTRUCTION,
    output_schema=CodeFinding,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
    tools=[gitlab_tools],
    before_tool_callback=tool_call_budget(15),
)
