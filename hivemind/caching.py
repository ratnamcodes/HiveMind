"""Gemini context-cache config for ADK agents.
Used only by scripts/measure_caching.py; not wired into the orchestrator.
"""

from __future__ import annotations

from google.adk.agents.context_cache_config import ContextCacheConfig

# Explicit caching only above Gemini's 32,768-token floor; refresh hourly.
# cache_intervals defaults to 10 (reuse a cache for up to 10 calls).
CACHE_CONFIG = ContextCacheConfig(min_tokens=32_768, ttl_seconds=3600)
