#!/usr/bin/env bash
# Fail if desk-pack emily commodity prompts still use the pre-insight load order.
# Observation-only static check — no network, no secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HOST="${ROOT}/scripts/host"

PASS=0
FAIL=0

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold() { printf '\033[1m%s\033[0m\n' "$*"; }

ok() {
 PASS=$((PASS + 1))
 green " PASS $*"
}

fail() {
 FAIL=$((FAIL + 1))
 red " FAIL $*"
}

# Legacy (pre 8-skill): sources → signal → world → puzzle → trunk
OLD_LOAD_RE='commodity-sources-crawl[[:space:]]*(→|->)[[:space:]]*commodity-signal-table[[:space:]]*(→|->)[[:space:]]*world-to-commodity'

# Canonical Keep-8 long form (ASCII -> or Unicode →)
NEW_LOAD_RE='commodity-sources-crawl[[:space:]]*(→|->)[[:space:]]*world-to-commodity[[:space:]]*(→|->)[[:space:]]*commodity-insight[[:space:]]*(→|->)[[:space:]]*commodity-direction[[:space:]]*(→|->)[[:space:]]*commodity-forecast[[:space:]]*(→|->)[[:space:]]*commodity-signal-table[[:space:]]*(→|->)[[:space:]]*commodity-puzzle[[:space:]]*(→|->)[[:space:]]*commodity-session-report'

C_DIR_BAN_RE='C_\*[[:space:]]*Direction|C_\*[[:space:]]*written[[:space:]]+into[[:space:]]+Direction'

bold "== Desk-pack emily load-order check =="

PROMPT_FILES=(
 "${HOST}/desk_pack_daily_train_prompts.py"
 "${HOST}/desk_pack_weekly_prompts.py"
 "${HOST}/desk_pack_w_d1_prompts.py"
 "${HOST}/saturday_self_review_prompts.py"
)

for f in "${PROMPT_FILES[@]}"; do
 base="$(basename "$f")"
 if [[ ! -f "$f" ]]; then
 fail "missing prompt file: $base"
 continue
 fi
 if grep -Eq "$OLD_LOAD_RE" "$f"; then
 fail "$base still has OLD load (sources→signal→world…)"
 else
 ok "$base has no old load-order string"
 fi
 # Daily/weekly train + w_d1 commodities blocks should carry the new chain when present
 if grep -q 'COMMODITIES_' "$f" || grep -q 'commodity-sources-crawl' "$f"; then
 if grep -Eq "$NEW_LOAD_RE" "$f"; then
 ok "$base includes canonical 8-skill load"
 else
 fail "$base missing canonical 8-skill load (insight→direction→forecast)"
 fi
 fi
 if grep -Eq "$C_DIR_BAN_RE" "$f"; then
   ok "$base bans C_* in Direction column"
 else
   fail "$base missing C_* → Direction namespace ban"
 fi
done

# Weekly commodities card only. Rates already says "Lenses three lenses + Dominant"
# without "stub"; this exact phrase must live on the emily weekly card
# (SOUL Weekly Lenses = three lenses stub + Dominant → Zoe REJECT/Major).
WEEKLY_PROMPTS="${HOST}/desk_pack_weekly_prompts.py"
LENSES_STUB='Lenses stub + Dominant(Macro/Micro/Market)'
if grep -Fq "$LENSES_STUB" "$WEEKLY_PROMPTS"; then
 ok "desk_pack_weekly_prompts.py requires Lenses three lenses stub + Dominant"
else
 fail "desk_pack_weekly_prompts.py missing Lenses three lenses stub + Dominant"
fi
WEEKLY_NEWS='2–3 Emily-topic + calendar(URL ≤12)'
if grep -Fq "$WEEKLY_NEWS" "$WEEKLY_PROMPTS"; then
 ok "desk_pack_weekly_prompts.py requires News 2–3 Emily-topic"
else
 fail "desk_pack_weekly_prompts.py missing News 2–3 Emily-topic"
fi

# Daily / W-D1 use SOUL Daily lenses, not the weekly three lenses stub, and keep ≥1 news.
DAILY_LENSES='Lenses(Macro+Micro; Market ; Dominant)'
for daily in \
 "${HOST}/desk_pack_daily_train_prompts.py" \
 "${HOST}/desk_pack_w_d1_prompts.py"
do
 base="$(basename "$daily")"
 if grep -Fq "$DAILY_LENSES" "$daily"; then
 ok "$base requires daily Lenses (Macro+Micro; Market one sentence; Dominant)"
 else
 fail "$base missing daily Lenses phrase"
 fi
 if grep -Fq 'three lenses stub' "$daily"; then
 fail "$base must not use weekly three lenses stub"
 else
 ok "$base does not use weekly three lenses stub"
 fi
 if grep -Fq '≥1 Emily-topic' "$daily"; then
 ok "$base keeps daily News ≥1 Emily-topic"
 else
 fail "$base missing daily News ≥1 Emily-topic"
 fi
done


bold "== Desk-pack weekly YAML car order =="
WEEKLY_YAML="${ROOT}/profiles/desk/workflows/desk-pack-weekly.yaml"
if [[ ! -f "$WEEKLY_YAML" ]]; then
 fail "missing desk-pack-weekly.yaml"
else
 c1=$(grep -n 'Car 1 — christina' "$WEEKLY_YAML" | head -1 | cut -d: -f1 || true)
 c2=$(grep -n 'Car 2 — emily' "$WEEKLY_YAML" | head -1 | cut -d: -f1 || true)
 if [[ -n "$c1" && -n "$c2" ]] && (( c1 < c2 )); then
 ok "desk-pack-weekly.yaml Car1 christina before Car2 emily"
 else
 fail "desk-pack-weekly.yaml car order wrong (need Car1 christina → Car2 emily)"
 fi
fi
echo ""
echo "desk_pack prompts: ${PASS} passed, ${FAIL} failed"
if (( FAIL > 0 )); then
 red "RESULT: FAIL"
 exit 1
fi
green "RESULT: PASS"
exit 0
