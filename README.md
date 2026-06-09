# HiveMind

**An AI SRE crew that fixes incidents in your real telemetry.** The moment a real problem appears
on your service, HiveMind wakes, finds the root cause in real Dynatrace data, opens the GitLab fix,
waits for one human approval, and your service recovers — every artifact real, none of it seedable.

## Quickstart (one command)

```bash
make up        # Redis + Phoenix + API + web + the instrumented demo services
```

Open **http://localhost:3000** → sign up → connect your Dynatrace + GitLab (Test connection
verifies them live) → enter the war room. Then trigger a **real** incident:

```bash
bash scripts/inject_regression.sh break     # real 1.2s latency regression in the running app
#   the checkout service detects its own SLO breach and pages HiveMind automatically;
#   watch the crew diagnose, open a real MR, and pause for your approval in the war room.
bash scripts/inject_regression.sh revert     # ship the fix -> the app recovers
```

`make down` stops it.

## What's real (not scripted)

- **`apps/`** — real `checkout-service` + `payment-service` (OpenTelemetry-instrumented) emitting
  real traces/logs to Dynatrace, plus a load generator. A config knob (`downstream_delay_ms`,
  mirrored in the GitLab repo CodeArch fixes) drives a real, reversible latency regression.
- **The trigger** — checkout detects its *own* sustained SLO breach and `POST`s
  `/api/incoming/app-incident`. No seed, no manual fire. (The Dynatrace Davis-problem Workflow
  webhook is the deeper trigger, enabled once an `apiTokens.write`-scoped token is added.)
- **The loop** — six specialist agents (Detective→Dynatrace, LogDiver→Elastic, CodeArch→GitLab,
  Liaison→BigQuery, Scribe→Atlas, Reviewer→Phoenix) investigate, name the customers + revenue at
  risk, open a real merge request, and **pause at a human approval gate** (LangGraph `interrupt()`).
  Approve → the fix ships → the real app recovers.

## The product

- A landing page (`/`), email/password auth (`/sign-in`), and a "connect your stack" onboarding
  (`/onboarding`) with live connection tests — `app.py`, `web/`.
- The war room (`/c/*`): a Slack-style live channel with a pinned incident brief (what / severity /
  named $ impact / who), per-agent reasoning, and inline approval cards.

## Architecture

`app.py` (FastAPI) hosts the war-room event stream (`/ws`), the incident triggers, and the human
approval resume endpoint. `orchestrator/graph.py` is the LangGraph crew with the per-hop critic and
the human gate, checkpointed to Redis. `agents/` are the six ADK/Gemini specialists (Vertex AI).
Deep Dynatrace integration is documented in `docs/product_plan_v2.json`.
