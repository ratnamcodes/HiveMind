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

from agents.code_arch import CodeFinding, CodeSearchRequest, code_arch
from agents.customer_liaison import (
    CustomerContextQuery,
    CustomerImpactReport,
    customer_liaison,
)
from agents.detective import InvestigationFinding, InvestigationRequest, detective
from agents.log_diver import LogQuery, LogTriageReport, log_diver
from agents.reviewer import CriticVerdict, _phoenix_trace_url, reviewer
from agents.scribe import IncidentSummary, StoredIncident, scribe
from hivemind.memory import ColdMemory, Incident

load_dotenv()

MAX_REVISIONS = 2
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
async def _run_agent(agent, payload_json: str) -> str:
    """Run one ADK agent on a JSON payload; return its final text (its output schema)."""
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="hivemind", session_service=session_service)
    session = await session_service.create_session(
        app_name="hivemind", user_id="hivemind"
    )
    msg = types.Content(role="user", parts=[types.Part(text=payload_json)])
    final_text = ""
    async for event in runner.run_async(
        user_id=session.user_id, session_id=session.id, new_message=msg
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)
    return final_text


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


# --- nodes -----------------------------------------------------------------
async def detective_node(state: OrchestratorState) -> dict:
    p = state["alert_payload"]
    req = InvestigationRequest(
        channel_id=state["channel_id"],
        alert=p.get("alert", ""),
        affected_services=p.get("affected_services", []),
        severity=p.get("severity", "sev3"),
    )
    with _tracer.start_as_current_span(DETECTIVE):
        text = await _run_agent(detective, req.model_dump_json())
    return {"finding": InvestigationFinding.model_validate_json(text).model_dump(mode="json")}


async def log_diver_node(state: OrchestratorState) -> dict:
    f = state.get("finding")
    req = LogQuery(
        channel_id=state["channel_id"],
        query=(f.get("root_cause_hypothesis") if f else state["alert_payload"].get("alert", "")),
        services=_services(state),
    )
    with _tracer.start_as_current_span(LOG_DIVER):
        text = await _run_agent(log_diver, req.model_dump_json())
    return {"log_report": LogTriageReport.model_validate_json(text).model_dump(mode="json")}


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
    )
    with _tracer.start_as_current_span(CODE_ARCH):
        text = await _run_agent(code_arch, req.model_dump_json())
    return {"code_finding": CodeFinding.model_validate_json(text).model_dump(mode="json")}


async def customer_liaison_node(state: OrchestratorState) -> dict:
    req = CustomerContextQuery(
        channel_id=state["channel_id"],
        affected_services=_services(state),
        severity=state["alert_payload"].get("severity", "sev3"),
        incident_id=state["incident_id"],
    )
    with _tracer.start_as_current_span(LIAISON):
        text = await _run_agent(customer_liaison, req.model_dump_json())
    return {"customer_report": CustomerImpactReport.model_validate_json(text).model_dump(mode="json")}


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
    with _tracer.start_as_current_span(SCRIBE):
        text = await _run_agent(scribe, summary_in.model_dump_json())
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
    return {"stored_incident": stored.model_dump(mode="json")}


async def reviewer_node(state: OrchestratorState) -> dict:
    # The orchestrator Reviewer gates the WHOLE incident, so it sees every output dict.
    incident_view = {
        k: state.get(k)
        for k in ("finding", "log_report", "code_finding", "customer_report", "stored_incident")
    }
    with _tracer.start_as_current_span(REVIEWER):
        text = await _run_agent(reviewer, json.dumps(incident_view, default=str))
    verdict = CriticVerdict.model_validate_json(text)
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
    g.add_conditional_edges(REVIEWER, route_after_reviewer, [*FANOUT, "finalize"])
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
        incident_id = alert_payload.get("incident_id") or f"INC-{uuid.uuid4().hex[:8]}"
        channel_id = alert_payload.get("channel_id", incident_id)
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
                        "alert_payload": alert_payload,
                        "revision_count": 0,
                        "trace_id": trace_id,
                        "arize_trace_url": _phoenix_trace_url(trace_id),
                    }
                    final = await graph.ainvoke(init, config=config)

        output = final.get("output", {})
        return OrchestratorOutput(
            incident_id=incident_id,
            status="escalated" if output.get("escalated") else "resolved",
            output=output,
            trace_id=final.get("trace_id") or "",
            arize_trace_url=final.get("arize_trace_url"),
        )


runner = OrchestratorRunner()
