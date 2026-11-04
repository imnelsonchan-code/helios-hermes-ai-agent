#!/usr/bin/env bash
# Desk Pack post-step / legacy cron: T&M BUY digest + read-only exit overlay.
# Option A Telegram: hermes send inside this script (Desk Pack cron stays deliver=local).
# Does NOT write trade_journal.csv, place orders, or pass --mfe-json (time-stop -> position_watch).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${TM_EXITS_PYTHON:-${HOME}/.hermes/hermes-agent/venv/bin/python3}"
REPORT_DIR="${TM_EXITS_REPORT_DIR:-${HOME}/.hermes/shared/reports/renee/daily-trend-momentum}"
EXIT_CHECKER="${TM_EXITS_CHECKER:-${HERE}/exit_signal_checker.py}"
JOURNAL="${TM_EXITS_JOURNAL:-${HOME}/.hermes/trade_journal.csv}"
HERMES="${TM_EXITS_HERMES:-${HOME}/.local/bin/hermes}"
SEND_TG="${TM_EXITS_SEND_TELEGRAM:-1}"

if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || true)"
fi
if [[ -z "$PY" ]]; then
  echo "ERROR: no python3" >&2
  exit 127
fi
if [[ ! -f "$EXIT_CHECKER" ]]; then
  echo "ERROR: missing exit checker: $EXIT_CHECKER" >&2
  exit 127
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
checker_rc=0
exit_status="ok"

{
 echo "📈 T&M + Exit "
 echo ": $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo ""

  LATEST_DATA="$(ls -t "$REPORT_DIR"/*-data.json 2>/dev/null | head -1 || true)"
  if [[ -n "$LATEST_DATA" && -f "$LATEST_DATA" ]]; then
 echo "📊 "
    echo "-------------"
    echo "data: $LATEST_DATA"
    "$PY" - "$LATEST_DATA" <<'PY' || true
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
results = data if isinstance(data, list) else data.get("results", [])
buys = [r for r in results if (r.get("total") or r.get("tm_score") or 0) >= 60]
buys.sort(key=lambda x: x.get("total") or x.get("tm_score") or 0, reverse=True)
print(f" BUY : {len(buys)} ")
for r in buys[:10]:
    t = r.get("ticker", "?")
    s = r.get("total") or r.get("tm_score") or 0
    b = r.get("bracket", "?")
    ep = r.get("entry_price", "")
    sl = r.get("stop_loss", "")
    tp = r.get("take_profit", "")
    ep_s = f"${ep:.2f}" if isinstance(ep, (int, float)) else (ep or "—")
    sl_s = f"${sl:.2f}" if isinstance(sl, (int, float)) else (sl or "—")
    tp_s = f"${tp:.2f}" if isinstance(tp, (int, float)) else (tp or "—")
    print(f"  🟢 {t:5s} score={int(s):3d} {str(b):8s} entry={ep_s} SL={sl_s} TP={tp_s}")
PY
    echo ""
  else
 echo "⚠️ T&M data"
    echo ""
  fi

 echo "🔴 Exit (read-only · score decay; --mfe-json)"
  echo "-------------"
  checker_rc=0
  if [[ ! -f "$JOURNAL" ]] || ! grep -q ",OPEN," "$JOURNAL" 2>/dev/null; then
 echo " ✅ OPEN , exit "
    exit_status="no-OPEN-skip"
  else
    # NOTE: `|| rc=$?` (not `if ! cmd; then rc=$?`) — inside a negated-if
    # body `$?` is always 0, which used to report a crashed checker as OK.
    checker_rc=0
    out="$("$PY" "$EXIT_CHECKER" --dry-run 2>&1)" || checker_rc=$?
    echo "$out" | head -40
    if [[ "$checker_rc" -ne 0 ]]; then
 echo " ⚠️ exit_signal_checker exited $checker_rc( journal)"
      exit_status="checker_rc=$checker_rc"
    else
 echo " ✅ exit overlay ( journal · no orders)"
      exit_status="ok"
    fi
  fi

  echo "-------------"
 echo "📋 "
  # grep -c already prints 0 on no-match; `|| true` only swallows the rc
  # (the old `|| echo 0` appended a second "0" line to the count).
  OPEN_COUNT="$(grep -c ",OPEN," "$JOURNAL" 2>/dev/null || true)"
  [[ "$OPEN_COUNT" ]] || OPEN_COUNT=0
 echo " : ${OPEN_COUNT} "
  TODAY_BUYS="$("$PY" - "$REPORT_DIR" <<'PY' 2>/dev/null || echo "?"
import glob, json, sys
files = sorted(glob.glob(sys.argv[1] + "/*-data.json"))
if not files:
    print("?")
else:
    d = json.load(open(files[-1], encoding="utf-8"))
    r = d if isinstance(d, list) else d.get("results", [])
    print(sum(1 for x in r if (x.get("total") or x.get("tm_score") or 0) >= 60))
PY
)"
 echo " : ${TODAY_BUYS}"
  echo ""
 echo "⚠️ Not investment advice · "
} >"$TMP"

cat "$TMP"

# Desk Pack completion-gate receipt (post-step evidence; not from 23:00 position-watch).
DATE_UTC="$(date -u +%Y-%m-%d)"
RECEIPT_DIR="${TM_EXITS_RECEIPT_DIR:-${REPORTS_INBOX:-$HOME/workspace/reports/inbox}/desk-pack-exit}"
RECEIPT="${RECEIPT_DIR}/${DATE_UTC}-tm-exits.md"
if mkdir -p "$RECEIPT_DIR" 2>/dev/null \
  && printf '%s\n' \
    "timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "status: ${exit_status:-ok}" \
    "note: non-investment · Desk Pack daily_tm_with_exits receipt" \
    >"$RECEIPT" 2>/dev/null; then
  :
else
  echo "WARN: failed to write exit receipt: $RECEIPT" >&2
fi

if [[ "$SEND_TG" == "1" ]]; then
  if [[ -x "$HERMES" ]] || command -v hermes >/dev/null 2>&1; then
    CLI="$HERMES"
    [[ -x "$CLI" ]] || CLI="$(command -v hermes)"
    if ! "$CLI" send --to telegram "$(cat "$TMP")" >/dev/null 2>&1; then
      echo "WARN: hermes send telegram failed" >&2
    fi
  else
    echo "WARN: hermes CLI missing — skipped Telegram (Option A)" >&2
  fi
fi

exit "${checker_rc:-0}"
