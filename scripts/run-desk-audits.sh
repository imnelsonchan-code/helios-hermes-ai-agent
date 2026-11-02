#!/usr/bin/env bash
# Run desk session audits: emily + christina + desk smoke.
# Aggregate exit code. No network / no secrets.
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

run_one "emily" "${ROOT}/profiles/emily/tests/run_emily_audit.sh"
run_one "christina" "${ROOT}/profiles/christina/tests/run_christina_audit.sh"
run_one "desk" "${ROOT}/profiles/desk/tests/run_desk_audit.sh"

echo ""
if (( FAIL > 0 )); then
  echo "desk audits: ${FAIL} suite(s) failed"
  exit 1
fi
echo "desk audits: all PASS"
exit 0
