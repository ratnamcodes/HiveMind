"""Register the incident_log_triage workflow as an Agent Builder tool.

Agent Builder tools of type `workflow` wrap a Workflows-engine workflow, so
registration is three calls against Kibana:

  1. POST /api/workflows            create the workflow from YAML, capture its id
  2. POST /api/agent_builder/tools  register a `workflow` tool pointing at that id
  3. GET  /api/agent_builder/tools  verify it now shows up, so LogDiver's MCP
                                    connection will expose `incident_log_triage`

Steps 1-2 WRITE to Kibana app APIs, so the key needs the Kibana privileges
`workflowsManagement:all` and `agentBuilder:all`. A read-only key reaches step 3
but 403s on 1-2 — the script prints the server's response verbatim so the
missing privilege is obvious. Override the key with ELASTIC_REGISTER_API_KEY.

Run once:  python elastic/register_tools.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

WORKFLOW_YAML = Path(__file__).parent / "tools" / "incident_log_triage.yml"
# Must match the `name:` in the workflow YAML — used to find/reuse an existing
# valid workflow instead of piling up duplicates on each re-run.
WORKFLOW_NAME = "incident_log_triage"
TOOL_ID = "incident_log_triage"
TOOL_DESCRIPTION = (
    "Triage a spiking error across HiveMind service logs: hybrid-search the "
    "signature, z-score per-service error-rate anomalies, dedupe by normalized "
    "signature, and blame the most recent deploy on the noisiest service."
)
# A `workflow` tool derives its parameter schema from the workflow's top-level
# `inputs:` section (see incident_log_triage.yml) — Agent Builder rejects a
# top-level `schema` on the create body ("Additional properties are not allowed
# ('schema' was unexpected)"), so we send none and let derivation do the work.

KIBANA_URL = os.environ["KIBANA_URL"].rstrip("/")
# Registration is a write to Kibana app APIs; prefer an explicitly-scoped key,
# else the Kibana-scoped ELASTIC_API_KEY, else the ES admin key as a last resort.
API_KEY = (
    os.getenv("ELASTIC_REGISTER_API_KEY")
    or os.getenv("ELASTIC_API_KEY")
    or os.environ["ELASTIC_ADMIN_API_KEY"]
)

_HEADERS = {
    "Authorization": f"ApiKey {API_KEY}",
    "Content-Type": "application/json",
    "kbn-xsrf": "true",
    "x-elastic-internal-origin": "Kibana",
}


def _show(payload: object) -> str:
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, indent=2)
    return str(payload)


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{KIBANA_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, _parse(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())
    except urllib.error.URLError as e:
        print(f"  ! could not reach {url}: {e.reason}", file=sys.stderr)
        raise SystemExit(1)


def _parse(raw: bytes) -> object:
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw.decode(errors="replace")


def _ok(status: int) -> bool:
    return 200 <= status < 300


def _privilege_hint(status: int, privilege: str) -> None:
    if status in (401, 403):
        print(
            f"   ! {status} looks like a privileges problem — the API key needs "
            f"Kibana `{privilege}`.\n"
            "     Set ELASTIC_REGISTER_API_KEY to a key that has it (the "
            "read-only ELASTIC_API_KEY can list tools but not create them)."
        )


def _first_created(payload: object) -> dict | None:
    # The bulk create returns {created: [workflow], failed: []}; unwrap it
    # (tolerate the other shapes Kibana has used: workflows/results/data/list).
    if isinstance(payload, dict):
        for key in ("created", "workflows", "results", "data"):
            seq = payload.get(key)
            if isinstance(seq, list) and seq and isinstance(seq[0], dict):
                return seq[0]
        if isinstance(payload.get("workflow"), dict):
            return payload["workflow"]
        if "id" in payload:
            return payload
    elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return None


def _existing_workflow_id() -> str | None:
    # Create isn't idempotent (it slugs a fresh id each call), so re-running
    # would pile up duplicates. Reuse a valid workflow of the same name instead.
    status, payload = _request("GET", "/api/workflows")
    if _ok(status) and isinstance(payload, dict):
        for wf in payload.get("results", []):
            if isinstance(wf, dict) and wf.get("name") == WORKFLOW_NAME and wf.get("valid"):
                return wf.get("id")
    return None


def create_workflow() -> str | None:
    existing = _existing_workflow_id()
    if existing:
        print(
            f"1. workflow {WORKFLOW_NAME!r} already exists and is valid "
            f"(id={existing!r}); reusing.\n"
            "   (delete it in Kibana to force a recreate from the YAML.)"
        )
        return existing
    yaml_text = WORKFLOW_YAML.read_text()
    print(f"1. POST /api/workflows  ({WORKFLOW_YAML.name}, {len(yaml_text)} bytes)")
    # The endpoint is a bulk create: body is {workflows: [{yaml}]}, not {yaml}.
    status, payload = _request(
        "POST", "/api/workflows", {"workflows": [{"yaml": yaml_text}]}
    )
    if not _ok(status):
        print(f"   -> {status}; server said:\n{_show(payload)}")
        _privilege_hint(status, "workflowsManagement:all")
        return None
    item = _first_created(payload)
    if item is None:
        print(f"   -> {status}; couldn't find created workflow in response:\n{_show(payload)}")
        return None
    wid = item.get("id") or item.get("_id")
    valid = item.get("valid")
    print(f"   -> {status}; workflow id = {wid!r}; valid = {valid}; name = {item.get('name')!r}")
    # Kibana stores the YAML even when it fails schema validation (valid=false,
    # name defaults to "Untitled workflow"). Registering a tool over an invalid
    # workflow is pointless, so stop here and surface it.
    if valid is False:
        print(
            "   ! workflow stored but did NOT compile (valid=false) — Agent "
            "Builder can't run it. Fix the YAML against the kbn-workflows schema."
        )
        return None
    return wid


def register_tool(workflow_id: str) -> bool:
    # `workflow_id` wires the tool to the workflow; its parameter schema is
    # auto-derived from that workflow's top-level `inputs:` — so no `schema`
    # field here (Agent Builder rejects one on the create body).
    fields = {
        "type": "workflow",
        "description": TOOL_DESCRIPTION,
        "configuration": {"workflow_id": workflow_id},
    }
    print(f"2. POST /api/agent_builder/tools  (id={TOOL_ID}, type=workflow)")
    status, payload = _request(
        "POST", "/api/agent_builder/tools", {"id": TOOL_ID, **fields}
    )
    if _ok(status):
        print(f"   -> {status}; tool created (schema derived from workflow inputs)")
        return True
    # Re-runs: the tool already exists, so update it in place to pick up a new
    # description or workflow_id. `id`/`type` are immutable, so PUT only the rest.
    print(f"   -> {status}; create failed, updating in place via PUT. server said:\n{_show(payload)}")
    put_body = {k: v for k, v in fields.items() if k != "type"}
    status, payload = _request("PUT", f"/api/agent_builder/tools/{TOOL_ID}", put_body)
    if _ok(status):
        print(f"   -> {status}; tool updated (schema derived from workflow inputs)")
        return True
    print(f"   -> {status}; update failed:\n{_show(payload)}")
    _privilege_hint(status, "agentBuilder:all")
    return False


def verify() -> bool:
    print("3. GET /api/agent_builder/tools  (verify)")
    status, payload = _request("GET", "/api/agent_builder/tools")
    if not _ok(status):
        print(f"   -> {status}; could not list tools:\n{_show(payload)}")
        return False
    tools: list = []
    if isinstance(payload, list):
        tools = payload
    elif isinstance(payload, dict):
        for key in ("results", "tools", "data"):
            if isinstance(payload.get(key), list):
                tools = payload[key]
                break
    ids = [t.get("id") for t in tools if isinstance(t, dict)]
    present = TOOL_ID in ids
    print(f"   -> {status}; {len(ids)} tools registered; '{TOOL_ID}' present: {present}")
    if not present and ids:
        print(f"     (registered tool ids: {', '.join(map(str, ids))})")
    return present


def main() -> None:
    print(f"Kibana: {KIBANA_URL}\n")
    workflow_id = create_workflow()
    if workflow_id:
        register_tool(workflow_id)
    else:
        print("   (skipping tool registration — no workflow id)")
    print()
    ok = verify()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
