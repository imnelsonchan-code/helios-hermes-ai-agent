#!/usr/bin/env bash
# Cron entry: weekly scoring-eval overlays (eliza venv has yfinance).
set -euo pipefail
PY="${HOME}/.hermes/profiles/eliza/venv/bin/python3"
SCRIPT="${HOME}/.hermes/scripts/scoring_eval_weekly.py"
exec "$PY" "$SCRIPT" "$@"
