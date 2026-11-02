#!/usr/bin/env python3
"""verify_weekly_adx.py — Weekly SPY ADX pre-publish gate (W37 generator fix).

Purpose: prevent the W36 B1 regression from reaching a weekly report. The
weekly report header's SPY weekly ADX14 must be the canonical TRUE-WILDER
value (adx_wilder.py, same method as verify_adx.py) computed on W-FRI weekly
bars resampled from the shared daily data cache. This script:

  1. loads SPY daily OHLCV from the data cache for a date key (default: most
     recent cache dir <= today UTC — the Friday of the week being reported),
  2. resamples to W-FRI weekly bars (pipeline convention),
  3. computes canonical true-Wilder ADX(14) (last + prev, same-basis
     direction),
  4. compares the PIPELINE weekly ADX value against canonical and flags
     |pipeline - canonical| > threshold (default 1.0). The pipeline value is
     resolved from latest-weekly-summary.json -> spy_weekly_adx14.value
     (written by weekly_indicator_update.py since W37) or via --cached.
  5. fallback regression detector: when no pipeline record is available for
     the requested week, cross-checks pandas_ta `ta.adx` on the same W-FRI
     bars (the NON-CANONICAL smoothing get_regime used before W37 — W36 basis
     printed 18.93 vs canonical 15.09) and flags |ta.adx - canonical| > 1.0.

Incident anchor (W36 B1, Zoe REJECT 2026-09-06, t_0386a1a6):
  get_regime() ta.adx weekly ADX14 = 18.93  vs  canonical true-Wilder = 15.09
  (cache 2026-09-04 W-FRI basis; diff 3.84 > 1.0 -> FLAG).

USAGE:
  python3 verify_weekly_adx.py                  # most recent cache <= today
  python3 verify_weekly_adx.py --date 2026-09-04
  python3 verify_weekly_adx.py --date 2026-09-04 --cached 15.09   # explicit check
  python3 verify_weekly_adx.py --date 2026-09-04 --json

EXIT CODES (same semantics as verify_adx.py):
  0 = OK      (canonical computed; |pipeline/ta.adx - canonical| <= threshold)
  1 = FLAG    (pipeline record or ta.adx diverges > threshold — do not publish)
  2 = ERROR   (no usable cache / insufficient weekly bars / pandas_ta missing
               while in ta.adx fallback mode)

Run under the same interpreter as the weekly pipeline (hermes venv with
pandas_ta), i.e. plain `python3` on this host.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

SCRIPT_DIR = os.path.expanduser("~/.hermes/scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from adx_wilder import (  # noqa: E402
    DEFAULT_LENGTH,
    CACHE_ROOT,
    load_cache_ohlcv_df,
    resample_weekly,
    weekly_adx_from_cache,
)

DEFAULT_THRESHOLD = 1.0
WEEKLY_SUMMARY = os.path.expanduser(
    "~/.hermes/shared/reports/renee/trend-momentum/latest-weekly-summary.json"
)

try:  # pandas_ta is present in the hermes venv that runs the weekly pipeline
    import pandas_ta as ta
    HAVE_TA = True
except Exception:  # pragma: no cover
    ta = None
    HAVE_TA = False


def latest_cache_date(root: str = None) -> str:
    """Most recent data-cache dir (<= today UTC) that contains ohlcv_SPY.json."""
    root = root or CACHE_ROOT
    if not os.path.isdir(root):
        return None
    today = datetime.now(timezone.utc).date()
    for back in range(0, 12):
        d = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        if os.path.exists(os.path.join(root, d, "ohlcv_SPY.json")):
            return d
    return None


def find_cached_weekly_adx(week_date: str):
    """Read the weekly pipeline's recorded SPY weekly ADX14.

    Source: latest-weekly-summary.json -> spy_weekly_adx14.value, used only
    when summary.week_end == the requested week date (stale summaries must
    not gate a different week).
    Returns (value, source_desc) or (None, reason).
    """
    try:
        with open(WEEKLY_SUMMARY) as f:
            d = json.load(f)
        if d.get("week_end") != week_date:
            return None, (f"summary week_end {d.get('week_end')} != {week_date} "
                          f"(stale — not used)")
        adx = (d.get("spy_weekly_adx14") or {}).get("value")
        if adx is not None and float(adx) > 0:
            return float(adx), "latest-weekly-summary.json:spy_weekly_adx14.value"
        return None, "summary has no valid spy_weekly_adx14.value"
    except Exception as e:
        return None, f"summary unreadable: {e}"


def _ta_adx_cross_check(date: str, length: int):
    """NON-CANONICAL pandas_ta ta.adx on the same W-FRI bars (old get_regime
    smoothing). Returns (ta_value, diff_vs_canonical) using caller's canonical.
    """
    if not HAVE_TA:
        return None, None
    df = load_cache_ohlcv_df(date, ticker="SPY")
    if df.empty:
        return None, None
    wk = resample_weekly(df)
    try:
        adx_res = ta.adx(wk["High"], wk["Low"], wk["Close"], length=length)
        adx_col = [c for c in adx_res.columns if "ADX_" in c]
        if not adx_col:
            return None, None
        return float(adx_res[adx_col[0]].iloc[-1]), None
    except Exception:
        return None, None


def verify_weekly_spy_adx(date=None, cached_override=None,
                          length=DEFAULT_LENGTH, threshold=DEFAULT_THRESHOLD):
    """Compute canonical weekly SPY ADX and gate the pipeline/report value."""
    date = date or latest_cache_date()
    result = {
        "date": date,
        "length": length,
        "threshold": threshold,
        "canonical_adx": None,
        "prev_adx": None,
        "direction": None,
        "pipeline_adx": None,
        "pipeline_source": None,
        "diff_pipeline": None,
        "ta_adx": None,
        "diff_ta": None,
        "compare_mode": None,
        "flagged": False,
        "weekly_bars": 0,
        "note": None,
    }
    if result["date"] is None:
        result["note"] = "no SPY data cache found (<= today)"
        result["flagged"] = True
        return result

    res = weekly_adx_from_cache(result["date"], ticker="SPY", length=length)
    if res is None:
        result["note"] = (f"insufficient cache data for {result['date']} "
                          f"(need >= 2*{length}+1 weekly bars)")
        result["flagged"] = True
        return result

    result["canonical_adx"] = round(res["adx"], 2)
    result["prev_adx"] = None if res["prev_adx"] is None else round(res["prev_adx"], 2)
    result["direction"] = res["direction"]
    result["weekly_bars"] = res["weekly_bars"]

    # Informational: NON-CANONICAL pandas_ta ta.adx (old get_regime smoothing).
    ta_val, _ = _ta_adx_cross_check(result["date"], length)
    if ta_val is not None:
        result["ta_adx"] = round(ta_val, 2)
        result["diff_ta"] = round(abs(result["ta_adx"] - result["canonical_adx"]), 3)

    # Pipeline value: explicit --cached wins, else the weekly summary record.
    if cached_override is not None:
        cached = float(cached_override)
        result["pipeline_adx"] = round(cached, 2)
        result["pipeline_source"] = "pipeline-cached(override)"
    else:
        cached, src = find_cached_weekly_adx(result["date"])
        result["pipeline_source"] = src
        if cached is not None:
            result["pipeline_adx"] = round(float(cached), 2)

    if result["pipeline_adx"] is not None:
        result["compare_mode"] = "pipeline-record"
        pv = result["pipeline_adx"]
        if pv > 0:
            result["diff_pipeline"] = round(abs(pv - result["canonical_adx"]), 3)
            if result["diff_pipeline"] > threshold:
                result["flagged"] = True
        else:
            result["note"] = (f"pipeline ADX invalid ({pv}) — expected positive. "
                              "Do NOT trust a regime derived from it.")
            result["flagged"] = True
    else:
        # No pipeline record: fall back to the ta.adx regression detector —
        # exactly reproduces the W36 B1 divergence (18.93 vs 15.09 -> FLAG).
        if not HAVE_TA:
            result["note"] = ("pandas_ta unavailable and no pipeline record — "
                              "cannot complete the weekly ADX gate. Run under "
                              "the hermes venv (default python3).")
            result["flagged"] = True
            return result
        result["compare_mode"] = "ta.adx-fallback (no pipeline record)"
        if result["ta_adx"] is None:
            result["note"] = "ta.adx compute failed — cannot complete gate."
            result["flagged"] = True
            return result
        if result["diff_ta"] > threshold:
            result["flagged"] = True

    if result["note"] is None:
        if result["flagged"]:
            result["note"] = (f"FLAG — weekly SPY ADX diverges from canonical "
                              f"(compare_mode={result['compare_mode']})")
        else:
            result["note"] = ("OK — weekly SPY ADX within threshold "
                              f"(compare_mode={result['compare_mode']})")
    return result


def format_human(r: dict) -> str:
    lines = []
    lines.append(f"[VERIFY_WEEKLY_ADX] date={r['date']} weekly_bars={r['weekly_bars']} "
                 f"basis=data-cache W-FRI resample method=true-Wilder({r['length']})")
    if r["canonical_adx"] is None:
        lines.append(f"[VERIFY_WEEKLY_ADX] ERROR — {r.get('note', '')}")
        return "\n".join(lines)
    lines.append(f"[VERIFY_WEEKLY_ADX] canonical true-Wilder weekly ADX({r['length']}) "
                 f"= {r['canonical_adx']}  (prev {r['prev_adx']} -> {r['direction']})")
    if r["pipeline_adx"] is not None:
        lines.append(f"[VERIFY_WEEKLY_ADX] pipeline weekly ADX = {r['pipeline_adx']} "
                     f"({r['pipeline_source']})  |diff| = {r['diff_pipeline']}")
    if r["ta_adx"] is not None:
        lines.append(f"[VERIFY_WEEKLY_ADX] NON-CANONICAL pandas_ta ta.adx (old pipeline "
                     f"smoothing) = {r['ta_adx']}  |diff| = {r['diff_ta']}  "
                     f"threshold = {r['threshold']}  [informational]")
    if r["flagged"]:
        lines.append("[VERIFY_WEEKLY_ADX] ⚠️  FLAG — weekly SPY ADX diverges from "
                     "canonical true-Wilder. Do NOT publish this ADX without review.")
    else:
        lines.append("[VERIFY_WEEKLY_ADX] ✅ OK — weekly SPY ADX matches canonical "
                     "true-Wilder within threshold.")
    if r.get("note"):
        lines.append(f"[VERIFY_WEEKLY_ADX] note: {r['note']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Weekly SPY ADX pre-publish gate (W37)")
    ap.add_argument("--date", default=None,
                    help="Cache date key (YYYY-MM-DD, usually the report Friday). "
                         "Default: most recent cache <= today UTC.")
    ap.add_argument("--cached", default=None, type=float,
                    help="Pipeline weekly ADX value to compare (overrides the "
                         "latest-weekly-summary.json record).")
    ap.add_argument("--threshold", default=DEFAULT_THRESHOLD, type=float,
                    help="Flag threshold on |diff| (default 1.0).")
    ap.add_argument("--json", action="store_true",
                    help="Machine-readable JSON output.")
    args = ap.parse_args()

    r = verify_weekly_spy_adx(date=args.date, cached_override=args.cached,
                              threshold=args.threshold)
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print(format_human(r))
    if r["canonical_adx"] is None:
        return 2
    return 1 if r["flagged"] else 0


if __name__ == "__main__":
    sys.exit(main())
