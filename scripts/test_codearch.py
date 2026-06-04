#!/usr/bin/env python3
"""End-to-end smoke test for CodeArch against the live community GitLab MCP.

Sends one fake, known-fixable incident:

    "retry timeout in payment-service is 1s, should be 5s"

CodeArch must chain its GitLab tools — search_project_code -> get_file_contents ->
create_branch -> create_or_update_file -> create_merge_request -> create_note — and land
a merge request UNDER THE BOT IDENTITY (@hivemind-bot) carrying the full observability
chain.

Asserts the REAL ground truth via the GitLab API (not the agent's say-so):
  (a) a draft MR exists in GITLAB_TARGET_PROJECT on branch hivemind-bot/fix-<id>,
      authored_by == hivemind-bot
  (b) a follow-up note on that MR contains all 4 observability links

Like test_detective.py, it also guards against a hallucinated pass: if the agent made 0
tool calls the MCP never connected, so any "MR" it claims is fabricated.

Self-contained: seeds a buggy payment-service fixture on main (idempotent, via the OWNER
token — the Developer-level bot can't push to protected main) so CodeArch has a real fix
to find. Cleans up the fix branch + MR afterwards unless CODEARCH_KEEP_MR is set.

Prereq: GITLAB_BOT_TOKEN + GITLAB_TARGET_PROJECT in .env, the bot has Developer on the
repo (scripts/verify_gitlab_bot.py), and npx can fetch @zereight/mcp-gitlab.

Run:  python scripts/test_codearch.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import urllib.parse
import uuid

import requests
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Put the project root on sys.path so this runs directly as
# `python scripts/test_codearch.py` (mirrors pyproject's pytest pythonpath=["."]).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.code_arch import (  # noqa: E402
    CodeFinding,
    CodeSearchRequest,
    code_arch,
    gitlab_tools,
)

load_dotenv()

APP_NAME = "test-codearch"
USER_ID = "demo"

BOT_USERNAME = os.environ.get("GITLAB_BOT_USERNAME", "hivemind-bot")
BASE = (os.environ.get("GITLAB_URL") or "https://gitlab.com").rstrip("/")
BOT_TOKEN = os.environ.get("GITLAB_BOT_TOKEN")
OWNER_TOKEN = os.environ.get("GITLAB_TOKEN")  # to seed the fixture on protected main
PROJECT = os.environ.get("GITLAB_TARGET_PROJECT")

OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"

# Unique per run so the fix branch never collides and the test is repeatable.
INCIDENT_ID = f"INC-{uuid.uuid4().hex[:8]}"
FIX_BRANCH = f"hivemind-bot/fix-{INCIDENT_ID}"

# Fake but distinctive observability URLs — the test asserts these exact strings reappear
# on the MR note, proving the closing-the-loop chain is actually wired end to end.
ARIZE_URL = f"https://app.arize.com/trace/{INCIDENT_ID}-arize"
DT_NOTEBOOK_URL = f"https://jyl55158.apps.dynatrace.com/ui/notebook/{INCIDENT_ID}-nb"
DT_WORKFLOW_URL = f"https://jyl55158.apps.dynatrace.com/ui/workflow/{INCIDENT_ID}-wf"
MONGO_DOC_ID = f"{INCIDENT_ID}-mongo"
OBS_LINKS = [ARIZE_URL, DT_NOTEBOOK_URL, DT_WORKFLOW_URL, MONGO_DOC_ID]

# The intentionally-buggy fixture CodeArch is meant to find and fix.
FIXTURE_PATH = "payment-service/config.yaml"
FIXTURE_CONTENT = (
    "# payment-service configuration\n"
    "service: payment-service\n"
    "retry:\n"
    "  timeout_seconds: 1   # too low: aborts valid calls under load — should be 5\n"
    "  max_attempts: 3\n"
)

_PROJECT_ENC = urllib.parse.quote(PROJECT or "", safe="")


def _proj(method: str, path: str, token: str, **kw) -> requests.Response:
    url = f"{BASE}/api/v4/projects/{_PROJECT_ENC}{path}"
    return requests.request(
        method, url, headers={"PRIVATE-TOKEN": token}, timeout=25, **kw
    )


def ensure_fixture() -> None:
    """Seed the buggy file on main if absent (idempotent). Uses the OWNER token because
    a Developer-level bot can't push to protected main — which is exactly why the bot
    proposes its fix via an MR instead."""
    if not OWNER_TOKEN:
        print("  (no GITLAB_TOKEN — skipping fixture seed; CodeArch will create the file fresh)")
        return
    enc = urllib.parse.quote(FIXTURE_PATH, safe="")
    exists = _proj("GET", f"/repository/files/{enc}", OWNER_TOKEN, params={"ref": "main"})
    if exists.status_code == 200:
        print(f"  (fixture {FIXTURE_PATH} already on main)")
        return
    r = _proj(
        "POST",
        f"/repository/files/{enc}",
        OWNER_TOKEN,
        json={
            "branch": "main",
            "content": FIXTURE_CONTENT,
            "commit_message": "seed: payment-service retry timeout fixture (intentionally buggy)",
        },
    )
    print(
        f"  (seeded fixture {FIXTURE_PATH} on main)"
        if r.status_code in (200, 201)
        else f"  (couldn't seed fixture: HTTP {r.status_code} {r.text[:120]})"
    )


def find_mr_by_branch() -> dict | None:
    r = _proj("GET", "/merge_requests", BOT_TOKEN, params={"source_branch": FIX_BRANCH, "state": "all"})
    if r.status_code != 200 or not r.json():
        return None
    return r.json()[0]


def cleanup() -> None:
    """Best-effort: close the MR + delete the fix branch so re-runs stay clean."""
    try:
        mr = find_mr_by_branch()
        if mr and mr.get("state") == "opened":
            _proj("PUT", f"/merge_requests/{mr['iid']}", BOT_TOKEN, params={"state_event": "close"})
        _proj("DELETE", f"/repository/branches/{urllib.parse.quote(FIX_BRANCH, safe='')}", BOT_TOKEN)
        print(f"  (cleaned up branch {FIX_BRANCH})")
    except Exception as e:  # noqa: BLE001
        print(f"  (cleanup skipped: {e})")


async def run_codearch(payload: CodeSearchRequest) -> tuple[list[str], CodeFinding | None]:
    print(f"\n{'=' * 70}\nCODEARCH — GitLab fix loop (as @{BOT_USERNAME})\n{'=' * 70}")
    print(f"incident: {payload.incident_id}   branch: {FIX_BRANCH}")

    session_service = InMemorySessionService()
    runner = Runner(agent=code_arch, app_name=APP_NAME, session_service=session_service)
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role="user", parts=[types.Part(text=payload.model_dump_json())])

    tool_calls: list[str] = []
    final_text = ""
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=message
    ):
        for call in event.get_function_calls() or []:
            tool_calls.append(call.name)
            print(f"  CALL   {call.name}  {str(dict(call.args or {}))[:160]}")
        for resp in event.get_function_responses() or []:
            print(f"  RESULT {resp.name}")
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)

    print(f"\n  tool calls ({len(tool_calls)}): {tool_calls}")
    finding: CodeFinding | None = None
    try:
        finding = CodeFinding.model_validate_json(final_text)
        print(finding.model_dump_json(indent=2))
    except Exception as e:  # noqa: BLE001
        print(f"  ! final response was not a valid CodeFinding: {e}")
        print(f"  raw: {final_text[:800]}")
    return tool_calls, finding


async def main() -> int:
    if not (BOT_TOKEN and PROJECT):
        print(f"  {FAIL}  Missing GITLAB_BOT_TOKEN or GITLAB_TARGET_PROJECT")
        return 1

    # What did the MCP actually hand CodeArch? Confirms the fix-loop tools are wired.
    try:
        tools = await gitlab_tools.get_tools()
        names = [t.name for t in tools]
        print(f"MCP tools available to CodeArch ({len(names)}):")
        for n in names:
            print(" -", n)
        for needed in ("get_file_contents", "create_merge_request", "create_note"):
            if needed not in names:
                print(f" (note: required tool {needed} not exposed!)")
    except Exception as e:  # noqa: BLE001
        print(f"(couldn't list MCP tools up front: {e})")

    print("\nseeding fixture...")
    ensure_fixture()

    payload = CodeSearchRequest(
        channel_id=INCIDENT_ID,
        question=(
            "The retry timeout in payment-service is set to 1s but should be 5s — the "
            "value lives in the file payment-service/config.yaml. Short timeouts abort "
            "valid calls under load and cause spurious payment failures."
        ),
        incident_id=INCIDENT_ID,
        short_title="payment-service retry timeout too low",
        root_cause_hypothesis=(
            "payment-service retry timeout of 1s is below downstream p99 latency, so valid "
            "calls abort and retry-storm."
        ),
        confidence=0.82,
        arize_trace_url=ARIZE_URL,
        dynatrace_notebook_url=DT_NOTEBOOK_URL,
        workflow_public_url=DT_WORKFLOW_URL,
        mongo_doc_id=MONGO_DOC_ID,
    )

    keep = bool(os.environ.get("CODEARCH_KEEP_MR"))
    try:
        tool_calls, _finding = await run_codearch(payload)

        print(f"\n{'=' * 70}")
        # 1. anti-hallucination: it must have ACTUALLY driven the MCP.
        if not tool_calls:
            print(f"  {FAIL}  agent made 0 tool calls — the MCP never connected, so any MR it "
                  "claims is hallucinated.")
            return 1
        for needed in ("create_merge_request", "create_note"):
            if needed not in tool_calls:
                print(f"  {FAIL}  {needed} was never called — the MR/note is fabricated.")
                return 1

        # 2. ground truth (a): the MR really exists, under the bot identity.
        mr = find_mr_by_branch()
        if not mr:
            print(f"  {FAIL}  no MR found on branch {FIX_BRANCH} in {PROJECT}.")
            return 1
        author = (mr.get("author") or {}).get("username") or ""
        print(f"  {OK}  MR !{mr['iid']} exists: {mr.get('web_url')}")
        # GitLab usernames are case-insensitive-unique, so compare case-folded.
        if author.lower() != BOT_USERNAME.lower():
            print(f"  {FAIL}  MR authored_by @{author}, expected @{BOT_USERNAME} — provenance broken.")
            return 1
        print(f"  {OK}  MR authored_by @{author} — bot provenance confirmed.")

        # 3. ground truth (b): a note carries the full 4-link observability chain.
        nr = _proj("GET", f"/merge_requests/{mr['iid']}/notes", BOT_TOKEN)
        notes = nr.json() if nr.status_code == 200 else []
        chain_note = next(
            (n for n in notes if all(link in (n.get("body") or "") for link in OBS_LINKS)),
            None,
        )
        if not chain_note:
            print(f"  {FAIL}  no note on MR !{mr['iid']} carries all 4 observability links:")
            for link in OBS_LINKS:
                present = any(link in (n.get("body") or "") for n in notes)
                print(f"           {'ok ' if present else 'MISS'}  {link}")
            return 1
        print(f"  {OK}  follow-up note carries all 4 observability links — loop closed.")

        print(f"\n  PASS — @{BOT_USERNAME} drafted MR !{mr['iid']} with the full chain.")
        print(f"  {mr.get('web_url')}")
        return 0
    finally:
        if keep:
            print(f"\n  (CODEARCH_KEEP_MR set — leaving {FIX_BRANCH} + its MR for inspection)")
        else:
            cleanup()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
