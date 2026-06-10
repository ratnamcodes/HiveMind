#!/usr/bin/env bash
set -e
# Bundled in-memory broker for the event bus (Redis pub/sub) on a single Cloud Run instance.
# noeviction so the /ws backlog isn't dropped under memory pressure. The LangGraph checkpointer
# tries RediSearch here and, finding none, falls back to an in-process MemorySaver (see graph.py).
redis-server --save "" --appendonly no --maxmemory 512mb --maxmemory-policy noeviction --daemonize no &
# Wait until Redis answers before the app starts (the event bus connects on first request).
for _ in $(seq 1 50); do redis-cli ping 2>/dev/null | grep -q PONG && break; sleep 0.2; done
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info
