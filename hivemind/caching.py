"""Gemini context caching for HiveMind agents (T15-A).

The course spec describes a manual CacheManager — `client.caches.create()` over the system
prompt + tool schemas, plus a `before_model_callback` that injects `cached_content` and
strips system/tools from each request. ADK 2.1.0 makes all of that obsolete: it has NATIVE
context caching via `App(context_cache_config=ContextCacheConfig(...))`. You set a token
floor and ADK creates / reuses / refreshes the Vertex cache itself, strips the cached prefix
from each request, and reports `cacheable_contents_token_count`.

With `min_tokens=32_768` (Gemini's explicit-cache floor), the per-agent split the spec
spells out happens for free: Detective / CodeArch / LogDiver / Liaison / Reviewer — whose
stable prefix (system + concatenated MCP tool schemas) clears 32k — get explicit caching;
Scribe (no tools, narrow) falls below the floor and rides free implicit caching. No manual
cache plumbing, no fragile callback surgery.

NOTE (proven in scripts/measure_caching.py): ADK explicit caching only reuses a cache
within a PERSISTENT session. The orchestrator runs a fresh session per incident to keep
investigations isolated, so this explicit layer is intentionally NOT wired there (it would
only create throwaway caches) — that path rides free implicit caching. This config pays off
in any persistent-session context: a chat mode, or an agent re-running in the revise loop.

Reference: https://ai.google.dev/gemini-api/docs/caching
"""

from __future__ import annotations

from google.adk.agents.context_cache_config import ContextCacheConfig

# Explicit caching only above Gemini's 32,768-token floor; refresh hourly (matches the
# spec's 60-min TTL). cache_intervals defaults to 10 (reuse a cache for up to 10 calls).
CACHE_CONFIG = ContextCacheConfig(min_tokens=32_768, ttl_seconds=3600)
