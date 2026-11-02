#!/usr/bin/env bash
# OPEN position watch — 23:00 UTC Mon–Fri. Stdout = unique bullets only.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${RENEE_VENV:-$HOME/.hermes/profiles/renee/.venv/bin/python3}"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
# Live delivery: unique bullets Telegram; trail compare / Kelly / ACK / NAV
# stay file-only inside position_watch.py. Pass --shadow to silence Yahoo/risk-plan
# classes again. atr-chandelier-v1 adopt remains owner-driven (PROPOSED_TRAIL).
exec "$PY" "$HERE/position_watch.py" "$@"
