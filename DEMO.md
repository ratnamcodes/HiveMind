# HiveMind — Demo Runbook

> **A steerable crew of AI specialists notices a business problem nobody filed a ticket for,
> correlates it across six live systems, names the exact customers and dollars at risk, hides
> their private data, drafts the fix as a real merge request — and pauses to ask a human before
> shipping.** The coding agent on your laptop would never have known to look.

## Why this isn't possible with a solo coding agent (Claude Code / Codex)

A coding agent is a brilliant individual locked inside one repo's sandbox: it only acts when
told, has no live reach into production, and no idea which real customers or dollars a bug
touches. HiveMind is the opposite — six **separately-credentialed** specialists that watch the
live state of a running business (metrics, logs, the data warehouse, revenue, named customers),
reach consensus, and defer to a human at the high-stakes moment.

| Agent | Partner | Does |
|---|---|---|
| **Detective** | Dynatrace (Grail) | NL→DQL→Davis root-cause from real logs |
| **LogDiver** | Elastic | ES\|QL over the logs, blames the exact deploy |
| **CodeArch** | GitLab | reads the repo, opens a **real MR** as `@HiveMind-bot` |
| **CustomerLiaison** | Fivetran → BigQuery | names affected customers + revenue; **redacts PII** before a public MR |
| **Scribe** | MongoDB Atlas | writes the postmortem; recalls past incidents |
| **Reviewer** | Phoenix | grades the run (advisory in human-in-the-loop mode) |

## The five scenarios (each fixes a *different* real file)

| # | Domain | Business symptom (no error thrown) | The real fix |
|---|---|---|---|
| **S1** | 2026 World Cup | On-sale confirmed 312 orders but **recognized revenue = $0.00** | `ticketing-service/pricing-rules.yaml` — restore the Toronto tier price + a min-price floor |
| **S2** | Financial Services | "Fraud" decline storm is actually the filter **strangling real cardholders** (every decline is HTTP 200) | `fraud-rules/velocity.yaml` — `max_txn_per_min 2→5` + enterprise whitelist; **redact customer_id/email** before the public MR |
| **S3** | Brick-and-Mortar Retail | One mall region **down 22% revenue, footfall flat** — silent stockouts from a broken sync | `inventory-service/sync-config.yaml` — add the dropped region back to the sync allowlist |
| **S4** | World Cup / Retail peak | In-store **tap-to-pay failing under match-day surge** (only under load) | `pos-gateway/capacity.yaml` — `connection_pool_size 20→200`, `timeout 1000→5000ms` |
| **S5** | Proactive / Compliance | No alert — a **scheduled sweep catches customer PII about to leak** to a public destination | `data-policy/pii-allowlist.yaml` — declare + enforce the PII allowlist; redact via Fivetran |

Each routes to a genuinely different real file and tells a different cross-system story. The
**theme is real, not a reskin** — Detective/LogDiver/CodeArch all converge on the same root cause
per scenario, grounded in seeded telemetry + warehouse data.

## What a third person sees (the human-in-the-loop war room, `:3000`)

1. **A pinned incident BRIEF** the instant the channel opens — *what / severity / who's on it*,
   and (once Liaison reports) the **named $ impact** + a "PII redacted" chip. 5-second legibility.
2. **Each agent narrates its reasoning live** ("Detective: pulling Dynatrace logs around the
   deploy window…") with real tool-call pills (`execute_dql`, `create_merge_request`).
3. **The run PAUSES** at the approval card — *"Paused — your call · Ship the fix?"* — showing the
   drafted MR, the file, the impact, and the crew's confidence. Nothing irreversible has happened.
4. **The human clicks Approve & ship** (or Request changes / Escalate) → it resumes from the Redis
   checkpoint, ships the real MR, and resolves.

## Recorded videos

`scripts/demo_recording/S{1..5}/war-room-demo.mp4` — each ~2.5–5.5 min, the full live flow:
brief → agents investigate → impact named → **human approves** → real MR shipped → resolved.

## Run it yourself

```bash
# infra (Redis + Phoenix already up across sessions)
docker compose up -d

# backend (loads the orchestrator + the 6 agents + the HITL endpoints)
PYTHONPATH=. .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000

# war-room (leave NEXT_PUBLIC_API_BASE unset → mock sidebar; live incident streams over /ws)
cd web && bun dev                       # http://localhost:3000

# pick a scenario, seed its coherent cross-system data, then record (or just fire):
.venv/bin/python scripts/seed_scenario.py S2          # S1..S5
.venv/bin/python scripts/record_demo.py --scenario S2 --hitl   # drives the browser + clicks Approve
#   (or fire to the live browser and click Approve yourself:)
.venv/bin/python scripts/verify_demo_e2e.py --scenario S2 --hitl --user hivemind
```

`scripts/scenarios.py` is the registry (the cross-system story per scenario);
`scripts/seed_scenario.py` seeds Dynatrace + Elastic + Atlas + BigQuery coherently;
`scripts/record_demo.py` drives a real browser through the whole flow and records it.

## Engineering notes (reliability, learned from live runs)

- **Cause vs customer service**: Detective/LogDiver/CodeArch query each scenario's *unique* cause
  service (its own Grail logs — `ticketing-service`, `fraud-decision`, …) so back-to-back scenarios
  don't contaminate the diagnosis; Liaison grounds customer impact on the customer-facing service.
- **Deterministic fix target**: the diagnosis passes a `code_target` so CodeArch patches the right
  subsystem (it still reads + patches the real file).
- **Human-in-the-loop**: built on LangGraph `interrupt()` over the Redis checkpointer; the war-room
  POSTs the decision to `/api/incident/{id}/resume` (CORS-enabled). The Reviewer's verdict is
  *advisory* — the human always makes the final call when a fix was drafted.
- **Vertex is per-minute throttled** — full runs are serial (~3–6 min); record one at a time.
- **Seeds are time-relative** — re-seed a scenario right before recording it.
