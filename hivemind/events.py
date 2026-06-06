"""Typed real-time event bus for the war room (T17).

The orchestrator and the Dynatrace webhook PUBLISH typed events to a per-user Redis
pub/sub channel `events:{user_id}`; the /ws WebSocket handler SUBSCRIBES and forwards
them to the browser, which streams tokens, updates agent status pills, and materializes
new incident channels live.

Event shapes (the contract the frontend's useEventStream consumes):
  {"type": "channel_created", "channel": {...Channel...}}
  {"type": "status",  "channel_id", "agent_id", "state": "thinking|tool_call|done", "tool"?}
  {"type": "token",   "channel_id", "agent_id", "message_id", "text"}
  {"type": "complete","channel_id", "message_id", "payload": {...final output...}}
"""

from __future__ import annotations

import json
from typing import Any

from hivemind.redis_client import get_redis

DEFAULT_USER = "hivemind"


def channel_name(user_id: str) -> str:
    return f"events:{user_id}"


async def publish(user_id: str, event: dict[str, Any]) -> None:
    """Publish one typed event to the user's pub/sub channel. Best-effort: a Redis
    hiccup must never crash the incident run, so callers can ignore failures."""
    await get_redis().publish(channel_name(user_id), json.dumps(event, default=str))


# --- typed event builders --------------------------------------------------
def channel_created(channel: dict[str, Any]) -> dict[str, Any]:
    return {"type": "channel_created", "channel": channel}


def status(
    channel_id: str, agent_id: str, state: str, tool: str | None = None
) -> dict[str, Any]:
    """state is one of: thinking | tool_call | done."""
    event: dict[str, Any] = {
        "type": "status",
        "channel_id": channel_id,
        "agent_id": agent_id,
        "state": state,
    }
    if tool:
        event["tool"] = tool
    return event


def token(
    channel_id: str, agent_id: str, message_id: str, text: str
) -> dict[str, Any]:
    return {
        "type": "token",
        "channel_id": channel_id,
        "agent_id": agent_id,
        "message_id": message_id,
        "text": text,
    }


def complete(
    channel_id: str, message_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "type": "complete",
        "channel_id": channel_id,
        "message_id": message_id,
        "payload": payload,
    }
