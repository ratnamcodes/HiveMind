"""External Evaluator (T19) — the Critic, promoted out of the graph.

This is NOT a graph node. It runs AFTER the crew (the Generator) finishes and grades the
*finished* run the way a user would: it independently gathers evidence — the final MongoDB
incident record, the filed GitLab MR (and its diff), the Phoenix trace, and the run
transcript — and scores it against the per-incident done-contract
(`harness/contract.schema.json`) plus the `hivemind-grounding-rubric` (`evals/rubric.md`).

Out of the box Gemini is a soft grader, so the judge prompt carries 3 few-shot human FAIL
verdicts from `harness/calibration.json` (plausible-looking runs that were actually FAILs).

It writes `harness/runs/<incident_id>/feedback.json`:
    { verdict, failed_contract_clauses[], evidence_trace_links[], one_paragraph_diff }

Gemini runs on VERTEX (the project's Google Cloud billing), not the depleted Developer-API key.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

RUNS_DIR = ROOT / "harness" / "runs"
RUBRIC_PATH = ROOT / "evals" / "rubric.md"
CALIBRATION_PATH = ROOT / "harness" / "calibration.json"

GITLAB_URL = (os.environ.get("GITLAB_URL") or "https://gitlab.com").rstrip("/")
GITLAB_TOKEN = os.environ.get("GITLAB_BOT_TOKEN") or os.environ.get("GITLAB_TOKEN")
TARGET = os.environ.get("GITLAB_TARGET_PROJECT", "")
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
JUDGE_MODEL = "gemini-3.5-flash"

AGENT_STATE_KEY = {
    "detective": "finding",
    "log_diver": "log_report",
    "code_arch": "code_finding",
    "customer_liaison": "customer_report",
    "scribe": "stored_incident",
    "reviewer": "verdict",
}


# --- the contract ----------------------------------------------------------
def default_contract(incident_id: str, severity: str = "sev2") -> dict:
    """A standard HiveMind done-contract (reuses T18's expected_* shape)."""
    allowed = {"sev1": ["sev1"], "sev2": ["sev1", "sev2"], "sev3": ["sev2", "sev3"]}
    return {
        "incident_id": incident_id,
        "required_intermediates": [
            {"agent": "detective", "must_call_tools": ["execute_dql"],
             "must_output_fields": ["root_cause_hypothesis", "confidence"]},
            {"agent": "code_arch", "must_call_tools": ["create_merge_request"],
             "must_output_fields": ["merge_request_url"]},
            {"agent": "customer_liaison", "must_call_tools": [],
             "must_output_fields": ["customers_affected"]},
        ],
        "required_final": {
            "mr_filed": True, "notebook_created": True,
            "customers_identified": True, "severity_within": allowed.get(severity, ["sev1", "sev2"]),
        },
        "rubric_weights": {},
    }


# --- evidence gathering (independent of what the crew claims) ---------------
async def _read_incident_record(incident_id: str) -> dict | None:
    """Read the final incident record from Atlas (best-effort). Async so it runs on the
    caller's event loop (the harness loop) — a nested asyncio.run() would silently no-op."""
    try:
        from hivemind.mongo_client import close_mongo, get_db

        doc = await get_db().incidents.find_one(
            {"$or": [{"_id": incident_id}, {"id": incident_id}]}
        )
        await close_mongo()
        return doc
    except Exception:  # noqa: BLE001
        return None


def _fetch_mr(incident_id: str) -> dict | None:
    """Fetch the filed MR for this incident from GitLab + its changed files, so the
    Evaluator can verify the fix is REAL (patches a file that exists), not hallucinated."""
    if not (GITLAB_TOKEN and TARGET):
        return None
    branch = f"hivemind-bot/fix-{incident_id}"
    pid = urllib.parse.quote(TARGET, safe="")
    h = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    try:
        r = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{pid}/merge_requests",
            headers=h, params={"source_branch": branch, "state": "all"}, timeout=20,
        )
        if not (r.ok and r.json()):
            return None
        mr = r.json()[0]
        diffs = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{pid}/merge_requests/{mr['iid']}/changes",
            headers=h, timeout=20,
        )
        changed = [c.get("new_path") for c in diffs.json().get("changes", [])] if diffs.ok else []
        return {"iid": mr["iid"], "web_url": mr.get("web_url"), "title": mr.get("title"),
                "state": mr.get("state"), "changed_files": changed}
    except requests.RequestException:
        return None


# --- contract checks (deterministic) ---------------------------------------
def _present(v) -> bool:
    return v is not None and v != "" and v != []


def _check_contract(contract: dict, run_output: dict, run_state: dict, mr: dict | None) -> list[str]:
    """Return the list of FAILED contract clauses (empty = all clauses met)."""
    failed: list[str] = []

    for req in contract.get("required_intermediates", []):
        agent = req["agent"]
        out = (run_state or {}).get(AGENT_STATE_KEY.get(agent, ""), {}) or {}
        for f in req.get("must_output_fields", []):
            if not _present(out.get(f)):
                failed.append(f"{agent}.must_output_fields: missing '{f}'")

    rf = contract.get("required_final", {})
    o = run_output or {}
    if rf.get("mr_filed") and not o.get("mr_url"):
        failed.append("required_final.mr_filed: no MR url in output")
    if rf.get("notebook_created") and not o.get("notebook_url"):
        failed.append("required_final.notebook_created: no notebook url")
    if rf.get("customers_identified") and not (o.get("customers_affected") or 0) > 0:
        failed.append("required_final.customers_identified: 0 customers")
    if "severity_within" in rf:
        sev = (run_state.get("stored_incident") or {}).get("severity")
        if sev and sev not in rf["severity_within"]:
            failed.append(f"required_final.severity_within: {sev} not in {rf['severity_within']}")

    # Ground-truth: the MR must patch a file that actually exists (anti-hallucination).
    if rf.get("mr_filed"):
        if mr is None:
            failed.append("required_final.mr_filed: claimed but no MR found in GitLab")
        elif not mr.get("changed_files"):
            failed.append("code_arch: MR changes no files (empty/fake diff)")

    return failed


# --- the calibrated LLM judge (Vertex) -------------------------------------
def _vertex(prompt: str) -> str:
    from google import genai

    client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    resp = client.models.generate_content(
        model=JUDGE_MODEL, contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return resp.text or "{}"


def _llm_verdict(contract: dict, evidence: dict) -> dict:
    rubric = RUBRIC_PATH.read_text() if RUBRIC_PATH.exists() else ""
    calib = json.loads(CALIBRATION_PATH.read_text()) if CALIBRATION_PATH.exists() else []
    prompt = (
        "You are HiveMind's EXTERNAL Evaluator. You grade a finished incident run against a "
        "done-contract + a grounding rubric. You are STRICT: a run can look complete and still "
        "be a FAIL if the evidence is ungrounded, hallucinated, or stale. Study these human "
        "verdicts where a plausible-looking run was actually a FAIL:\n\n"
        f"{json.dumps(calib, indent=2)}\n\n"
        f"GROUNDING RUBRIC:\n{rubric}\n\n"
        f"DONE-CONTRACT:\n{json.dumps(contract, indent=2)}\n\n"
        f"EVIDENCE GATHERED (independently — Mongo record, the real MR + its changed files, "
        f"trace, transcript):\n{json.dumps(evidence, default=str)[:7000]}\n\n"
        'Return ONLY JSON: {"verdict": "PASS"|"FAIL", "failed_contract_clauses": [..], '
        '"one_paragraph_diff": "what is wrong / what would make it pass"}.'
    )
    try:
        return json.loads(_vertex(prompt))
    except Exception as e:  # noqa: BLE001
        return {"verdict": "FAIL", "failed_contract_clauses": [f"judge error: {e}"],
                "one_paragraph_diff": "Evaluator LLM call failed; defaulting to FAIL (do not pass on judge error)."}


# --- public entry ----------------------------------------------------------
async def evaluate(incident_id: str, contract: dict | None = None,
                   run_output: dict | None = None, run_state: dict | None = None) -> dict:
    """Grade a finished run. Returns the feedback dict (also written to disk)."""
    run_output = run_output or {}
    run_state = run_state or {}
    contract = contract or default_contract(incident_id)

    record = await _read_incident_record(incident_id)
    mr = _fetch_mr(incident_id)
    evidence = {
        "incident_id": incident_id,
        "mongo_record": record,
        "merge_request": mr,
        "trace_url": run_output.get("arize_trace_url"),
        "output": run_output,
        "transcript": {k: run_state.get(v) for k, v in AGENT_STATE_KEY.items() if run_state.get(v)},
    }

    hard_failures = _check_contract(contract, run_output, run_state, mr)
    judged = _llm_verdict(contract, evidence)

    # FAIL if either the deterministic contract checks fail OR the calibrated judge says FAIL.
    verdict = "FAIL" if (hard_failures or judged.get("verdict") == "FAIL") else "PASS"
    evidence_links = [x for x in [
        (mr or {}).get("web_url"),
        run_output.get("arize_trace_url"),
        f"incidents/{incident_id}" if record else None,
    ] if x]

    feedback = {
        "incident_id": incident_id,
        "verdict": verdict,
        "failed_contract_clauses": sorted(set(hard_failures + (judged.get("failed_contract_clauses") or []))),
        "evidence_trace_links": evidence_links,
        "one_paragraph_diff": judged.get("one_paragraph_diff", ""),
    }
    write_feedback(incident_id, feedback)
    return feedback


def write_feedback(incident_id: str, feedback: dict) -> Path:
    out_dir = RUNS_DIR / incident_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "feedback.json"
    path.write_text(json.dumps(feedback, indent=2, default=str))
    return path


if __name__ == "__main__":
    import asyncio

    if len(sys.argv) < 2:
        print("usage: python harness/evaluator.py <incident_id>")
        raise SystemExit(2)
    fb = asyncio.run(evaluate(sys.argv[1]))
    print(json.dumps(fb, indent=2, default=str))
