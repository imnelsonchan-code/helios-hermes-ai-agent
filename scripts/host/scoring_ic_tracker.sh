#!/usr/bin/env bash
# Cron entry: Renee Scoring IC (eliza venv has scipy + yfinance).
# Hermes cron deliberately ignores shebang on .py — must wrap like scoring_eval_*.sh.
set -euo pipefail
PY="${HOME}/.hermes/profiles/eliza/venv/bin/python3"
SCRIPT="${HOME}/.hermes/scripts/scoring_ic_tracker.py"
exec "$PY" "$SCRIPT" "$@"
