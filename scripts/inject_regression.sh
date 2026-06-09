#!/usr/bin/env bash
# Inject a REAL regression into the running payment-service: flip downstream_delay_ms 0 -> 1200.
# This is not seeded data — it changes the real app's real behavior, so /checkout p95 jumps from
# ~80ms to ~1.3s in real spans/logs, which Dynatrace sees and (once anomaly detection is on) Davis
# raises as a real Problem. Run `./scripts/inject_regression.sh revert` to set it back to 0.
set -euo pipefail
CONFIG="$(cd "$(dirname "$0")/.." && pwd)/apps/config/payment.yaml"
MODE="${1:-break}"
if [[ "$MODE" == "revert" || "$MODE" == "fix" ]]; then
  VAL=0; WHAT="REVERTED (healthy)"
else
  VAL=1200; WHAT="BROKEN (1200ms downstream delay)"
fi
# rewrite just the downstream_delay_ms line
tmp="$(mktemp)"
sed -E "s/^downstream_delay_ms:.*/downstream_delay_ms: ${VAL}/" "$CONFIG" > "$tmp" && mv "$tmp" "$CONFIG"
echo "payment-service config -> downstream_delay_ms=${VAL}  [${WHAT}]"
echo "(the service re-reads this file per request — effect is immediate, no restart)"
