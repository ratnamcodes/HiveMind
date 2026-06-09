#!/usr/bin/env bash
for p in payment checkout loadgen; do
  [ -f "/tmp/hm_${p}.pid" ] && kill "$(cat /tmp/hm_${p}.pid)" 2>/dev/null && echo "stopped ${p}"
done
