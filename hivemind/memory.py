"""Two-tier memory for HiveMind agents.

HotMemory (Redis) holds the last 20 turns per channel (24h TTL).

ColdMemory (MongoDB Atlas) holds finished incidents as semantic records.
Voyage AI auto-embeds the `summary` field on insert via the
collection-level autoEmbed index, so this module never embeds anything
itself; both inserts and `$vectorSearch` queries pass plain text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from hivemind.mongo_client import get_db
from hivemind.redis_client import get_redis

CHANNEL_KEY_TEMPLATE = "channel:{channel_id}:turns"
HOT_WINDOW = 20
HOT_TTL_SECONDS = 60 * 60 * 24  # 24h

INCIDENTS_COLLECTION = "incidents"
VECTOR_INDEX = "incidents_vector_idx"
EMBED_PATH = "summary"

# Atomic RPUSH + LTRIM + EXPIRE so concurrent appends never race the trim.
# KEYS[1] = list key, ARGV[1] = turn JSON, ARGV[2] = max length, ARGV[3] = ttl.
_APPEND_LUA = """
redis.call('RPUSH', KEYS[1], ARGV[1])
redis.call('LTRIM', KEYS[1], -tonumber(ARGV[2]), -1)
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
return 1
"""


Role = Literal["user", "agent", "system"]
Severity = Literal["sev1", "sev2", "sev3"]


class Turn(BaseModel):
    """One message in a channel's short-term memory."""

    role: Role
    content: str
    agent_id: str | None = None
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Incident(BaseModel):
    """A finished incident archived to ColdMemory."""

    id: str
    title: str
    summary: str  # Voyage auto-embeds this into the vector index.
    services: list[str] = Field(default_factory=list)
    severity: Severity = "sev3"
    started_at: datetime
    resolved_at: datetime | None = None
    mr_url: str | None = None
    participants: list[str] = Field(default_factory=list)


class IncidentRecall(Incident):
    """An incident returned from a recall query, annotated with its score."""

    score: float


class HotMemory:
    """Sliding window of recent turns per channel, backed by Redis.

    All ops are atomic: append uses a Lua script that combines RPUSH + LTRIM
    + EXPIRE so concurrent appends can't interleave with the trim. Only the
    memory-tools surface and scripts use this today.
    """

    def __init__(self) -> None:
        self._redis = get_redis()

    @staticmethod
    def _key(channel_id: str) -> str:
        return CHANNEL_KEY_TEMPLATE.format(channel_id=channel_id)

    async def append(
        self,
        channel_id: str,
        role: Role,
        content: str,
        agent_id: str | None = None,
    ) -> None:
        """Push one turn into the channel's window and refresh its TTL."""
        turn = Turn(role=role, content=content, agent_id=agent_id)
        await self._redis.eval(
            _APPEND_LUA,
            1,
            self._key(channel_id),
            turn.model_dump_json(),
            str(HOT_WINDOW),
            str(HOT_TTL_SECONDS),
        )

    async def recent(self, channel_id: str, n: int = HOT_WINDOW) -> list[Turn]:
        """Return up to the last n turns, ordered oldest -> newest."""
        n = max(1, min(n, HOT_WINDOW))
        raw = await self._redis.lrange(self._key(channel_id), -n, -1)
        return [Turn.model_validate_json(item) for item in raw]

    async def clear(self, channel_id: str) -> None:
        """Drop the channel's window. Typically called when the incident closes."""
        await self._redis.delete(self._key(channel_id))


_PROJECTED_FIELDS: dict[str, Any] = {
    "_id": 1,
    "title": 1,
    "summary": 1,
    "services": 1,
    "severity": 1,
    "started_at": 1,
    "resolved_at": 1,
    "mr_url": 1,
    "participants": 1,
    "score": {"$meta": "vectorSearchScore"},
}


class ColdMemory:
    """Long-term semantic memory of finished incidents in MongoDB Atlas.

    Backed by the collection-level Voyage autoEmbed index on `summary`;
    inserts and queries both pass plain text, so no embedding code or
    API keys live in this process.
    """

    def __init__(self) -> None:
        self._collection = get_db()[INCIDENTS_COLLECTION]

    async def store_incident(self, incident: Incident) -> None:
        """Insert an incident; Atlas auto-embeds the `summary` on write."""
        doc = incident.model_dump(mode="python")
        doc["_id"] = doc.pop("id")
        await self._collection.insert_one(doc)

    async def recall(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[IncidentRecall]:
        """Top-k incidents most similar to `query`, with optional post-filter.

        `filters` is a MongoDB query expression applied as a `$match` stage
        after `$vectorSearch`. When filters are present we over-fetch from
        vector search so post-filtering rarely returns fewer than k results.
        """
        vector_limit = k * 4 if filters else k
        pipeline: list[dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX,
                    "path": EMBED_PATH,
                    "query": query,
                    "limit": vector_limit,
                    "numCandidates": max(vector_limit * 10, 50),
                }
            }
        ]
        if filters:
            pipeline.append({"$match": filters})
        pipeline.append({"$limit": k})
        pipeline.append({"$project": _PROJECTED_FIELDS})

        results: list[IncidentRecall] = []
        async for doc in self._collection.aggregate(pipeline):
            doc["id"] = doc.pop("_id")
            results.append(IncidentRecall.model_validate(doc))
        return results

    async def related_to(self, incident_id: str, k: int = 3) -> list[IncidentRecall]:
        """Find the k most similar incidents to an existing one.

        Re-uses the source incident's `summary` text as the recall query and
        drops the source itself from results. We over-fetch by one so a
        self-match doesn't shrink the returned set below k. Only the
        memory-tools surface and scripts use this today.
        """
        source = await self._collection.find_one(
            {"_id": incident_id}, {"summary": 1}
        )
        if not source or not source.get("summary"):
            return []
        candidates = await self.recall(source["summary"], k=k + 1)
        return [r for r in candidates if r.id != incident_id][:k]
