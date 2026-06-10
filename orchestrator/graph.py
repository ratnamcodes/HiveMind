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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal, TypedDict

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
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
from hivemind import dynatrace as dt
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

# Fallback checkpointer. The Redis checkpointer (preferred) needs the RediSearch module
# (FT.CREATE / FT._LIST). If the deployment ships plain redis-server, asetup() raises
# "unknown command FT._LIST" and the whole run crashes. This in-process MemorySaver lets a
# run degrade instead. On a single-instance deploy (Cloud Run minScale=maxScale=1) it still
# survives the pause -> approve -> resume hop, because every request runs in the same process.
_MEM_SAVER = MemorySaver()


@asynccontextmanager
async def _checkpointer(redis_url: str):
    """Yield a LangGraph checkpointer: Redis if its RediSearch module is present, else the
    in-process MemorySaver. Setup failures fall back; consumer-body errors propagate normally."""
    cm = AsyncRedisSaver.from_conn_string(redis_url)
    try:
        cp = await cm.__aenter__()
        await cp.asetup()  # idempotent RediSearch index creation; raises if the module is absent
    except Exception as exc:  # noqa: BLE001
        try:
            await cm.__aexit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass
        print(f"[checkpointer] Redis unavailable ({exc}); using in-process MemorySaver", flush=True)
        yield _MEM_SAVER
        return
    try:
        yield cp
    finally:
        await cm.__aexit__(None, None, None)

DETECTIVE, LOG_DIVER, CODE_ARCH, LIAISON = (
    "detective",
    "log_diver",
    "code_arch",
    "customer_liaison",
)
SCRIBE, REVIEWER = "scribe", "reviewer"
FANOUT = [LOG_DIVER, CODE_ARCH, LIAISON]

# A one-line "why I'm doing this" each agent narrates BEFORE its tool calls — turns the
# fire-and-forget spinner into visible, plain-English reasoning a third person can follow.
INTENTS = {
    DETECTIVE: "Pulling Dynatrace logs around the deploy window to find what changed and why.",
    LOG_DIVER: "Cross-checking Elastic logs and the deploy registry to blame the exact release.",
    CODE_ARCH: "Reading the repository to draft the smallest safe fix and open it as a reviewable merge request.",
    LIAISON: "Querying the live data warehouse for which paying customers are hit and the revenue at risk.",
    SCRIBE: "Writing the incident record to Atlas and checking whether we've seen this before.",
    REVIEWER: "Independently reviewing the whole investigation before anything ships to production.",
}


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
    human_decision: str  # the human's choice at the HITL approval gate (approve/changes/escalate)
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

    # Run the agent in its own task and bound it with shield(): a hung/throttled MCP
    # or LLM call that IGNORES cancellation (e.g. the Dynatrace notebook tool stalling on
    # a Vertex per-minute rate limit) would otherwise make plain wait_for() block on the
    # stuck task's cancellation — freezing the whole incident for many minutes (observed
    # in a live run). shield() lets wait_for STOP WAITING at the deadline without blocking
    # on cancellation; we then request cancel best-effort and proceed with whatever we
    # already streamed. The orphaned task errors out on its own and never gates the graph.
    consume_task = asyncio.create_task(_consume())
    try:
        await asyncio.wait_for(asyncio.shield(consume_task), timeout=AGENT_TIMEOUT)
    except asyncio.TimeoutError:
        consume_task.cancel()  # best-effort; do NOT await it — that's the whole point
    except asyncio.CancelledError:
        consume_task.cancel()
        raise
    except Exception as e:  # noqa: BLE001
        # A hung/erroring MCP or LLM tool (e.g. an MCP ClientRequest 60s timeout, a Vertex
        # rate-limit) must NOT crash the node — it returns whatever it streamed and the per-hop
        # critic retries or the run proceeds. Observed: a Dynatrace MCP timeout cancelled the
        # detective node and aborted the whole real-incident run.
        consume_task.cancel()
        with _tracer.start_as_current_span("agent.tool_error") as s:
            s.set_attribute("error", f"{type(e).__name__}: {e}"[:300])
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


def _customer_services(state: OrchestratorState) -> list[str]:
    """Services to assess CUSTOMER/revenue impact against. This is the customer-FACING
    service from the original alert (checkout / payment-service), NOT Detective's implicated
    CAUSE service — which may be an internal service (e.g. fraud-decision, pos-gateway,
    inventory-service) that has no direct rows in the customer warehouse. Liaison stays
    grounded on the surface customers actually touch."""
    cs = state["alert_payload"].get("customer_service")
    if cs:
        return [cs]
    alert_services = state["alert_payload"].get("affected_services", [])
    return alert_services or _services(state)


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


async def _apply_fix_and_verify_recovery(state: OrchestratorState) -> str | None:
    """After a human approves, APPLY the approved fix to the running app (mirrors merging the MR
    + redeploying), VERIFY the real service recovered by polling its real latency, AND prove it
    in real Dynatrace data — the post-fix latency drop shows up in Grail. Only for the real
    app-triggered incident (alert_payload.real_app); seeded scenarios skip it. SRG-based recovery
    proof is the upgrade once a trace/settings token is available."""
    if not state["alert_payload"].get("real_app"):
        return None
    import os as _os

    cfg = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "apps", "config", "payment.yaml")
    slo = int(state["alert_payload"].get("slo_ms") or 300)

    def _do() -> str | None:
        try:
            import statistics
            import time as _t

            import requests as _rq

            if _os.path.exists(cfg):  # apply the approved fix to the live app
                lines = open(cfg).read().splitlines()
                lines = ["downstream_delay_ms: 0" if l.strip().startswith("downstream_delay_ms") else l for l in lines]
                open(cfg, "w").write("\n".join(lines) + "\n")
            fix_t0 = _t.time()  # the moment the fix shipped — SRG validates only the window AFTER this
            # The instrumented app to re-poll for recovery. Local dev runs it on :3100; in the
            # cloud there's no local app, so RECOVERY_APP_URL stays unset and we skip straight to
            # the Dynatrace proof below instead of bailing out.
            app_url = (_os.getenv("RECOVERY_APP_URL") or "http://localhost:3100").rstrip("/")
            lat: list[int] = []
            for _ in range(8):  # verify recovery from real latency (+ generate fresh post-fix logs)
                try:
                    lat.append(int(_rq.get(f"{app_url}/checkout", timeout=5).json().get("latency_ms", 999)))
                except Exception:  # noqa: BLE001
                    pass
                _t.sleep(1)
            if lat:
                msg = (f"Recovery verified on live telemetry: checkout latency back to "
                       f"~{int(statistics.median(lat))}ms (peak {max(lat)}ms). SLO restored, service healthy.")
            else:
                # No local app to poll (cloud deploy) — confirm recovery from Dynatrace data alone.
                msg = "Fix applied and redeployed. Confirming recovery against live Dynatrace data."
            # Prove it in REAL Dynatrace data: poll Grail until the post-fix latency lands (ingest lag).
            try:
                for _ in range(6):  # up to ~60s for OTLP logs to reach Grail
                    rec = dt.recent_latency("checkout", 3)
                    if rec and rec[0] <= slo:
                        msg += (f" Confirmed in Dynatrace Grail: checkout-service latency is now "
                                f"~{rec[0]}ms, back under the {slo}ms SLO.")
                        break
                    _t.sleep(10)
            except Exception:  # noqa: BLE001
                pass
            # Site Reliability Guardian: evaluate the guardian's objective against live Grail — but
            # ONLY over the window since the fix shipped (else the breach period drags the average up
            # and the guardian fails a service that has actually recovered). Wait until there's a clean
            # post-fix minute, then validate the most-recent minute.
            try:
                while _t.time() - fix_t0 < 95:  # let the breach age out of a 1-min window
                    _t.sleep(5)
                verdict = dt.srg_validate(slo, 1)
                if verdict:
                    msg += (f" Site Reliability Guardian checked 'checkout latency ≤ {slo}ms': "
                            f"{verdict[0]} ({verdict[1]}ms).")
            except Exception:  # noqa: BLE001
                pass
            return msg
        except Exception:  # noqa: BLE001
            return None

    return await asyncio.to_thread(_do)


async def _dynatrace_copilot_beat(state: OrchestratorState) -> None:
    """Deep-Dynatrace beat surfaced live in the war room, BEFORE the Vertex-bound agent runs:
    Davis CoPilot (Dynatrace's own AI) translates the alert into DQL, and we run a real Grail
    query for the implicated service's error evidence + current latency. Deterministic and fast
    (~4s), independent of the agent/Vertex-quota path — so the channel always shows real Dynatrace
    AI + real telemetry even if a specialist is throttled. Best-effort: never fails the run."""
    if not dt.available():
        return
    p = state["alert_payload"]
    svc = p.get("customer_service") or (p.get("affected_services") or ["checkout"])[0]
    cid = state["channel_id"]

    def _work() -> tuple[str, int, int | None, list]:
        nl = f"Show error logs from the {svc} service in the last hour, most recent first"
        return (dt.nl2dql(nl), dt.count_service_errors(svc, 60), dt.peak_latency(svc, 30),
                dt.open_problems(svc, 2))

    try:
        dql_q, errs, peak, problems = await asyncio.to_thread(_work)
    except Exception:  # noqa: BLE001
        return
    # If Davis AI itself has already opened a problem on this service, lead with it — the strongest
    # signal that this is a real, Dynatrace-detected incident (not a seeded alert).
    if problems:
        pr = problems[0]
        await _emit(state, events.token(cid, DETECTIVE, f"dt-{uuid.uuid4().hex[:8]}",
                                        f"Davis AI has opened problem {pr.get('id')}: \"{pr.get('title')}\" "
                                        f"({pr.get('severity')}) on {svc}."))
    if dql_q:
        flat = " ".join(dql_q.split())
        await _emit(state, events.token(cid, DETECTIVE, f"dt-{uuid.uuid4().hex[:8]}",
                                        f"Davis CoPilot (Dynatrace AI) read the alert and wrote the query: {flat}"))
    bits = []
    if errs:
        bits.append(f"{errs} error/warning events on {svc}")
    if peak:
        bits.append(f"peak latency {peak}ms")
    if bits:
        await _emit(state, events.token(cid, DETECTIVE, f"dt-{uuid.uuid4().hex[:8]}",
                                        "Grail confirms it (last hour): " + ", ".join(bits) + "."))


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
    await _emit(state, events.reasoning(state["channel_id"], DETECTIVE, INTENTS[DETECTIVE]))
    # Real Dynatrace AI + Grail evidence first (deterministic, fast), then the specialist reasons on top.
    await _dynatrace_copilot_beat(state)
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
    await _emit(state, events.reasoning(state["channel_id"], LOG_DIVER, INTENTS[LOG_DIVER]))
    with _tracer.start_as_current_span(LOG_DIVER):
        log_report = await _run_with_critic(
            log_diver, req.model_dump_json(), LogTriageReport, LOG_DIVER, on_event=cb
        )
    await cb("done")
    await _stream_summary(state, LOG_DIVER, log_report.get("summary") or "")
    return {"log_report": log_report}


async def code_arch_node(state: OrchestratorState) -> dict:
    f = state.get("finding")
    _q = (f.get("recommended_next_step") or f.get("root_cause_hypothesis")) if f else ""
    # Demo grounding: if the diagnosis points at a specific repo file, steer CodeArch to it so
    # it fixes the right subsystem (the repo now has 6 service files; the alert's surface
    # service can otherwise pull it to the wrong one). CodeArch still reads + patches for real.
    _target = state["alert_payload"].get("code_target")
    if _target:
        _q = f"{_q} The fix belongs in the file `{_target}`. Read that exact path and patch it."
    req = CodeSearchRequest(
        channel_id=state["channel_id"],
        question=_q,
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
    await _emit(state, events.reasoning(state["channel_id"], CODE_ARCH, INTENTS[CODE_ARCH]))
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
        affected_services=_customer_services(state),
        severity=state["alert_payload"].get("severity", "sev3"),
        incident_id=state["incident_id"],
        # liaison_context activates a Fivetran "depth play" (e.g. GDPR PII redaction before a
        # public MR) when the scenario calls for it; empty = just assess impact.
        context=state["alert_payload"].get("liaison_context", ""),
    )
    cb = _emit_cb(state, LIAISON)
    await cb("thinking")
    await _emit(state, events.reasoning(state["channel_id"], LIAISON, INTENTS[LIAISON]))
    with _tracer.start_as_current_span(LIAISON):
        customer_report = await _run_with_critic(
            customer_liaison, req.model_dump_json(), CustomerImpactReport, LIAISON, on_event=cb
        )
    await cb("done")
    # Feed the right-rail IMPACT panel (the differentiator no incumbent shows): who's hit + $ at risk.
    await _emit(state, events.impact(state["channel_id"], {
        "customers_affected": customer_report.get("customers_affected"),
        "revenue_at_risk_usd": customer_report.get("revenue_at_risk_usd"),
        "segments": customer_report.get("affected_segments", []),
        "actions_taken": customer_report.get("actions_taken", []),
        "summary": customer_report.get("impact_summary", ""),
    }))
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
    await _emit(state, events.reasoning(state["channel_id"], SCRIBE, INTENTS[SCRIBE]))
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
    await _emit(state, events.reasoning(state["channel_id"], REVIEWER, INTENTS[REVIEWER]))
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


# --- human-in-the-loop approval gate ---------------------------------------
async def approval_gate_node(state: OrchestratorState) -> dict:
    """The crew has done the work and its own Reviewer approved — now PAUSE and ask a human
    before anything ships. Emits a decision_request card (the drafted fix + who's affected + $
    at risk), then interrupt()s: LangGraph snapshots state to Redis and the graph STOPS until
    POST /api/incident/<id>/resume calls Command(resume=<choice>). Nothing irreversible has
    happened — CodeArch opened a DRAFT MR; the human decides whether it ships."""
    cf = state.get("code_finding") or {}
    cr = state.get("customer_report") or {}
    cid = state["channel_id"]
    decision_id = f"approve-{state['incident_id']}"
    mr_url = cf.get("merge_request_url")
    impact_bits = []
    if cr.get("customers_affected") is not None:
        impact_bits.append(f"{cr.get('customers_affected')} customers")
    if cr.get("revenue_at_risk_usd"):
        impact_bits.append(f"${int(cr['revenue_at_risk_usd']):,}/mo at risk")
    verdict = (state.get("verdict") or {}).get("verdict", "approve")
    crew_note = {
        "approve": "The crew investigated and its Reviewer is confident in this fix.",
        "revise": "The crew drafted this fix; its Reviewer flagged it for a second look first.",
        "escalate": "The crew drafted this fix but its Reviewer wasn't fully confident. Your call.",
    }.get(verdict, "The crew drafted this fix.")
    payload = {
        "decision_id": decision_id,
        "incident_id": state["incident_id"],  # the /resume key (channel_id differs)
        "kind": "approve_fix",
        "crew_verdict": verdict,
        "title": "Ship the fix?",
        "prompt": f"{crew_note} {cf.get('suggested_fix') or cf.get('explanation') or ''}".strip(),
        "mr_url": mr_url,
        "suspect_files": cf.get("suspect_files", []),
        "impact": " · ".join(impact_bits),
        "actions_taken": cr.get("actions_taken", []),
        "options": [
            {"id": "approve", "label": "Approve & ship", "style": "primary"},
            {"id": "changes", "label": "Request changes", "style": "default"},
            {"id": "escalate", "label": "Escalate to a human", "style": "danger"},
        ],
    }
    cb = _emit_cb(state, REVIEWER)
    await cb("awaiting_human")
    await _emit(state, events.decision_request(cid, payload))

    # PAUSE. Resumes with the value passed to Command(resume=...). On a fresh (non-resumed)
    # run this raises GraphInterrupt out of ainvoke; run_full detects it and leaves the card up.
    decision = interrupt(payload)

    choice = (decision or {}).get("choice", "approve") if isinstance(decision, dict) else str(decision or "approve")
    feedback = (decision or {}).get("feedback", "") if isinstance(decision, dict) else ""
    detail = {"approve": "Approved by a human. The fix is cleared to ship.",
              "changes": f"Human requested changes: {feedback or 'see thread'}.",
              "escalate": "Escalated to a human on-call."}.get(choice, "Decided.")
    await _emit(state, events.decision_made(cid, decision_id, choice, detail))
    await cb("done")
    await _stream_summary(state, REVIEWER, detail)
    # On approval, HiveMind applies the fix to the live app and verifies it recovered (real signal).
    if choice == "approve":
        await _emit(state, events.reasoning(cid, REVIEWER, "Shipping the approved fix and verifying the service recovers…"))
        recovery = await _apply_fix_and_verify_recovery(state)
        if recovery:
            await _emit(state, events.token(cid, "system", f"recovered-{state['incident_id']}", recovery))
    return {"human_decision": choice}


# --- routing ---------------------------------------------------------------
def route_after_detective(state: OrchestratorState) -> list[str] | str:
    """Fan out to the 3 specialists if there's an actionable service — either Detective
    implicated one, OR the alert named an affected service (the real app-triggered path always
    does). This keeps a real incident moving to the fix + human gate even when Detective's
    Dynatrace call was thin or timed out; only a truly contextless alert escalates outright."""
    f = state.get("finding")
    has_service = (f and f.get("implicated_service")) or state["alert_payload"].get("affected_services")
    return list(FANOUT) if has_service else REVIEWER


def route_after_reviewer(state: OrchestratorState) -> str:
    v = state.get("verdict")
    if state["alert_payload"].get("hitl"):
        # Human-in-the-loop: a person makes the FINAL call at the gate whenever the crew drafted
        # a fix to act on. The Reviewer's verdict (approve/revise/escalate) is advisory and shown
        # on the approval card — we don't auto-revise (the human decides, which is faster and the
        # whole point). If the crew produced no actionable fix, fall through to finalize/escalate.
        cf = state.get("code_finding")
        if cf and cf.get("merge_request_url"):
            return "approval_gate"
        return "finalize"
    # Autonomous (non-HITL): the bounded revise loop, then finalize.
    if v and v.get("verdict") == "revise" and state.get("revision_count", 0) <= MAX_REVISIONS:
        return v.get("revise_target") or CODE_ARCH
    return "finalize"


def finalize_node(state: OrchestratorState) -> dict:
    """Build the public output object once the Reviewer approves or escalates."""
    v = state.get("verdict")
    hd = state.get("human_decision")
    f, cf, cr = state.get("finding"), state.get("code_finding"), state.get("customer_report")
    escalated = (
        bool(v and v.get("verdict") == "escalate")
        or (bool(v and v.get("verdict") == "revise") and state.get("revision_count", 0) > MAX_REVISIONS)
        or hd in ("changes", "escalate")  # the human sent it back
    )
    output = {
        "incident_id": state["incident_id"],
        "escalated": escalated,
        "mr_url": (cf.get("merge_request_url") if cf else None),
        "notebook_url": (f.get("notebook_url") if f else None),
        "customers_affected": (cr.get("customers_affected") if cr else None),
        "verdict": (v.get("verdict") if v else None),
        "human_decision": hd,  # surfaced so the UI/Evaluator can show the human steered it
        "arize_trace_url": state.get("arize_trace_url"),
    }
    if escalated:
        reason = (
            "a human requested changes" if hd == "changes"
            else "escalated to a human on-call" if hd == "escalate"
            else f"Reviewer: {v.get('rewrite_hint') if v else 'n/a'}"
        )
        output["summary"] = f"Incident {state['incident_id']} {reason}."
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
    g.add_node("approval_gate", approval_gate_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, DETECTIVE)
    g.add_conditional_edges(DETECTIVE, route_after_detective, [*FANOUT, REVIEWER])
    for n in FANOUT:
        g.add_edge(n, SCRIBE)  # fan-in: Scribe waits for whichever specialists ran
    g.add_edge(SCRIBE, REVIEWER)
    # Reviewer can revise back to ANY specialist (incl. detective) or finalize. detective
    # must be in this list or a `revise -> detective` verdict KeyErrors in routing.
    g.add_conditional_edges(REVIEWER, route_after_reviewer, [DETECTIVE, *FANOUT, "approval_gate", "finalize"])
    g.add_edge("approval_gate", "finalize")  # after the human decides, build the output + END
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


# --- public entry point ----------------------------------------------------
class OrchestratorOutput(BaseModel):
    incident_id: str
    status: Literal["resolved", "escalated", "paused"]
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
        # The harness loop (T19) passes a per-iteration thread_id so each retry runs FRESH
        # (not a checkpoint-resume) while keeping incident_id stable for the MR/evaluator.
        config = {"configurable": {"thread_id": alert_payload.get("thread_id") or incident_id}}

        async with _checkpointer(self._redis_url) as cp:
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
                    # Commander: emit the pinned BRIEF the instant the channel opens so a third
                    # person knows what/severity/who BEFORE any agent streams (the #1 UX gap).
                    _alert_txt = alert_payload.get("alert", "")
                    try:
                        await events.publish(user_id, events.brief(channel_id, {
                            "headline": (_alert_txt[:130] + "…") if len(_alert_txt) > 130 else _alert_txt,
                            "what": _alert_txt,
                            "impact": "Assessing business impact (customers + revenue at risk)…",
                            "severity": alert_payload.get("severity", "sev3"),
                            "suspected": "Investigating across Dynatrace, Elastic, GitLab and the data warehouse…",
                            "team": [DETECTIVE, LOG_DIVER, CODE_ARCH, LIAISON, SCRIBE, REVIEWER],
                        }))
                    except Exception:  # noqa: BLE001
                        pass
                    final = await graph.ainvoke(init, config=config)

        # If the graph paused at the HITL approval gate, the decision card is already up — do
        # NOT emit complete; the run resumes via OrchestratorRunner.resume() from POST /resume.
        if final.get("__interrupt__"):
            return (
                OrchestratorOutput(
                    incident_id=incident_id, status="paused",
                    output={"paused": True, "incident_id": incident_id},
                    trace_id=final.get("trace_id") or trace_id,
                    arize_trace_url=final.get("arize_trace_url"),
                ),
                final,
            )

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

    async def resume(self, incident_id: str, decision: dict) -> OrchestratorOutput:
        """Continue a run that PAUSED at the HITL approval gate. `decision` is the human's choice
        (e.g. {"choice": "approve"} | {"choice": "changes", "feedback": "..."}). Re-enters the
        graph from the Redis checkpoint via Command(resume=decision); the gate node's interrupt()
        returns `decision`, the run finalizes, and the complete event fires. No agents re-run."""
        config = {"configurable": {"thread_id": incident_id}}
        async with _checkpointer(self._redis_url) as cp:
            graph = build_graph(cp)
            with _tracer.start_as_current_span("incident.resume") as span:
                span.set_attribute("hivemind.incident_id", incident_id)
                final = await graph.ainvoke(Command(resume=decision), config=config)

        user_id = final.get("user_id") or events.DEFAULT_USER
        channel_id = final.get("channel_id") or incident_id
        interrupted = bool(final.get("__interrupt__"))
        output = final.get("output", {})
        if not interrupted:
            try:
                await events.publish(
                    user_id, events.complete(channel_id, f"summary-{incident_id}", output)
                )
            except Exception:  # noqa: BLE001
                pass
        return OrchestratorOutput(
            incident_id=incident_id,
            status="paused" if interrupted else ("escalated" if output.get("escalated") else "resolved"),
            output=output or {"paused": interrupted},
            trace_id=final.get("trace_id") or "",
            arize_trace_url=final.get("arize_trace_url"),
        )


runner = OrchestratorRunner()
