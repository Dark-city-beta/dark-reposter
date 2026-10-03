#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PID_FILE="data/dark-reposter.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "NOT_RUNNING"
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "NOT_RUNNING"
  exit 0
fi

kill "$pid"
rm -f "$PID_FILE"
echo "STOPPED $pid"
