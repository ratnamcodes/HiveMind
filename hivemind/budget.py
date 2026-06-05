"""Token budget manager (T15-B).

The spec summarizes old turns in `state.messages` when context nears the model's window.
But HiveMind's orchestrator state is structured per-incident (`finding`, `log_report`, …) —
there's no growing message list there, so a literal port has nothing to summarize. The
place a token budget *actually* applies is the CHANNEL CONVERSATION: the Redis `HotMemory`
sliding window of turns. This is that manager, reframed onto it.

When a channel's turns exceed `threshold_pct` of the model window, `compact()` folds
everything older than the last `keep_recent` turns into ONE `previous_context` turn (via a
cheap `thinking_level="minimal"` Gemini call) and logs the compaction to Phoenix as a span.
Wire it wherever channel history feeds a model (e.g. before passing `HotMemory.recent(...)`
into a prompt).
"""

from __future__ import annotations

from google import genai
from google.genai import types
from opentelemetry import trace as otel_trace

from hivemind.memory import Turn

# Context windows (tokens). Gemini 3.5 Flash is 1M → summarize at ~800k (80%).
_MODEL_WINDOWS = {"gemini-3.5-flash": 1_000_000}
_tracer = otel_trace.get_tracer("hivemind.budget")


class TokenBudget:
    def __init__(self, model: str = "gemini-3.5-flash", threshold_pct: float = 0.8) -> None:
        self.model = model
        self.threshold = int(_MODEL_WINDOWS.get(model, 1_000_000) * threshold_pct)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """~4 chars/token — fast and network-free; precise enough for a budget threshold."""
        return (len(text) + 3) // 4

    def tokens(self, turns: list[Turn]) -> int:
        return sum(self.estimate_tokens(t.content) for t in turns)

    def over_budget(self, turns: list[Turn]) -> bool:
        return self.tokens(turns) > self.threshold

    async def compact(self, turns: list[Turn], keep_recent: int = 10) -> list[Turn]:
        """If the turns exceed budget, fold everything older than the last `keep_recent`
        into a single `previous_context` turn; otherwise return them unchanged."""
        if len(turns) <= keep_recent or not self.over_budget(turns):
            return turns
        old, recent = turns[:-keep_recent], turns[-keep_recent:]
        with _tracer.start_as_current_span("budget.summarize") as span:
            span.set_attribute("turns_summarized", len(old))
            span.set_attribute("tokens_before", self.tokens(turns))
            summary = await self._summarize(old)
            prev = Turn(role="system", content=f"[previous_context] {summary}")
            compacted = [prev, *recent]
            span.set_attribute("tokens_after", self.tokens(compacted))
        return compacted

    async def _summarize(self, turns: list[Turn]) -> str:
        client = genai.Client()  # inherits Vertex config from the environment
        joined = "\n".join(f"{t.role}: {t.content}" for t in turns)
        resp = await client.aio.models.generate_content(
            model=self.model,
            contents=(
                "Summarize this incident conversation history into a compact paragraph "
                "that preserves key facts, decisions, services, and identifiers:\n\n" + joined
            ),
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            ),
        )
        return resp.text or ""
