"""FastAPI entry point for HiveMind.

Wires the orchestrator LangGraph (Task 3) behind POST /chat and exposes
GET /healthz backed by a Redis ping. A lifespan handler verifies Redis is
reachable at startup and crashes the app if it isn't.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
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
