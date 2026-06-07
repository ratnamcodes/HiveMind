#!/usr/bin/env python3
"""Scheduled garbage collection (T19-E).

Weekly cron: scan MongoDB `harness_runs` for ENTROPY — contract clauses that always fail,
incidents that needed many retries, and dead (escalated) scenarios — then open a GitLab
issue summarizing it and proposing deletions. (Uses the GitLab REST API — the same GitLab
the MCP drives — for reliability.)

Run:  .venv/bin/python harness/gc.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

GITLAB_URL = (os.environ.get("GITLAB_URL") or "https://gitlab.com").rstrip("/")
GITLAB_TOKEN = os.environ.get("GITLAB_BOT_TOKEN") or os.environ.get("GITLAB_TOKEN")
TARGET = os.environ.get("GITLAB_TARGET_PROJECT", "")


async def _load_runs() -> list[dict]:
    from hivemind.mongo_client import close_mongo, get_db

    docs = await get_db().harness_runs.find({}).to_list(length=5000)
    await close_mongo()
    return docs


def analyze(runs: list[dict]) -> dict:
    clause_freq: Counter = Counter()
    iters_by_incident: dict[str, int] = {}
    escalated: set[str] = set()
    for r in runs:
        for c in r.get("failed_contract_clauses", []):
            clause_freq[c] += 1
        inc = r.get("incident_id", "?")
        iters_by_incident[inc] = max(iters_by_incident.get(inc, 0), r.get("iteration", 0))
        if r.get("verdict") == "ESCALATED":
            escalated.add(inc)
    return {
        "total_runs": len(runs),
        "chronic_clauses": [c for c, n in clause_freq.most_common() if n >= 3],
        "clause_freq": dict(clause_freq.most_common(10)),
        "retry_heavy_incidents": {i: n for i, n in iters_by_incident.items() if n >= 3},
        "escalated_incidents": sorted(escalated),
    }


def build_issue_body(report: dict) -> str:
    lines = [
        f"# HiveMind harness GC — {datetime.now(timezone.utc):%Y-%m-%d}",
        "",
        f"Scanned **{report['total_runs']}** `harness_runs` events.",
        "",
    ]
    if report["chronic_clauses"]:
        lines.append("## Chronic contract clauses (fail ≥3×) — fix or drop:")
        lines += [f"- `{c}` (×{report['clause_freq'].get(c)})" for c in report["chronic_clauses"]]
    if report["retry_heavy_incidents"]:
        lines += ["", "## Retry-heavy incidents (≥3 iterations) — investigate the loop:"]
        lines += [f"- {i}: {n} iterations" for i, n in report["retry_heavy_incidents"].items()]
    if report["escalated_incidents"]:
        lines += ["", "## Dead / escalated scenarios — candidates for deletion:"]
        lines += [f"- {i}" for i in report["escalated_incidents"]]
    if not (report["chronic_clauses"] or report["retry_heavy_incidents"] or report["escalated_incidents"]):
        lines.append("No entropy detected — the harness is healthy. 🟢")
    lines += ["", "_Auto-proposed by `harness/gc.py` (weekly)._"]
    return "\n".join(lines)


def open_issue(title: str, body: str) -> str | None:
    if not (GITLAB_TOKEN and TARGET):
        return None
    pid = urllib.parse.quote(TARGET, safe="")
    try:
        r = requests.post(
            f"{GITLAB_URL}/api/v4/projects/{pid}/issues",
            headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
            json={"title": title, "description": body},
            timeout=20,
        )
        return r.json().get("web_url") if r.ok else None
    except requests.RequestException:
        return None


async def main() -> int:
    report = analyze(await _load_runs())
    body = build_issue_body(report)
    print(body)
    title = (
        f"Harness GC {datetime.now(timezone.utc):%Y-%m-%d}: "
        f"{len(report['chronic_clauses'])} chronic clauses, "
        f"{len(report['escalated_incidents'])} dead scenarios"
    )
    url = open_issue(title, body)
    print(f"\nGitLab issue: {url or '(not opened — no token/target or API error)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
