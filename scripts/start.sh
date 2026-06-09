#!/usr/bin/env bash
# One command to bring up the ENTIRE HiveMind stack, then open http://localhost:3000:
#   infra (Redis + Phoenix) · the API · the web app · the instrumented demo services + load.
# Idempotent — safe to re-run. Stop with scripts/stop.sh.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BUN="$(command -v bun || echo /opt/homebrew/bin/bun)"

echo "[1/4] infra: Redis + Phoenix (docker)…"
docker compose up -d redis phoenix >/dev/null 2>&1 || docker compose up -d >/dev/null 2>&1

echo "[2/4] API on :8000…"
pkill -f "uvicorn app:app" >/dev/null 2>&1; sleep 1
PYTHONPATH="$ROOT" "$ROOT/.venv/bin/python" -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level warning >/tmp/hivemind_api.log 2>&1 &
for _ in $(seq 1 30); do curl -s -m2 http://localhost:8000/healthz >/dev/null 2>&1 && break; sleep 1; done

echo "[3/4] web on :3000…"
pkill -f "next dev" >/dev/null 2>&1; sleep 1
( cd "$ROOT/web" && NEXT_PUBLIC_API_BASE= "$BUN" dev >/tmp/hivemind_web.log 2>&1 & )
for _ in $(seq 1 30); do curl -s -m2 -o /dev/null http://localhost:3000/ 2>/dev/null && break; sleep 1; done

echo "[4/4] instrumented services: checkout + payment + load generator…"
bash "$ROOT/scripts/run_apps.sh" >/dev/null 2>&1

echo ""
echo "  HiveMind is up  ->  http://localhost:3000"
echo "  Trigger a real incident:   bash scripts/inject_regression.sh break"
echo "  (the checkout app detects its own SLO breach and pages HiveMind automatically)"
