"""HiveMind agent package.

Importing this package registers Phoenix/OTEL tracing once per process: the
OpenInference GoogleADKInstrumentor patches ADK so Gemini calls, agent/tool
spans, and LangGraph nodes export to Phoenix. The collector endpoint comes
from PHOENIX_COLLECTOR_ENDPOINT (PHOENIX_API_KEY optional).
"""

from __future__ import annotations

import os
import warnings

from dotenv import load_dotenv

# Load .env early: this __init__ runs before any agent submodule's own
# load_dotenv(), and register() below reads PHOENIX_* straight from the env.
load_dotenv()

try:
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor
    from phoenix.otel import register

    _endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
    # Skip tracing when there's no reachable collector: otherwise the batch
    # exporter retries localhost:6006 forever and floods the logs.
    if os.getenv("PHOENIX_DISABLE", "").lower() in ("1", "true", "yes") or not _endpoint:
        raise RuntimeError("Phoenix tracing disabled (PHOENIX_DISABLE set or no endpoint)")
    _tracer_provider = register(
        endpoint=f"{_endpoint.rstrip('/')}/v1/traces",
        project_name=os.getenv("PHOENIX_PROJECT", "hivemind"),
        api_key=os.getenv("PHOENIX_API_KEY"),  # None for self-host; set for Cloud
        protocol="http/protobuf",
        batch=True,
        auto_instrument=False,  # we attach the ADK instrumentor ourselves
        set_global_tracer_provider=True,
    )
    GoogleADKInstrumentor().instrument(tracer_provider=_tracer_provider)
except Exception as exc:  # noqa: BLE001
    # Never let tracing setup break the agent package; degrade to "no tracing"
    # (e.g. Phoenix not running) but make the skip loud.
    warnings.warn(
        f"Phoenix tracing disabled: {type(exc).__name__}: {exc}", stacklevel=2
    )
