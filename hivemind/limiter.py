from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator

from fastapi import Request
from slowapi import Limiter

from hivemind.redis_client import get_redis

if TYPE_CHECKING:
    from google.adk.agents.llm_agent import BeforeToolCallback
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext

DEFAULT_AGENT_CONCURRENCY = 5
SEMAPHORE_POLL_INTERVAL = 0.1
DEFAULT_TOOL_BUDGET = 4
_TOOL_BUDGET_KEY = "tool_calls_made"


def _channel_key(request: Request) -> str:
    cid = getattr(request.state, "channel_id", None)
    if cid:
        return cid
    return request.client.host if request.client else "anon"


limiter = Limiter(
    key_func=_channel_key,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379"),
    default_limits=[],
)


async def populate_channel_id(request: Request, call_next):
    """Read channel_id from /chat body and stash it on request.state.

    Required because slowapi's key_func is sync and runs before the
    endpoint, so we cache the value (and reinject the body) here.
    """
    if request.url.path == "/chat" and request.method == "POST":
        body = await request.body()
        try:
            data = json.loads(body)
            request.state.channel_id = data.get("channel_id", "anon")
        except Exception:
            request.state.channel_id = "anon"

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
    return await call_next(request)


@asynccontextmanager
async def acquire(
    agent_id: str, max: int = DEFAULT_AGENT_CONCURRENCY
) -> AsyncIterator[None]:
    """Block until <= `max` concurrent slots are taken for `agent_id`.

    Caps runaway agents (e.g. a Reviewer stuck in a retry loop) by gating
    every LLM call through a Redis-backed counter shared across replicas.
    """
    redis = get_redis()
    key = f"semaphore:{agent_id}"

    while True:
        count = await redis.incr(key)
        if count <= max:
            break
        await redis.decr(key)
        await asyncio.sleep(SEMAPHORE_POLL_INTERVAL)

    try:
        yield
    finally:
        await redis.decr(key)


def tool_call_budget(max_calls: int = DEFAULT_TOOL_BUDGET) -> "BeforeToolCallback":
    """Return an ADK ``before_tool_callback`` that caps tool calls per run.

    ADK runs the callback before every tool call: returning ``None`` lets it
    proceed, returning a dict short-circuits the call and feeds that dict back
    as the tool's result. Calls are counted in session state keyed by
    ``invocation_id`` so each fresh investigation starts with a full budget.
    """

    def _before_tool(
        tool: "BaseTool", args: dict[str, Any], tool_context: "ToolContext"
    ) -> dict[str, Any] | None:
        key = f"{_TOOL_BUDGET_KEY}:{tool_context.invocation_id}"
        used = tool_context.state.get(key, 0)
        if used >= max_calls:
            return {
                "error": "tool_call_budget_exhausted",
                "budget": max_calls,
                "message": (
                    f"Tool-call budget of {max_calls} reached. Do not call any "
                    "more tools — write your final report from the evidence you "
                    "have already gathered."
                ),
            }
        tool_context.state[key] = used + 1
        return None

    return _before_tool
