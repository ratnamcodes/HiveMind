#!/usr/bin/env bash
# Run the real demo services locally, emitting real OTLP telemetry to the Dynatrace tenant.
# Logs flow to Grail today (logs.ingest) and ground the live Detective evidence + recovery proof.
# Traces/metrics stay OFF (they'd 403/retry-storm and starve the logs export) until a scoped token
# exists — then set DT_OTLP_TOKEN + DT_TRACES=1 in .env. Stop with scripts/stop_apps.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps"

DT_ENV="$(grep -E '^DT_ENVIRONMENT=' "$ROOT/.env" | head -1 | cut -d= -f2 | sed 's#/$##; s/\.apps\./.live./')"
export DT_OTLP_ENDPOINT="${DT_ENV}/api/v2/otlp"
export DT_OTLP_TOKEN="$(grep -E '^DT_OTLP_TOKEN=' "$ROOT/.env" | head -1 | cut -d= -f2)"
[ -z "${DT_OTLP_TOKEN:-}" ] && export DT_OTLP_TOKEN="$(grep -E '^DT_API_TOKEN=' "$ROOT/.env" | tail -1 | cut -d= -f2)"
# Enable real trace+metric export when a scoped token is configured (DT_TRACES=1 in .env).
export DT_TRACES="$(grep -E '^DT_TRACES=' "$ROOT/.env" | head -1 | cut -d= -f2)"
echo "OTLP -> ${DT_OTLP_ENDPOINT} (token ${DT_OTLP_TOKEN:0:14}..., traces=${DT_TRACES:-0})"

PORT=3101 OTEL_SERVICE_NAME=payment-service node -r ./otel.js payment-service.js >/tmp/hm_payment.log 2>&1 & echo $! > /tmp/hm_payment.pid
sleep 2
PORT=3100 PAYMENT_URL=http://localhost:3101 OTEL_SERVICE_NAME=checkout-service node -r ./otel.js checkout-service.js >/tmp/hm_checkout.log 2>&1 & echo $! > /tmp/hm_checkout.pid
sleep 2
RPS=10 node loadgen.js >/tmp/hm_loadgen.log 2>&1 & echo $! > /tmp/hm_loadgen.pid
echo "apps up: payment(:3101) checkout(:3100) loadgen(~10rps). logs in /tmp/hm_*.log"
