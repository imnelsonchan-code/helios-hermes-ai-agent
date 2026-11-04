#!/usr/bin/env bash
# Cron entry: Renee Scoring IC (eliza venv has scipy + yfinance).
# Hermes cron deliberately ignores shebang on .py — must wrap like scoring_eval_*.sh.
# NOTE (public pack): scoring_ic_tracker.py is a host-only helper not in this
# snapshot — this wrapper errors clearly until you provide it.
set -euo pipefail
PY="${HOME}/.hermes/profiles/eliza/venv/bin/python3"
SCRIPT="${HOME}/.hermes/scripts/scoring_ic_tracker.py"
if [[ ! -f "$PY" ]]; then
  echo "ERROR: python not found: $PY" >&2
  exit 127
fi
if [[ ! -f "$SCRIPT" ]]; then
  echo "ERROR: missing script: $SCRIPT (host-only, not in the public pack)" >&2
  exit 127
fi
exec "$PY" "$SCRIPT" "$@"
