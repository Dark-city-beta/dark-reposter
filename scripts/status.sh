#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if systemctl --user is-active dark-reposter.service &>/dev/null; then
  echo "=== SYSTEMD SERVICE: ACTIVE (RUNNING) ==="
  systemctl --user status dark-reposter.service --no-pager
  echo "=== RECENT LOGS ==="
  journalctl --user -u dark-reposter -n 30 --no-pager
  exit 0
fi

PID_FILE="data/dark-reposter.pid"
LOG_FILE="logs/dark-reposter.log"

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "RUNNING $pid (standalone)"
  else
    echo "STALE_PID"
  fi
else
  echo "NOT_RUNNING"
fi

tail -80 "$LOG_FILE" 2>/dev/null || true
