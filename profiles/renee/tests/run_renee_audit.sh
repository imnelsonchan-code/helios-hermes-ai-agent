#!/usr/bin/env bash
# renee T&M sleeve audit harness
# Static grep/assert + lightweight session / funnel hygiene (no network, no API keys, no PnL).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RENEE="${ROOT}/profiles/renee"
SKILLS="${RENEE}/skills"
TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="${TESTS}/fixtures"
SESSION_SKILL="${SKILLS}/tm-session-report/SKILL.md"
FUNNEL_SKILL="${SKILLS}/tm-signal-funnel/SKILL.md"
E5_SKILL="${SKILLS}/tm-e5-firewall/SKILL.md"
SESSION_FIXTURE="${TESTS}/tm_session_fixture.md"
WEEKLY_FIXTURE="${TESTS}/tm_weekly_fixture.md"
FUNNEL_FIXTURE="${TESTS}/funnel_fixture.md"
FUNNEL_NULL_ADX_FIXTURE="${TESTS}/funnel_null_adx_fixture.md"
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
section "1. P0 skills exist"
# ---------------------------------------------------------------------------

EXPECTED=(tm-session-report tm-signal-funnel tm-e5-firewall)
for skill in "${EXPECTED[@]}"; do
  f="${SKILLS}/${skill}/SKILL.md"
  if [[ -f "$f" ]]; then
    ok "skill present: ${skill}"
  else
    fail "missing skill file: $f"
  fi
done

# ---------------------------------------------------------------------------
section "2. Keywords (no score rewrite · Session summary · E5 · Option G weekly · funnel N/A)"
# ---------------------------------------------------------------------------

if [[ -f "$SESSION_SKILL" ]]; then
  if grep -Eqi 'no score rewrite|do not change.*tm_score|score rewrite' "$SESSION_SKILL"; then
    ok "tm-session-report documents no score rewrite"
  else
    fail "tm-session-report missing no score rewrite"
  fi
  if grep -Eq '## Session summary' "$SESSION_SKILL"; then
    ok "tm-session-report requires ## Session summary"
  else
    fail "tm-session-report missing ## Session summary"
  fi
  if grep -Fq 'this report has no ## Market insight' "$SESSION_SKILL" && grep -Fq 'Fail-closed G1' "$SESSION_SKILL"; then
    ok "tm-session-report fail-closed G1 (insert headings; no forbidden empty-brief phrase)"
  else
    fail "tm-session-report missing fail-closed G1 phrases"
  fi
  if grep -Eqi 'weekly.*no Option G|NO Option G|no Option G|weekly never' "$SESSION_SKILL"; then
    ok "tm-session-report bans weekly Option G"
  else
    fail "tm-session-report missing weekly Option G ban"
  fi
  if grep -Eq '^## Market insight|^### 2\. `## Market insight`' "$SESSION_SKILL"; then
    ok "tm-session-report requires ## Market insight"
  else
    fail "tm-session-report missing ## Market insight requirement"
  fi
  if grep -Fq 'after Lenses / before ranking' "$SESSION_SKILL"; then
    ok "tm-session-report places funnel after Lenses"
  else
    fail "tm-session-report missing funnel placement after Lenses"
  fi
  if grep -Fq 'Lenses → optional funnel → ranking' "$SESSION_SKILL"; then
    ok "tm-session-report description keeps optional funnel in the chain"
  else
    fail "tm-session-report description omits optional funnel"
  fi
  if grep -Fq 'Lenses → ranking (live pack)' "$SESSION_SKILL"; then
    fail "tm-session-report description still skips optional funnel"
  else
    ok "tm-session-report description does not skip funnel"
  fi
  if grep -Fq 'No formal market-insight brief today' "$SESSION_SKILL" && grep -Fq 'NOT Alice pull' "$SESSION_SKILL"; then
    ok "tm-session-report Alice pull forbids empty-brief substitute"
  else
    fail "tm-session-report missing Alice pull / Lenses miss split"
  fi
  if grep -Fq 'News: miss' "$SESSION_SKILL" && grep -Eq 'Ranking without a News section and without explicit `News: miss` → Zoe \*\*REJECT\*\*' "$SESSION_SKILL"; then
    ok "tm-session-report News miss is a REJECT gate"
  else
    fail "tm-session-report missing News: miss REJECT gate"
  fi
  if grep -Fq 'Headlines-only with empty Session summary' "$SESSION_SKILL"; then
    ok "tm-session-report bans headlines-only empty sections"
  else
    fail "tm-session-report missing headlines-only ban"
  fi
  if grep -Fq 'Risk-on/off' "$SESSION_SKILL"; then
    ok "tm-session-report documents desk Risk-on/off ban"
  else
    fail "tm-session-report missing Risk-on/off ban"
  fi
else
  fail "missing $SESSION_SKILL"
fi

if [[ -f "$E5_SKILL" ]]; then
  if grep -Eqi 'E5|never blend|valuation_score' "$E5_SKILL"; then
    ok "tm-e5-firewall documents E5 / never-blend"
  else
    fail "tm-e5-firewall missing E5 / never-blend keywords"
  fi
  if grep -Fq 'score_breakdown' "$E5_SKILL"; then
    ok "tm-e5-firewall requires score_breakdown"
  else
    fail "tm-e5-firewall missing score_breakdown"
  fi
  if grep -Fq '## Market insight' "$E5_SKILL" && grep -Fq '## Session summary' "$E5_SKILL"; then
    ok "tm-e5-firewall Alice cite includes Market insight + Session summary"
  else
    fail "tm-e5-firewall Alice cite missing Market insight or Session summary"
  fi
else
  fail "missing $E5_SKILL"
fi

if [[ -f "$FUNNEL_SKILL" ]]; then
  if grep -Eqi '\bN/A\b|N/A if missing|N/A \+ pending|N/A — ADX' "$FUNNEL_SKILL"; then
    ok "tm-signal-funnel documents N/A when missing"
  else
    fail "tm-signal-funnel missing N/A keyword"
  fi
  if grep -Eqi 'monotonic|theo.*after_G|after_G.*after_vol' "$FUNNEL_SKILL"; then
    ok "tm-signal-funnel documents monotonic funnel counts"
  else
    fail "tm-signal-funnel missing monotonicity keywords"
  fi
  if grep -Fq 'after `## Lenses` / before ranking' "$FUNNEL_SKILL"; then
    ok "tm-signal-funnel places section after Lenses"
  else
    fail "tm-signal-funnel missing after-Lenses placement"
  fi
  if grep -Fq 'after header / Session summary / before ranking' "$FUNNEL_SKILL"; then
    fail "tm-signal-funnel still uses old placement (after Session summary)"
  else
    ok "tm-signal-funnel does not keep old Session-summary placement"
  fi
  if grep -Eq 'Mon–Fri|Mon-Fri' "$FUNNEL_SKILL"; then
    ok "tm-signal-funnel documents Mon–Fri Saturday roll-up"
  else
    fail "tm-signal-funnel missing Mon–Fri roll-up"
  fi
else
  fail "missing $FUNNEL_SKILL"
fi

SOUL="${RENEE}/SOUL.md"
if [[ -f "$SOUL" ]]; then
  if grep -Fq 'after `## Lenses` / before ranking' "$SOUL"; then
    ok "SOUL places funnel after Lenses"
  else
    fail "SOUL missing funnel placement after Lenses"
  fi
  if grep -Fq 'after header / Session summary / before ranking' "$SOUL"; then
    fail "SOUL still uses old funnel placement (after Session summary)"
  else
    ok "SOUL does not keep old Session-summary funnel placement"
  fi
  if grep -Fq 'No formal market-insight brief today' "$SOUL"; then
    ok "SOUL Alice pull forbids empty-brief substitute"
  else
    fail "SOUL missing Alice pull forbidden phrase"
  fi
else
  fail "missing $SOUL"
fi

# ---------------------------------------------------------------------------
section "3. Checklist: no 'no per-agent skills tree' · P0 skills present"
# ---------------------------------------------------------------------------

CL="${RENEE}/skills-checklist.md"
if [[ ! -f "$CL" ]]; then
  fail "missing $CL"
else
  if grep -Eqi 'no per-agent skills tree|no profile skills tree|without.*per-agent skills' "$CL"; then
    fail "checklist still claims 'no per-agent skills tree'"
  else
    ok "checklist does not claim 'no per-agent skills tree'"
  fi
  if grep -Fq 'Lenses → optional funnel → ranking' "$CL"; then
    ok "checklist P0 chain includes optional funnel"
  else
    fail "checklist P0 chain omits optional funnel"
  fi
  for skill in tm-session-report tm-signal-funnel tm-e5-firewall; do
    if grep -Eq "$skill" "$CL"; then
      ok "checklist mentions ${skill}"
    else
      fail "checklist missing mention: ${skill}"
    fi
  done
fi

# ---------------------------------------------------------------------------
section "4. apply-to-hermes.sh RENEE_SKILLS"
# ---------------------------------------------------------------------------

if [[ -f "$APPLY" ]]; then
  missing=()
  for skill in tm-session-report tm-signal-funnel tm-e5-firewall; do
    if awk '/^RENEE_SKILLS=\(/,/^\)/' "$APPLY" | grep -Eq "^[[:space:]]*${skill}[[:space:]]*$"; then
      :
    elif grep -Eq "${skill}" "$APPLY"; then
      :
    else
      missing+=("$skill")
    fi
  done
  if ((${#missing[@]} == 0)); then
    ok "apply-to-hermes.sh RENEE_SKILLS includes tm-session-report / tm-signal-funnel / tm-e5-firewall"
  else
    fail "apply-to-hermes.sh RENEE_SKILLS missing: ${missing[*]}"
  fi
else
  ok "apply-to-hermes.sh absent (public snapshot; skills under profiles/renee/skills/)"
fi

# ---------------------------------------------------------------------------
section "5. Fixture hygiene (good PASS · bad FAIL negative control)"
# ---------------------------------------------------------------------------

score_tm_session() {
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

add("has Session summary", bool(re.search(r"^## Session summary", text, re.M)))
add("has Market insight", bool(re.search(r"^## Market insight", text, re.M)))
add("has News section", bool(re.search(r"^## News", text, re.M)))
add("has Lenses", bool(re.search(r"^## Lenses", text, re.M)))
add("has tm_score movers", bool(re.search(r"(?i)tm_score", text)))

# valuation_score as a ranking/table COLUMN (not ban-prose)
blend = False
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
    headers = [c.strip().strip("`").lower() for c in rows[0].strip("|").split("|")]
    if "valuation_score" in headers:
        blend = True
# Affirmative blend language
if re.search(r"(?i)\bblends?\s+valuation_score\b|sorted by blended", text):
    blend = True
add("no valuation_score blend in ranking", not blend)

# Affirmative weekly Option G suppress-as-applied (ignore "No weekly Option G…" prose)
weekly_og = bool(re.search(r"(?i)Weekly BUY counts suppressed", text))
if re.search(r"(?i)cadence:\s*weekly", text) and re.search(r"(?i)Option G applied", text):
    weekly_og = True
add("no weekly Option G suppress-as-applied", not weekly_og)

failed = [c for c in checks if not c[1]]
print("T&M session hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
}

score_funnel() {
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

add("has funnel section", bool(re.search(r"(?i)signal funnel|T&M signal funnel", text)))

# Extract three counts — prefer labeled rows / fields
def find_count(*pats):
    for pat in pats:
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1))
    return None

theo = find_count(
    r"buys_theoretical[`\s\|:]*[|:\s]*(\d+)",
    r"Theoretical BUY[^\d]*(\d+)",
    r"theoretical[^\d]*(\d+)",
)
after_g = find_count(
    r"buys_after_option_g[`\s\|:]*[|:\s]*(\d+)",
    r"After Option G[^\d]*(\d+)",
)
after_vol = find_count(
    r"buys_after_volume_gate[`\s\|:]*[|:\s]*(\d+)",
    r"After volume gate[^\d]*(\d+)",
)

# Fallback: table Label | Count rows
if theo is None or after_g is None or after_vol is None:
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, val = cells[0].lower(), cells[1]
        if not re.fullmatch(r"\d+", val):
            continue
        n = int(val)
        if "theoretical" in label and theo is None:
            theo = n
        elif "option g" in label and after_g is None:
            after_g = n
        elif "volume" in label and after_vol is None:
            after_vol = n

add("parsed theo/after_G/after_vol", theo is not None and after_g is not None and after_vol is not None,
    f"theo={theo} after_G={after_g} after_vol={after_vol}")
mono = False
if theo is not None and after_g is not None and after_vol is not None:
    mono = theo >= after_g >= after_vol
add("monotonic theo ≥ after_G ≥ after_vol", mono, f"theo={theo} after_G={after_g} after_vol={after_vol}")
# after_G=0 ⇒ after_vol=0 (and empty demotions expected in live packs)
zero_ok = True
if after_g is not None and after_vol is not None:
    if after_g == 0 and after_vol > 0:
        zero_ok = False
add("after_G=0 ⇒ after_vol=0", zero_ok, f"after_G={after_g} after_vol={after_vol}")

failed = [c for c in checks if not c[1]]
print("Funnel hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
}

score_funnel_null_adx() {
  python3 - "$1" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

add("has funnel section", bool(re.search(r"(?i)signal funnel|T&M signal funnel", text)))
add(
    "N/A — ADX missing",
    bool(re.search(r"(?i)N/A\s*[—\-–]\s*ADX missing|ADX missing|option_g_skipped", text)),
)

# option_g_active: false in a table / field row (not ban-prose "do not set … false")
treated_false = False
for line in text.splitlines():
    if re.search(r"(?i)do\s*\*{0,2}\s*not|never|Not:|Hard line|Banned", line):
        continue
    if re.search(r"(?i)option_g_active[`\s\|:]*[|:\s]*false", line):
        treated_false = True
        break
    # Table row: | `option_g_active` | false |
    if re.search(r"(?i)\|\s*`?option_g_active`?\s*\|\s*`?false`?\s*\|", line):
        treated_false = True
        break
add("not option_g false-as-applied", not treated_false)

# Affirmative "treated as trending" / "regime: trending" without negation on same line
affirm_trending = False
for line in text.splitlines():
    if re.search(r"(?i)not\s*\*{0,2}\s*treat|do\s+\*{0,2}not\*{0,2}\s+treat|never\s+treat|Not:|Hard line|N/A", line):
        continue
    if re.search(r"(?i)treated as trending|regime:\s*trending", line):
        affirm_trending = True
        break
add("not treated as trending", not affirm_trending)

failed = [c for c in checks if not c[1]]
print("Null-ADX funnel hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
}

# Good fixtures
if [[ ! -f "$SESSION_FIXTURE" ]]; then
  fail "missing session fixture: $SESSION_FIXTURE"
else
  set +e
  score_tm_session "$SESSION_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "tm_session_fixture.md passes hygiene"
  else
    fail "tm_session_fixture.md failed hygiene"
  fi
fi

if [[ ! -f "$WEEKLY_FIXTURE" ]]; then
  fail "missing weekly fixture: $WEEKLY_FIXTURE"
else
  set +e
  score_tm_session "$WEEKLY_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "tm_weekly_fixture.md passes hygiene"
  else
    fail "tm_weekly_fixture.md failed hygiene"
  fi
fi

if [[ ! -f "$FUNNEL_FIXTURE" ]]; then
  fail "missing funnel fixture: $FUNNEL_FIXTURE"
else
  set +e
  score_funnel "$FUNNEL_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "funnel_fixture.md passes hygiene"
  else
    fail "funnel_fixture.md failed hygiene"
  fi
fi

if [[ ! -f "$FUNNEL_NULL_ADX_FIXTURE" ]]; then
  fail "missing null-ADX funnel fixture: $FUNNEL_NULL_ADX_FIXTURE"
else
  set +e
  score_funnel_null_adx "$FUNNEL_NULL_ADX_FIXTURE"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "funnel_null_adx_fixture.md passes hygiene"
  else
    fail "funnel_null_adx_fixture.md failed hygiene"
  fi
fi

# Bad negative controls
BAD_S="${FIXTURES}/tm_session_bad.md"
BAD_F="${FIXTURES}/funnel_bad.md"
BAD_G0="${FIXTURES}/funnel_after_g_zero_bad.md"

if [[ ! -f "$BAD_S" ]]; then
  fail "missing bad session fixture: $BAD_S"
else
  set +e
  score_tm_session "$BAD_S" >/dev/null
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    ok "tm_session_bad.md fails hygiene (negative control)"
  else
    fail "tm_session_bad.md should FAIL hygiene (negative control)"
  fi
fi

if [[ ! -f "$BAD_F" ]]; then
  fail "missing bad funnel fixture: $BAD_F"
else
  set +e
  score_funnel "$BAD_F" >/dev/null
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    ok "funnel_bad.md fails hygiene (negative control)"
  else
    fail "funnel_bad.md should FAIL hygiene (negative control)"
  fi
fi

if [[ ! -f "$BAD_G0" ]]; then
  fail "missing bad after_G=0 fixture: $BAD_G0"
else
  set +e
  score_funnel "$BAD_G0" >/dev/null
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    ok "funnel_after_g_zero_bad.md fails hygiene (negative control)"
  else
    fail "funnel_after_g_zero_bad.md should FAIL hygiene (negative control)"
  fi
fi

# ---------------------------------------------------------------------------
section "Summary"
# ---------------------------------------------------------------------------

echo ""
echo "renee audit: ${PASS} passed, ${FAIL} failed"
if (( FAIL > 0 )); then
  red "RESULT: FAIL"
  exit 1
fi
green "RESULT: PASS"
exit 0
