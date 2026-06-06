"""FastAPI entry point for HiveMind.

Wires the orchestrator LangGraph (Task 3) behind POST /chat and exposes
GET /healthz backed by a Redis ping. A lifespan handler verifies Redis is
reachable at startup and crashes the app if it isn't.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from hivemind.limiter import limiter, populate_channel_id


def rate_limit_exceeded(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate limit exceeded: {exc.detail}"},
        headers={"Retry-After": "60"},
    )
from hivemind import events
from hivemind.redis_client import close_redis, get_redis
from orchestrator.graph import runner as orchestrator_runner

load_dotenv()


class ChatRequest(BaseModel):
    channel_id: str
    message: str


class ChatResponse(BaseModel):
    incident_id: str
    status: str
    output: dict
    trace_id: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = get_redis()
    if not await redis.ping():
        raise RuntimeError("Redis ping failed at startup")
    yield
    await close_redis()


app = FastAPI(title="HiveMind", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded)
app.add_middleware(SlowAPIMiddleware)
app.middleware("http")(populate_channel_id)


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat(request: Request, req: ChatRequest) -> ChatResponse:
    # Dispatch the message as an incident through the orchestrator (T14). NOTE: a
    # /chat call is now a FULL incident run — it drives all six specialists against
    # live partners and can open a real MR; it is not a quick reply.
    result = await orchestrator_runner.run(
        {"alert": req.message, "channel_id": req.channel_id}
    )
    return ChatResponse(
        incident_id=result.incident_id,
        status=result.status,
        output=result.output,
        trace_id=result.trace_id,
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    redis = get_redis()
    try:
        if not await redis.ping():
            raise HTTPException(status_code=503, detail="redis ping returned falsy")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"redis error: {e}") from e
    return {"status": "ok", "redis": "ok"}


# --- T17: live event stream (/ws) + Dynatrace webhook ----------------------
_WS_BACKLOG_MAX = 100
# Reuse HMAC_SECRET if a dedicated webhook secret isn't set, so this works out of the box.
_DT_WEBHOOK_SECRET = os.getenv("DT_WEBHOOK_SECRET") or os.getenv("HMAC_SECRET", "")
_SEVERITIES = {"sev1", "sev2", "sev3"}


def _drop_one_token(backlog: deque[str]) -> bool:
    """Drop the oldest `token` event, keeping status/channel_created/complete. The
    backpressure rule: under load we shed streamed text, never lifecycle/status."""
    for i, item in enumerate(backlog):
        try:
            if json.loads(item).get("type") == "token":
                del backlog[i]
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    """One WS per browser tab. Subscribes to the user's Redis event channel and forwards
    typed events (token/status/channel_created/complete). Backpressure: if the send
    backlog exceeds 100, drop the oldest TOKEN events but always keep status/lifecycle."""
    user_id = websocket.query_params.get("user") or events.DEFAULT_USER
    await websocket.accept()
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(events.channel_name(user_id))
    backlog: deque[str] = deque()

    async def pump() -> None:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            backlog.append(message["data"])
            while len(backlog) > _WS_BACKLOG_MAX:
                if not _drop_one_token(backlog):
                    backlog.popleft()

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            if backlog:
                await websocket.send_text(backlog.popleft())
            else:
                await asyncio.sleep(0.02)
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        try:
            await pubsub.unsubscribe(events.channel_name(user_id))
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass


class DynatraceProblem(BaseModel):
    problem_id: str = "UNKNOWN"
    service: str = "unknown-service"
    severity: str = "sev2"
    title: str = ""


def _verify_dt_signature(raw: bytes, signature: str | None) -> bool:
    if not _DT_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(_DT_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


async def _run_incident_bg(payload: dict) -> None:
    """Run an incident in the background; on failure, surface it into the channel so the
    UI doesn't hang on a 'thinking' pill."""
    try:
        await orchestrator_runner.run(payload)
    except Exception as e:  # noqa: BLE001
        try:
            await events.publish(
                payload.get("user_id", events.DEFAULT_USER),
                events.token(
                    payload["channel_id"], "system", "err",
                    f"⚠️ Incident run failed: {type(e).__name__}: {e}",
                ),
            )
        except Exception:  # noqa: BLE001
            pass


@app.post("/api/incoming/dynatrace")
async def dynatrace_webhook(request: Request) -> dict:
    """Real Dynatrace alert webhook — the closing-the-loop entry point. Validates the
    HMAC signature, materializes a war-room incident channel, posts the alert, then spawns
    a full orchestrator run whose live events stream to the browser over /ws."""
    raw = await request.body()
    if not _verify_dt_signature(raw, request.headers.get("X-DT-Signature")):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    body = json.loads(raw or b"{}")
    problem = DynatraceProblem(
        problem_id=str(body.get("problem_id") or body.get("ProblemID") or "UNKNOWN"),
        service=str(body.get("service") or body.get("ImpactedEntity") or "unknown-service"),
        severity=str(body.get("severity") or "sev2").lower(),
        title=str(body.get("title") or body.get("ProblemTitle") or "Dynatrace problem"),
    )
    severity = problem.severity if problem.severity in _SEVERITIES else "sev2"
    user_id = request.query_params.get("user") or events.DEFAULT_USER
    channel_id = f"inc-{problem.service}-{problem.problem_id}".lower()

    channel = {
        "id": channel_id,
        "name": channel_id,
        "kind": "incident",
        "severity": severity,
        "unread": 1,
        "isNew": True,
        "topic": problem.title,
        "resolved": False,
    }
    # 1) Materialize the channel in the sidebar (pulse), then post the alert banner.
    await events.publish(user_id, events.channel_created(channel))
    await events.publish(
        user_id,
        events.token(
            channel_id, "system", f"alert-{problem.problem_id}",
            f"🚨 Dynatrace alert: {problem.title} — {problem.service} ({severity}). "
            f"Problem {problem.problem_id}. HiveMind is investigating…",
        ),
    )

    # 2) Spawn the full incident run; its status/token/complete events stream to /ws.
    asyncio.create_task(
        _run_incident_bg(
            {
                "incident_id": f"INC-{problem.problem_id}",
                "channel_id": channel_id,
                "user_id": user_id,
                "alert": f"{problem.title} on {problem.service} (severity {severity}).",
                "affected_services": [problem.service],
                "severity": severity,
            }
        )
    )
    return {"status": "accepted", "channel_id": channel_id, "problem_id": problem.problem_id}
