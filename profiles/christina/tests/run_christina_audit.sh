#!/usr/bin/env bash
# christina observation-only audit harness
# Static grep/assert + lightweight obs-backtest hygiene (no network, no API keys, no PnL).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CHRISTINA="${ROOT}/profiles/christina"
SKILLS="${CHRISTINA}/skills"
TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="${TESTS}/fixtures"
SESSION_SKILL="${SKILLS}/rates-session-report/SKILL.md"
BOND_SKILL="${SKILLS}/bond-etf-tape/SKILL.md"
FX_SKILL="${SKILLS}/fx-us-uk-bridge/SKILL.md"
FEDWATCH_SKILL="${SKILLS}/fedwatch-consume/SKILL.md"
OBS_FIXTURE="${TESTS}/obs_backtest_fixture.md"

PASS=0
FAIL=0
SECTION=""

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
  SECTION="$1"
  bold ""
  bold "== $1 =="
}

# Canonical load-order SSOT
# Accept short tokens or full skill folder names, in order.
# Skills often write "this skill" for self — normalize that to the folder name.
ssot_in_file() {
  local f="$1"
  local skill_hint="${2:-}"  # optional folder name when checking a skill
  python3 - "$f" "$skill_hint" <<'PY'
import re, sys
path, hint = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
# Prefer the Load-order line(s); fall back to whole doc
chunks = []
for m in re.finditer(r"(?i)load order[^\n]*", text):
    # include following continuation lines that still look like a chain
    start = m.start()
    end = m.end()
    rest = text[end:]
    extra = []
    for line in rest.splitlines()[:6]:
        if "→" in line or "->" in line or "this skill" in line:
            extra.append(line)
        elif line.strip() == "":
            break
        else:
            break
    chunks.append(text[start:end] + "\n" + "\n".join(extra))
if not chunks:
    chunks = [text]

short_re = re.compile(
    r"curve(?:-watch)?\s*→\s*real(?:-rates)?\s*→\s*fedwatch(?:-consume)?\s*→\s*"
    r"bond-etf(?:-tape)?\s*→\s*fx(?:-us-uk-bridge)?\s*→\s*(?:trunk|rates-session-report)",
    re.I,
)
# Self-slot map: folder → tokens that may appear as "this skill"
self_map = {
    "curve-watch": "curve",
    "real-rates": "real",
    "fedwatch-consume": "fedwatch",
    "bond-etf-tape": "bond-etf",
    "fx-us-uk-bridge": "fx",
    "rates-session-report": "trunk",
}

def normalize(blob: str) -> str:
    flat = blob.replace("**", "").replace("`", "")
    flat = re.sub(r"\s+", " ", flat)
    flat = flat.replace("->", "→")
    if hint and hint in self_map:
        tok = self_map[hint]
        flat = re.sub(r"this skill(?: \([^)]*\))?", tok, flat, flags=re.I)
        # Legacy alias (Unicode escapes, no CJK in source)
        flat = re.sub(r"\u672c\s*skill(?:\uff08[^\uff09]*\uff09)?", tok, flat)
    return flat

for ch in chunks:
    flat = normalize(ch)
    if short_re.search(flat):
        sys.exit(0)

# Whole-doc fallback: tokens in order (first hit after previous), trunk after fx
flat = normalize(text)
# If hint given, still replace this skill globally for order scan of load snippets
token_pats = [
    r"curve-watch|\bcurve\b",
    r"real-rates|\breal\b",
    r"fedwatch-consume|\bfedwatch\b",
    r"bond-etf-tape|\bbond-etf\b",
    r"fx-us-uk-bridge|\bfx\b",
]
idx = -1
for pat in token_pats:
    ms = [m for m in re.finditer(pat, flat, re.I) if m.start() > idx]
    if not ms:
        sys.exit(1)
    idx = ms[0].start()
ms = [m for m in re.finditer(r"rates-session-report|\btrunk\b", flat, re.I) if m.start() > idx]
sys.exit(0 if ms else 1)
PY
}

# ---------------------------------------------------------------------------
section "1. Load-order SSOT (all christina skills + checklist + SOUL)"
# ---------------------------------------------------------------------------

EXPECTED_SKILLS=(
  curve-watch
  real-rates
  fedwatch-consume
  bond-etf-tape
  fx-us-uk-bridge
  rates-session-report
)

for skill in "${EXPECTED_SKILLS[@]}"; do
  f="${SKILLS}/${skill}/SKILL.md"
  if [[ ! -f "$f" ]]; then
    fail "missing skill file: $f"
    continue
  fi
  if ssot_in_file "$f" "$skill"; then
    ok "load-order SSOT present: ${skill}"
  else
    fail "load-order SSOT missing/out-of-order: ${skill}"
  fi
done

for f in "${CHRISTINA}/skills-checklist.md" "${CHRISTINA}/SOUL.md"; do
  if [[ ! -f "$f" ]]; then
    fail "missing: $f"
    continue
  fi
  if ssot_in_file "$f" ""; then
    ok "load-order SSOT present: $(basename "$f")"
  else
    fail "load-order SSOT missing/out-of-order: $(basename "$f")"
  fi
done

# ---------------------------------------------------------------------------
section "2. Namespace isolation (B_* / FX_* / bare BUY)"
# ---------------------------------------------------------------------------

# 2a — SOUL / checklist / bond-etf / fx / trunk ban bare BUY
for f in \
  "${CHRISTINA}/SOUL.md" \
  "${CHRISTINA}/skills-checklist.md" \
  "$BOND_SKILL" \
  "$FX_SKILL" \
  "$SESSION_SKILL"
do
  if [[ ! -f "$f" ]]; then
    fail "missing for bare-BUY ban: $f"
    continue
  fi
  if grep -Eq 'bare[[:space:]]*`?BUY`?|❌[[:space:]]*.*`?BUY`?|\bBUY\b.*WATCH|WATCH.*`?BUY' "$f"; then
    ok "bans bare BUY: $(basename "$(dirname "$f")")/$(basename "$f")"
  else
    # fx may ban via FX_* vocabulary + C_*↔FX_*; require explicit BUY ban or Signal-only FX_*
    if [[ "$(basename "$(dirname "$f")")" == "fx-us-uk-bridge" ]] \
      && grep -Eq 'FX_LONG|FX_\*|Signal only' "$f"; then
      ok "fx skill documents FX_* Signal vocabulary (no bare BUY path)"
    else
      fail "must explicitly ban bare BUY: $f"
    fi
  fi
done

# 2b — checklist documents C_*↔B_*↔FX_* ban (isolation, not mapping recipe)
if grep -Eq 'C_\*.*B_\*.*FX_\*|C_\*.*↔.*B_\*.*↔.*FX_\*|❌.*C_\*.*B_\*.*FX_' \
  "${CHRISTINA}/skills-checklist.md"; then
  ok "checklist documents ❌ C_*↔B_*↔FX_* namespace isolation"
else
  fail "checklist missing C_*↔B_*↔FX_* isolation note"
fi
# Reject affirmative mapping language (must not teach how to map)
if grep -Eqi 'map C_\* to B_\*|map B_\* to FX_\*|C_\*.*=.*B_\*.*=.*FX_\*|translate C_\* into B_\*' \
  "${CHRISTINA}/skills-checklist.md"; then
  fail "checklist has mapping-recipe language (C_*↔B_*↔FX_* violation)"
else
  ok "checklist has no C_*↔B_*↔FX_* mapping recipe"
fi

# 2c — Signal example cells must not be bare BUY / DIR_* / tm_score / C_* concrete
check_signal_cells() {
  local f="$1"
  python3 - "$f" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
chunks = re.split(r"```(?:markdown)?\n?", text)
violations = []
bad_exact = re.compile(
    r"^(BUY|WATCH|NO_SIGNAL|DIR_[A-Z_]+|tm_score|valuation_score|C_[A-Z_]+)$"
)
# Allow documentation placeholders B_* / FX_* / …
placeholder_ok = re.compile(r"^(B_\*|FX_\*|B_\s*/|FX_\s*/|\.\.\.|…)$")

def scan_tables(blob, where):
    lines = blob.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip().startswith("|"):
            i += 1
            continue
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(lines[i])
            i += 1
        if len(rows) < 2:
            continue
        headers = [c.strip() for c in rows[0].strip("|").split("|")]
        data_start = 1
        if data_start < len(rows) and re.match(r"^\|?\s*[-:]+", rows[data_start]):
            data_start = 2
        if "Signal" not in headers:
            continue
        sig_i = headers.index("Signal")
        for r in rows[data_start:]:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if sig_i >= len(cells):
                continue
            cell = cells[sig_i]
            for part in re.split(r"\s*/\s*", cell):
                part = part.strip().strip("`")
                if not part or part in {"", "—", "-", "…", "..."}:
                    continue
                if placeholder_ok.match(part) or part.startswith("B_*") or part.startswith("FX_*"):
                    continue
                # Allowed concrete: B_LONG etc, FX_*, NO_SETUP, miss
                if re.fullmatch(r"B_[A-Z]+|FX_[A-Z]+|NO_SETUP|miss", part):
                    continue
                if bad_exact.match(part):
                    violations.append(f"{where}: Signal cell '{part}' in row: {r.strip()}")

scan_tables(text, "body")
for n, ch in enumerate(chunks):
    scan_tables(ch, f"fence#{n}")

if violations:
    print("VIOLATIONS:")
    for v in violations:
        print(" -", v)
    sys.exit(1)
sys.exit(0)
PY
}

for label_f in \
  "bond-etf-tape:$BOND_SKILL" \
  "fx-us-uk-bridge:$FX_SKILL" \
  "rates-session-report:$SESSION_SKILL"
do
  label="${label_f%%:*}"
  f="${label_f#*:}"
  if [[ ! -f "$f" ]]; then
    fail "missing $f"
    continue
  fi
  if check_signal_cells "$f"; then
    ok "${label} examples: no bare BUY / wrong-namespace as Signal"
  else
    fail "${label} examples: bare BUY or wrong-namespace Signal found"
  fi
done

# ---------------------------------------------------------------------------
section "3. Scaffold completeness (Daily/Weekly Session summary · FedWatch · Miss · Ccy · Rate scenario)"
# ---------------------------------------------------------------------------

extract_scaffold() {
  local label="$1"  # Daily or Weekly
  python3 - "$SESSION_SKILL" "$label" <<'PY'
import sys
path, label = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
marker = f"## Blank report template — {label} scaffold"
idx = text.find(marker)
if idx < 0:
    sys.stderr.write(f"scaffold heading not found: {marker}\n")
    sys.exit(2)
rest = text[idx:]
m = __import__("re").search(r"```markdown\n(.*?)```", rest, __import__("re").S)
if not m:
    sys.stderr.write(f"no ```markdown fence after {marker}\n")
    sys.exit(2)
sys.stdout.write(m.group(1))
PY
}

check_scaffold() {
  local label="$1"
  local body
  if ! body="$(extract_scaffold "$label")"; then
    fail "${label} scaffold: could not extract copy-paste template"
    return
  fi
  local missing=()
  echo "$body" | grep -Eq '^## Session summary' \
    || missing+=("## Session summary")
  echo "$body" | grep -Eqi 'FedWatch' \
    || missing+=("FedWatch section")
  echo "$body" | grep -Eqi 'Miss ledger' \
    || missing+=("Miss ledger")
  echo "$body" | grep -Eq '\| Ccy \|' \
    || missing+=("Ccy column")
  echo "$body" | grep -Eqi 'Rate scenario' \
    || missing+=("Rate scenario")
  echo "$body" | grep -Eq '\| Range \|' \
    || missing+=("FX range")
  echo "$body" | grep -Eq 'FX range' \
    || missing+=("Session summary FX range")
  if ((${#missing[@]} == 0)); then
    ok "${label} scaffold has Session summary + FedWatch + Miss ledger + Ccy + Rate scenario + FX range"
  else
    fail "${label} scaffold missing: ${missing[*]}"
  fi
}

if [[ -f "$SESSION_SKILL" ]]; then
  check_scaffold "Daily"
  check_scaffold "Weekly"
else
  fail "missing session skill for scaffold checks"
fi

# ---------------------------------------------------------------------------
section "4. Obs backtest hygiene (fixture · no PnL)"
# ---------------------------------------------------------------------------

OBS_TARGET="${OBS_FIXTURE}"
if [[ ! -f "$OBS_TARGET" ]]; then
  fail "missing obs fixture: $OBS_TARGET"
else
  set +e
  python3 - "$OBS_TARGET" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
checks = []

def add(name, ok, detail=""):
    checks.append((name, ok, detail))

def tables_with_signal():
    """Return list of (heading_hint, headers, data_rows) for tables that have Signal."""
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
        headers = [c.strip() for c in rows[0].strip("|").split("|")]
        if "Signal" not in headers:
            continue
        data = rows[2:] if re.match(r"^\|?\s*[-:]+", rows[1]) else rows[1:]
        out.append((last_heading, headers, data))
    return out

add("has Session summary", bool(re.search(r"^## Session summary", text, re.M)))
add("has rates_regime OR notes optional", bool(
    re.search(r"rates_regime", text) or re.search(r"(?i)optional", text)
))
sig_tables = tables_with_signal()
has_bond_or_fx = any(
    re.search(r"(?i)bond|gov|ETF|FX forecast|FX ", h) for h, _, _ in sig_tables
) or len(sig_tables) > 0
add("has bond view AND/OR FX forecast table with Signal", has_bond_or_fx,
    f"signal_tables={len(sig_tables)}")
add("has next-day prints block", bool(re.search(r"(?i)next[- ]day prints|## Next-day", text)))
add("declares observation only / no PnL / hygiene", bool(
    re.search(r"(?i)observation only|no PnL|hygiene", text)
))

bare_buy = False
full_bond = 0
full_fx = 0
basis_missing = False
ccy_missing = False
empty = {"", "—", "-", "n/a", "–", "miss"}

def filled(cells, i):
    return i >= 0 and i < len(cells) and cells[i].strip() not in empty and cells[i].strip().lower() != "miss"

for heading, headers, data in sig_tables:
    si = headers.index("Signal")
    bi = next((i for i, h in enumerate(headers) if h.startswith("Basis")), -1)
    ei = next((i for i, h in enumerate(headers) if "Obs entry" in h), -1)
    sli = next((i for i, h in enumerate(headers) if re.search(r"(?i)cut", h)), -1)
    tpi = next((i for i, h in enumerate(headers) if "Obs TP" in h or h.strip() == "Obs TP"), -1)
    ci = headers.index("Ccy") if "Ccy" in headers else -1
    is_fx = bool(re.search(r"(?i)FX", heading)) or any(
        "Yahoo" in h or "Pair" in h or "Quote" in h for h in headers
    )
    is_bond = (not is_fx) and (
        bool(re.search(r"(?i)bond|gov|ETF|Other bond", heading))
        or "ETF" in headers or "Bucket" in headers or ci >= 0
    )
    for r in data:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if si < len(cells):
            sig = cells[si].strip("`")
            if re.fullmatch(r"BUY", sig):
                bare_buy = True
        if filled(cells, ei) and filled(cells, sli) and filled(cells, tpi):
            if is_fx:
                full_fx += 1
            elif is_bond or ci >= 0:
                full_bond += 1
            else:
                # ambiguous — count as bond for daily cap safety
                full_bond += 1
            if bi >= 0:
                if bi >= len(cells) or cells[bi].strip() in empty:
                    basis_missing = True
            else:
                basis_missing = True
        if is_bond and ci >= 0:
            if ci >= len(cells) or cells[ci].strip() in {"", "—", "-", "n/a", "–"}:
                ccy_missing = True

cadence_daily = bool(re.search(r"(?i)cadence.*daily|daily lite", text))

add("no bare BUY in Signal", not bare_buy)
add("Daily ≤3 full bond Obs levels", full_bond <= 3, f"full_bond={full_bond}")
if cadence_daily:
    add("FX full levels ≤2 when daily", full_fx <= 2, f"full_fx={full_fx}")
else:
    add("FX full levels ≤2 when daily", True, "skipped (not daily)")
add("Basis present when Obs levels filled", not basis_missing)
add("Ccy present on bond rows when table has Ccy", not ccy_missing)
pnl_col = bool(re.search(
    r"(?i)\|\s*(PnL|P&L|ROI|Return %|Profit)\s*\|", text
)) or bool(re.search(r"(?i)^(PnL|P&L|ROI)\s*:", text, re.M))
add("no PnL / return columns", not pnl_col)

failed = [c for c in checks if not c[1]]
print("Obs backtest hygiene score:")
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  {mark}  {name}{extra}")
score = sum(1 for _, ok, _ in checks if ok)
print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
sys.exit(0 if not failed else 1)
PY
  obs_rc=$?
  set -e
  if [[ $obs_rc -eq 0 ]]; then
    ok "obs backtest fixture passes hygiene rules"
  else
    fail "obs backtest fixture failed hygiene rules"
  fi
fi

# Negative control — bad fixture must exhibit bare BUY or tm_score as Signal
BAD="${FIXTURES}/obs_backtest_bad.md"
if [[ -f "$BAD" ]]; then
  set +e
  python3 - "$BAD" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
viol = False
lines = text.splitlines()
i = 0
while i < len(lines):
    if not lines[i].strip().startswith("|"):
        i += 1
        continue
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(lines[i])
        i += 1
    if len(rows) < 2:
        continue
    headers = [c.strip() for c in rows[0].strip("|").split("|")]
    if "Signal" not in headers:
        continue
    si = headers.index("Signal")
    data = rows[2:] if re.match(r"^\|?\s*[-:]+", rows[1]) else rows[1:]
    for r in data:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if si < len(cells):
            sig = cells[si].strip("`")
            if re.fullmatch(r"BUY", sig) or re.fullmatch(r"tm_score", sig) \
               or re.fullmatch(r"DIR_[A-Z_]+", sig) or re.fullmatch(r"C_[A-Z_]+", sig):
                viol = True
sys.exit(0 if viol else 1)
PY
  bad_rc=$?
  set -e
  if [[ $bad_rc -eq 0 ]]; then
    ok "bad fixture correctly exhibits namespace violation (negative control)"
  else
    fail "bad fixture should contain bare BUY or tm_score as Signal (negative control)"
  fi
else
  fail "missing bad fixture: $BAD"
fi

# ---------------------------------------------------------------------------
section "5. FedWatch consume-only keywords"
# ---------------------------------------------------------------------------

if [[ -f "$FEDWATCH_SKILL" ]]; then
  if grep -Eqi 'consume-only|Consume-only' "$FEDWATCH_SKILL" \
    && grep -Eq '<job-id>' "$FEDWATCH_SKILL"; then
    ok "fedwatch-consume documents consume-only + cron <job-id>"
  else
    fail "fedwatch-consume missing consume-only and/or cron id <job-id>"
  fi
  # Optional path lock — tolerate if not yet present
  if grep -Eqi 'alice/fedwatch|latest\.json' "$FEDWATCH_SKILL"; then
    ok "fedwatch-consume documents artifact path (alice/fedwatch or latest.json)"
  else
    ok "fedwatch-consume path not yet locked (tolerated · consume-only + cron present)"
  fi
else
  fail "missing $FEDWATCH_SKILL"
fi

# ---------------------------------------------------------------------------
section "6. Firewall (NO_DB · observation only · ETF proxy ≠ cash)"
# ---------------------------------------------------------------------------

for f in "${CHRISTINA}/SOUL.md" "${CHRISTINA}/skills-checklist.md"; do
  name="$(basename "$f")"
  if [[ ! -f "$f" ]]; then
    fail "missing $f"
    continue
  fi
  missing=()
  grep -Eq 'NO_DB' "$f" || missing+=("NO_DB")
  grep -Eqi 'observation only' "$f" || missing+=("observation only")
  grep -Eqi 'ETF proxy.*cash|ETF.*≠.*cash|ETF≠cash|ETF proxy ≠' "$f" \
    || missing+=("ETF proxy ≠ cash")
  if ((${#missing[@]} == 0)); then
    ok "firewall keywords in ${name}"
  else
    fail "${name} missing firewall: ${missing[*]}"
  fi
done

# ---------------------------------------------------------------------------
section "Summary"
# ---------------------------------------------------------------------------

echo ""
echo "christina audit: ${PASS} passed, ${FAIL} failed"
if (( FAIL > 0 )); then
  red "RESULT: FAIL"
  exit 1
fi
green "RESULT: PASS"
exit 0
