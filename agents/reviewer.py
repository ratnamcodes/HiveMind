"""Reviewer — HiveMind's critic, Phoenix-backed (T13).

- Rubric (system prompt) is pulled at runtime from Phoenix prompt management (the
  `production`-tagged `hivemind-critic-rubric`) via an ADK instruction provider, so
  a T18 retag ships a new rubric without redeploy.
- Carries the Phoenix MCP toolset (read traces, manage the rubric prompt, read
  datasets/experiments) — the meta-loop "seeds".
- `review()` runs the critic inside one OTEL span, captures that run's Phoenix
  trace URL (for CodeArch to stamp into the MR — T11), and writes the verdict as a
  span annotation the T18 flywheel mines for critic miss-patterns. (phoenix-mcp has
  no write-annotation tool, so the annotation goes through the phoenix-client SDK.)

Its input is the *output* of any other agent, so it imports their output schemas.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import warnings
from typing import Literal

from dotenv import load_dotenv
from google.adk.agents import LlmAgent as Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from opentelemetry import trace as otel_trace
from pydantic import BaseModel, Field

from agents.code_arch import CodeFinding
from agents.customer_liaison import CustomerImpactReport
from agents.detective import InvestigationFinding
from agents.log_diver import LogTriageReport
from agents.scribe import StoredIncident

load_dotenv()

PROMPT_NAME = "hivemind-critic-rubric"
PRODUCTION_TAG = "production"
_PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://localhost:6006").rstrip("/")
_PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT", "hivemind")

# Baked-in copy of the seed v1 rubric — used ONLY as a fallback when Phoenix is
# unreachable, so the Reviewer always constructs with a usable instruction.
CRITIC_RUBRIC_FALLBACK = (
    "You are Reviewer, the critic of HiveMind. You score every agent output "
    "against the rubric and reject anything ungrounded, contradicted by "
    "evidence, or below the quality bar. Your verdict is one of {approve, "
    "revise, escalate}. You always cite the specific rubric line and the "
    "offending fragment."
)

_last_good_rubric: str | None = None
_project_id_cache: str | None = None


def _pull_production_rubric() -> str:
    """Return the production-tagged rubric's system text from Phoenix.

    Reads the raw template messages off the PromptVersion instead of `.format()`:
    with model_provider == GOOGLE, `.format()` imports the legacy `google.generativeai`
    SDK, which this project deliberately doesn't install.
    """
    from phoenix.client import Client

    pv = Client(base_url=_PHOENIX_HOST).prompts.get(
        prompt_identifier=PROMPT_NAME, tag=PRODUCTION_TAG
    )
    messages = pv._template["messages"]  # noqa: SLF001 — see docstring
    system_text = "\n\n".join(
        m["content"]
        for m in messages
        if m.get("role") == "system" and m.get("content")
    )
    if not system_text:
        raise ValueError(f"no system message in {PROMPT_NAME}@{PRODUCTION_TAG}")
    return system_text


def load_rubric(_ctx: object = None) -> str:
    """ADK instruction provider: the current production rubric (re-fetched per
    invocation, so a T18 retag ships live). Falls back to last good, then baked-in."""
    global _last_good_rubric
    try:
        _last_good_rubric = _pull_production_rubric()
        return _last_good_rubric
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"rubric pull from Phoenix failed ({type(exc).__name__}: {exc}); "
            "using fallback rubric.",
            stacklevel=2,
        )
        return _last_good_rubric or CRITIC_RUBRIC_FALLBACK


# ---- schemas --------------------------------------------------------------
# An agent output is ANY ONE of these five shapes.
AgentOutput = (
    InvestigationFinding
    | LogTriageReport
    | CodeFinding
    | CustomerImpactReport
    | StoredIncident
)


class AnyAgentOutput(BaseModel):
    """Wraps one specialist's output together with who produced it."""

    producer: Literal[
        "Detective", "LogDiver", "CodeArch", "CustomerLiaison", "Scribe"
    ]
    output: AgentOutput


class RubricFinding(BaseModel):
    """One concrete way an agent output violates the rubric."""

    rubric_line: str  # the rubric expectation it breaks
    fragment: str  # the offending fragment of the reviewed output
    severity: int = Field(description="1 (minor) .. 5 (critical)")


class CriticVerdict(BaseModel):
    """What Reviewer returns: a grounded verdict on another agent's output."""

    verdict: Literal["approve", "revise", "escalate"]
    rubric_findings: list[RubricFinding] = Field(default_factory=list)
    rewrite_hint: str | None = None
    # On a `revise` verdict, which specialist should redo its work (orchestrator
    # routing — `rewrite_hint` is the human-readable "why", this is the machine target).
    revise_target: (
        Literal["detective", "log_diver", "code_arch", "customer_liaison"] | None
    ) = None


# ---- Phoenix MCP toolset (the meta-loop "seeds") --------------------------
# Same self-hosted Phoenix the traces land in; we spread os.environ so the
# `/usr/bin/env node` shebang resolves and PHOENIX_HOST/PHOENIX_API_KEY (if set,
# for Cloud) reach the subprocess. NOTE the spec's literal env
# (PHOENIX_API_KEY=ARIZE_API_KEY, PHOENIX_BASE_URL=app.arize.com) 401s — proven —
# because phoenix-mcp speaks the Phoenix API, not Arize AX.
phoenix_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=shutil.which("phoenix-mcp") or "phoenix-mcp",
            args=[],
            env={**os.environ, "PHOENIX_HOST": _PHOENIX_HOST},
        ),
        timeout=30.0,
    ),
    # On-rails: read traces, manage the rubric prompt, read datasets/experiments.
    # phoenix-mcp has NO write-annotation tool, so add-span-annotation is done via
    # the SDK in review() below; running experiments is SDK-only too (T18).
    tool_filter=[
        "list-projects",
        "list-traces",
        "get-trace",
        "get-spans",
        "get-span-annotations",
        "list-prompts",
        "get-prompt",
        "get-prompt-version-by-tag",
        "list-prompt-versions",
        "upsert-prompt",
        "add-prompt-version-tag",
        "list-datasets",
        "get-dataset",
        "list-experiments-for-dataset",
        "get-experiment-by-id",
    ],
)


reviewer = Agent(
    name="reviewer",
    model="gemini-3.5-flash",
    instruction=load_rubric,  # runtime pull of the production rubric (T13 step 5)
    output_schema=CriticVerdict,
    generate_content_config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high"),
    ),
    tools=[phoenix_tools],
)


# ---- review(): run the critic, capture the trace, annotate the span -------
class ReviewResult(BaseModel):
    """What the orchestrator gets back from a review pass."""

    verdict: CriticVerdict
    arize_trace_url: str  # Phoenix deep-link; CodeArch stamps it into the MR (T11)
    reviewer_span_id: str
    annotation_written: bool


def _phoenix_trace_url(trace_id: str) -> str:
    """Deep-link to this run's trace in the Phoenix UI. localhost today; becomes a
    Phoenix Cloud URL once PHOENIX_HOST points there — identical shape."""
    global _project_id_cache
    if not _project_id_cache:  # None or "" — never cache an empty miss; retry next time
        import httpx

        try:
            data = httpx.get(f"{_PHOENIX_HOST}/v1/projects", timeout=10).json()["data"]
            _project_id_cache = next(
                (p["id"] for p in data if p["name"] == _PHOENIX_PROJECT), ""
            )
        except Exception:  # noqa: BLE001
            _project_id_cache = ""
    pid = _project_id_cache or _PHOENIX_PROJECT
    return f"{_PHOENIX_HOST}/projects/{pid}/traces/{trace_id}"


def _findings_text(verdict: CriticVerdict) -> str:
    """Human-readable rendering of the verdict for the span annotation."""
    lines = [
        f"[sev {f.severity}] {f.rubric_line}: {f.fragment}"
        for f in verdict.rubric_findings
    ] or ["(no specific rubric findings)"]
    if verdict.rewrite_hint:
        lines.append(f"rewrite_hint: {verdict.rewrite_hint}")
    return "\n".join(lines)


async def _annotate_verdict(span_id: str, verdict: CriticVerdict) -> bool:
    """Write the verdict onto the reviewer span via the phoenix-client SDK. Retries
    while Phoenix finishes ingesting the just-flushed span."""
    from phoenix.client import Client

    client = Client(base_url=_PHOENIX_HOST)
    score = {"approve": 1.0, "revise": 0.5, "escalate": 0.0}.get(verdict.verdict)
    for _ in range(5):
        try:
            client.spans.add_span_annotation(
                span_id=span_id,
                annotation_name="reviewer_verdict",
                annotator_kind="LLM",
                label=verdict.verdict,
                score=score,
                explanation=_findings_text(verdict),
                metadata={
                    "rubric_findings": [f.model_dump() for f in verdict.rubric_findings],
                    "rewrite_hint": verdict.rewrite_hint,
                },
                sync=True,
            )
            return True
        except Exception:  # noqa: BLE001
            await asyncio.sleep(1.0)
    return False


async def review(payload: AnyAgentOutput) -> ReviewResult:
    """Run the critic on one agent output; return the verdict, this run's Phoenix
    trace URL, and whether the verdict was annotated onto the reviewer span.

    The whole pass runs inside one OTEL `reviewer` span so the Gemini call + tool
    calls nest under it and share a trace id we can deep-link to and annotate.
    """
    tracer = otel_trace.get_tracer("hivemind.reviewer")
    session_service = InMemorySessionService()
    runner = Runner(
        agent=reviewer, app_name="hivemind", session_service=session_service
    )
    session = await session_service.create_session(
        app_name="hivemind", user_id="hivemind"
    )
    message = types.Content(
        role="user", parts=[types.Part(text=payload.model_dump_json())]
    )

    final_text = ""
    with tracer.start_as_current_span("reviewer") as span:
        sctx = span.get_span_context()
        trace_id = format(sctx.trace_id, "032x")
        span_id = format(sctx.span_id, "016x")
        span.set_attribute("hivemind.agent", "reviewer")
        span.set_attribute("hivemind.producer", payload.producer)
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)

    try:
        verdict = CriticVerdict.model_validate_json(final_text)
    except Exception as e:  # noqa: BLE001
        raise ValueError(
            f"Reviewer did not return a valid CriticVerdict: {e}\nraw: {final_text[:500]}"
        ) from e

    # Flush so Phoenix has the span. Annotate FIRST: its retry loop waits out
    # Phoenix's async ingestion, which also guarantees the project now exists — so
    # the trace-URL lookup resolves to the project id, not a name fallback.
    otel_trace.get_tracer_provider().force_flush()
    annotated = await _annotate_verdict(span_id, verdict)
    trace_url = _phoenix_trace_url(trace_id)

    return ReviewResult(
        verdict=verdict,
        arize_trace_url=trace_url,
        reviewer_span_id=span_id,
        annotation_written=annotated,
    )
