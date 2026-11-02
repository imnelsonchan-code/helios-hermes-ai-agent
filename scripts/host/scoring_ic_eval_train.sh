#!/usr/bin/env bash
# Sunday night train: Renee Scoring IC, then scoring eval weekly overlays.
# IC failure must not skip eval. The train stays red if IC exits non-zero.
# Both cars use eliza-venv .sh wrappers (scipy / yfinance). Do not blend sleeves:
# Car 1 = T&M weekly composite IC; Car 2 = Value IC + Book T/V + PIT + settle.
set -uo pipefail

IC="${SCORING_IC_EVAL_IC:-${HOME}/.hermes/scripts/scoring_ic_tracker.sh}"
EVAL="${SCORING_IC_EVAL_WEEKLY:-${HOME}/.hermes/scripts/scoring_eval_weekly.sh}"

if [[ ! -f "$IC" ]]; then
  echo "ERROR: missing IC wrapper: $IC" >&2
  exit 127
fi
if [[ ! -f "$EVAL" ]]; then
  echo "ERROR: missing eval wrapper: $EVAL" >&2
  exit 127
fi

echo "=== Car 1 — Renee Scoring IC (T&M 1w) ==="
ic_rc=0
bash "$IC" || ic_rc=$?
if [[ "$ic_rc" -ne 0 ]]; then
  echo "WARN: Scoring IC exited $ic_rc — continuing to scoring eval weekly" >&2
fi

echo "=== Car 2 — scoring eval weekly (Value IC + books + PIT + settle) ==="
eval_rc=0
bash "$EVAL" "$@" || eval_rc=$?

if [[ "$eval_rc" -ne 0 ]]; then
  exit "$eval_rc"
fi
exit "$ic_rc"
