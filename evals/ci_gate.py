#!/usr/bin/env python3
"""CI gate. Compares this PR's eval pass_rate to the main baseline and blocks on
a regression worse than 2 points. Reads evals/last_run.json (written by runner.py) and
evals/baseline.json; writes a PR-comment body to evals/pr_comment.md; exits 1 if blocked.

Usage:
  python evals/ci_gate.py           # gate a PR run (exit 1 = block merge)
  python evals/ci_gate.py --update  # write current pass_rate back to baseline (run on main)
"""
from __future__ import annotations

import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAST = os.path.join(ROOT, "evals", "last_run.json")
BASELINE = os.path.join(ROOT, "evals", "baseline.json")
COMMENT = os.path.join(ROOT, "evals", "pr_comment.md")
THRESHOLD = 0.02  # allow up to a 2-point drop vs the main baseline


def _load(path: str, default: dict) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="write current pass_rate to baseline")
    args = ap.parse_args()

    run = _load(LAST, {"summary": {"pass_rate": 0.0, "passed": 0, "total": 0}, "results": []})
    cur = run["summary"].get("pass_rate", 0.0)

    if args.update:
        with open(BASELINE, "w") as f:
            json.dump({"pass_rate": cur}, f, indent=2)
        print(f"baseline updated -> {cur:.0%}")
        return 0

    base = _load(BASELINE, {"pass_rate": 0.0}).get("pass_rate", 0.0)
    floor = base - THRESHOLD
    ok = cur >= floor
    failures = [r for r in run.get("results", []) if not r.get("passed")]

    lines = [
        f"### HiveMind evals — {'✅ PASS' if ok else '❌ BLOCKED (regression)'}",
        "",
        f"- pass_rate: **{cur:.0%}** ({run['summary'].get('passed', 0)}/{run['summary'].get('total', 0)})",
        f"- main baseline: {base:.0%}  ·  floor: {floor:.0%} (−{int(THRESHOLD * 100)} pts)",
    ]
    if failures:
        lines.append("- failing scenarios:")
        for r in failures:
            lines.append(f"  - `{r['name']}` — {r.get('diff', 'failed')}")
    body = "\n".join(lines) + "\n"
    with open(COMMENT, "w") as f:
        f.write(body)
    print(body)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
