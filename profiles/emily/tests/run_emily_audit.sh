#!/usr/bin/env bash
# emily observation-only audit harness
# Static grep/assert + lightweight obs-backtest hygiene (no network, no API keys, no PnL).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
EMILY="${ROOT}/profiles/emily"
SKILLS="${EMILY}/skills"
TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="${TESTS}/fixtures"
SESSION_SKILL="${SKILLS}/commodity-session-report/SKILL.md"
SIGNAL_SKILL="${SKILLS}/commodity-signal-table/SKILL.md"
OBS_FIXTURE="${TESTS}/obs_backtest_fixture.md"

PASS=0
FAIL=0
SECTION=""

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

section() {
 SECTION="$1"
 bold ""
 bold "== $1 =="
}

# Canonical short load-order SSOT (checklist / SOUL)
# Accept either short tokens or full skill folder names, in order.
SSOT_SHORT_RE='sources[[:space:]]*→[[:space:]]*world[[:space:]]*→[[:space:]]*insight[[:space:]]*→[[:space:]]*direction[[:space:]]*→[[:space:]]*forecast[[:space:]]*→[[:space:]]*signal[[:space:]]*→[[:space:]]*puzzle[[:space:]]*→[[:space:]]*trunk'
SSOT_LONG_RE='commodity-sources-crawl[[:space:]]*→[[:space:]]*world-to-commodity[[:space:]]*→[[:space:]]*commodity-insight[[:space:]]*→[[:space:]]*commodity-direction[[:space:]]*→[[:space:]]*commodity-forecast[[:space:]]*→[[:space:]]*commodity-signal-table[[:space:]]*→[[:space:]]*commodity-puzzle[[:space:]]*→[[:space:]]*(commodity-session-report|trunk)'

# Multiline block form used in signal-table / session-report
ssot_in_file() {
 local f="$1"
 # Flatten + strip markdown bold/backticks so `sources` / **world** still match SSOT
 local flat
 flat="$(tr '\n' ' ' <"$f" | sed -e 's/\*\*//g' -e 's/`//g' -e 's/[[:space:]]\+/ /g')"
 if echo "$flat" | grep -Eq "$SSOT_SHORT_RE"; then
 return 0
 fi
 if echo "$flat" | grep -Eq "$SSOT_LONG_RE"; then
 return 0
 fi
 # Also accept vertical arrows with commodity-* names appearing in order
 local idx=-1 next
 for token in commodity-sources-crawl world-to-commodity commodity-insight \
 commodity-direction commodity-forecast commodity-signal-table \
 commodity-puzzle; do
 next="$(echo "$flat" | grep -bo "$token" | head -1 | cut -d: -f1 || true)"
 if [[ -z "${next}" ]]; then
 return 1
 fi
 if (( next <= idx )); then
 return 1
 fi
 idx=$next
 done
 # trunk or commodity-session-report after puzzle
 next="$(echo "$flat" | grep -Ebo 'commodity-session-report|\btrunk\b' | head -1 | cut -d: -f1 || true)"
 [[ -n "${next}" ]] && (( next > idx ))
}

# ---------------------------------------------------------------------------
section "1. Load-order SSOT (all emily skills + checklist + SOUL)"
# ---------------------------------------------------------------------------

EXPECTED_SKILLS=(
 commodity-sources-crawl
 world-to-commodity
 commodity-insight
 commodity-direction
 commodity-forecast
 commodity-signal-table
 commodity-puzzle
 commodity-session-report
)

for skill in "${EXPECTED_SKILLS[@]}"; do
 f="${SKILLS}/${skill}/SKILL.md"
 if [[ ! -f "$f" ]]; then
 fail "missing skill file: $f"
 continue
 fi
 if ssot_in_file "$f"; then
 ok "load-order SSOT present: ${skill}"
 else
 fail "load-order SSOT missing/out-of-order: ${skill}"
 fi
done

for f in "${EMILY}/skills-checklist.md" "${EMILY}/SOUL.md"; do
 if [[ ! -f "$f" ]]; then
 fail "missing: $f"
 continue
 fi
 if ssot_in_file "$f"; then
 ok "load-order SSOT present: $(basename "$f")"
 else
 fail "load-order SSOT missing/out-of-order: $(basename "$f")"
 fi
done

# ---------------------------------------------------------------------------
section "2. Namespace isolation (DIR_* / bare BUY)"
# ---------------------------------------------------------------------------

# 2a — signal-table must ban bare BUY and DIR_* in Signal column
if [[ -f "$SIGNAL_SKILL" ]]; then
 if grep -Eq 'bare[[:space:]]*`?BUY`?|❌[[:space:]]*bare[[:space:]]*`?BUY' "$SIGNAL_SKILL"; then
 ok "signal-table bans bare BUY"
 else
 fail "signal-table must explicitly ban bare BUY"
 fi
 if grep -Eq 'DIR_\*.*(written into|writeinto).*Signal|❌[[:space:]]*.*DIR_\*.*Signal' "$SIGNAL_SKILL"; then
 ok "signal-table bans DIR_* in Signal column"
 else
 fail "signal-table must ban DIR_* written into Signal"
 fi
else
 fail "missing $SIGNAL_SKILL"
fi

# 2b — In Trade map / Signal example tables, Signal cells must not be DIR_* values
# Extract fenced markdown tables that have a "Signal" header; scan data cells in Signal col.
check_signal_cells_no_dir() {
 local f="$1"
 python3 "${TESTS}/signal_cell_audit.py" "$f"
}

if check_signal_cells_no_dir "$SIGNAL_SKILL"; then
 ok "signal-table examples: no DIR_* / bare BUY as Signal values"
else
 fail "signal-table examples: DIR_* or bare BUY found as Signal values"
fi

if check_signal_cells_no_dir "$SESSION_SKILL"; then
 ok "session-report Trade map examples: no DIR_* / bare BUY as Signal values"
else
 fail "session-report Trade map examples: DIR_* or bare BUY as Signal values"
fi

# 2c — checklist Exclude row documents namespace isolation
if grep -Eq 'DIR_\*.*Signal|Namespace' "${EMILY}/skills-checklist.md"; then
 ok "checklist documents DIR_*/Signal namespace isolation"
else
 fail "checklist missing namespace isolation note"
fi

# ---------------------------------------------------------------------------
section "3. Scaffold completeness (Daily/Weekly Insight·Direction·Forecast cite slots)"
# ---------------------------------------------------------------------------

extract_scaffold() {
 local label="$1" # Daily or Weekly
 python3 "${TESTS}/extract_session_scaffold.py" "$SESSION_SKILL" "$label"
}

check_cite_slots() {
 local label="$1"
 local body
 if ! body="$(extract_scaffold "$label")"; then
 fail "${label} scaffold: could not extract copy-paste template"
 return
 fi
 local missing=()
 echo "$body" | grep -Eq '^## Market insight' \
 || missing+=("## Market insight")
 echo "$body" | grep -Eq '^## Commodity direction \(cite commodity-direction' \
 || missing+=("## Commodity direction (cite commodity-direction...)")
 echo "$body" | grep -Eq '^## Commodity forecast \(cite commodity-forecast' \
 || missing+=("## Commodity forecast (cite commodity-forecast...)")
 if ((${#missing[@]} == 0)); then
 ok "${label} scaffold has Insight + Direction + Forecast cite slots"
 else
 fail "${label} scaffold missing: ${missing[*]}"
 fi
 # Soft assert: emit "cite" in each slot heading (already in titles)
 if echo "$body" | grep -Eq 'cite commodity-insight' \
 && echo "$body" | grep -Eq 'cite commodity-direction' \
 && echo "$body" | grep -Eq 'cite commodity-forecast'; then
 ok "${label} scaffold cite wording present for all three"
 else
 fail "${label} scaffold missing cite wording for Insight/Direction/Forecast"
 fi
 if echo "$body" | grep -Eq 'Forecast: skip|or skip'; then
 fail "${label} scaffold still allows Forecast skip"
 else
 ok "${label} scaffold forbids whole-doc Forecast skip"
 fi
 if echo "$body" | grep -q 'lean: base'; then
 ok "${label} scaffold Basis example names a scenario lean"
 else
 fail "${label} scaffold Basis example missing lean: base"
 fi
}

if [[ -f "$SESSION_SKILL" ]]; then
 check_cite_slots "Daily"
 check_cite_slots "Weekly"
else
 fail "missing session skill for scaffold checks"
fi

FORECAST_SKILL="${SKILLS}/commodity-forecast/SKILL.md"
if [[ -f "$FORECAST_SKILL" ]]; then
 if grep -q 'optional Est value bands' "$FORECAST_SKILL"; then
 fail "forecast frontmatter still marks Est bands optional"
 else
 ok "forecast frontmatter does not mark Est bands optional"
 fi
 fuel="$(sed -n '/^### Forecast fuel footnotes (cite-or-miss)$/,/^```$/p' "$FORECAST_SKILL")"
 fuel_missing=()
 for row in Soy Wheat Corn Oil; do
 echo "$fuel" | grep -q "^| ${row} |" || fuel_missing+=("$row")
 done
 if ((${#fuel_missing[@]} == 0)); then
 ok "forecast fuel footnotes list Soy Wheat Corn Oil"
 else
 fail "forecast fuel footnotes missing: ${fuel_missing[*]}"
 fi
else
 fail "missing commodity-forecast skill"
fi
if grep -q 'lean: base|bull|bear|two-way' "$SIGNAL_SKILL"; then
 ok "signal-table requires Basis lean tag"
else
 fail "signal-table missing Basis lean tag"
fi

# ---------------------------------------------------------------------------
section "4. Obs backtest hygiene (fixture · no PnL)"
# ---------------------------------------------------------------------------

OBS_TARGET="${OBS_FIXTURE}"
if [[ ! -f "$OBS_TARGET" ]]; then
 fail "missing obs fixture: $OBS_TARGET"
else
 # Hygiene scorer — observation rules only (no returns / no PnL)
 set +e
 python3 "${TESTS}/obs_hygiene_audit.py" good "$OBS_TARGET"
 obs_rc=$?
 set -e
 if [[ $obs_rc -eq 0 ]]; then
 ok "obs backtest fixture passes hygiene rules"
 else
 fail "obs backtest fixture failed hygiene rules"
 fi
fi

# Also score the intentional bad fixture (must FAIL hygiene) if present
BAD="${FIXTURES}/obs_backtest_bad.md"
if [[ -f "$BAD" ]]; then
 set +e
 python3 "${TESTS}/obs_hygiene_audit.py" bad "$BAD"
 bad_rc=$?
 set -e
 if [[ $bad_rc -eq 0 ]]; then
 ok "bad fixture correctly exhibits namespace violation (negative control)"
 else
 fail "bad fixture should contain bare BUY or DIR_* as Signal (negative control)"
 fi
fi

# ---------------------------------------------------------------------------
section "5. ADAPT patch gates (static keyword presence)"
# ---------------------------------------------------------------------------

# 5a — post-crawl QA / data_delay
CRAWL="${SKILLS}/commodity-sources-crawl/SKILL.md"
if [[ -f "$CRAWL" ]] && grep -Eq 'data_delay|Post-crawl QA|post-crawl QA' "$CRAWL"; then
 ok "sources-crawl documents post-crawl QA / data_delay"
else
 fail "sources-crawl missing post-crawl QA / data_delay"
fi
# 5a2 — high fix: no handoff-only phrasing in sources-crawl (handoff ≠ deliverable)
if [[ -f "$CRAWL" ]] && grep -Fq 'handoff-only phrasing' "$CRAWL"; then
 fail "sources-crawl must not contain handoff-only phrasing"
else
 ok "sources-crawl has no handoff-only phrasing"
fi
# 5a3 — precious US Last = gold-api (Yahoo XAUUSD=X / XAGUSD=X dead)
if [[ -f "$CRAWL" ]] \
 && grep -Eq 'api\.gold-api\.com/price/XAU|gold-api\.com.*XAU' "$CRAWL" \
 && grep -Eq 'api\.gold-api\.com/price/XAG|gold-api\.com.*XAG' "$CRAWL" \
 && grep -Eq 'XAUUSD=X' "$CRAWL" \
 && grep -Eq 'dead|delisted|ban' "$CRAWL"; then
 ok "sources-crawl SSOT: gold-api XAU/XAG + Yahoo XAUUSD/XAGUSD ban"
else
 fail "sources-crawl must pin gold-api XAU/XAG and ban dead Yahoo XAUUSD=X/XAGUSD=X"
fi
# Map table must not list Yahoo XAUUSD=X / XAGUSD=X as US primary cells
if [[ -f "$CRAWL" ]]; then
 if awk '/ ten-column dual-leg map/,/Miss recipes/' "$CRAWL" | grep -Eq '\| Gold \| `?XAUUSD=X`? \|' \
 || awk '/ ten-column dual-leg map/,/Miss recipes/' "$CRAWL" | grep -Eq '\| Silver \| `?XAGUSD=X`? \|'; then
 fail "sources-crawl map still lists Yahoo XAUUSD=X/XAGUSD=X as US primary"
 else
 ok "sources-crawl map US Gold/Silver are not Yahoo XAUUSD=X/XAGUSD=X"
 fi
fi
if grep -Eq 'gold-api.*XAU|XAU.*gold-api' "${EMILY}/SOUL.md" \
 && grep -Eq 'XAUUSD=X' "${EMILY}/SOUL.md"; then
 ok "SOUL pins gold-api precious US + documents Yahoo XAUUSD ban"
else
 fail "SOUL missing gold-api precious US SSOT / Yahoo XAUUSD ban"
fi

# 5b — term structure + CY + COT in insight + direction
for skill in commodity-insight commodity-direction; do
 f="${SKILLS}/${skill}/SKILL.md"
 if [[ -f "$f" ]] && grep -Eq 'Contango|Backwardation|convenience yield|convenience yield' "$f" \
 && grep -Eq 'COT|Disagg|Managed Money' "$f"; then
 ok "${skill} documents term-structure/CY + COT cite-or-miss"
 else
 fail "${skill} missing term-structure/CY or COT gates"
 fi
done

# 5c — shock skeleton + calendar / FMP ban in world
WORLD="${SKILLS}/world-to-commodity/SKILL.md"
if [[ -f "$WORLD" ]] && grep -Eq 'shock|Shock|' "$WORLD" \
 && grep -Eq 'FMP|WASDE|EIA' "$WORLD"; then
 ok "world-to-commodity documents shock skeleton + calendar/FMP gate"
else
 fail "world-to-commodity missing shock/calendar/FMP gates"
fi

# 5d — forecast anti Method A
FORECAST="${SKILLS}/commodity-forecast/SKILL.md"
if [[ -f "$FORECAST" ]] && grep -Eq 'ARIMA|LSTM|darts' "$FORECAST"; then
 ok "forecast bans ARIMA/LSTM/darts as Scenario (anti Method A)"
else
 fail "forecast missing anti-ARIMA/LSTM/darts Method A gate"
fi

# 5e — shadow breakdown named factors
if [[ -f "$SIGNAL_SKILL" ]] && grep -Eq 'commodity_signal_breakdown|named factor|breakdown items' "$SIGNAL_SKILL"; then
 ok "signal-table documents shadow breakdown named factors"
else
 fail "signal-table missing shadow breakdown named-factors gate"
fi

# 5f — obs-backtest exists and is OUT of Keep load (directory present; not in EXPECTED_SKILLS daily chain docs)
OBS_SKILL="${SKILLS}/commodity-obs-backtest/SKILL.md"
if [[ -f "$OBS_SKILL" ]]; then
 ok "commodity-obs-backtest SKILL.md present (Eval/Sat)"
else
 fail "missing commodity-obs-backtest/SKILL.md"
fi
if [[ -f "$OBS_SKILL" ]] && grep -Eq 'not in|Eval|Sat|Eval/Sat' "$OBS_SKILL"; then
 ok "obs-backtest declares Eval/Sat (out of daily Keep load)"
else
 fail "obs-backtest must declare Eval/Sat / out of Keep load"
fi
# Ensure Keep expected list does NOT include obs-backtest
if printf '%s\n' "${EXPECTED_SKILLS[@]}" | grep -qx 'commodity-obs-backtest'; then
 fail "EXPECTED_SKILLS must not include commodity-obs-backtest"
else
 ok "obs-backtest not in Keep EXPECTED_SKILLS load chain"
fi

# 5f2 — christina-macro-bridge exists and is OUT of Keep load (Receive／optional)
BRIDGE_SKILL="${SKILLS}/christina-macro-bridge/SKILL.md"
if [[ -f "$BRIDGE_SKILL" ]]; then
 ok "christina-macro-bridge SKILL.md present (Receive／optional)"
else
 fail "missing christina-macro-bridge/SKILL.md"
fi
if [[ -f "$BRIDGE_SKILL" ]] && grep -Eq 'not in|Receive／optional|Receive/optional|receive-only|receive only' "$BRIDGE_SKILL"; then
 ok "christina-macro-bridge declares Receive／optional / not in Keep"
else
 fail "christina-macro-bridge must declare Receive／optional / not in Keep"
fi
if printf '%s\n' "${EXPECTED_SKILLS[@]}" | grep -qx 'christina-macro-bridge'; then
 fail "EXPECTED_SKILLS must not include christina-macro-bridge"
else
 ok "christina-macro-bridge not in Keep EXPECTED_SKILLS load chain"
fi

# 5g — SOUL Zoe REJECT covers ARIMA / FMP / carry
if grep -Eq 'ARIMA|LSTM' "${EMILY}/SOUL.md" \
 && grep -Eq 'FMP' "${EMILY}/SOUL.md" \
 && grep -Eq 'carry|convenience yield|fake curve' "${EMILY}/SOUL.md"; then
 ok "SOUL Zoe REJECT / compliance covers ARIMA/FMP/carry invent"
else
 fail "SOUL missing ARIMA/FMP/carry invent coverage"
fi

# 5h — apply-to-hermes includes new Keep skills (absent in public snapshot)
APPLY="${ROOT}/scripts/apply-to-hermes.sh"
if [[ -f "$APPLY" ]]; then
 if grep -q 'commodity-insight' "$APPLY" \
 && grep -q 'commodity-direction' "$APPLY" \
 && grep -q 'commodity-forecast' "$APPLY" \
 && grep -q 'commodity-obs-backtest' "$APPLY" \
 && grep -q 'christina-macro-bridge' "$APPLY"; then
 ok "apply-to-hermes.sh EMILY_SKILLS includes insight/direction/forecast/obs-backtest/christina-macro-bridge"
 else
 fail "apply-to-hermes.sh EMILY_SKILLS missing new emily skills"
 fi
else
 ok "apply-to-hermes.sh absent (public snapshot; skills under profiles/emily/skills/)"
fi

# 5i — P1 Later stubs exist (folder + SKILL) but NOT in Keep EXPECTED_SKILLS
for stub in eia-wpsr usda-wasde-psd cftc-cot-disagg; do
 stub_f="${SKILLS}/${stub}/SKILL.md"
 if [[ -f "$stub_f" ]] && grep -Eqi 'Later|Stub' "$stub_f"; then
 ok "Later stub present: ${stub}"
 else
 fail "missing Later stub SKILL.md or Later marker: ${stub}"
 fi
 if printf '%s\n' "${EXPECTED_SKILLS[@]}" | grep -qx "$stub"; then
 fail "Later stub must not be in Keep EXPECTED_SKILLS: ${stub}"
 else
 ok "Later stub not in Keep load: ${stub}"
 fi
done
if grep -Eq 'Stub[ /／]+Later' "${EMILY}/SOUL.md" \
 && grep -Eq 'Stub/Later' "${EMILY}/skills-checklist.md"; then
 ok "SOUL + checklist mark P1 stubs as Stub/Later"
else
 fail "SOUL/checklist missing Stub/Later status for P1 stubs"
fi

# ---------------------------------------------------------------------------
section "6. Desk-pack prompts (no old emily load order)"
# ---------------------------------------------------------------------------

CHECK_PROMPTS="${TESTS}/check_desk_pack_prompts.sh"
if [[ -x "$CHECK_PROMPTS" ]] || [[ -f "$CHECK_PROMPTS" ]]; then
 if bash "$CHECK_PROMPTS"; then
 ok "check_desk_pack_prompts.sh PASS"
 else
 fail "check_desk_pack_prompts.sh FAIL (old load order or missing 8-skill chain)"
 fi
else
 fail "missing check_desk_pack_prompts.sh"
fi

# ---------------------------------------------------------------------------
section "Summary"
# ---------------------------------------------------------------------------

echo ""
echo "emily audit: ${PASS} passed, ${FAIL} failed"
if (( FAIL > 0 )); then
 red "RESULT: FAIL"
 exit 1
fi
green "RESULT: PASS"
exit 0
