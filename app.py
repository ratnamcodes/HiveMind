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
from fastapi.middleware.cors import CORSMiddleware
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
from hivemind import dynatrace, events
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
    # The REAL Dynatrace trigger: poll Davis problems and fire an incident on each new one.
    poller = None
    if os.getenv("DT_PROBLEM_POLL") and dynatrace.available():
        poller = asyncio.create_task(_dynatrace_problem_poller())
    yield
    if poller:
        poller.cancel()
    await close_redis()


app = FastAPI(title="HiveMind", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded)
app.add_middleware(SlowAPIMiddleware)
# The war-room (localhost:3000) POSTs human-in-the-loop decisions to this backend
# (localhost:8000) — a cross-origin request. Allow it (local demo; tighten in prod).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
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


# --- the REAL Dynatrace trigger: a live Davis problem drives the crew --------
_seen_dt_problems: set[str] = set()


async def _fire_incident_from_dt_problem(p: dict) -> None:
    """Materialize a war-room channel for a real Davis problem and run the full crew on it."""
    pid = str(p.get("id") or "P-unknown")
    title = str(p.get("title") or "Dynatrace problem")
    user_id = events.DEFAULT_USER
    channel_id = f"inc-checkout-{pid}".lower()
    channel = {
        "id": channel_id, "name": channel_id, "kind": "incident", "severity": "sev1",
        "unread": 1, "isNew": True, "topic": title, "resolved": False,
    }
    await events.publish(user_id, events.channel_created(channel))
    await events.publish(
        user_id,
        events.token(channel_id, "system", f"alert-{pid}",
                     f"Dynatrace Davis AI opened problem {pid}: {title}. HiveMind is investigating…"),
    )
    asyncio.create_task(_run_incident_bg({
        "incident_id": f"INC-{pid}",
        "channel_id": channel_id,
        "user_id": user_id,
        "alert": f"{title} (Davis problem {pid}).",
        "affected_services": ["checkout"],
        "severity": "sev1",
        "hitl": True,
        "real_app": True,
        "customer_service": "checkout",
        "code_target": "payment-service/config.yaml",
        "problem_id": pid,
    }))


async def _dynatrace_problem_poller() -> None:
    """Poll Dynatrace for OPEN Davis problems on checkout-service and fire a HiveMind incident on
    each newly-seen, recent one. This is the real Dynatrace trigger — a Davis problem (raised by the
    log-event rule on live breach logs) drives the crew, replacing the app self-trigger."""
    import time as _t

    await asyncio.sleep(8)
    while True:
        try:
            for p in await asyncio.to_thread(dynatrace.open_problems, "checkout", 1):
                pid = p.get("id")
                started = p.get("start") or 0
                recent = (_t.time() * 1000 - started) < 20 * 60 * 1000  # opened within 20 min
                if pid and recent and pid not in _seen_dt_problems:
                    _seen_dt_problems.add(pid)
                    await _fire_incident_from_dt_problem(p)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(45)


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
            f"Dynatrace alert: {problem.title} on {problem.service} ({severity}). "
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
                # Optional scenario hint that activates a CustomerLiaison Fivetran depth play
                # (e.g. GDPR PII redaction before the public MR).
                "liaison_context": str(body.get("liaison_context") or ""),
                # When true, the run PAUSES at the approval gate and waits for a human to
                # approve via POST /api/incident/<id>/resume (the human-in-the-loop demo).
                "hitl": bool(body.get("hitl")),
                # Demo grounding: the repo path the diagnosis points at, so CodeArch fixes the
                # right subsystem deterministically when the alert's surface service is generic.
                "code_target": str(body.get("code_target") or ""),
                # The customer-FACING service Liaison should compute blast radius against (the
                # implicated CAUSE service, e.g. fraud-decision, may have no warehouse rows).
                "customer_service": str(body.get("customer_service") or ""),
            }
        )
    )
    return {"status": "accepted", "channel_id": channel_id, "problem_id": problem.problem_id}


# --- human-in-the-loop: resume a run paused at an approval gate -------------
class ResumeRequest(BaseModel):
    choice: str = "approve"  # approve | changes | escalate
    feedback: str = ""


async def _resume_bg(incident_id: str, decision: dict) -> None:
    try:
        await orchestrator_runner.resume(incident_id, decision)
    except Exception:  # noqa: BLE001
        pass


@app.post("/api/incident/{incident_id}/resume")
async def resume_incident(incident_id: str, req: ResumeRequest) -> dict:
    """The human clicked a button on the approval card. Continue the paused run from its Redis
    checkpoint with the chosen decision; the complete event streams once it finalizes."""
    asyncio.create_task(
        _resume_bg(incident_id, {"choice": req.choice, "feedback": req.feedback})
    )
    return {"status": "resuming", "incident_id": incident_id, "choice": req.choice}


# --- the REAL trigger: a real service self-reports sustained degradation -----
# The instrumented checkout-service calls this when its OWN real latency breaches the SLO
# (real behavior, not a seed). HiveMind then investigates the real telemetry, drafts the fix,
# and pauses for a human. This is the unblocked "real, not scripted" trigger; the Dynatrace
# Davis-problem Workflow webhook (above) is the deeper integration once the trace token is added.
@app.post("/api/incoming/app-incident")
async def app_incident(request: Request) -> dict:
    body = json.loads(await request.body() or b"{}")
    service = str(body.get("service") or "checkout")
    severity = str(body.get("severity") or "sev1").lower()
    if severity not in _SEVERITIES:
        severity = "sev1"
    symptom = str(body.get("symptom") or f"{service} SLO breach detected from live telemetry")
    evidence = str(body.get("evidence") or "")
    user_id = request.query_params.get("user") or events.DEFAULT_USER
    pid = str(body.get("problem_id") or f"R-{os.urandom(3).hex()}")
    channel_id = f"inc-{service}-{pid}".lower()

    channel = {
        "id": channel_id, "name": channel_id, "kind": "incident", "severity": severity,
        "unread": 1, "isNew": True, "topic": symptom, "resolved": False,
    }
    await events.publish(user_id, events.channel_created(channel))
    await events.publish(
        user_id,
        events.token(channel_id, "system", f"alert-{pid}",
                     f"Live alert from {service}: {symptom}. {evidence} HiveMind is investigating…"),
    )
    asyncio.create_task(
        _run_incident_bg({
            "incident_id": f"INC-{pid}",
            "channel_id": channel_id,
            "user_id": user_id,
            "alert": f"{symptom} on {service} (severity {severity}). {evidence}",
            "affected_services": [service],
            "severity": severity,
            "hitl": True,  # the real loop always pauses for a human before shipping
            "real_app": True,  # on approval, apply the fix to the live app + verify recovery
            "customer_service": "checkout",
            "code_target": "payment-service/config.yaml",
        })
    )
    return {"status": "accepted", "channel_id": channel_id, "problem_id": pid}


# --- talk to the crew: the war-room composer posts here ---------------------
_CHAT_PERSONAS = {
    "detective": "Detective, the root-cause specialist. You query real Dynatrace Grail data to find why a service broke.",
    "log_diver": "LogDiver, the logs specialist. You pin a slowdown to the exact deploy from Elastic logs.",
    "code_arch": "CodeArch. You write the smallest safe fix and open it as a GitLab merge request.",
    "customer_liaison": "Liaison. You find which paying customers and how much revenue an incident puts at risk.",
    "scribe": "Scribe. You write the incident record and recall whether we have seen something before.",
    "reviewer": "Reviewer. You independently check a fix and prove the service recovered with a Dynatrace Site Reliability Guardian.",
}


async def _agent_chat_reply(user_id: str, channel_id: str, agent_id: str, text: str) -> None:
    """A teammate messaged the crew in the war room. Reply briefly and in character, streamed back
    over /ws so the channel feels alive. Best-effort: a model hiccup falls back to a plain reply."""
    agent_id = agent_id if agent_id in _CHAT_PERSONAS else "detective"
    mid = f"{agent_id}-chat-{os.urandom(3).hex()}"
    await events.publish(user_id, events.status(channel_id, agent_id, "thinking"))
    reply = ""
    try:
        from google import genai

        client = genai.Client()  # inherits Vertex config from the environment
        prompt = (
            f"You are {_CHAT_PERSONAS[agent_id]} You are one of six specialists in HiveMind, an AI "
            f"incident-response crew with a human in command. A teammate wrote in the team chat: "
            f'"{text}". Reply in character, helpful and plain, 1 to 3 short sentences. '
            f"No markdown, no preamble."
        )
        resp = await asyncio.to_thread(
            lambda: client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
        )
        reply = (getattr(resp, "text", "") or "").strip()
    except Exception:  # noqa: BLE001
        reply = ""
    if not reply:
        reply = (
            "I'm standing by. I jump in the moment Dynatrace flags a real problem on your service. "
            "Trigger an incident and you'll see the whole crew work it end to end."
        )
    words = reply.split()
    for i in range(0, len(words), 5):
        await events.publish(
            user_id, events.token(channel_id, agent_id, mid, " ".join(words[i : i + 5]) + " ")
        )
        await asyncio.sleep(0.04)
    await events.publish(user_id, events.status(channel_id, agent_id, "done"))


class ChatMsg(BaseModel):
    channel_id: str = "ops"
    text: str = ""
    agent_id: str = ""


@app.post("/api/chat")
async def chat_in_channel(request: Request, msg: ChatMsg) -> dict:
    """Composer entry point: route a teammate's message to the @mentioned agent (or Detective) for
    a short, in-character reply that streams back into the channel over /ws."""
    user_id = request.query_params.get("user") or events.DEFAULT_USER
    if msg.text.strip():
        asyncio.create_task(_agent_chat_reply(user_id, msg.channel_id, msg.agent_id, msg.text.strip()))
    return {"status": "ok"}


# --- Auth user store -------------------------------------------------------
# The Next.js frontend (web/lib/session.ts) hashes the password with scrypt and uses these two
# endpoints as its user store. Backed by Atlas, so accounts survive the frontend's serverless
# cold starts (a file store on Vercel can't — its filesystem is ephemeral and read-only).
class UserRecord(BaseModel):
    email: str
    name: str = ""
    hash: str = ""


@app.post("/api/users")
async def create_user(rec: UserRecord) -> dict:
    from hivemind.mongo_client import get_db

    email = rec.email.strip().lower()
    if not email or not rec.hash:
        return {"ok": False, "error": "email and hash required"}
    users = get_db()["users"]
    if await users.find_one({"_id": email}):
        return {"ok": False, "error": "exists"}
    await users.insert_one({"_id": email, "email": email, "name": rec.name, "hash": rec.hash})
    return {"ok": True}


@app.get("/api/users/{email}")
async def get_user(email: str) -> dict:
    from hivemind.mongo_client import get_db

    u = await get_db()["users"].find_one({"_id": email.strip().lower()})
    if not u:
        return {"found": False}
    return {"found": True, "email": u["email"], "name": u.get("name", ""), "hash": u.get("hash", "")}


@app.get("/api/health")
async def api_health() -> dict[str, str]:
    """Health probe on a non-reserved path. Cloud Run's Google Frontend shadows /healthz, so
    external uptime checks should target this instead."""
    try:
        ok = await get_redis().ping()
    except Exception:  # noqa: BLE001
        ok = False
    return {"status": "ok", "redis": "ok" if ok else "down"}
