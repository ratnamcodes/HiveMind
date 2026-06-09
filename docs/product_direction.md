# HiveMind — Product Direction (v2: real, not scripted)

The pivot: from a script-seeded demo to a **real, deployable product** a business connects and
watches solve a **real incident in a real running app, live** — no seed scripts.

## Four pillars (user feedback, 2026-06-08)

1. **All-in on Dynatrace (apply in the Dynatrace track).** Research + integrate deeply across the
   full tool surface: Problems API, Davis AI + Davis CoPilot, Grail/DQL, Metrics, Traces/Spans,
   Smartscape/topology, OneAgent, OTLP/OpenTelemetry ingest, Workflows (AutomationEngine),
   Notebooks, Site Reliability Guardian, Dashboards/Apps. The trigger should be a **real Davis
   problem**, not a synthetic webhook. Integrate deeply enough to blow judges' minds.

2. **Real, not scripted.** Deploy a **real instrumented app** that emits **real telemetry**;
   trigger a **real regression**; HiveMind detects + diagnoses + fixes from **real Dynatrace data**,
   the human approves, the fix deploys, and the app **recovers** (visible in Dynatrace). Seeded data
   can be gamed — this must feel real and magical.

3. **A product.** Next.js email/password auth (Auth.js to start) + a **strong landing page** +
   onboarding ("connect your Dynatrace + GitLab"). It should be deployable; any business can use it.

4. **UI overhaul.** Remove emojis and gradients (they read AI-generated). Integrate a real **icon
   library**; make it look like a professional dev-tool (Linear / Vercel / Datadog / incident.io
   quality): restrained color, real iconography, good typography, density.

Test everything end-to-end (no demo videos this round). Mom test each iteration: so good and easy
to use that **no usage instructions are needed**.

## Where we are (to build on)

6-agent LangGraph crew, each on a real partner MCP; Detective already drives the Dynatrace MCP
(`@dynatrace-oss/dynatrace-mcp-server`, `DT_PLATFORM_TOKEN`): NL→DQL→Davis→notebook. War-room
(Next.js 16) has the brief card, live agent reasoning, the human-in-the-loop approval gate
(LangGraph `interrupt()` + `/api/incident/{id}/resume`), and an impact view. 5 scenarios work
end-to-end but are **seeded** (`scripts/seed_scenario.py`). No auth, no landing, emoji/gradient UI.

The work plan lives alongside this file once the research synthesizes (see `docs/redesign_spec.json`
for the prior round).
