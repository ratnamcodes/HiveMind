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


# --- legibility events (so a third person instantly understands the channel) ---
def brief(channel_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """The pinned Incident Commander BRIEF card, emitted the instant the channel opens —
    the 5-second 'what / impact / severity / suspected / who's on it' a newcomer reads first.
    fields: {headline, what, impact, severity, suspected, team:[agent_id]}."""
    return {"type": "brief", "channel_id": channel_id, **fields}


def reasoning(channel_id: str, agent_id: str, text: str) -> dict[str, Any]:
    """A one-line 'why I'm doing this' an agent narrates BEFORE its tool calls — turns the
    fire-and-forget spinner into visible, expertise-supportive thinking."""
    return {
        "type": "reasoning",
        "channel_id": channel_id,
        "agent_id": agent_id,
        "text": text,
    }


def impact(channel_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """A business-impact update for the right-rail panel: customers + revenue at risk, by name.
    fields: {customers_affected, revenue_at_risk_usd, segments:[...], named:[{id,plan,mrr}], summary}."""
    return {"type": "impact", "channel_id": channel_id, **fields}


# --- human-in-the-loop events (the run pauses and asks a person) ---
def decision_request(channel_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """The run has PAUSED at a high-stakes step and needs a human. Rendered as an inline
    approval card. payload: {decision_id, kind, title, prompt, mr_url?, diff_summary?, impact?,
    options:[{id,label,style?}]}. Nothing irreversible has happened yet."""
    return {"type": "decision_request", "channel_id": channel_id, **payload}


def decision_made(
    channel_id: str, decision_id: str, choice: str, detail: str = ""
) -> dict[str, Any]:
    """Audit line after the human (or the timeout default) decides — clears the approval card."""
    return {
        "type": "decision_made",
        "channel_id": channel_id,
        "decision_id": decision_id,
        "choice": choice,
        "detail": detail,
    }
