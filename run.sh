#!/usr/bin/env bash
set -euo pipefail
# Load centralized proxy environment
if [ -f /home/dark/online24/proxy.env ]; then
    . /home/dark/online24/proxy.env
fi
cd /home/dark/dark-reposter
export PYTHONPATH=src
exec /home/dark/dark-reposter/.venv/bin/python -m dark_reposter