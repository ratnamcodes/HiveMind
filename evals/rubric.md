# HiveMind grounding rubric (`hivemind-grounding-rubric`)

LLM-as-judge criteria for scoring each agent hop in a HiveMind incident run. Used by
`evals/runner.py` (per-hop scoring) and seeded into Phoenix as the custom eval template
`hivemind-grounding-rubric`. The judge returns a score in **[0,1]** per criterion plus a
one-line justification; the hop's score is the weighted mean (weights below, overridable
per scenario via `rubric_overrides`).

## Criteria

1. **Grounding (weight 0.35)** — Every factual claim (a latency number, a deploy id, a
   file path, a customer count) traces to data the agent actually pulled via a tool. No
   claim is asserted without a tool result behind it. Score 0 if the agent states a
   conclusion it never gathered evidence for.

2. **No hallucination (weight 0.25)** — URLs, MR iids, notebook links, MongoDB ids, and
   file paths are real (returned by a tool), never invented. An invented link or a patch
   to a file that doesn't exist in the repo is an automatic 0 on this criterion.

3. **Relevance (weight 0.20)** — The output addresses *this* incident (the alert's
   service + symptom), not a generic or copy-pasted answer. A hypothesis about the wrong
   service scores low.

4. **Completeness (weight 0.15)** — The agent populated the fields its role requires
   (e.g. Detective: `root_cause_hypothesis` + `confidence`; CodeArch: `merge_request_url`
   when a fix was filed). Missing required fields lowers the score.

5. **Actionability (weight 0.05)** — The output moves the incident forward: a concrete
   next step, a minimal patch, a specific customer list — not vague advice.

## Per-agent expectations (what "grounded" means for each)

- **detective** — root cause cites specific log/DQL evidence + a confidence; implicated
  service/deploy come from the data, not the alert text alone.
- **log_diver** — error counts + representative messages come from an actual Elastic
  query, with the spike correlated to the deploy window.
- **code_arch** — patches a file that EXISTS in the repo tree; the diff is minimal and
  addresses the stated root cause; the MR is real (a returned iid/url).
- **customer_liaison** — the affected-customer count + names come from the data
  warehouse query, not estimated.
- **scribe** — the incident record faithfully summarizes the other hops; no invented
  participants or links.
- **reviewer** — the verdict cites the specific rubric line and the offending fragment;
  `approve` only when the hypothesis is grounded AND the fix addresses it.

## Verdict mapping

- **pass**: weighted score ≥ 0.7 AND no criterion scored 0.
- **fail**: weighted score < 0.7 OR any automatic-0 (hallucinated link / non-existent
  file / ungrounded conclusion).
