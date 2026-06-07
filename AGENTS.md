# HiveMind — AGENTS.md (system of record)

Scarce by design. This file is load-bearing: the CI gate fails the build if a required
section (`## Architecture`, `## Anti-patterns`, `## Contract`) is missing.

## Architecture
HiveMind is an incident-response crew. A LangGraph **orchestrator** (`orchestrator/graph.py`)
fans one Dynatrace alert out to **6 specialists** — Detective (Dynatrace), LogDiver
(Elastic), CodeArch (GitLab), Liaison (Fivetran→BigQuery), Scribe (MongoDB Atlas), Reviewer
(Phoenix) — with a per-hop critic gate and a bounded revise loop. The crew **generates**.
An **external Evaluator** (`harness/evaluator.py`), which is NOT a graph node, then drives
the finished run like a user — reading the Mongo incident record, the filed GitLab MR, the
Phoenix trace, and the war-room transcript — and **judges** it against a per-incident
done-contract. Generator and Evaluator are separate processes; the crew cannot grade itself.

## Anti-patterns (non-guidance — these must never happen)
- **An agent never approves its own envelope.** Grading is external (the Evaluator), never self.
- **No tool call outside an MCPToolset.** Every external action goes through a registered MCP
  tool — with one documented exception: the Liaison's read-only `query_customer_data` BigQuery
  path (the Fivetran MCP can't query BQ). Exceptions are allowlisted with a reason in
  `harness/check_taste.py`; an *undocumented* non-MCP tool fails the build.
- **The Evaluator never edits code.** It only reads artifacts and writes a verdict file.
- **A verdict is never agent-to-agent chat.** It is a file: `harness/runs/<incident_id>/feedback.json`.
- **No unbounded retries.** The Generator→Evaluator loop is capped (5) then escalates to a human.

## Contract
The per-incident "done contract" is defined by **`harness/contract.schema.json`** — required
intermediates (which agent must call which tool, which fields it must populate), required
final state (MR filed, notebook created, customers identified, severity bound), and rubric
weights. It reuses T18's `expected_intermediates`/`expected_final` shape. The Evaluator scores
against this contract plus the `hivemind-grounding-rubric` (`evals/rubric.md`).
