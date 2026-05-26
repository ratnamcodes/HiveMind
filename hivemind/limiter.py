from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Request
from slowapi import Limiter

from hivemind.redis_client import get_redis

DEFAULT_AGENT_CONCURRENCY = 5
SEMAPHORE_POLL_INTERVAL = 0.1


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
