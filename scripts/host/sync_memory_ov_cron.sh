#!/usr/bin/env bash
# Cron wrapper for sync_memory_to_ov.py — watchdog mode.
#
# Silent on success (empty stdout, exit 0).
# On failure prints to stdout and exits 1 so a no_agent cron surfaces it.
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="${HERMES_HOME}/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
exec python3 "${HERMES_HOME}/scripts/sync_memory_to_ov.py" --quiet
