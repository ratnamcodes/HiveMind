"""HiveMind Atlas Provisioner — Milestone 1 money shot.

A Gemini 3.5 agent (Google ADK + MongoDB MCP) provisions HiveMind's Atlas
infrastructure end-to-end with no human in the loop: project, M0 cluster,
DB user, network rule, database, collection, and a Voyage AI autoEmbed
vector search index on the `incidents.summary` field.

Idempotent: re-running detects existing resources and skips them.

Prereq (manual, one-time per Atlas org):
    Add a payment method to your MongoDB Atlas org so Voyage AI auto-embed
    has standard rate limits. Without it, the index builds fine but the
    first insert / recall hits a 3 RPM cap and 429s. You won't be charged
    at hackathon scale — voyage-4 free tokens cover it.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

load_dotenv()


# --- ANSI colors (no extra dep) ---------------------------------------------
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


# --- Provisioning config ----------------------------------------------------
PROJECT_NAME = "hivemind"
CLUSTER_NAME = "hivemind-cluster"
PROVIDER = "GCP"
REGION = "CENTRAL_US"
DB_NAME = "hivemind"
COLLECTION_NAME = "incidents"
DB_USER = "hivemind-app"
VECTOR_INDEX_NAME = "incidents_vector_idx"
EMBED_PATH = "summary"  # the source text field Atlas will auto-embed
EMBED_MODEL = "voyage-4"  # MongoDB-managed Voyage AI model for auto-embed

APP_NAME = "atlas-provisioner"
USER_ID = "provisioner"
MODEL = "gemini-3.5-flash"

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"


# --- Logging helpers --------------------------------------------------------
def _banner(text: str) -> None:
    line = "═" * 70
    print(f"\n{BOLD}{CYAN}{line}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{line}{RESET}\n")


def _trunc(s: str, n: int = 220) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def _log_call(name: str, args: dict[str, Any]) -> None:
    args_str = _trunc(json.dumps(args, default=str))
    print(f"{CYAN}[tool ▶]{RESET} {BOLD}{name}{RESET} {DIM}{args_str}{RESET}")


def _log_response(name: str, response: dict[str, Any]) -> None:
    resp_str = _trunc(json.dumps(response, default=str))
    print(f"{GREEN}[  ok ✓]{RESET} {name} {DIM}{resp_str}{RESET}")


def _log_thought(text: str) -> None:
    text = text.strip()
    if not text:
        return
    for line in text.splitlines():
        print(f"{MAGENTA}[agent]{RESET}  {line}")


# --- .env / secrets ---------------------------------------------------------
def _gen_password() -> str:
    """Generate a strong URL-safe password (no Atlas-illegal chars)."""
    return secrets.token_urlsafe(24)


def _existing_password() -> str | None:
    """Recover the app password already on file, preferring the one embedded
    in a working MDB_URI over MDB_APP_PASSWORD (URI is the source of truth)."""
    from urllib.parse import unquote

    uri = os.getenv("MDB_URI") or ""
    m = re.search(r"://[^:/@]+:([^@]+)@", uri)
    if m:
        return unquote(m.group(1))
    return os.getenv("MDB_APP_PASSWORD") or None


def _upsert_env(key: str, value: str) -> None:
    """Set KEY=VALUE in .env, replacing any existing line for that key."""
    contents = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(contents):
        contents = pattern.sub(new_line, contents)
    else:
        if contents and not contents.endswith("\n"):
            contents += "\n"
        contents += new_line + "\n"
    ENV_FILE.write_text(contents)


def _mask_uri(uri: str) -> str:
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:****@", uri)


def _inject_creds(uri: str, user: str, password: str) -> str:
    """Inject user:password into an SRV connection string if absent."""
    user_q = quote_plus(user)
    pass_q = quote_plus(password)
    if re.search(r"://[^/]+@", uri):
        return re.sub(r"://[^/]+@", f"://{user_q}:{pass_q}@", uri, count=1)
    return uri.replace("://", f"://{user_q}:{pass_q}@", 1)


# --- Agent wiring -----------------------------------------------------------
def _build_mcp_toolset() -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "mongodb-mcp-server"],
                env={
                    "MDB_MCP_API_CLIENT_ID": os.environ["MDB_MCP_API_CLIENT_ID"],
                    "MDB_MCP_API_CLIENT_SECRET": os.environ["MDB_MCP_API_CLIENT_SECRET"],
                    "MDB_MCP_CONFIRMATION_REQUIRED_TOOLS": "",
                    "MDB_MCP_TELEMETRY": "disabled",
                },
            )
        )
    )


def _build_instruction(org_id: str, password: str) -> str:
    return f"""You are an Atlas infrastructure provisioning agent for HiveMind.

Your mission: ensure the resources below exist in MongoDB Atlas. Create any
that are missing, skip any that already exist. BE IDEMPOTENT — if a tool
returns "already exists" or similar, treat it as success and continue.

ORG_ID = {org_id}

RESOURCES TO ENSURE:
  1. Project: name = "{PROJECT_NAME}"  (inside ORG_ID above)
  2. Cluster: name = "{CLUSTER_NAME}", tier = "M0" (free), provider = "{PROVIDER}", region = "{REGION}"
  3. DB user: username = "{DB_USER}", password = "{password}",
     role = "readWrite" on database "{DB_NAME}"
  4. Network rule: CIDR = "0.0.0.0/0"  (hackathon-mode)
  5. Database "{DB_NAME}" + collection "{COLLECTION_NAME}"
     (Atlas creates these implicitly when a document or index is first added.
      If unsure, insert one placeholder document {{"_id": "init"}} into
      {DB_NAME}.{COLLECTION_NAME} to materialize them.)
  6. Vector search index (Voyage AI Automated Embedding — Public Preview):
       name        = "{VECTOR_INDEX_NAME}"
       database    = "{DB_NAME}"
       collection  = "{COLLECTION_NAME}"
       type        = "vectorSearch"   (the high-level Atlas index TYPE)
       definition  = a vector search index whose `fields` is exactly:
                       [{{
                         "type": "autoEmbed",
                         "modality": "text",
                         "path": "{EMBED_PATH}",
                         "model": "{EMBED_MODEL}"
                       }}]

       IMPORTANT: do NOT add `numDimensions`, `similarity`, or
       `quantization` — autoEmbed derives those from the model. If the
       tool refuses without them, call `search-knowledge` for
       "vector search autoEmbed index definition" before retrying.

       If `atlas-create-search-index` fails with a billing error
       (HTTP 429 / payment method required), STOP and surface the
       error in the final JSON. The Atlas org needs a payment method
       on file before autoEmbed will work.

PROCEDURE:
  - List existing resources first (atlas-list-projects, atlas-list-clusters,
    atlas-list-db-users, atlas-list-network-permissions, etc.) and skip
    anything that already matches.
  - After creating the cluster, poll its status until it reaches "IDLE"
    before creating the vector index.
  - When checking for an EXISTING vector index, also verify its definition
    has fields[0].type == "autoEmbed". If a same-named index exists with
    the OLD vectorSearch field shape (path=embedding, numDimensions=1024),
    delete it and recreate with the autoEmbed shape above.
  - After everything is in place, fetch the cluster's standardSrv
    connection string via atlas-inspect-cluster (or atlas-list-clusters).
  - If you don't know a tool's exact parameters, call `search-knowledge`
    with a precise query (e.g. "atlas-create-free-cluster parameters")
    and follow the docs.

CRITICAL TERMINATION RULES:
  - The MOMENT you have either created or confirmed-existing the vector search index,
    STOP calling tools and emit the final JSON in your very next message.
  - Do NOT call `collection-indexes`, `list-search-indexes`, `atlas-list-clusters`,
    or any other "verification" tool after the vector index is in place. That is a loop.
  - If a tool call returns "already exists" or similar, that's success. Move on.
  - You have a HARD BUDGET of ~50 tool calls. Stay well under it. If you find yourself
    repeating the same tool, you're stuck — emit the JSON with whatever you know and stop.

FINAL OUTPUT (the last message you produce):
A single raw JSON object — NO markdown fence, NO prose around it — with:
{{
  "project_id": "...",
  "cluster_name": "{CLUSTER_NAME}",
  "connection_string": "mongodb+srv://...",   // standardSrv, no credentials
  "db_user": "{DB_USER}",
  "database": "{DB_NAME}",
  "collection": "{COLLECTION_NAME}",
  "vector_index": "{VECTOR_INDEX_NAME}",
  "created": [...],
  "skipped": [...]
}}
"""


def _parse_final_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of the agent's final response."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"raw": text}


MAX_TOOL_CALLS = 60
_SRV_RE = re.compile(r"mongodb\+srv://[^\s\"',}\\]+")


async def _run_agent(org_id: str, password: str) -> dict[str, Any]:
    mcp_tools = _build_mcp_toolset()
    agent = LlmAgent(
        name="atlas_provisioner",
        model=MODEL,
        instruction=_build_instruction(org_id, password),
        tools=[mcp_tools],
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )

    prompt = (
        "Provision the HiveMind Atlas stack now per the system instructions. "
        "Stream your tool calls. End with the JSON object only."
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    observed_srv: str | None = None
    tool_calls = 0
    forced_stop = False

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        for call in event.get_function_calls() or []:
            tool_calls += 1
            args = dict(call.args or {})
            _log_call(call.name, args)
            for v in args.values():
                if isinstance(v, str):
                    m = _SRV_RE.search(v)
                    if m:
                        observed_srv = observed_srv or m.group(0)
        for resp in event.get_function_responses() or []:
            response = dict(resp.response or {})
            _log_response(resp.name, response)
            m = _SRV_RE.search(json.dumps(response, default=str))
            if m:
                observed_srv = observed_srv or m.group(0)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and not event.is_final_response():
                    _log_thought(part.text)
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text or "" for part in event.content.parts)
            break
        if tool_calls >= MAX_TOOL_CALLS:
            forced_stop = True
            print(
                f"{YELLOW}[force-stop] tool-call cap ({MAX_TOOL_CALLS}) reached; "
                f"halting agent and synthesizing result from observed state{RESET}"
            )
            break

    result = _parse_final_json(final_text) if final_text else {}
    if observed_srv and not result.get("connection_string"):
        result["connection_string"] = observed_srv
    if forced_stop:
        result.setdefault("note", "agent terminated via tool-call cap")
    return result


# --- Victory banner ---------------------------------------------------------
ASCII_BANNER = r"""
   ██╗  ██╗██╗██╗   ██╗███████╗███╗   ███╗██╗███╗   ██╗██████╗
   ██║  ██║██║██║   ██║██╔════╝████╗ ████║██║████╗  ██║██╔══██╗
   ███████║██║██║   ██║█████╗  ██╔████╔██║██║██╔██╗ ██║██║  ██║
   ██╔══██║██║╚██╗ ██╔╝██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║  ██║
   ██║  ██║██║ ╚████╔╝ ███████╗██║ ╚═╝ ██║██║██║ ╚████║██████╔╝
   ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝
                      A T L A S   P R O V I S I O N E D
"""


def _victory(result: dict[str, Any], masked_uri: str) -> None:
    print(f"{GREEN}{BOLD}{ASCII_BANNER}{RESET}")
    print(f"  {BOLD}Project:{RESET}      {result.get('project_id', '?')}")
    print(f"  {BOLD}Cluster:{RESET}      {result.get('cluster_name', CLUSTER_NAME)}")
    print(f"  {BOLD}Database:{RESET}     {result.get('database', DB_NAME)}.{result.get('collection', COLLECTION_NAME)}")
    print(f"  {BOLD}Vector idx:{RESET}   {result.get('vector_index', VECTOR_INDEX_NAME)} (autoEmbed → {EMBED_MODEL} on '{EMBED_PATH}')")
    print(f"  {BOLD}Connection:{RESET}   {masked_uri}")
    created = result.get("created") or []
    skipped = result.get("skipped") or []
    if created:
        print(f"  {BOLD}Created:{RESET}      {', '.join(created)}")
    if skipped:
        print(f"  {BOLD}Already there:{RESET} {', '.join(skipped)}")
    print(f"\n  {DIM}→ MDB_URI and MDB_APP_PASSWORD written to .env{RESET}\n")


# --- Fast path: skip the agent when everything is already in place ---------
async def _fast_path_result() -> dict[str, Any] | None:
    """If MDB_URI works AND the vector index is READY, return a synthetic
    'all skipped' result so we can bypass the agent. Otherwise return None."""
    uri = os.getenv("MDB_URI")
    if not uri:
        return None
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        ping = await client.admin.command("ping")
        if ping.get("ok") != 1:
            client.close()
            return None
        indexes = await client[DB_NAME][COLLECTION_NAME].list_search_indexes().to_list(length=None)
        client.close()
        idx = next((i for i in indexes if i.get("name") == VECTOR_INDEX_NAME), None)
        if not idx or idx.get("status") not in {"READY", "ACTIVE"}:
            return None
        # Confirm it's the autoEmbed shape — an old vectorSearch-type index
        # with the same name would silently break HiveMind, so don't fast-path.
        defn = idx.get("latestDefinition") or idx.get("definition") or {}
        fields = defn.get("fields") or []
        if not fields or fields[0].get("type") != "autoEmbed":
            return None
        return {
            "connection_string": uri,
            "cluster_name": CLUSTER_NAME,
            "db_user": DB_USER,
            "database": DB_NAME,
            "collection": COLLECTION_NAME,
            "vector_index": VECTOR_INDEX_NAME,
            "created": [],
            "skipped": ["project", "cluster", "db_user", "network_rule", "collection", "vector_index"],
            "fast_path": True,
        }
    except Exception:
        return None


# --- Entrypoint -------------------------------------------------------------
def main() -> int:
    required = ["MDB_MCP_API_CLIENT_ID", "MDB_MCP_API_CLIENT_SECRET", "ATLAS_ORG_ID"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(
            f"{RED}error: missing env vars in .env: {missing}{RESET}",
            file=sys.stderr,
        )
        return 1

    org_id = os.environ["ATLAS_ORG_ID"]
    password = _existing_password() or _gen_password()
    _upsert_env("MDB_APP_PASSWORD", password)

    _banner("HiveMind Atlas Provisioner — Milestone 1")
    print(f"  {DIM}org={org_id}  project={PROJECT_NAME}  cluster={CLUSTER_NAME}  region={PROVIDER}/{REGION}{RESET}")
    print(f"  {DIM}db={DB_NAME}.{COLLECTION_NAME}  vector=autoEmbed:{EMBED_MODEL} on '{EMBED_PATH}'{RESET}\n")

    fast = asyncio.run(_fast_path_result())
    if fast:
        print(f"  {GREEN}✓ Pre-flight: cluster reachable, vector index READY — skipping agent.{RESET}\n")
        _victory(fast, _mask_uri(fast["connection_string"]))
        return 0

    print(f"  {DIM}password resolved → saved to .env as MDB_APP_PASSWORD{RESET}\n")

    try:
        result = asyncio.run(_run_agent(org_id, password))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}aborted by user{RESET}", file=sys.stderr)
        return 130

    conn = result.get("connection_string")
    if conn:
        full_uri = _inject_creds(conn, DB_USER, password)
        _upsert_env("MDB_URI", full_uri)
        _victory(result, _mask_uri(full_uri))
        return 0

    print(
        f"{YELLOW}warning: agent did not return a connection_string.{RESET}\n"
        f"{DIM}raw final response:{RESET}\n{result}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
