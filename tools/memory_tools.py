"""ADK function-call tools wrapping HiveMind's two-tier memory layer.

These plain async callables are picked up by Google ADK's LlmAgent
(via `tools=[...]`) and exposed to Gemini as native function calls.
Docstrings double as the tool schema, so they're written for the model
to read.
"""

from __future__ import annotations

from typing import Any

from hivemind.memory import ColdMemory, HotMemory, Incident

_hot = HotMemory()
_cold = ColdMemory()


async def remember_turn(
    channel_id: str,
    role: str,
    content: str,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Append a conversation turn to a channel's short-term memory.

    Call this every time a message is produced in an incident channel so
    any agent joining the channel later can catch up on context.

    Args:
        channel_id: The incident channel id, e.g. "inc-0142".
        role: One of "user", "agent", "system".
        content: The full text of the message.
        agent_id: Optional name of the agent producing this turn.

    Returns:
        {"status": "ok"} on success.
    """
    await _hot.append(channel_id, role, content, agent_id=agent_id)  # type: ignore[arg-type]
    return {"status": "ok"}


async def recent_turns(channel_id: str, n: int = 20) -> dict[str, Any]:
    """Read the most recent turns from a channel's short-term memory.

    Use this when joining a channel mid-incident, or before responding,
    so you have context on what's already been said.

    Args:
        channel_id: The incident channel id.
        n: Max number of turns to return (1..20).

    Returns:
        {"status": "ok", "turns": [...]} where each turn has
        role / content / agent_id / ts (ISO timestamp).
    """
    turns = await _hot.recent(channel_id, n=n)
    return {"status": "ok", "turns": [t.model_dump(mode="json") for t in turns]}


async def recall_similar_incidents(
    query: str,
    k: int = 5,
    services: list[str] | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    """Semantic search of past resolved incidents most similar to `query`.

    Use this at the START of a new incident or whenever you want to know
    "have we seen something like this before?". Matches are by meaning,
    not by exact words — feel free to paraphrase the problem.

    Args:
        query: Free-text description of the current problem.
        k: How many past incidents to return (default 5).
        services: Optional list of service names to filter by, e.g.
            ["postgres"]. Only incidents touching ANY listed service
            are returned.
        severity: Optional severity filter — "sev1", "sev2", or "sev3".

    Returns:
        {"status": "ok", "incidents": [...]} ordered most -> least similar.
        Each incident includes title, summary, services, severity,
        started_at, resolved_at, mr_url, participants, and a `score`
        (higher = more similar).
    """
    filters: dict[str, Any] = {}
    if services:
        filters["services"] = {"$in": services}
    if severity:
        filters["severity"] = severity
    results = await _cold.recall(query, k=k, filters=filters or None)
    return {
        "status": "ok",
        "incidents": [r.model_dump(mode="json") for r in results],
    }


async def store_finished_incident(incident: dict[str, Any]) -> dict[str, Any]:
    """Archive a fully-resolved incident into long-term memory.

    Atlas auto-embeds the `summary` field on insert so future
    `recall_similar_incidents` queries can find this incident by meaning.

    Args:
        incident: Dict matching the Incident schema with keys: id, title,
            summary, services, severity (sev1/sev2/sev3), started_at
            (ISO), resolved_at (ISO or null), mr_url (str or null),
            participants (list of agent ids).

    Returns:
        {"status": "ok", "id": <incident_id>}.
    """
    inc = Incident.model_validate(incident)
    await _cold.store_incident(inc)
    return {"status": "ok", "id": inc.id}


MEMORY_TOOLS = [
    remember_turn,
    recent_turns,
    recall_similar_incidents,
    store_finished_incident,
]
