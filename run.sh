#!/usr/bin/env bash
set -euo pipefail
cd /home/dark/dark-reposter
export PYTHONPATH=src
exec /home/dark/dark-reposter/.venv/bin/python -m dark_reposter