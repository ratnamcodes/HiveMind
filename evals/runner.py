#!/usr/bin/env python3
"""Scenario eval runner (T18-A).

For each scenario in evals/scenarios/*.json: fires the synthetic alert through the
orchestrator, captures the Phoenix trace, and scores the run:
  - deterministic assertions — expected_intermediates (the tools each agent called +
    the fields it populated) and expected_final (mr_filed / notebook_created /
    customers_identified / severity_within);
  - grounding score — one LLM-as-judge call per scenario scoring each hop against
    evals/rubric.md (the hivemind-grounding-rubric).
Outputs JSON: per-scenario pass/fail + scores + trace link + a 1-line diff for failures,
plus a pass_rate summary.

LIVE: each scenario is a full orchestrator run that opens a REAL MR; the runner closes +
deletes those bot MRs afterward (unless --keep-mrs). Default --limit 3 to keep it sane.

Run:  .venv/bin/python evals/runner.py --limit 3
      .venv/bin/python evals/runner.py --all --out evals/last_run.json --no-judge
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import sys
import urllib.parse
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from redis.asyncio import from_url as redis_from_url  # noqa: E402
from hivemind import events  # noqa: E402
from orchestrator.graph import OrchestratorRunner  # noqa: E402

SCENARIO_GLOB = os.path.join(ROOT, "evals", "scenarios", "*.json")
RUBRIC_PATH = os.path.join(ROOT, "evals", "rubric.md")
GITLAB_URL = (os.environ.get("GITLAB_URL") or "https://gitlab.com").rstrip("/")
GITLAB_TOKEN = os.environ.get("GITLAB_BOT_TOKEN") or os.environ.get("GITLAB_TOKEN")
TARGET = os.environ.get("GITLAB_TARGET_PROJECT", "")

# agent id -> the orchestrator-state key holding that agent's structured output
AGENT_STATE_KEY = {
    "detective": "finding",
    "log_diver": "log_report",
    "code_arch": "code_finding",
    "customer_liaison": "customer_report",
    "scribe": "stored_incident",
    "reviewer": "verdict",
}


def load_scenarios() -> list[dict]:
    out: list[dict] = []
    for path in sorted(glob.glob(SCENARIO_GLOB)):
        with open(path) as f:
            data = json.load(f)
        out.extend(data if isinstance(data, list) else [data])
    return out


async def _collect_tool_calls(user_id: str, tools_by_agent: dict, stop: asyncio.Event) -> None:
    """Subscribe to the orchestrator's event bus and record tool_call status events per
    agent (reuses the T17 stream), until `stop` is set."""
    redis = redis_from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe(events.channel_name(user_id))
    try:
        while not stop.is_set():
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg:
                continue
            try:
                ev = json.loads(msg["data"])
            except Exception:  # noqa: BLE001
                continue
            if ev.get("type") == "status" and ev.get("state") == "tool_call" and ev.get("tool"):
                tools_by_agent.setdefault(ev["agent_id"], set()).add(ev["tool"])
    finally:
        await pubsub.unsubscribe(events.channel_name(user_id))
        await pubsub.aclose()
        await redis.aclose()


def _present(v) -> bool:
    return v is not None and v != "" and v != []


def _check(sc: dict, output: dict, final: dict, tools_by_agent: dict):
    """Return (passed, assertions, diffs)."""
    assertions: dict = {"intermediates": [], "final": {}}
    diffs: list[str] = []

    for exp in sc.get("expected_intermediates", []):
        agent = exp["agent"]
        called = tools_by_agent.get(agent, set())
        tools_missing = [t for t in exp.get("must_call_tools", []) if t not in called]
        agent_out = final.get(AGENT_STATE_KEY.get(agent, ""), {}) or {}
        fields_missing = [f for f in exp.get("must_output_fields", []) if not _present(agent_out.get(f))]
        ok = not tools_missing and not fields_missing
        assertions["intermediates"].append(
            {"agent": agent, "ok": ok, "tools_missing": tools_missing, "fields_missing": fields_missing}
        )
        if tools_missing:
            diffs.append(f"{agent} skipped tools {tools_missing}")
        if fields_missing:
            diffs.append(f"{agent} missing fields {fields_missing}")

    ef = sc.get("expected_final", {})
    fin: dict = {}
    if "mr_filed" in ef:
        got = bool(output.get("mr_url"))
        fin["mr_filed"] = {"want": ef["mr_filed"], "got": got, "ok": got == ef["mr_filed"]}
        if got != ef["mr_filed"]:
            diffs.append(f"mr_filed want={ef['mr_filed']} got={got}")
    if "notebook_created" in ef:
        got = bool(output.get("notebook_url"))
        fin["notebook_created"] = {"want": ef["notebook_created"], "got": got, "ok": got == ef["notebook_created"]}
        if got != ef["notebook_created"]:
            diffs.append(f"notebook_created want={ef['notebook_created']} got={got}")
    if "customers_identified" in ef:
        ca = output.get("customers_affected")
        got = ca is not None and ca > 0
        fin["customers_identified"] = {"want": ef["customers_identified"], "got": got, "ok": got == ef["customers_identified"]}
        if got != ef["customers_identified"]:
            diffs.append(f"customers_identified want={ef['customers_identified']} got={got} (n={ca})")
    if "severity_within" in ef:
        stored = final.get("stored_incident") or {}
        sev = stored.get("severity") or sc["input_alert"].get("severity")
        got = sev in ef["severity_within"]
        fin["severity_within"] = {"allowed": ef["severity_within"], "got": sev, "ok": got}
        if not got:
            diffs.append(f"severity {sev} not in {ef['severity_within']}")
    assertions["final"] = fin

    passed = all(i["ok"] for i in assertions["intermediates"]) and all(v["ok"] for v in fin.values())
    return passed, assertions, diffs


_RUBRIC: str | None = None


def _rubric() -> str:
    global _RUBRIC
    if _RUBRIC is None:
        try:
            with open(RUBRIC_PATH) as f:
                _RUBRIC = f.read()
        except Exception:  # noqa: BLE001
            _RUBRIC = ""
    return _RUBRIC


def _grounding_score(sc: dict, final: dict) -> dict | None:
    """One LLM-as-judge call scoring each hop against the rubric. Best-effort — returns
    an {error} dict on any failure so it never fails the scenario."""
    try:
        from google import genai

        hops = {k: final.get(v) for k, v in AGENT_STATE_KEY.items() if final.get(v)}
        prompt = (
            "Score this multi-agent incident response against the grounding rubric.\n\n"
            f"RUBRIC:\n{_rubric()}\n\n"
            f"ALERT:\n{json.dumps(sc['input_alert'])}\n\n"
            f"AGENT OUTPUTS (hops):\n{json.dumps(hops, default=str)[:6000]}\n\n"
            'Return ONLY JSON: {"hops": {"<agent>": {"score": <0..1>, "reason": "..."}}, '
            '"overall": <0..1>}.'
        )
        # Vertex (the project's Google Cloud billing), not the Developer-API key pool.
        client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        )
        resp = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return json.loads(resp.text or "{}")
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def _cleanup_branch(branch: str) -> None:
    if not (GITLAB_TOKEN and TARGET):
        return
    pid = urllib.parse.quote(TARGET, safe="")
    h = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    try:
        r = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{pid}/merge_requests",
            headers=h, params={"source_branch": branch, "state": "opened"}, timeout=20,
        )
        if r.ok and r.json():
            iid = r.json()[0]["iid"]
            requests.put(
                f"{GITLAB_URL}/api/v4/projects/{pid}/merge_requests/{iid}",
                headers=h, params={"state_event": "close"}, timeout=20,
            )
        requests.delete(
            f"{GITLAB_URL}/api/v4/projects/{pid}/repository/branches/{urllib.parse.quote(branch, safe='')}",
            headers=h, timeout=20,
        )
    except requests.RequestException:
        pass


async def run_scenario(
    sc: dict, idx: int, judge: bool, keep_mrs: bool, timeout: float = 600.0
) -> dict:
    incident_id = f"INC-eval-{uuid.uuid4().hex[:6]}"
    user_id = f"eval-{incident_id}"
    alert_payload = {
        "incident_id": incident_id,
        "channel_id": f"eval-{idx}",
        "user_id": user_id,
        **sc["input_alert"],
    }
    tools_by_agent: dict[str, set] = {}
    stop = asyncio.Event()
    collector = asyncio.create_task(_collect_tool_calls(user_id, tools_by_agent, stop))
    out = None
    final: dict = {}
    timed_out = False
    try:
        # Per-scenario hard timeout — a hung agent/LLM call must never freeze the suite.
        out, final = await asyncio.wait_for(
            OrchestratorRunner().run_full(alert_payload), timeout=timeout
        )
    except asyncio.TimeoutError:
        timed_out = True
    finally:
        stop.set()
        try:
            await collector
        except Exception:  # noqa: BLE001
            pass

    if not keep_mrs:
        _cleanup_branch(f"hivemind-bot/fix-{incident_id}")

    if timed_out:
        return {
            "name": sc["name"],
            "passed": False,
            "diff": f"timeout after {int(timeout)}s (scenario hung)",
            "tools_by_agent": {a: sorted(t) for a, t in tools_by_agent.items()},
        }

    passed, assertions, diffs = _check(sc, out.output, final, tools_by_agent)
    grounding = _grounding_score(sc, final) if judge else None

    result = {
        "name": sc["name"],
        "passed": passed,
        "trace_url": out.arize_trace_url,
        "tools_by_agent": {a: sorted(t) for a, t in tools_by_agent.items()},
        "assertions": assertions,
        "grounding": grounding,
    }
    if not passed:
        result["diff"] = "; ".join(diffs) or "assertions failed"
    return result


async def main() -> int:
    ap = argparse.ArgumentParser(description="HiveMind scenario eval runner")
    ap.add_argument("--limit", type=int, default=3, help="run the first N scenarios")
    ap.add_argument("--all", action="store_true", help="run every scenario")
    ap.add_argument("--no-judge", action="store_true", help="skip the LLM grounding judge")
    ap.add_argument("--keep-mrs", action="store_true", help="don't clean up the bot MRs")
    ap.add_argument("--scenario-timeout", type=float, default=600.0, help="kill a hung scenario after N seconds")
    ap.add_argument("--out", default=os.path.join(ROOT, "evals", "last_run.json"))
    args = ap.parse_args()

    scenarios = load_scenarios()
    if not args.all:
        scenarios = scenarios[: args.limit]
    print(f"running {len(scenarios)} scenario(s){' (no judge)' if args.no_judge else ''}...")

    results = []
    for i, sc in enumerate(scenarios):
        print(f"[{i + 1}/{len(scenarios)}] {sc['name']} ...", flush=True)
        try:
            res = await run_scenario(
                sc, i, judge=not args.no_judge, keep_mrs=args.keep_mrs,
                timeout=args.scenario_timeout,
            )
        except Exception as e:  # noqa: BLE001
            res = {"name": sc["name"], "passed": False, "diff": f"runner error: {type(e).__name__}: {e}"}
        results.append(res)
        print(f"    -> {'PASS' if res['passed'] else 'FAIL'}" + ("" if res["passed"] else f"  ({res.get('diff', '')})"))
        # Write incrementally so a long (~1hr) run still yields a report if interrupted.
        _p = sum(1 for r in results if r["passed"])
        with open(args.out, "w") as f:
            json.dump(
                {
                    "summary": {
                        "total": len(scenarios),
                        "completed": len(results),
                        "passed": _p,
                        "pass_rate": round(_p / len(results), 4) if results else 0.0,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    },
                    "results": results,
                },
                f, indent=2, default=str,
            )

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    report = {
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        "results": results,
    }
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\npass_rate {passed}/{total} = {report['summary']['pass_rate']:.0%}  ->  {args.out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
