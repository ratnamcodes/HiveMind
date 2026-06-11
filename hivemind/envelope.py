"""Signed agent envelope; currently exercised only by its test."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from hivemind.redis_client import get_redis

T = TypeVar("T", bound=BaseModel)

MAX_AGE_SECONDS = 60
MAX_FUTURE_SKEW_SECONDS = 5
NONCE_SET_KEY = "envelope:nonces"
NONCE_SET_MAX_SIZE = 10_000
NONCE_SET_TTL_SECONDS = 120


class EnvelopeError(Exception):
    """Raised when an envelope fails any trust check."""


class AgentEnvelope(BaseModel, Generic[T]):
    from_agent: str
    to_agent: str
    payload: T
    message_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nonce: str = Field(default_factory=lambda: secrets.token_hex(16))
    signature: str = ""


def _canonical_bytes(envelope: AgentEnvelope) -> bytes:
    """JSON serialize the envelope excluding the signature, with sorted keys."""
    data = envelope.model_dump(exclude={"signature"}, mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(envelope: AgentEnvelope, secret: str) -> str:
    """Produce an HMAC-SHA256 hex digest over the canonical envelope bytes."""
    return hmac.new(
        secret.encode("utf-8"),
        _canonical_bytes(envelope),
        hashlib.sha256,
    ).hexdigest()


async def verify(envelope: AgentEnvelope, secret: str) -> bool:
    """Verify timestamp, signature, and nonce uniqueness.

    Raises `EnvelopeError` on any failure. Returns True on success.
    """
    now = datetime.now(timezone.utc)
    age = (now - envelope.timestamp).total_seconds()
    if age > MAX_AGE_SECONDS:
        raise EnvelopeError(
            f"envelope expired: {age:.1f}s old (> {MAX_AGE_SECONDS}s)"
        )
    if age < -MAX_FUTURE_SKEW_SECONDS:
        raise EnvelopeError(
            f"envelope timestamp is in the future: {-age:.1f}s ahead"
        )

    expected = sign(envelope, secret)
    if not hmac.compare_digest(envelope.signature, expected):
        raise EnvelopeError("signature mismatch")

    redis = get_redis()
    score = now.timestamp()
    added = await redis.zadd(NONCE_SET_KEY, {envelope.nonce: score}, nx=True)
    if added == 0:
        raise EnvelopeError(f"nonce already seen: {envelope.nonce}")

    cutoff = score - MAX_AGE_SECONDS
    await redis.zremrangebyscore(NONCE_SET_KEY, "-inf", cutoff)
    size = await redis.zcard(NONCE_SET_KEY)
    if size > NONCE_SET_MAX_SIZE:
        await redis.zremrangebyrank(NONCE_SET_KEY, 0, size - NONCE_SET_MAX_SIZE - 1)
    await redis.expire(NONCE_SET_KEY, NONCE_SET_TTL_SECONDS)

    return True
