#!/usr/bin/env bash
# Sync inbox reports → web-infra/reports-server/www (nginx :8080)
#
# Canonical folders match inbox (job function, not profile name).
# Legacy inbox aliases are copied into the canonical folder, then removed from www.
# Only md/html/json under 2 MiB are published (no tarballs).
# Daily-dated files older than 7 days → archive. Weekly older than 8 ISO weeks → archive.
set -uo pipefail

SRC="${REPORTS_INBOX:-$HOME/workspace/reports/inbox}"
DST="${REPORTS_WWW:-$HOME/web-infra/reports-server/www}"
ARCHIVE="${REPORTS_ARCHIVE:-$HOME/web-infra/reports-server/archive}"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d 'yesterday' +%Y-%m-%d)
SEVEN_DAYS_AGO=$(date -d '7 days ago' +%s)
MAX_BYTES=$((2 * 1024 * 1024))

CANONICAL=(
  analysis
  commodities-session
  daily-social
  daily-trend-momentum
  market-close
  position-watch
  rates-session
  social-watch
  scoring-eval
  valuation-width
  value-session
  weekly-deep-dive
  weekly-performance
  weekly-trend-momentum
  sec-monitor
  sec-filings
  moa-reviews
  planning
  research
  system-audit
  technical
  exports
)

# inbox folder → www folder (legacy names)
alias_dest() {
  case "$1" in
    weekly-valuation) echo valuation-width ;;
    daily) echo daily-trend-momentum ;;
    weekly) echo weekly-trend-momentum ;;
    *) echo "$1" ;;
  esac
}

# Trains that produce a Zoe revise: draft *-report.md must not sit beside *-revised.md on www.
REVISE_TRAINS="valuation-width weekly-trend-momentum weekly-deep-dive weekly-performance market-close daily-trend-momentum commodities-session rates-session value-session"

is_revise_train() {
  case " $REVISE_TRAINS " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

period_prefix() {
  local name="$1"
  if [[ "$name" =~ ([0-9]{4}-W[0-9]{2}) ]]; then
    echo "${BASH_REMATCH[1]}"
    return
  fi
  if [[ "$name" =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
    echo "${BASH_REMATCH[1]}"
    return
  fi
  echo ""
}

is_draft_report() {
  local base="$1"
  [[ "$base" == *.md ]] || return 1
  [[ "$base" == *revised* ]] && return 1
  [[ "$base" == *-report.md ]] && return 0
  [[ "$base" == *-trend-momentum-report.md ]] && return 0
  [[ "$base" == *-weekly-deep-dive.md ]] && return 0
  [[ "$base" == *-weekly-performance.md ]] && return 0
  [[ "$base" == *-phase2-summary.md ]] && return 0
  [[ "$base" == *-market-close.md ]] && return 0
  [[ "$base" == *-session.md ]] && return 0
  return 1
}

has_revised_sibling() {
  local dir="$1" prefix="$2"
  [[ -n "$prefix" ]] || return 1
  local r b
  shopt -s nullglob
  for r in "$dir"/*-revised.md "$dir"/*revised*.md; do
    [[ -f "$r" ]] || continue
    b=$(basename "$r")
    [[ "$b" == *"$prefix"* ]] || continue
    shopt -u nullglob
    return 0
  done
  shopt -u nullglob
  return 1
}

should_skip_draft() {
  local dir="$1" dest_name="$2" base="$3"
  is_revise_train "$dest_name" || return 1
  is_draft_report "$base" || return 1
  local prefix
  prefix=$(period_prefix "$base")
  has_revised_sibling "$dir" "$prefix"
}

is_publishable() {
  local f="$1"
  local base ext
  base=$(basename "$f")
  [[ "$base" == index.html ]] && return 1
  ext="${base##*.}"
  case "$ext" in
    md|html|json) ;;
    *) return 1 ;;
  esac
  local sz
  sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
  [[ "$sz" -gt 0 && "$sz" -le "$MAX_BYTES" ]]
}

mkdir -p "$DST/today" "$ARCHIVE"

HERE_EARLY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$HERE_EARLY/desk_pack_revised_gate.py"
if [[ -f "$GATE" ]]; then
  python3 "$GATE" --min-age 180 || echo "[warn] desk_pack_revised_gate.py status $?" >&2
fi

echo "[sync] inbox → www (canonical structure)"

# ── Step 1: copy publishable files (canonical + aliases) ──
for dir in "$SRC"/*/; do
  [ -d "$dir" ] || continue
  src_name=$(basename "$dir")
  dest_name=$(alias_dest "$src_name")
  mkdir -p "$DST/$dest_name"
  find "$dir" -maxdepth 2 -type f | while read -r f; do
    is_publishable "$f" || continue
    base=$(basename "$f")
    if should_skip_draft "$dir" "$dest_name" "$base"; then
      echo "[skip-draft] $src_name/$base (revised sibling present)"
      continue
    fi
    rel="${f#"$dir"}"
    dest_file="$DST/$dest_name/$rel"
    mkdir -p "$(dirname "$dest_file")"
    cp -u "$f" "$dest_file"
  done
done

# ── Step 1b: archive www drafts that already sit beside a revise ──
for dest_name in $REVISE_TRAINS; do
  [ -d "$DST/$dest_name" ] || continue
  find "$DST/$dest_name" -maxdepth 2 -type f -name "*.md" | while read -r f; do
    base=$(basename "$f")
    is_draft_report "$base" || continue
    prefix=$(period_prefix "$base")
    has_revised_sibling "$(dirname "$f")" "$prefix" || continue
    rel="${f#"$DST/"}"
    echo "[archive-draft] www/$rel (revised sibling present)"
    mkdir -p "$(dirname "$ARCHIVE/$rel")"
    mv -f "$f" "$ARCHIVE/$rel" 2>/dev/null || true
  done
done

# Root-level notes (not the dashboard)
for f in "$SRC"/*.md; do
  [ -f "$f" ] || continue
  is_publishable "$f" || continue
  cp -u "$f" "$DST/"
done

# ── Step 2: move leftover www dirs that are not canonical / today ──
for dir in "$DST"/*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  [[ "$name" == today || "$name" == jobs ]] && continue
  keep=0
  for c in "${CANONICAL[@]}"; do
    [[ "$name" == "$c" ]] && keep=1 && break
  done
  if [[ "$keep" -eq 0 ]]; then
    echo "[archive] leftover www/$name"
    mkdir -p "$ARCHIVE/$name"
    find "$dir" -mindepth 1 -maxdepth 1 -exec mv -n {} "$ARCHIVE/$name/" \;
    rmdir "$dir" 2>/dev/null || true
  fi
done

# ── Step 3: today/ symlinks (today + yesterday in filename) ──
echo "[today] rebuild symlinks"
find "$DST/today" -maxdepth 1 -type l -delete 2>/dev/null || true
find "$DST" -maxdepth 3 -type f \( -name "*.md" -o -name "*.html" -o -name "*.json" \) | while read -r f; do
  [ -L "$f" ] && continue
  [[ "$(basename "$f")" == index.html || "$(basename "$f")" == status.json ]] && continue
  [[ "${f#"$DST/"}" == jobs/* ]] && continue
  fname=$(basename "$f")
  echo "$fname" | grep -qE "$TODAY|$YESTERDAY" || continue
  rel="${f#"$DST/"}"
  ln -sfn "../$rel" "$DST/today/$fname"
done

# ── Step 4: today/ index ──
TODAY_DISPLAY=$(date '+%A, %-d %B %Y')
{
  cat <<INDEXEOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Today's Reports</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0d1117; color: #c9d1d9; }
  h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
  a { color: #58a6ff; text-decoration: none; display: block; padding: 8px 12px; margin: 4px 0; border-radius: 6px; }
  a:hover { background: #161b22; }
  .date { color: #8b949e; font-size: 0.85em; }
  .back { margin: 20px 0; }
  .back a { display: inline; padding: 4px 12px; border: 1px solid #30363d; border-radius: 6px; }
  ul { list-style: none; padding: 0; }
  li { border-bottom: 1px solid #21262d; }
</style>
</head>
<body>
<h1>Today's Reports</h1>
<p class="date">${TODAY_DISPLAY}</p>
<ul>
INDEXEOF
  find "$DST/today" -maxdepth 1 -type l | sort | while read -r link; do
    name=$(basename "$link")
    target=$(readlink "$link")
    category=$(echo "$target" | sed 's|^\.\./||; s|/.*||')
    echo "<li><a href=\"$name\">$category — $name</a></li>"
  done
  cat <<'ENDHTML'
</ul>
<div class="back"><a href="../">All Reports</a></div>
</body>
</html>
ENDHTML
} > "$DST/today/index.html"

# ── Step 5: prune old dated files → archive ──
echo "[prune] daily >7d, weekly >8 ISO weeks"
CURRENT_WEEK=$(date +%V)
CURRENT_YEAR=$(date +%Y)
WEEK_CUTOFF=$((10#$CURRENT_WEEK - 8))

find "$DST" -maxdepth 3 -type f \( -name "*.md" -o -name "*.html" -o -name "*.json" \) | while read -r f; do
  [ -L "$f" ] && continue
  [[ "$(basename "$f")" == index.html ]] && continue
  fname=$(basename "$f")

  week=$(echo "$fname" | grep -oE '[0-9]{4}-W[0-9]{2}' | head -1)
  if [ -n "$week" ]; then
    wy=${week:0:4}
    ww=$((10#${week:6:2}))
    if [ "$wy" -lt "$CURRENT_YEAR" ] || { [ "$wy" -eq "$CURRENT_YEAR" ] && [ "$ww" -lt "$WEEK_CUTOFF" ]; }; then
      rel="${f#"$DST/"}"
      mkdir -p "$(dirname "$ARCHIVE/$rel")"
      mv "$f" "$ARCHIVE/$rel" 2>/dev/null || true
    fi
    continue
  fi

  fdate=$(echo "$fname" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
  if [ -z "$fdate" ]; then
    raw=$(echo "$fname" | grep -oE '[0-9]{8}' | head -1)
    if [ -n "$raw" ]; then
      fdate="${raw:0:4}-${raw:4:2}-${raw:6:2}"
    fi
  fi
  if [ -n "$fdate" ]; then
    cat_name=$(echo "${f#"$DST/"}" | cut -d/ -f1)
    case "$cat_name" in
      daily-social|daily-trend-momentum|social-watch|analysis|position-watch|commodities-session|rates-session|value-session) cutoff=$SEVEN_DAYS_AGO ;;
      *) cutoff=$(date -d '90 days ago' +%s) ;;
    esac
    fepoch=$(date -d "$fdate" +%s 2>/dev/null || echo 0)
    if [ "$fepoch" -gt 0 ] && [ "$fepoch" -lt "$cutoff" ]; then
      rel="${f#"$DST/"}"
      mkdir -p "$(dirname "$ARCHIVE/$rel")"
      mv "$f" "$ARCHIVE/$rel" 2>/dev/null || true
    fi
  fi
done

# Tarballs / binaries / checksum leftovers never belong on www
find "$DST" -type f \( -name "*.tar.gz" -o -name "*.zip" -o -name "*.tgz" -o -name "*.sha256" -o -name "*.txt" \) | while read -r f; do
  rel="${f#"$DST/"}"
  mkdir -p "$(dirname "$ARCHIVE/$rel")"
  mv "$f" "$ARCHIVE/$rel" 2>/dev/null || true
done

# ── Step 6: dashboard (single-file portal) ──
# Source: reports-index.html next to this script (~/.hermes/scripts/ after apply-host-scripts scp).
# apply-host-scripts also stamps www/index.html immediately after scp; cron sync re-stamps here.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$HERE/reports-index.html"
if [[ -f "$TPL" ]]; then
  STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  python3 - "$TPL" "$DST/index.html" "$STAMP" <<'PY'
from pathlib import Path
import sys
src, dest, stamp = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
text = src.read_text(encoding="utf-8").replace("__SYNC_STAMP__", stamp)
dest.write_text(text, encoding="utf-8")
print(f"[index] portal written stamp={stamp}")
PY
else
  echo "[warn] missing $TPL — left existing index.html" >&2
fi

# ── Step 6b: investment job traffic lights ──
STATUS_PY="$HERE/investment_jobs_status.py"
if [[ -f "$STATUS_PY" ]]; then
  python3 "$STATUS_PY" || echo "[warn] investment_jobs_status.py failed" >&2
else
  echo "[warn] missing $STATUS_PY" >&2
fi

# ── Step 7: keep every canonical folder (new reports have a home) ──
for c in "${CANONICAL[@]}"; do
  mkdir -p "$DST/$c"
done
find "$DST" -mindepth 1 -maxdepth 1 -type d -empty -not -name today -not -name jobs | while read -r d; do
  name=$(basename "$d")
  keep=0
  for c in "${CANONICAL[@]}"; do
    [[ "$name" == "$c" ]] && keep=1 && break
  done
  [[ "$keep" -eq 1 ]] && continue
  rmdir "$d" 2>/dev/null || true
done
find "$DST" -type d -exec chmod 755 {} \; 2>/dev/null || true
find "$DST" -type f -exec chmod 644 {} \; 2>/dev/null || true

DST_FILE_COUNT=$(find "$DST" -maxdepth 3 -type f \( -name "*.md" -o -name "*.html" -o -name "*.json" \) | wc -l)
TODAY_LINK_COUNT=$(find "$DST/today" -maxdepth 1 -type l | wc -l)
echo "[ok] files=$DST_FILE_COUNT today_links=$TODAY_LINK_COUNT"
REPORTS_URL="${REPORTS_URL:-http://localhost:8080/reports/}"
echo "    ${REPORTS_URL}"
echo "    ${REPORTS_URL}today/"
if [ "$DST_FILE_COUNT" -eq 0 ]; then
  echo "[warn] 0 files in destination" >&2
  exit 1
fi
