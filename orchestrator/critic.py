"""Per-hop critic: a fast mechanical gate after each specialist node.

Checks that the output is schema-valid, non-empty, and grounded (at least one tool
call). The caller retries the agent once on failure before proceeding.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel


@dataclass
class Critique:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def critique(
    output_text: str,
    schema: type[BaseModel],
    tool_calls: int,
    *,
    expect_tools: bool = True,
) -> Critique:
    """Cheap correctness gate for one agent's output. `expect_tools=False` for agents
    that legitimately use no tools (e.g. Scribe), so they're not flagged as ungrounded."""
    reasons: list[str] = []
    if not (output_text or "").strip():
        reasons.append("empty output")
    try:
        schema.model_validate_json(output_text)
    except Exception:  # noqa: BLE001
        reasons.append("output is not schema-valid")
    if expect_tools and tool_calls < 1:
        reasons.append("ungrounded: agent made 0 tool calls")
    return Critique(passed=not reasons, reasons=reasons)
