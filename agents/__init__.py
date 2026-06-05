"""HiveMind agent package.

Importing this package turns on Phoenix tracing (T13): the OpenInference
GoogleADKInstrumentor patches ADK so every Gemini call, agent/tool span, and
LangGraph node is exported to our Phoenix instance, where phoenix-mcp can read
those traces back for the Reviewer's meta-loop.

It runs here, at package import, because OTEL instrumentation only captures the
process it runs in. Putting it in __init__.py means it fires exactly once in
whatever loads the agents — including the module shipped via `adk deploy`, not
just a local entry point — which is the failure mode the task warns about
(traces vanishing post-deploy).

Backend is config, not code: PHOENIX_COLLECTOR_ENDPOINT (+ optional
PHOENIX_API_KEY) selects self-hosted Phoenix today and Phoenix Cloud for the
hosted demo later — the register() call below is byte-for-byte identical for
both.
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
    _tracer_provider = register(
        endpoint=f"{_endpoint.rstrip('/')}/v1/traces",
        project_name=os.getenv("PHOENIX_PROJECT", "hivemind"),
        api_key=os.getenv("PHOENIX_API_KEY"),  # None for self-host; set for Cloud
        protocol="http/protobuf",
        batch=True,  # batch export, like production
        auto_instrument=False,  # we attach the ADK instrumentor ourselves
        set_global_tracer_provider=True,
    )
    GoogleADKInstrumentor().instrument(tracer_provider=_tracer_provider)
except Exception as exc:  # noqa: BLE001
    # Never let tracing setup break the agent package — degrade to "no tracing"
    # (e.g. Phoenix not running) but make the skip loud.
    warnings.warn(
        f"Phoenix tracing disabled: {type(exc).__name__}: {exc}", stacklevel=2
    )
