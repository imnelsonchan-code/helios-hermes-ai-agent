#!/usr/bin/env bash
# Cron entry: daily scoring-eval overlays (use eliza venv for consistency).
set -euo pipefail
PY="${HOME}/.hermes/profiles/eliza/venv/bin/python3"
SCRIPT="${HOME}/.hermes/scripts/scoring_eval_daily.py"
exec "$PY" "$SCRIPT" "$@"
