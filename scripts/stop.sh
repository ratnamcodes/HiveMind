#!/usr/bin/env bash
# Stop the local HiveMind processes (leaves Redis/Phoenix docker running).
bash "$(dirname "$0")/stop_apps.sh" 2>/dev/null
pkill -f "uvicorn app:app" 2>/dev/null && echo "stopped api"
pkill -f "next dev" 2>/dev/null && echo "stopped web"
