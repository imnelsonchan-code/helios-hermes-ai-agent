#!/usr/bin/env bash
# Cron entry: weekly scoring-eval overlays (eliza venv has yfinance).
set -euo pipefail
PY="${HOME}/.hermes/profiles/eliza/venv/bin/python3"
SCRIPT="${HOME}/.hermes/scripts/scoring_eval_weekly.py"
if [[ ! -f "$PY" ]]; then
  echo "ERROR: python not found: $PY" >&2
  exit 127
fi
if [[ ! -f "$SCRIPT" ]]; then
  echo "ERROR: missing script: $SCRIPT" >&2
  exit 127
fi
exec "$PY" "$SCRIPT" "$@"
