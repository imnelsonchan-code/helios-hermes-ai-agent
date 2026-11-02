#!/usr/bin/env bash
# Run equity-sleeve audits: eliza + renee (+ desk smoke). Aggregate exit code.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

run_one() {
  local label="$1"
  local script="$2"
  echo ""
  echo "======== ${label} ========"
  if [[ ! -x "$script" && ! -f "$script" ]]; then
    echo "MISSING: $script"
    FAIL=$((FAIL + 1))
    return
  fi
  if bash "$script"; then
    echo "${label}: PASS"
  else
    echo "${label}: FAIL"
    FAIL=$((FAIL + 1))
  fi
}

run_one "eliza" "${ROOT}/profiles/eliza/tests/run_eliza_audit.sh"
run_one "renee" "${ROOT}/profiles/renee/tests/run_renee_audit.sh"
run_one "desk" "${ROOT}/profiles/desk/tests/run_desk_audit.sh"

echo ""
if (( FAIL > 0 )); then
  echo "equity-sleeve audits: ${FAIL} suite(s) failed"
  exit 1
fi
echo "equity-sleeve audits: all PASS"
exit 0
