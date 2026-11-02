#!/usr/bin/env bash
# Zoe challenge->revision tracker wrapper
# Runs the tracker and only outputs if there are CURRENT unresolved issues
set -euo pipefail

OUTPUT=$($HOME/.hermes/profiles/renee/.venv/bin/python3 $HOME/.hermes/scripts/zoe_tracker.py --days 14 --items 2>&1) || true

# Summary only (first ~8 lines). Telegram on missing revision / stale / orphan.
# Do not page on "Resolved (w/ items open)" — that is a file-level pass.
SUMMARY=$(echo "$OUTPUT" | head -8)

if echo "$SUMMARY" | grep -qE "Stale.+: [1-9]|Unresolved.+: [1-9]|Orphaned.+: [1-9]|💀"; then
    echo "$OUTPUT"
    echo ""
    echo "[ACTION REQUIRED] Stale, unresolved, or orphaned challenges — please review."
else
    exit 0
fi
