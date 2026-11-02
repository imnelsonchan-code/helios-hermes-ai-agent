#!/usr/bin/env bash
# eliza value-sleeve audit harness
# Static grep/assert + lightweight value-session / width hygiene (no network, no API keys, no PnL).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ELIZA="${ROOT}/profiles/eliza"
SKILLS="${ELIZA}/skills"
TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="${TESTS}/fixtures"
VALUE_SKILL="${SKILLS}/value-session/SKILL.md"
WIDTH_SKILL="${SKILLS}/valuation-width/SKILL.md"
A08_SKILL="${SKILLS}/a08-followup/SKILL.md"
VALUE_FIXTURE="${TESTS}/value_session_fixture.md"
WIDTH_FIXTURE="${TESTS}/width_fixture.md"
A08_FIXTURE="${TESTS}/a08_fixture.md"
APPLY="${ROOT}/scripts/apply-to-hermes.sh"

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
section "1. P0 + earnings skills exist"
# ---------------------------------------------------------------------------

EXPECTED_P0=(value-session valuation-width a08-followup)
EXPECTED_EARNINGS=(earnings-preview earnings-analysis comps-analysis)

for skill in "${EXPECTED_P0[@]}" "${EXPECTED_EARNINGS[@]}"; do
  f="${SKILLS}/${skill}/SKILL.md"
  if [[ -f "$f" ]]; then
    ok "skill present: ${skill}"
  else
    fail "missing skill file: $f"
  fi
done

# ---------------------------------------------------------------------------
section "2. P0 skill keywords (tm_score ban · Session summary · Candidate/+15% · A-08)"
# ---------------------------------------------------------------------------

# value-session
if [[ -f "$VALUE_SKILL" ]]; then
  if grep -Eq 'tm_score' "$VALUE_SKILL" \
    && grep -Eqi 'never|❌|do not |ban|Never' "$VALUE_SKILL"; then
    ok "value-session bans / never-emits tm_score"
  else
    fail "value-session must ban tm_score"
  fi
  if grep -Eq '## Session summary' "$VALUE_SKILL"; then
    ok "value-session requires ## Session summary"
  else
    fail "value-session missing ## Session summary requirement"
  fi
  if grep -Eqi '\bas_of\b' "$VALUE_SKILL"; then
    ok "value-session mentions as_of"
  else
    fail "value-session missing as_of"
  fi
  if grep -Eqi 'Alice pull' "$VALUE_SKILL" \
    && grep -Eqi 'THIS file' "$VALUE_SKILL" \
    && grep -Eq 'Market insight' "$VALUE_SKILL" \
    && grep -Eq '\|[[:space:]]*Ticker[[:space:]]*\|.*Sunday `valuation_score`' "$VALUE_SKILL"; then
    ok "value-session Alice pull points at THIS file Market insight + movers Sunday valuation_score"
  else
    fail "value-session must require Alice pull → THIS file Market insight and movers table header Sunday valuation_score"
  fi
  if grep -Eq 'Sunday lock FV' "$VALUE_SKILL" \
    && grep -Eq 'Display upside' "$VALUE_SKILL"; then
    ok "value-session requires Sunday lock FV + Display upside"
  else
    fail "value-session must match Sunday lock FV AND Display upside"
  fi
else
  fail "missing $VALUE_SKILL"
fi

# valuation-width
if [[ -f "$WIDTH_SKILL" ]]; then
  if grep -Eq 'tm_score' "$WIDTH_SKILL" \
    && grep -Eqi 'never|❌|do not |ban|Never' "$WIDTH_SKILL"; then
    ok "valuation-width bans tm_score"
  else
    fail "valuation-width must ban tm_score"
  fi
  if grep -Eq '## Session summary' "$WIDTH_SKILL"; then
    ok "valuation-width requires ## Session summary"
  else
    fail "valuation-width missing ## Session summary requirement"
  fi
  if grep -Eq '\+15%|≥\+15%|>=\+15%' "$WIDTH_SKILL"; then
    ok "valuation-width documents Candidate ≥+15%"
  else
    fail "valuation-width missing Candidate +15% floor"
  fi
  if grep -Eqi '\bas_of\b' "$WIDTH_SKILL"; then
    ok "valuation-width mentions as_of"
  else
    fail "valuation-width missing as_of"
  fi
  if grep -Eq 'scoring-engine-v4' "$WIDTH_SKILL" \
    || { grep -Eqi '\bE5\b' "$WIDTH_SKILL" && grep -Eqi 'never blend|Never.*blend|do not .*blend|do not.*blend' "$WIDTH_SKILL"; }; then
    ok "valuation-width bans scoring-engine-v4 or documents E5 never blend"
  else
    fail "valuation-width must ban scoring-engine-v4 or document E5 never blend"
  fi
  if grep -Eq 'FV Range' "$WIDTH_SKILL" \
    && grep -Eq 'Upside' "$WIDTH_SKILL"; then
    ok "valuation-width requires FV Range + Upside"
  else
    fail "valuation-width must match FV Range AND Upside"
  fi
else
  fail "missing $WIDTH_SKILL"
fi

# a08-followup
if [[ -f "$A08_SKILL" ]]; then
  if grep -Eq 'tm_score' "$A08_SKILL" \
    && grep -Eqi 'never|❌|do not |ban|Never' "$A08_SKILL"; then
    ok "a08-followup bans tm_score"
  else
    fail "a08-followup must ban tm_score"
  fi
  if grep -Eqi 'no re-score|no re-rank|do not change.*valuation_score|do not change .*valuation_score' "$A08_SKILL"; then
    ok "a08-followup documents no re-score / no re-rank"
  else
    fail "a08-followup missing no re-score / no re-rank keywords"
  fi
  if grep -Eqi '\bas_of\b' "$A08_SKILL" \
    && grep -Eqi 'generated_at|data_delay|provenance' "$A08_SKILL"; then
    ok "a08-followup mentions as_of + generated_at/data_delay/provenance"
  else
    fail "a08-followup missing as_of / generated_at|data_delay|provenance"
  fi
  if grep -Eq 'Sunday lock FV' "$A08_SKILL" \
    && grep -Eq 'Display upside' "$A08_SKILL"; then
    ok "a08-followup requires Sunday lock FV + Display upside"
  else
    fail "a08-followup must match Sunday lock FV AND Display upside"
  fi
else
  fail "missing $A08_SKILL"
fi

# ---------------------------------------------------------------------------
section "3. SOUL + checklist mention new P0 skills"
# ---------------------------------------------------------------------------

for name in value-session valuation-width a08-followup; do
  if grep -Eq "$name" "${ELIZA}/SOUL.md"; then
    ok "SOUL mentions ${name}"
  else
    fail "SOUL missing mention: ${name}"
  fi
  if grep -Eq "$name" "${ELIZA}/skills-checklist.md"; then
    ok "checklist mentions ${name}"
  else
    fail "checklist missing mention: ${name}"
  fi
done

# ---------------------------------------------------------------------------
section "4. apply-to-hermes.sh ELIZA_SKILLS"
# ---------------------------------------------------------------------------

if [[ -f "$APPLY" ]]; then
  missing=()
  for skill in value-session valuation-width a08-followup; do
    # Prefer the ELIZA_SKILLS array block
    if awk '/^ELIZA_SKILLS=\(/,/^\)/' "$APPLY" | grep -Eq "^[[:space:]]*${skill}[[:space:]]*$"; then
      :
    elif grep -Eq "ELIZA_SKILLS|eliza" "$APPLY" && grep -Eq "${skill}" "$APPLY"; then
      :
    else
      missing+=("$skill")
    fi
  done
  if ((${#missing[@]} == 0)); then
    ok "apply-to-hermes.sh ELIZA_SKILLS includes value-session / valuation-width / a08-followup"
  else
    fail "apply-to-hermes.sh ELIZA_SKILLS missing: ${missing[*]}"
  fi
else
  ok "apply-to-hermes.sh absent (public snapshot)"
fi

# ---------------------------------------------------------------------------
section "5. Fixture hygiene (good PASS · bad FAIL negative control)"
# ---------------------------------------------------------------------------

score_value_session() {
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

def tables():
    """Yield (heading, headers, data) — skip Hygiene scorecard tables."""
    out = []
    lines = text.splitlines()
    i = 0
    last_heading = ""
    while i < len(lines):
        if re.match(r"^##\s+", lines[i]):
            last_heading = lines[i]
            i += 1
            continue
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(lines[i])
            i += 1
        if len(rows) < 2:
            continue
        if re.search(r"(?i)hygiene scorecard", last_heading):
            continue
        headers = [c.strip().strip("`") for c in rows[0].strip("|").split("|")]
        data = rows[2:] if re.match(r"^\|?\s*[-:]+", rows[1]) else rows[1:]
        out.append((last_heading, headers, data))
    return out

add("has Session summary", bool(re.search(r"^## Session summary", text, re.M)))
add("has Market insight", bool(re.search(r"^## Market insight", text, re.M)))
add("has News/Market or Lenses", bool(re.search(r"^## (News|Lenses)", text, re.M)))
add("no desk Risk-on/off final call", not bool(re.search(r"(?i)desk Risk-on/off\s*[:=]", text) and not re.search(r"(?i)❌|do not write|do not set|Alice Macro", text)))
add("has valuation stance", bool(re.search(r"(?i)valuation stance|Valuation stance", text)))
add("cites Sunday valuation_score", bool(re.search(r"(?i)sunday.*valuation_score|valuation_score", text)))
add("no tm_score emit", not bool(re.search(r"(?i)\btm_score\b", text) and not re.search(r"(?i)never.*tm_score|no.*tm_score|do not .*tm_score", text)))
# Stricter: fail if tm_score appears in a table cell / column header
tm_col = bool(re.search(r"(?i)\|\s*`?tm_score`?\s*\|", text))
tm_cell = bool(re.search(r"(?i)\|\s*\d+\s*\|\s*[^|]*tm_score", text))
# any table header or cell that is literally tm_score as a column
has_tm_col = bool(re.search(r"(?i)\|\s*tm_score\s*\|", text))
add("no tm_score column/cell", not has_tm_col)
add("has as_of", bool(re.search(r"(?i)\bas_of\b", text)))
bare_score = bool(re.search(r"(?i)\|\s*Score\s*\|", text)) and not bool(re.search(r"(?i)Valuation Score", text))
add("no bare Score column", not bare_score)
has_fv_upside = False
for _heading, headers, _data in tables():
    blob = " ".join(h.lower() for h in headers)
    if "sunday lock fv" in blob and "upside" in blob:
        has_fv_upside = True
add("movers table has Sunday lock FV + upside", has_fv_upside)

failed = [c for c in checks if not c[1]]
print("Value-session hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
}

score_width() {
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

def tables():
    """Yield (heading, headers, data) — skip Hygiene scorecard tables."""
    out = []
    lines = text.splitlines()
    i = 0
    last_heading = ""
    while i < len(lines):
        if re.match(r"^##\s+", lines[i]):
            last_heading = lines[i]
            i += 1
            continue
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(lines[i])
            i += 1
        if len(rows) < 2:
            continue
        if re.search(r"(?i)hygiene scorecard", last_heading):
            continue
        headers = [c.strip().strip("`") for c in rows[0].strip("|").split("|")]
        data = rows[2:] if re.match(r"^\|?\s*[-:]+", rows[1]) else rows[1:]
        out.append((last_heading, headers, data))
    return out

add("has Session summary", bool(re.search(r"^## Session summary", text, re.M)))
add("has Market insight", bool(re.search(r"^## Market insight", text, re.M)))
add("has News/Market or Lenses", bool(re.search(r"^## (News|Lenses)", text, re.M)))
add("no desk Risk-on/off final call", not bool(re.search(r"(?i)desk Risk-on/off\s*[:=]", text) and not re.search(r"(?i)❌|do not write|do not set|Alice Macro", text)))
has_vs = False
has_wv = False
has_score_adj = False
has_tm = False
has_na_selected = False
for heading, headers, data in tables():
    hnorm = [h.lower() for h in headers]
    # Only flag bare Score/Adj — not "Valuation Score"
    if any(h == "score" for h in hnorm) or any(h == "adj" for h in hnorm):
        has_score_adj = True
    if any(h == "tm_score" or h == "`tm_score`" for h in hnorm) or any(
        h.replace("`", "") == "tm_score" for h in hnorm
    ):
        has_tm = True
    if any("valuation_score" in h for h in hnorm):
        has_vs = True
        vi = next(i for i, h in enumerate(hnorm) if "valuation_score" in h)
        for r in data:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if vi < len(cells) and cells[vi].upper() in {"N/A", "NA"}:
                has_na_selected = True
    if any("width_verdict" in h for h in hnorm):
        has_wv = True

has_fv_upside = False
q_fv = False
for heading, headers, data in tables():
    hnorm = [h.lower() for h in headers]
    joined = " ".join(hnorm)
    if "fv range" in joined and "upside" in joined:
        has_fv_upside = True
        fi = next(i for i, h in enumerate(hnorm) if "fv range" in h)
        for r in data:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if fi < len(cells) and cells[fi].startswith("?"):
                q_fv = True

add("Track table has valuation_score", has_vs)
add("Track table has width_verdict", has_wv)
add("Track table has FV Range + Upside", has_fv_upside)
add("no ?-prefixed FV Range cells", not q_fv)
add("no Score/Adj columns", not has_score_adj)
add("no tm_score column", not has_tm)
add("no selected N/A valuation_score", not has_na_selected)
add("has as_of", bool(re.search(r"(?i)\bas_of\b", text)))

failed = [c for c in checks if not c[1]]
print("Width hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
}

score_a08() {
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

def tables():
    """Yield (heading, headers, data) — skip Hygiene scorecard tables."""
    out = []
    lines = text.splitlines()
    i = 0
    last_heading = ""
    while i < len(lines):
        if re.match(r"^##\s+", lines[i]):
            last_heading = lines[i]
            i += 1
            continue
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(lines[i])
            i += 1
        if len(rows) < 2:
            continue
        if re.search(r"(?i)hygiene scorecard", last_heading):
            continue
        headers = [c.strip().strip("`") for c in rows[0].strip("|").split("|")]
        data = rows[2:] if re.match(r"^\|?\s*[-:]+", rows[1]) else rows[1:]
        out.append((last_heading, headers, data))
    return out

add("has as_of", bool(re.search(r"(?i)\bas_of\b", text)))
add("cites Sunday valuation_score", bool(re.search(
    r"(?i)sunday.*valuation_score|valuation_score.*verbatim|verbatim.*valuation_score|`valuation_score`",
    text,
)))
add(
    "skip Avoid/🔴 note",
    bool(re.search(r"(?i)skip.*🔴|🔴.*skip|skip.*Avoid|Avoid.*skip|skipped.*🔴|skipped.*Avoid", text)),
)
has_tm_col = bool(re.search(r"(?i)\|\s*`?tm_score`?\s*\|", text))
add("no tm_score column", not has_tm_col)
has_fv_upside = False
for _heading, headers, _data in tables():
    blob = " ".join(h.lower() for h in headers)
    if "sunday lock fv" in blob and "upside" in blob:
        has_fv_upside = True
add("names table has Sunday lock FV + upside", has_fv_upside)

# Affirmative invent / re-score — ignore ban-prose lines (never / no / do not  / Not: / Hard line)
invent_aff = False
for line in text.splitlines():
    if re.search(r"(?i)never|no invent|do not invent |do not invent|Not:|Hard line|Banned|ban ", line):
        continue
    if re.search(
        r"(?i)re-scored valuation_score|re-score[sd]?\s+to|invented prices?|invents? (price|score|valuation)|emits tm_score|new valuation_score\s*[:=]",
        line,
    ):
        invent_aff = True
        break
add("no invent/re-score affirmative", not invent_aff)

failed = [c for c in checks if not c[1]]
print("A-08 hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
}

# Good fixtures must PASS
if [[ ! -f "$VALUE_FIXTURE" ]]; then
  fail "missing value fixture: $VALUE_FIXTURE"
else
  set +e
  score_value_session "$VALUE_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "value_session_fixture.md passes hygiene"
  else
    fail "value_session_fixture.md failed hygiene"
  fi
fi

if [[ ! -f "$WIDTH_FIXTURE" ]]; then
  fail "missing width fixture: $WIDTH_FIXTURE"
else
  set +e
  score_width "$WIDTH_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "width_fixture.md passes hygiene"
  else
    fail "width_fixture.md failed hygiene"
  fi
fi

if [[ ! -f "$A08_FIXTURE" ]]; then
  fail "missing A-08 fixture: $A08_FIXTURE"
else
  set +e
  score_a08 "$A08_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "a08_fixture.md passes hygiene"
  else
    fail "a08_fixture.md failed hygiene"
  fi
fi

# Bad fixtures must FAIL hygiene (negative control)
BAD_VS="${FIXTURES}/value_session_bad.md"
BAD_W="${FIXTURES}/width_bad.md"
BAD_A08="${FIXTURES}/a08_bad.md"

if [[ ! -f "$BAD_VS" ]]; then
  fail "missing bad value fixture: $BAD_VS"
else
  set +e
  score_value_session "$BAD_VS" >/dev/null
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    ok "value_session_bad.md fails hygiene (negative control)"
  else
    fail "value_session_bad.md should FAIL hygiene (negative control)"
  fi
fi

if [[ ! -f "$BAD_W" ]]; then
  fail "missing bad width fixture: $BAD_W"
else
  set +e
  score_width "$BAD_W" >/dev/null
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    ok "width_bad.md fails hygiene (negative control)"
  else
    fail "width_bad.md should FAIL hygiene (negative control)"
  fi
fi

if [[ ! -f "$BAD_A08" ]]; then
  fail "missing bad A-08 fixture: $BAD_A08"
else
  set +e
  score_a08 "$BAD_A08" >/dev/null
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    ok "a08_bad.md fails hygiene (negative control)"
  else
    fail "a08_bad.md should FAIL hygiene (negative control)"
  fi
fi

# ---------------------------------------------------------------------------
section "6. No secrets / host paths in skills (soft)"
# ---------------------------------------------------------------------------

SECRET_HITS=0
while IFS= read -r -d '' f; do
  hits=""
  if grep -Eniq 'Telegram|API_KEY=|~/.hermes/profiles/|/home/[^/]+/\.hermes' "$f"; then
    hits="$(grep -Eni 'Telegram|API_KEY=|~/.hermes/profiles/|/home/[^/]+/\.hermes' "$f" || true)"
  fi
  if [[ -n "$hits" ]]; then
    SECRET_HITS=$((SECRET_HITS + 1))
    fail "secret/host-path pattern in ${f#"$ROOT"/}: $(echo "$hits" | head -3 | tr '\n' ';')"
  fi
done < <(find "$SKILLS" -name 'SKILL.md' -print0 2>/dev/null)

if [[ $SECRET_HITS -eq 0 ]]; then
  ok "no Telegram / API_KEY= / ~/.hermes/profiles absolute paths in eliza skills"
fi

# ---------------------------------------------------------------------------
section "Summary"
# ---------------------------------------------------------------------------

echo ""
echo "eliza audit: ${PASS} passed, ${FAIL} failed"
if (( FAIL > 0 )); then
  red "RESULT: FAIL"
  exit 1
fi
green "RESULT: PASS"
exit 0
