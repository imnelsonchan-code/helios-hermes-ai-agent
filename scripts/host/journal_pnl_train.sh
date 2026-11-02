#!/usr/bin/env bash
# Sunday night train: journal integrity, then Portfolio P&L.
# A dirty journal must not skip P&L. The train stays red if integrity exits non-zero.
# Hermes cron ignores .py shebangs — call the gateway venv explicitly.
set -uo pipefail

PY="${JOURNAL_PNL_PYTHON:-${HOME}/.hermes/hermes-agent/venv/bin/python3}"
INTEG="${JOURNAL_PNL_INTEGRITY:-${HOME}/.hermes/scripts/journal_integrity_check.py}"
PNL="${JOURNAL_PNL_TRACKER:-${HOME}/.hermes/scripts/portfolio_tracker.py}"

if [[ ! -x "$PY" ]]; then
  echo "ERROR: python not executable: $PY" >&2
  exit 127
fi

echo "=== Car 1 — journal integrity ==="
integ_rc=0
"$PY" "$INTEG" || integ_rc=$?
if [[ "$integ_rc" -ne 0 ]]; then
  echo "WARN: journal integrity exited $integ_rc — continuing to Portfolio P&L" >&2
fi

echo "=== Car 2 — Portfolio P&L ==="
pnl_rc=0
"$PY" "$PNL" "$@" || pnl_rc=$?

if [[ "$pnl_rc" -ne 0 ]]; then
  exit "$pnl_rc"
fi
exit "$integ_rc"
