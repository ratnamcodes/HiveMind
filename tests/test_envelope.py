"""Trust-boundary tests for AgentEnvelope sign/verify."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from pydantic import BaseModel

from hivemind.envelope import (
    AgentEnvelope,
    EnvelopeError,
    NONCE_SET_KEY,
    sign,
    verify,
)
from hivemind.redis_client import get_redis

load_dotenv()

SECRET = "test-secret-key-do-not-use-in-prod"


class HelloPayload(BaseModel):
    text: str


@pytest.fixture(autouse=True)
async def _flush_nonces():
    redis = get_redis()
    await redis.delete(NONCE_SET_KEY)
    yield
    await redis.delete(NONCE_SET_KEY)


def make_signed_envelope() -> AgentEnvelope[HelloPayload]:
    env = AgentEnvelope[HelloPayload](
        from_agent="alpha",
        to_agent="beta",
        payload=HelloPayload(text="hello"),
    )
    env.signature = sign(env, SECRET)
    return env


async def test_happy_path():
    env = make_signed_envelope()
    assert await verify(env, SECRET) is True


async def test_tampered_payload():
    env = make_signed_envelope()
    env.payload.text = "evil"
    with pytest.raises(EnvelopeError, match="signature"):
        await verify(env, SECRET)


async def test_expired_timestamp():
    env = AgentEnvelope[HelloPayload](
        from_agent="alpha",
        to_agent="beta",
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=120),
        payload=HelloPayload(text="hello"),
    )
    env.signature = sign(env, SECRET)
    with pytest.raises(EnvelopeError, match="expired"):
        await verify(env, SECRET)


async def test_replayed_nonce():
    env = make_signed_envelope()
    assert await verify(env, SECRET) is True
    with pytest.raises(EnvelopeError, match="nonce"):
        await verify(env, SECRET)


async def test_wrong_from_agent():
    env = make_signed_envelope()
    env.from_agent = "attacker"
    with pytest.raises(EnvelopeError, match="signature"):
        await verify(env, SECRET)
