#!/usr/bin/env bash
# desk cross-cutting smoke audit (docs + workflow YAML + Zoe Z-XC)
# Static grep/assert only — no network, no API keys, no live cron.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTRACTS="${ROOT}/docs/desk-artifact-contracts.md"
WF="${ROOT}/profiles/desk/workflows"
ZOE="${ROOT}/profiles/zoe"
DAILY_WF="${WF}/desk-pack-daily.yaml"
WEEKLY_WF="${WF}/desk-pack-weekly.yaml"

PASS=0
FAIL=0

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold() { printf '\033[1m%s\033[0m\n' "$*"; }

ok() {
  PASS=$((PASS + 1))
  green "  PASS  $*"
}

fail() {
  FAIL=$((FAIL + 1))
  red "  FAIL  $*"
}

section() {
  bold ""
  bold "== $1 =="
}

# ---------------------------------------------------------------------------
section "1. desk-artifact-contracts.md (ART ids)"
# ---------------------------------------------------------------------------

ART_IDS=(
  ART-TM-DAILY-PACK
  ART-VAL-WIDTH-PACK
  ART-TM-SESSION-D
  ART-VAL-SESSION
  ART-E5-OVERLAP
  ART-SESSION-SUMMARY
)

if [[ -f "$CONTRACTS" ]]; then
  ok "docs/desk-artifact-contracts.md exists"
  for id in "${ART_IDS[@]}"; do
    if grep -Fq "$id" "$CONTRACTS"; then
      ok "contracts mention ${id}"
    else
      fail "contracts missing ${id}"
    fi
  done
else
  fail "missing docs/desk-artifact-contracts.md"
  for id in "${ART_IDS[@]}"; do
    fail "contracts missing ${id} (file absent)"
  done
fi

# ---------------------------------------------------------------------------
section "2. workflow YAML files (presence + markers)"
# ---------------------------------------------------------------------------

WORKFLOWS=(desk-pack-daily.yaml desk-pack-weekly.yaml desk-pack-saturday.yaml)

for y in "${WORKFLOWS[@]}"; do
  f="${WF}/${y}"
  if [[ ! -f "$f" ]]; then
    fail "missing workflow: $f"
    continue
  fi
  ok "workflow present: ${y}"

  if grep -Eq '^kind:[[:space:]]*documentation_workflow[[:space:]]*$' "$f" \
    || grep -Fq 'kind: documentation_workflow' "$f"; then
    ok "${y}: kind: documentation_workflow"
  else
    fail "${y}: missing kind: documentation_workflow"
  fi

  if grep -Eq 'E5_no_blend|\bE5\b' "$f"; then
    ok "${y}: E5_no_blend or E5"
  else
    fail "${y}: missing E5_no_blend or E5"
  fi

  if grep -Eq '^reviser_map:|^[[:space:]]*reviser_map:' "$f" \
    || grep -Fq 'reviser_map:' "$f"; then
    ok "${y}: reviser_map present"
  else
    fail "${y}: missing reviser_map"
  fi

  if grep -Fq 'Z-XC-01' "$f"; then
    ok "${y}: mentions Z-XC-01"
  else
    fail "${y}: missing Z-XC-01"
  fi

  if grep -Eq 'Z-XC' "$f"; then
    ok "${y}: mentions Z-XC"
  else
    fail "${y}: missing Z-XC mention"
  fi
done

# ---------------------------------------------------------------------------
section "2b. desk-pack-weekly.yaml car order (Car1 christina → Car2 emily)"
# ---------------------------------------------------------------------------

if [[ ! -f "$WEEKLY_WF" ]]; then
  fail "missing desk-pack-weekly.yaml"
else
  c1=$(grep -n 'Car 1 — christina' "$WEEKLY_WF" | head -1 | cut -d: -f1 || true)
  c2=$(grep -n 'Car 2 — emily' "$WEEKLY_WF" | head -1 | cut -d: -f1 || true)
  if [[ -n "$c1" && -n "$c2" ]] && (( c1 < c2 )); then
    ok "weekly YAML: Car1 christina before Car2 emily"
  else
    fail "weekly YAML must have Car1 christina before Car2 emily"
  fi
  if grep -Fq 'Car 1 — emily' "$WEEKLY_WF"; then
    fail "weekly YAML still emily-first Car 1"
  else
    ok "weekly YAML not emily-first Car 1"
  fi
fi

# ---------------------------------------------------------------------------
section "2c. desk-pack-daily.yaml reviser_map (tm→renee, value→eliza)"
# ---------------------------------------------------------------------------

if [[ ! -f "$DAILY_WF" ]]; then
  fail "missing desk-pack-daily.yaml (cannot check revisers)"
else
  if grep -Eq 'tm_session_daily:[[:space:]]*renee' "$DAILY_WF"; then
    ok "daily YAML: tm_session_daily reviser = renee"
  else
    fail "daily YAML: tm_session_daily must map to renee"
  fi
  if grep -Eq 'value_session:[[:space:]]*eliza' "$DAILY_WF"; then
    ok "daily YAML: value_session reviser = eliza"
  else
    fail "daily YAML: value_session must map to eliza"
  fi
fi

# ---------------------------------------------------------------------------
section "3. Zoe Z-XC-01…08 (SOUL + checklist)"
# ---------------------------------------------------------------------------

ZOE_SOUL="${ZOE}/SOUL.md"
ZOE_CHECKLIST="${ZOE}/skills-checklist.md"

if [[ ! -f "$ZOE_SOUL" ]]; then
  fail "missing $ZOE_SOUL"
else
  # Accept either individual Z-XC-01..08 rows or a compact Z-XC-01…08 / Z-XC-01...08 table label.
  if grep -Eq 'Z-XC-01[[:space:]]*[….]{1,3}[[:space:]]*08' "$ZOE_SOUL"; then
    ok "SOUL.md has Z-XC-01…08 table/range"
  else
    missing_xc=()
    for n in 01 02 03 04 05 06 07 08; do
      if ! grep -Fq "Z-XC-${n}" "$ZOE_SOUL"; then
        missing_xc+=("Z-XC-${n}")
      fi
    done
    if ((${#missing_xc[@]} == 0)); then
      ok "SOUL.md contains Z-XC-01 through Z-XC-08"
    else
      fail "SOUL.md missing: ${missing_xc[*]}"
    fi
  fi
fi

if [[ ! -f "$ZOE_CHECKLIST" ]]; then
  fail "missing $ZOE_CHECKLIST"
else
  if grep -Eq 'Z-XC' "$ZOE_CHECKLIST"; then
    ok "skills-checklist.md mentions Z-XC"
  else
    fail "skills-checklist.md missing Z-XC"
  fi
fi

# ---------------------------------------------------------------------------
section "Summary"
# ---------------------------------------------------------------------------

echo ""
echo "desk audit: ${PASS} passed, ${FAIL} failed"
if (( FAIL > 0 )); then
  red "RESULT: FAIL"
  exit 1
fi
green "RESULT: PASS"
exit 0
