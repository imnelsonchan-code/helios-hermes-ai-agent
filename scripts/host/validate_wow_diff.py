#!/usr/bin/env python3
"""validate_wow_diff.py — Standalone week-over-week diff checker for valuation-width scans.

Compares the current week's report JSON against the previous week's and emits
alerts for unusual shifts: stock count swings, yfinance gap rate changes,
top-10 turnover, and mean composite score drift.

If the exact previous ISO week file is missing (skipped week), walk back to the
latest existing YYYY-W##-valuation-width.json older than current (cap 8 weeks).

Non-blocking: always exits 0. Intended for post-scan cron invocation.

Usage:
    validate_wow_diff.py [--current <path>] [--dir <report_dir>]

    --current  Path to current week JSON. If omitted, auto-detects latest
               *-valuation-width.json in --dir.
    --dir      Report directory (default: ~/.hermes/profiles/eliza/workspace/valuation-width/)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_REPORT_DIR = os.path.expanduser(
    "~/.hermes/profiles/eliza/workspace/valuation-width"
)
SHARED_REPORT_DIR = os.path.expanduser(
    "~/.hermes/shared/reports/eliza/valuation-width"
)
MAX_WALKBACK_WEEKS = 8


def _parse_year_week(filename: str) -> tuple | None:
    """Extract (year, week_num) from a filename like '2026-W29-valuation-width.json'."""
    m = re.match(r"(\d{4})-W(\d{2})-valuation-width\.json$", filename)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _week_label(year: int, week: int) -> str:
    return f"{year}-W{week:02d}"


def _prev_week(year: int, week: int) -> tuple[int, int]:
    """Return (year, week-1), wrapping W01 -> previous year W52/W53."""
    if week > 1:
        return year, week - 1
    prev_year = year - 1
    from datetime import date
    dec28 = date(prev_year, 12, 28)
    prev_week_num = dec28.isocalendar()[1]
    return prev_year, prev_week_num


def find_latest_report(report_dir: str) -> str | None:
    """Find the most recent *-valuation-width.json by YEAR-WEEK in report_dir."""
    best_path = None
    best_yw = (0, 0)
    try:
        for entry in os.listdir(report_dir):
            yw = _parse_year_week(entry)
            if yw is None:
                continue
            if yw > best_yw:
                best_yw = yw
                best_path = os.path.join(report_dir, entry)
    except FileNotFoundError:
        return None
    return best_path


def _existing_week_file(filename: str, *dirs: str) -> str | None:
    for d in dirs:
        if not d:
            continue
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return None


def find_baseline(curr_year: int, curr_week: int, *search_dirs: str) -> tuple[str | None, str | None, int]:
    """Walk back from W-1 up to MAX_WALKBACK_WEEKS for an existing JSON.

    Returns (path, week_label, weeks_back) or (None, None, 0).
    weeks_back=1 means exact previous ISO week.
    """
    year, week = curr_year, curr_week
    for n in range(1, MAX_WALKBACK_WEEKS + 1):
        year, week = _prev_week(year, week)
        filename = f"{_week_label(year, week)}-valuation-width.json"
        path = _existing_week_file(filename, *search_dirs)
        if path:
            return path, _week_label(year, week), n
    return None, None, 0


def load_report(path: str) -> dict:
    """Load a valuation-width JSON report. Returns empty dict on failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        print(f"[validate_wow_diff] WARNING: cannot load {path}: {e}", file=sys.stderr)
        return {}


def all_rankings(report: dict) -> list[dict]:
    """Return merged list of all rankings across tracks A and B."""
    result = []
    for track_key in ("A", "B"):
        track = report.get("tracks", {}).get(track_key, {})
        result.extend(track.get("rankings", []))
    return result


def top10_tickers(report: dict) -> set[str]:
    """Set of tickers in top-10 across both tracks."""
    tickers = set()
    for track_key in ("A", "B"):
        track = report.get("tracks", {}).get(track_key, {})
        for r in track.get("rankings", [])[:10]:
            tickers.add(r.get("ticker", ""))
    tickers.discard("")
    return tickers


def gap_rate(rankings: list[dict]) -> float:
    """Fraction of rankings with _yfinance_status == 'FALLBACK'."""
    if not rankings:
        return 0.0
    fallback = sum(1 for r in rankings if r.get("_yfinance_status") == "FALLBACK")
    return fallback / len(rankings)


def mean_composite(rankings: list[dict]) -> float:
    """Mean composite_score across all rankings."""
    if not rankings:
        return 0.0
    scores = [r.get("composite_score", 0) for r in rankings]
    return sum(scores) / len(scores)


TRACK_B_MISSING_ALERT = (
    "🔴 WoW Track B missing/not screened in current (baseline had B) — "
    "partial run / do not treat as 0 hits"
)


def stock_count_wow_alert(curr_total: int, prev_total: int) -> str | None:
    """Alert when |WoW stock-count change| exceeds 50%. Signed ratio for display."""
    if prev_total <= 0:
        return None
    ratio = (curr_total - prev_total) / prev_total
    if abs(ratio) > 0.50:
        return f"🔴 WoW stock count {prev_total}->{curr_total} ({ratio:+.0%})"
    return None


def has_usable_track_b(report: dict) -> bool:
    """True if report has Track B that was screened or has non-empty rankings."""
    tracks = report.get("tracks")
    if not isinstance(tracks, dict) or "B" not in tracks:
        return False
    b = tracks.get("B")
    if not isinstance(b, dict):
        return False
    if b.get("screened"):
        return True
    rankings = b.get("rankings") or []
    return bool(rankings)


def lacks_track_b(report: dict) -> bool:
    """True if Track B is missing, screened:false, or empty/not screened."""
    tracks = report.get("tracks")
    if not isinstance(tracks, dict) or "B" not in tracks:
        return True
    b = tracks.get("B")
    if not isinstance(b, dict):
        return True
    if b.get("screened") is False:
        return True
    rankings = b.get("rankings") or []
    if not rankings and not b.get("screened"):
        return True
    return False


def track_b_missing_alert(curr: dict, prev: dict) -> str | None:
    """Alert when baseline had usable Track B but current did not screen it."""
    if has_usable_track_b(prev) and lacks_track_b(curr):
        return TRACK_B_MISSING_ALERT
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Week-over-week diff for valuation-width scans")
    parser.add_argument(
        "--current",
        help="Path to current week JSON (auto-detect latest if omitted)",
    )
    parser.add_argument(
        "--dir",
        default=DEFAULT_REPORT_DIR,
        help=f"Report directory (default: {DEFAULT_REPORT_DIR})",
    )
    args = parser.parse_args()

    report_dir = args.dir

    # ── Determine current path ──
    current_path = args.current
    if current_path is None:
        current_path = find_latest_report(report_dir)
        if current_path is None:
            print("[validate_wow_diff] No reports found — nothing to compare.", file=sys.stderr)
            sys.exit(0)
    if not os.path.exists(current_path):
        print(f"[validate_wow_diff] ERROR: --current file not found: {current_path}", file=sys.stderr)
        sys.exit(0)  # non-blocking

    # ── Parse current week ──
    current_filename = os.path.basename(current_path)
    current_yw = _parse_year_week(current_filename)
    if current_yw is None:
        print(f"[validate_wow_diff] ERROR: cannot parse YEAR-WEEK from {current_filename}",
              file=sys.stderr)
        sys.exit(0)
    curr_year, curr_week = current_yw

    # ── Determine previous path (W-1, then walk back up to 8 weeks) ──
    prev_path, baseline_week, weeks_back = find_baseline(
        curr_year, curr_week, report_dir, SHARED_REPORT_DIR
    )
    if not prev_path:
        print("No baseline — first run")
        sys.exit(0)

    if weeks_back == 1:
        print(f"[validate_wow_diff] baseline: {baseline_week}")
    else:
        print(
            f"[validate_wow_diff] baseline: {baseline_week} "
            f"(walked back {weeks_back} weeks; "
            f"{_week_label(*_prev_week(curr_year, curr_week))} missing)"
        )

    # ── Load both reports ──
    curr = load_report(current_path)
    prev = load_report(prev_path)
    if not curr:
        print("[validate_wow_diff] ERROR: current report empty/unreadable", file=sys.stderr)
        sys.exit(0)
    if not prev:
        print("[validate_wow_diff] ERROR: previous report empty/unreadable — no baseline",
              file=sys.stderr)
        sys.exit(0)

    curr_ranks = all_rankings(curr)
    prev_ranks = all_rankings(prev)
    curr_total = len(curr_ranks)
    prev_total = len(prev_ranks)

    alerts = []

    # ═══ 1. Stock count swing ═══
    count_alert = stock_count_wow_alert(curr_total, prev_total)
    if count_alert:
        alerts.append(count_alert)

    # ═══ 1b. Track B missing in current while baseline had B ═══
    b_alert = track_b_missing_alert(curr, prev)
    if b_alert:
        alerts.append(b_alert)

    # ═══ 2. yfinance gap rate ═══
    curr_gap = gap_rate(curr_ranks)
    prev_gap = gap_rate(prev_ranks)
    if curr_total > 0 and prev_total > 0:
        gap_delta = abs(curr_gap - prev_gap)
        if gap_delta > 0.20:
            alerts.append(
                f"🟡 WoW yfinance-gap {prev_gap:.0%}->{curr_gap:.0%}"
            )

    # ═══ 3. Top-10 overlap (Jaccard) ═══
    curr_top10 = top10_tickers(curr)
    prev_top10 = top10_tickers(prev)
    if curr_top10 and prev_top10:
        inter = curr_top10 & prev_top10
        union = curr_top10 | prev_top10
        jaccard = len(inter) / len(union) if union else 0.0
        if jaccard < 0.30:
            alerts.append(
                f"🟡 WoW top-10 Jaccard={jaccard:.0%} — possible universe shift"
            )

    # ═══ 4. Score drift ═══
    curr_mean = mean_composite(curr_ranks)
    prev_mean = mean_composite(prev_ranks)
    if curr_total > 0 and prev_total > 0:
        if abs(curr_mean - prev_mean) > 0.10:
            alerts.append(
                f"🟡 WoW mean composite score drift {prev_mean:.4f}->{curr_mean:.4f}"
            )

    # ── Output ──
    if alerts:
        for a in alerts:
            print(a)
    else:
        print("✅ WoW diff OK")

    sys.exit(0)


if __name__ == "__main__":
    main()
