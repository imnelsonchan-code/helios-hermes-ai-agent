#!/usr/bin/env bash
# validate_wow_diff.sh — post valuation-width-scan WoW health check (P2a)
# Runs validate_wow_diff.py against the latest valuation-width report.
# Then width_publish_guard.py (JSON vs published revised.md). Non-blocking.
set -u
ELIZA_VENV="${ELIZA_VENV:-$HOME/.hermes/profiles/eliza/venv/bin/python}"
SCRIPT="${VALIDATE_WOW_SCRIPT:-$HOME/.hermes/scripts/validate_wow_diff.py}"
if [[ ! -f "$SCRIPT" ]]; then
  SCRIPT="$HOME/.hermes/profiles/eliza/scripts/valuation/validate_wow_diff.py"
fi
if [[ ! -f "$SCRIPT" ]]; then
  echo "ERROR: missing script: $SCRIPT" >&2
  exit 127
fi
# Capture the main check's rc separately (never swallowed silently) and keep
# the wrapper non-blocking for the cron only on a *successful or soft-guard*
# run; a crashed checker still leaves a WARN in the delivered stdout.
wow_rc=0
OUT=$("$ELIZA_VENV" "$SCRIPT" 2>&1) || wow_rc=$?
if [[ "$wow_rc" -ne 0 ]]; then
  echo "WARN: validate_wow_diff.py exited $wow_rc — WoW check did not complete" >&2
fi
echo "$OUT"
GUARD="${WIDTH_GUARD:-$HOME/.hermes/scripts/width_publish_guard.py}"
if [[ -f "$GUARD" ]]; then
  "$ELIZA_VENV" "$GUARD" 2>&1 || true
fi
# surface to caller; cron delivers stdout via deliver='origin'
exit 0
