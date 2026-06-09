"""Rate-limit tests for /chat.

Fires concurrent ASGI requests against the in-process FastAPI app with the
LangGraph stubbed out, so the test is fast (no Gemini calls) and deterministic.
"""

from __future__ import annotations

import asyncio

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

import app as app_module
from hivemind.redis_client import get_redis

load_dotenv()


@pytest.fixture(autouse=True)
async def _flush_rate_limit_keys():
    redis = get_redis()
    keys = await redis.keys("LIMITS:*")
    if keys:
        await redis.delete(*keys)
    yield
    keys = await redis.keys("LIMITS:*")
    if keys:
        await redis.delete(*keys)


@pytest.fixture
def _stub_graph(monkeypatch):
    # /chat now drives a FULL incident via orchestrator_runner.run (not the old
    # graph_app.ainvoke). Stub that entry point so the rate-limit test stays fast and
    # deterministic — no Gemini, no partner calls, no real MR.
    from orchestrator.graph import OrchestratorOutput

    async def fake_run(payload):
        return OrchestratorOutput(
            incident_id="stub",
            status="resolved",
            output={"stubbed": True},
            trace_id="stub-trace",
        )

    monkeypatch.setattr(app_module.orchestrator_runner, "run", fake_run)


@pytest.fixture
async def _client():
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_rate_limit_fires_at_60_per_channel(_stub_graph, _client):
    payload = {"channel_id": "rate-test-fire", "message": "hi"}
    responses = await asyncio.gather(
        *[_client.post("/chat", json=payload) for _ in range(65)]
    )
    statuses = [r.status_code for r in responses]
    assert statuses.count(200) == 60, f"got {statuses.count(200)} 200s, expected 60"
    assert statuses.count(429) == 5, f"got {statuses.count(429)} 429s, expected 5"


async def test_429_response_includes_retry_after(_stub_graph, _client):
    payload = {"channel_id": "rate-test-retry", "message": "hi"}
    responses = await asyncio.gather(
        *[_client.post("/chat", json=payload) for _ in range(65)]
    )
    rate_limited = [r for r in responses if r.status_code == 429]
    assert rate_limited, "expected at least one 429"
    assert rate_limited[0].headers.get("retry-after") == "60"


async def test_channels_have_independent_limits(_stub_graph, _client):
    a = await asyncio.gather(
        *[_client.post("/chat", json={"channel_id": "a", "message": "x"}) for _ in range(30)]
    )
    b = await asyncio.gather(
        *[_client.post("/chat", json={"channel_id": "b", "message": "x"}) for _ in range(30)]
    )
    assert all(r.status_code == 200 for r in a), "channel a should not be rate-limited"
    assert all(r.status_code == 200 for r in b), "channel b should not be rate-limited"

    follow_up = await _client.post("/chat", json={"channel_id": "a", "message": "x"})
    assert follow_up.status_code == 200, "channel a should still have budget"
