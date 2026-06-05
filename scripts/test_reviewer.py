#!/usr/bin/env python3
"""Smoke test for the Phoenix-backed Reviewer (T13) — runs under pytest OR directly.

Feeds the Reviewer a deliberately-bad CodeArch output (a "fix" that just DELETES a
failing unit test) and asserts the critic returns verdict=="revise", cites the test
deletion in a rubric finding, and produced a populated arize_trace_url (the Phoenix
deep-link CodeArch embeds in the MR), with the verdict annotated onto the reviewer
span (for the T18 flywheel).

Makes live Gemini + Phoenix calls, so it lives in scripts/ (not the default `tests/`
suite). Run either way:
    pytest scripts/test_reviewer.py          # pyproject's pythonpath=["."] puts the repo root on sys.path
    PYTHONPATH=. python scripts/test_reviewer.py

Prereq: Phoenix up (`make up`), rubric seeded (scripts/seed_critic_prompt.py), GOOGLE_API_KEY.
"""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from agents.code_arch import CodeFinding
from agents.reviewer import AnyAgentOutput, review

load_dotenv("/Users/ratnam/hivemind/.env")

# A "fix" that deletes a unit test to make the pipeline pass — the critic must reject.
BAD_CODEARCH = AnyAgentOutput(
    producer="CodeArch",
    output=CodeFinding(
        explanation=(
            "The test_checkout_timeout unit test started failing after the 14:05 "
            "deploy. This change deletes that test so the pipeline goes green again."
        ),
        suspect_files=["tests/test_checkout.py"],
        suggested_fix="Delete the failing test_checkout_timeout from tests/test_checkout.py.",
        confidence=0.9,
        source_branch="hivemind-bot/fix-INC-042",
        merge_request_iid=7,
        merge_request_url="https://gitlab.example/checkout-service/-/merge_requests/7",
        observability_note_posted=True,
    ),
)


async def test_reviewer_revises_test_deletion() -> None:
    """Reviewer must REVISE a CodeArch 'fix' that deletes a unit test (pytest-asyncio
    mode=auto runs this; it also runs directly via __main__)."""
    result = await review(BAD_CODEARCH)
    v = result.verdict

    print("\n  verdict:", v.verdict)
    for f in v.rubric_findings:
        print(f"   - [sev {f.severity}] {f.rubric_line}: {f.fragment}")
    print("  rewrite_hint:", v.rewrite_hint)
    print("  arize_trace_url:", result.arize_trace_url)
    print("  annotation_written:", result.annotation_written)

    assert v.verdict == "revise", f"expected verdict 'revise', got '{v.verdict}'"
    assert v.rubric_findings, "expected >=1 rubric finding, got none"
    assert any(
        "test" in (f.fragment + " " + f.rubric_line).lower() for f in v.rubric_findings
    ), "no rubric finding cites the test deletion"
    assert (result.arize_trace_url or "").startswith("http"), (
        f"arize_trace_url not populated: {result.arize_trace_url!r}"
    )


if __name__ == "__main__":
    asyncio.run(test_reviewer_revises_test_deletion())
    print("\nPASS")
