#!/usr/bin/env bash
# Mon–Fri 23:00 train: Kelly size -> Live drawdown -> OPEN position watch.
# One car failing must not skip the rest. Train stays red if any car exits non-zero.
# Prefer position_watch exit code when it fails (primary inbox artifact).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${POSITION_RISK_PYTHON:-${HOME}/.hermes/hermes-agent/venv/bin/python3}"
KELLY="${POSITION_RISK_KELLY:-${HERE}/position_sizing_check.py}"
DD="${POSITION_RISK_DRAWDOWN:-${HERE}/drawdown_monitor.py}"
WATCH="${POSITION_RISK_WATCH:-${HERE}/position_watch.sh}"

if [[ ! -x "$PY" ]]; then
  echo "ERROR: python not executable: $PY" >&2
  exit 127
fi
if [[ ! -f "$KELLY" ]]; then
  echo "ERROR: missing Kelly script: $KELLY" >&2
  exit 127
fi
if [[ ! -f "$DD" ]]; then
  echo "ERROR: missing drawdown script: $DD" >&2
  exit 127
fi
if [[ ! -x "$WATCH" && ! -f "$WATCH" ]]; then
  echo "ERROR: missing position_watch: $WATCH" >&2
  exit 127
fi

echo "=== Car 1 — Kelly position sizing ==="
kelly_rc=0
"$PY" "$KELLY" || kelly_rc=$?
if [[ "$kelly_rc" -ne 0 ]]; then
  echo "WARN: Kelly exited $kelly_rc — continuing to drawdown" >&2
fi

echo "=== Car 2 — Live drawdown ==="
dd_rc=0
"$PY" "$DD" || dd_rc=$?
if [[ "$dd_rc" -ne 0 ]]; then
  echo "WARN: drawdown exited $dd_rc — continuing to position watch" >&2
fi

echo "=== Car 3 — OPEN position watch ==="
watch_rc=0
bash "$WATCH" "$@" || watch_rc=$?

if [[ "$watch_rc" -ne 0 ]]; then
  exit "$watch_rc"
fi
if [[ "$kelly_rc" -ne 0 ]]; then
  exit "$kelly_rc"
fi
exit "$dd_rc"
