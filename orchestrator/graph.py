"""HiveMind incident orchestrator (T14) — the conductor of the symphony.

Composes the 6 specialists into a stateful LangGraph incident-response graph:

    START → Detective ─(implicated_service?)─┬─ no ─→ Reviewer (escalate)
                                             └─ yes → { LogDiver ∥ CodeArch ∥ Liaison }
                                                        → Scribe → Reviewer
    Reviewer ─(verdict)─ approve  → END {mr_url, notebook_url, customers_affected, …}
                         revise   → back to verdict.revise_target  (≤ MAX_REVISIONS, then escalate)
                         escalate → END (flagged + human summary)

Each node runs one specialist via _run_agent() (the T13 review() pattern) inside its own
OTEL span, and OrchestratorRunner wraps the whole run in ONE Phoenix "incident" span — so
the trace tree is: incident → each agent → its Gemini + tool spans (T13's instrumentation).

State holds each agent's output as a model_dump() DICT (not the Pydantic instance) so the
Redis checkpointer can JSON-serialize it — that's what lets a killed run resume from its
last checkpoint. The `: dict` fields below carry the shapes named in the comments.

Fan-in is implicit: LogDiver/CodeArch/Liaison all edge to Scribe, and LangGraph runs Scribe
once its *triggered* predecessors complete — so the parallel path waits for all 3, while a
single revised agent waits for just itself.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Literal, TypedDict

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from opentelemetry import trace as otel_trace
from pydantic import BaseModel

from agents.code_arch import CodeFinding, CodeSearchRequest, code_arch, fetch_repo_tree
from agents.customer_liaison import (
    CustomerContextQuery,
    CustomerImpactReport,
    customer_liaison,
)
from agents.detective import InvestigationFinding, InvestigationRequest, detective
from agents.log_diver import LogQuery, LogTriageReport, log_diver
from agents.reviewer import CriticVerdict, _phoenix_trace_url, reviewer
from agents.scribe import IncidentSummary, StoredIncident, scribe
from hivemind import events
from hivemind.memory import ColdMemory, Incident
from orchestrator.critic import critique

load_dotenv()

MAX_REVISIONS = 2
# Per-agent hard cap (seconds): a hung or rate-limit-stalled LLM/tool call must never
# freeze a whole incident (that's what froze the eval suite on scenario #6). The per-hop
# critic retries once on a timed-out (empty) result, so a transient stall self-heals.
AGENT_TIMEOUT = 240.0
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_tracer = otel_trace.get_tracer("hivemind.orchestrator")

DETECTIVE, LOG_DIVER, CODE_ARCH, LIAISON = (
    "detective",
    "log_diver",
    "code_arch",
    "customer_liaison",
)
SCRIBE, REVIEWER = "scribe", "reviewer"
FANOUT = [LOG_DIVER, CODE_ARCH, LIAISON]


class OrchestratorState(TypedDict, total=False):
    incident_id: str
    channel_id: str
    user_id: str  # whose /ws stream receives this run's live events (T17)
    alert_payload: dict
    finding: dict | None  # InvestigationFinding.model_dump()
    log_report: dict | None  # LogTriageReport.model_dump()
    code_finding: dict | None  # CodeFinding.model_dump()
    customer_report: dict | None  # CustomerImpactReport.model_dump()
    stored_incident: dict | None  # StoredIncident.model_dump()
    verdict: dict | None  # CriticVerdict.model_dump()
    revision_count: int
    output: dict
    trace_id: str
    arize_trace_url: str


# --- helpers ---------------------------------------------------------------
async def _run_agent(agent, payload_json: str, on_event=None) -> tuple[str, int]:
    """Run one ADK agent on a JSON payload; return (final text, number of tool calls made).

    Fresh session per call — HiveMind investigates each incident in isolation (no cross-
    incident memory). ADK *explicit* context caching only reuses within a persistent
    session (proven in scripts/measure_caching.py), so it does NOT apply on this path and
    would only create throwaway caches; this path rides free *implicit* caching instead.
    See hivemind/caching.py for the explicit layer + when it pays off.
    """
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="hivemind", session_service=session_service)
    session = await session_service.create_session(
        app_name="hivemind", user_id="hivemind"
    )
    msg = types.Content(role="user", parts=[types.Part(text=payload_json)])
    final_text, tool_calls = "", 0

    async def _consume() -> None:
        nonlocal final_text, tool_calls
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=msg
        ):
            calls = event.get_function_calls() or []
            tool_calls += len(calls)
            if on_event:
                for call in calls:
                    # surface each tool call as a live status pill (e.g. execute_dql)
                    await on_event("tool_call", call.name)
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)

    try:
        await asyncio.wait_for(_consume(), timeout=AGENT_TIMEOUT)
    except asyncio.TimeoutError:
        # Hung/throttled agent → return what we have (likely empty); the per-hop critic
        # treats it as a failed attempt and retries, so the incident proceeds, never freezes.
        pass
    return final_text, tool_calls


async def _run_with_critic(
    agent, payload_json: str, schema, node_name: str, *, expect_tools: bool = True, on_event=None
) -> dict:
    """Run an agent, then apply the per-hop critic (schema-valid + non-empty + grounded).
    On failure, retry ONCE before proceeding — catching ungrounded/garbage output at the
    hop instead of letting it ride to the final Reviewer. Returns the validated dict."""
    text, tool_calls = "", 0
    for attempt in range(2):
        text, tool_calls = await _run_agent(agent, payload_json, on_event=on_event)
        crit = critique(text, schema, tool_calls, expect_tools=expect_tools)
        if crit.passed:
            return schema.model_validate_json(text).model_dump(mode="json")
        with _tracer.start_as_current_span(f"{node_name}.critic_reject") as s:
            s.set_attribute("attempt", attempt)
            s.set_attribute("tool_calls", tool_calls)
            s.set_attribute("reasons", "; ".join(crit.reasons))
    # Retries exhausted: proceed with the best-effort output (the final Reviewer is the
    # backstop); this raises only if it's truly unparseable, which ADK's output_schema
    # makes rare.
    return schema.model_validate_json(text).model_dump(mode="json")


def _services(state: OrchestratorState) -> list[str]:
    f = state.get("finding")
    if f and f.get("implicated_service"):
        return [f["implicated_service"]]
    return state["alert_payload"].get("affected_services", [])


def _incident_narrative(state: OrchestratorState) -> str:
    parts = [f"Alert: {state['alert_payload'].get('alert', '')}"]
    if (f := state.get("finding")):
        parts.append(f"Detective: {f.get('root_cause_hypothesis')} (confidence {f.get('confidence')}).")
    if (lr := state.get("log_report")):
        parts.append(f"LogDiver: {lr.get('summary')} ({lr.get('error_count')} errors).")
    if (cf := state.get("code_finding")):
        parts.append(f"CodeArch: {cf.get('explanation')} MR: {cf.get('merge_request_url')}.")
    if (cr := state.get("customer_report")):
        parts.append(
            f"CustomerLiaison: {cr.get('impact_summary')} ({cr.get('customers_affected')} customers)."
        )
    return " ".join(parts)


# --- live event emission (T17) ---------------------------------------------
async def _emit(state: OrchestratorState, event: dict) -> None:
    """Publish a war-room event, best-effort — an event-bus hiccup never fails the run."""
    try:
        await events.publish(state.get("user_id") or events.DEFAULT_USER, event)
    except Exception:  # noqa: BLE001
        pass


def _emit_cb(state: OrchestratorState, agent_id: str):
    """A status callback bound to one agent, passed into the agent runner so the
    pills update in real time as the agent thinks and calls tools."""
    cid = state["channel_id"]

    async def cb(agent_state: str, tool: str | None = None) -> None:
        await _emit(state, events.status(cid, agent_id, agent_state, tool))

    return cb


async def _stream_summary(state: OrchestratorState, agent_id: str, text: str) -> None:
    """Stream an agent's human-readable summary into the channel as token events,
    chunked for a 'typing' feel. The per-agent pacing is what makes the run feel live."""
    text = (text or "").strip()
    if not text:
        return
    cid = state["channel_id"]
    mid = f"{agent_id}-{uuid.uuid4().hex[:8]}"
    words = text.split()
    for i in range(0, len(words), 6):
        await _emit(state, events.token(cid, agent_id, mid, " ".join(words[i : i + 6]) + " "))
        await asyncio.sleep(0.03)


# --- nodes -----------------------------------------------------------------
async def detective_node(state: OrchestratorState) -> dict:
    p = state["alert_payload"]
    req = InvestigationRequest(
        channel_id=state["channel_id"],
        alert=p.get("alert", ""),
        affected_services=p.get("affected_services", []),
        severity=p.get("severity", "sev3"),
    )
    cb = _emit_cb(state, DETECTIVE)
    await cb("thinking")
    with _tracer.start_as_current_span(DETECTIVE):
        finding = await _run_with_critic(
            detective, req.model_dump_json(), InvestigationFinding, DETECTIVE, on_event=cb
        )
    await cb("done")
    await _stream_summary(state, DETECTIVE, finding.get("root_cause_hypothesis") or "")
    return {"finding": finding}


async def log_diver_node(state: OrchestratorState) -> dict:
    f = state.get("finding")
    req = LogQuery(
        channel_id=state["channel_id"],
        query=(f.get("root_cause_hypothesis") if f else state["alert_payload"].get("alert", "")),
        services=_services(state),
    )
    cb = _emit_cb(state, LOG_DIVER)
    await cb("thinking")
    with _tracer.start_as_current_span(LOG_DIVER):
        log_report = await _run_with_critic(
            log_diver, req.model_dump_json(), LogTriageReport, LOG_DIVER, on_event=cb
        )
    await cb("done")
    await _stream_summary(state, LOG_DIVER, log_report.get("summary") or "")
    return {"log_report": log_report}


async def code_arch_node(state: OrchestratorState) -> dict:
    f = state.get("finding")
    req = CodeSearchRequest(
        channel_id=state["channel_id"],
        question=((f.get("recommended_next_step") or f.get("root_cause_hypothesis")) if f else ""),
        incident_id=state["incident_id"],
        short_title=state["alert_payload"].get("alert", "")[:60],
        root_cause_hypothesis=(f.get("root_cause_hypothesis") if f else ""),
        confidence=(f.get("confidence") if f else 0.0),
        arize_trace_url=state.get("arize_trace_url"),
        dynatrace_notebook_url=(f.get("notebook_url") if f else None),
        workflow_public_url=(f.get("workflow_public_url") if f else None),
        # Ground CodeArch in the repo's real layout so it reads an actual file
        # instead of guessing paths (the bug that left mr_url null).
        repo_tree=fetch_repo_tree(),
    )
    cb = _emit_cb(state, CODE_ARCH)
    await cb("thinking")
    with _tracer.start_as_current_span(CODE_ARCH):
        code_finding = await _run_with_critic(
            code_arch, req.model_dump_json(), CodeFinding, CODE_ARCH, on_event=cb
        )
    await cb("done")
    _mr = code_finding.get("merge_request_url")
    await _stream_summary(
        state,
        CODE_ARCH,
        (code_finding.get("explanation") or "") + (f" (MR: {_mr})" if _mr else ""),
    )
    return {"code_finding": code_finding}


async def customer_liaison_node(state: OrchestratorState) -> dict:
    req = CustomerContextQuery(
        channel_id=state["channel_id"],
        affected_services=_services(state),
        severity=state["alert_payload"].get("severity", "sev3"),
        incident_id=state["incident_id"],
    )
    cb = _emit_cb(state, LIAISON)
    await cb("thinking")
    with _tracer.start_as_current_span(LIAISON):
        customer_report = await _run_with_critic(
            customer_liaison, req.model_dump_json(), CustomerImpactReport, LIAISON, on_event=cb
        )
    await cb("done")
    await _stream_summary(state, LIAISON, customer_report.get("impact_summary") or "")
    return {"customer_report": customer_report}


async def scribe_node(state: OrchestratorState) -> dict:
    f = state.get("finding")
    cf = state.get("code_finding")
    started_at = datetime.now(timezone.utc)
    title = ((f.get("root_cause_hypothesis")[:80] if f and f.get("root_cause_hypothesis") else None)
             or state["alert_payload"].get("alert", "incident")[:80])
    mr_url = cf.get("merge_request_url") if cf else None
    summary_in = IncidentSummary(
        channel_id=state["channel_id"],
        title=title,
        narrative=_incident_narrative(state),
        services=_services(state),
        severity=state["alert_payload"].get("severity", "sev3"),
        started_at=started_at,
        mr_url=mr_url,
        participants=[DETECTIVE, *FANOUT],
    )
    cb = _emit_cb(state, SCRIBE)
    await cb("thinking")
    with _tracer.start_as_current_span(SCRIBE):
        text, _ = await _run_agent(scribe, summary_in.model_dump_json(), on_event=cb)
    stored = StoredIncident.model_validate_json(text)

    # Scribe has no write tool — the node persists the synthesis to Atlas ColdMemory.
    incident = Incident(
        id=(stored.incident_id or state["incident_id"]),
        title=stored.title,
        summary=stored.summary,
        services=stored.services,
        severity=stored.severity,
        started_at=started_at,
        mr_url=mr_url,
        participants=summary_in.participants,
    )
    try:
        await ColdMemory().store_incident(incident)
        stored = stored.model_copy(update={"stored": True, "incident_id": incident.id})
    except Exception as e:  # noqa: BLE001 — don't fail the incident on an Atlas hiccup
        stored = stored.model_copy(update={"stored": False})
        with _tracer.start_as_current_span("scribe.persist_error") as s:
            s.set_attribute("error", f"{type(e).__name__}: {e}")
    await cb("done")
    await _stream_summary(state, SCRIBE, stored.summary or stored.title or "")
    return {"stored_incident": stored.model_dump(mode="json")}


async def reviewer_node(state: OrchestratorState) -> dict:
    # The orchestrator Reviewer gates the WHOLE incident, so it sees every output dict.
    incident_view = {
        k: state.get(k)
        for k in ("finding", "log_report", "code_finding", "customer_report", "stored_incident")
    }
    cb = _emit_cb(state, REVIEWER)
    await cb("thinking")
    with _tracer.start_as_current_span(REVIEWER):
        text, _ = await _run_agent(reviewer, json.dumps(incident_view, default=str), on_event=cb)
    verdict = CriticVerdict.model_validate_json(text)
    await cb("done")
    await _stream_summary(
        state,
        REVIEWER,
        f"Verdict: {verdict.verdict}."
        + (f" {verdict.rewrite_hint}" if verdict.rewrite_hint else ""),
    )
    out: dict = {"verdict": verdict.model_dump(mode="json")}
    if verdict.verdict == "revise":
        out["revision_count"] = state.get("revision_count", 0) + 1
    return out


# --- routing ---------------------------------------------------------------
def route_after_detective(state: OrchestratorState) -> list[str] | str:
    """Fan out to the 3 specialists if a service is implicated; else straight to the
    Reviewer (which escalates — nothing actionable to investigate)."""
    f = state.get("finding")
    return list(FANOUT) if (f and f.get("implicated_service")) else REVIEWER


def route_after_reviewer(state: OrchestratorState) -> str:
    v = state.get("verdict")
    if v and v.get("verdict") == "revise" and state.get("revision_count", 0) <= MAX_REVISIONS:
        return v.get("revise_target") or CODE_ARCH
    # approve, escalate, or revisions exhausted → build the output object, then END
    return "finalize"


def finalize_node(state: OrchestratorState) -> dict:
    """Build the public output object once the Reviewer approves or escalates."""
    v = state.get("verdict")
    f, cf, cr = state.get("finding"), state.get("code_finding"), state.get("customer_report")
    escalated = bool(v and v.get("verdict") == "escalate") or (
        bool(v and v.get("verdict") == "revise") and state.get("revision_count", 0) > MAX_REVISIONS
    )
    output = {
        "incident_id": state["incident_id"],
        "escalated": escalated,
        "mr_url": (cf.get("merge_request_url") if cf else None),
        "notebook_url": (f.get("notebook_url") if f else None),
        "customers_affected": (cr.get("customers_affected") if cr else None),
        "verdict": (v.get("verdict") if v else None),
        "arize_trace_url": state.get("arize_trace_url"),
    }
    if escalated:
        output["summary"] = (
            f"Incident {state['incident_id']} escalated to a human. "
            f"Reviewer: {v.get('rewrite_hint') if v else 'n/a'}."
        )
    return {"output": output}


# --- graph -----------------------------------------------------------------
def build_graph(checkpointer=None):
    g = StateGraph(OrchestratorState)
    g.add_node(DETECTIVE, detective_node)
    g.add_node(LOG_DIVER, log_diver_node)
    g.add_node(CODE_ARCH, code_arch_node)
    g.add_node(LIAISON, customer_liaison_node)
    g.add_node(SCRIBE, scribe_node)
    g.add_node(REVIEWER, reviewer_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, DETECTIVE)
    g.add_conditional_edges(DETECTIVE, route_after_detective, [*FANOUT, REVIEWER])
    for n in FANOUT:
        g.add_edge(n, SCRIBE)  # fan-in: Scribe waits for whichever specialists ran
    g.add_edge(SCRIBE, REVIEWER)
    # Reviewer can revise back to ANY specialist (incl. detective) or finalize. detective
    # must be in this list or a `revise -> detective` verdict KeyErrors in routing.
    g.add_conditional_edges(REVIEWER, route_after_reviewer, [DETECTIVE, *FANOUT, "finalize"])
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


# --- public entry point ----------------------------------------------------
class OrchestratorOutput(BaseModel):
    incident_id: str
    status: Literal["resolved", "escalated"]
    output: dict
    trace_id: str
    arize_trace_url: str | None = None


class OrchestratorRunner:
    """The public entry point: alert_payload -> OrchestratorOutput. Used by /chat and
    (T17) the Dynatrace webhook. Checkpoints to Redis (redis-stack) keyed by incident_id,
    so a process killed mid-incident RESUMES from its last checkpoint on restart instead
    of re-running completed agents. The whole run is one Phoenix incident span."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or _REDIS_URL

    async def run(self, alert_payload: dict) -> OrchestratorOutput:
        """Public entry point (/chat + webhook): returns just the output object."""
        out, _final = await self.run_full(alert_payload)
        return out

    async def run_full(self, alert_payload: dict) -> tuple[OrchestratorOutput, dict]:
        incident_id = alert_payload.get("incident_id") or f"INC-{uuid.uuid4().hex[:8]}"
        channel_id = alert_payload.get("channel_id", incident_id)
        user_id = alert_payload.get("user_id") or events.DEFAULT_USER
        config = {"configurable": {"thread_id": incident_id}}

        async with AsyncRedisSaver.from_conn_string(self._redis_url) as cp:
            await cp.asetup()  # idempotent RediSearch index creation
            graph = build_graph(cp)
            with _tracer.start_as_current_span("incident") as span:
                trace_id = format(span.get_span_context().trace_id, "032x")
                span.set_attribute("hivemind.incident_id", incident_id)
                # Resume if this incident has a mid-run checkpoint; else start fresh.
                try:
                    pending = bool((await graph.aget_state(config)).next)
                except Exception:  # noqa: BLE001
                    pending = False
                if pending:
                    final = await graph.ainvoke(None, config=config)
                else:
                    init: OrchestratorState = {
                        "incident_id": incident_id,
                        "channel_id": channel_id,
                        "user_id": user_id,
                        "alert_payload": alert_payload,
                        "revision_count": 0,
                        "trace_id": trace_id,
                        "arize_trace_url": _phoenix_trace_url(trace_id),
                    }
                    final = await graph.ainvoke(init, config=config)

        output = final.get("output", {})
        # Final "complete" event — the frontend swaps the streaming placeholder for the
        # resolved summary (MR link, notebook, customers affected, verdict).
        try:
            await events.publish(
                user_id, events.complete(channel_id, f"summary-{incident_id}", output)
            )
        except Exception:  # noqa: BLE001
            pass
        # run_full also returns the raw final state so the eval runner (T18) can assert
        # per-agent intermediate outputs (finding/code_finding/customer_report/…).
        return (
            OrchestratorOutput(
                incident_id=incident_id,
                status="escalated" if output.get("escalated") else "resolved",
                output=output,
                trace_id=final.get("trace_id") or "",
                arize_trace_url=final.get("arize_trace_url"),
            ),
            final,
        )


runner = OrchestratorRunner()
