"""FastAPI entry point for HiveMind.

Wires the orchestrator LangGraph (Task 3) behind POST /chat and exposes
GET /healthz backed by a Redis ping. A lifespan handler verifies Redis is
reachable at startup and crashes the app if it isn't.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from hivemind.redis_client import close_redis, get_redis
from orchestrator.graph import app as graph_app

load_dotenv()


class ChatRequest(BaseModel):
    channel_id: str
    message: str


class ChatResponse(BaseModel):
    output: str
    trace_id: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = get_redis()
    if not await redis.ping():
        raise RuntimeError("Redis ping failed at startup")
    yield
    await close_redis()


app = FastAPI(title="HiveMind", lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    trace_id = str(uuid.uuid4())
    result = await graph_app.ainvoke({"input": req.message, "output": ""})
    return ChatResponse(output=result["output"], trace_id=trace_id)


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
