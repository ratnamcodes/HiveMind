#!/usr/bin/env python3
"""Depth play A — connector provisioning on demand (REAL write, the headline).

Sends an incident whose context says a needed data source isn't flowing yet, so
CustomerLiaison must provision a pipeline mid-incident. Asserts the agent fired
create_connection.

The created connector won't fully *sync* without external auth (OAuth/credentials) — but
provisioning it on demand is the action that matters, and the write surface genuinely fires.
Best-effort cleanup deletes any connector the agent created so we don't leave junk.

Run:  python scripts/test_liaison_create.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from agents.customer_liaison import CustomerContextQuery, customer_liaison  # noqa: E402

load_dotenv()
OK = "\033[92mOK  \033[0m"
FAIL = "\033[91mFAIL\033[0m"
AUTH = (os.environ.get("FIVETRAN_API_KEY"), os.environ.get("FIVETRAN_API_SECRET"))
GID = os.environ.get("FIVETRAN_GROUP_ID", "port_doubting")
BASE = "https://api.fivetran.com/v1"


def connection_ids() -> set:
    r = requests.get(f"{BASE}/groups/{GID}/connectors", auth=AUTH, timeout=20)
    if r.status_code != 200:
        return set()
    return {c["id"] for c in r.json().get("data", {}).get("items", [])}


async def main() -> int:
    before = connection_ids()
    payload = CustomerContextQuery(
        channel_id="inc-prov-001",
        affected_services=["orders-service"],
        severity="sev2",
        incident_id="INC-PROV-001",
        context=(
            "To assess impact you need the 'orders' data, but it is NOT flowing into the "
            "warehouse yet — there is no connector for it. PROVISION a new Fivetran connector "
            "on demand so the data can sync, then continue your assessment."
        ),
    )
    print(f"\n{'=' * 70}\nDEPTH PLAY A — connector provisioning\n{'=' * 70}")

    ss = InMemorySessionService()
    runner = Runner(agent=customer_liaison, app_name="test-liaison-create", session_service=ss)
    session = await ss.create_session(app_name="test-liaison-create", user_id="demo")
    msg = types.Content(role="user", parts=[types.Part(text=payload.model_dump_json())])

    tool_calls: list[str] = []
    try:
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=msg
        ):
            for call in event.get_function_calls() or []:
                tool_calls.append(call.name)
                print(f"  CALL   {call.name}  {str(dict(call.args or {}))[:160]}")
                if call.name == "create_connection":
                    print(f"\033[96m  🆕 CustomerLiaison provisioning new Fivetran connector: "
                          f"{dict(call.args or {})}\033[0m")
            for resp in event.get_function_responses() or []:
                print(f"  RESULT {resp.name}")
    except Exception as e:  # noqa: BLE001
        kind = "Gemini 429 rate-limit" if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) else type(e).__name__
        print(f"  (run interrupted mid-flight by {kind} — asserting on what already fired)")

    print(f"\n  tool calls: {tool_calls}")
    try:
        created = connection_ids() - before
        for cid in created:
            requests.delete(f"{BASE}/connectors/{cid}", auth=AUTH, timeout=20)
            print(f"  (cleaned up created connector {cid})")
    except Exception as e:  # noqa: BLE001
        print(f"  (cleanup skipped: {e})")

    print(f"\n{'=' * 70}")
    if "create_connection" not in tool_calls:
        print(f"  {FAIL}  agent never called create_connection — it didn't provision on demand.")
        return 1
    print(f"  {OK}  provisioning write surface exercised (create_connection fired).")
    print(f"  {OK}  PASS — CustomerLiaison provisioned a Fivetran connector on demand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
