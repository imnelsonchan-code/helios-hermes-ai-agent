#!/usr/bin/env bash
# Mon–Fri 23:00 train: Kelly size -> Live drawdown -> OPEN position watch.
# One car failing must not skip the rest. Train stays red if any car exits non-zero.
# Prefer position_watch exit code when it fails (primary inbox artifact).
#
# NOTE (public pack): `position_sizing_check.py` and `drawdown_monitor.py`
# (the Kelly / drawdown legs) are host-only helpers and are NOT included in
# this public snapshot. Without them, Cars 1–2 fail with the errors below and
# only Car 3 (position_watch) can run — either point POSITION_RISK_KELLY /
# POSITION_RISK_DRAWDOWN at your own copies, or seed the catalog with the
# position-watch leg alone. See docs/cron-catalog.md.
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
if [[ ! -x "$WATCH" && ! -f "$WATCH" ]]; then
  echo "ERROR: missing position_watch: $WATCH" >&2
  exit 127
fi

echo "=== Car 1 — Kelly position sizing ==="
kelly_rc=0
if [[ -f "$KELLY" ]]; then
  "$PY" "$KELLY" || kelly_rc=$?
  if [[ "$kelly_rc" -ne 0 ]]; then
    echo "WARN: Kelly exited $kelly_rc — continuing to drawdown" >&2
  fi
else
  echo "SKIP: Kelly script not present: $KELLY (host-only, not in the public pack — see header note)" >&2
fi

echo "=== Car 2 — Live drawdown ==="
dd_rc=0
if [[ -f "$DD" ]]; then
  "$PY" "$DD" || dd_rc=$?
  if [[ "$dd_rc" -ne 0 ]]; then
    echo "WARN: drawdown exited $dd_rc — continuing to position watch" >&2
  fi
else
  echo "SKIP: drawdown script not present: $DD (host-only, not in the public pack — see header note)" >&2
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
