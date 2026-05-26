"""Process-wide async Redis client built from the REDIS_URL env var."""

from __future__ import annotations

import os

from redis.asyncio import Redis, from_url

_client: Redis | None = None


def get_redis() -> Redis:
    """Return the shared async Redis client, lazy-initialized on first call."""
    global _client
    if _client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _client = from_url(url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """Close the shared client. Safe to call when nothing was opened."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
