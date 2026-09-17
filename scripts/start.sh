#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p logs data

PID_FILE="data/dark-reposter.pid"
LOG_FILE="logs/dark-reposter.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "ALREADY_RUNNING $old_pid"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

export PYTHONPATH="$PWD/src"
nohup "$PWD/.venv/bin/python" -m dark_reposter >> "$LOG_FILE" 2>&1 &
pid="$!"
echo "$pid" > "$PID_FILE"
sleep 3

if kill -0 "$pid" 2>/dev/null; then
  echo "STARTED $pid"
else
  echo "PROCESS_EXITED"
  tail -80 "$LOG_FILE" || true
  exit 1
fi
