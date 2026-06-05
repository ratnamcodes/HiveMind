"""Per-hop critic (T15-C): a fast gate after each specialist node.

The spec frames this as a "fast thinking_level=minimal Gemini critic," but its three
checks are all MECHANICAL:

  - schema-valid   — does the output parse into the node's output schema?
  - non-empty      — is there actually output?
  - grounded       — did the agent make >= 1 tool call (vs hallucinating an answer)?

So we run them as a free, instant code check (no Gemini call — strictly cheaper than the
spec) and retry the agent once on failure, catching ungrounded/garbage output AT THE HOP
instead of letting it ride all the way to the final Reviewer and waste downstream tokens.
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
