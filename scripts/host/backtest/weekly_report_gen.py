#!/usr/bin/env python3
"""weekly_report_gen.py — W37+ weekly T&M report dataset + data-table generator.

Generator-layer fix for the W36 Zoe REJECT (t_0386a1a6, follow-up
t_f1230df9): the W35/W36 M1 (Risk%/ATR14% dual columns) and B1 (weekly SPY
ADX true-Wilder) fixes were only applied to the REPORT, so the generators
could regress. This module is the durable code path for the W37+ weekly
draft: dataset assembly (DB weekly_snapshots + shared daily cache) and the
DATA-DRIVEN markdown blocks (§2 ranking table with Risk% + ATR14%, §5 width
additions with DB-derived counts). Narrative sections are authored around the
printed numbers — never hand-written inside the data tables.

WHAT IT PRODUCES
  1. <week>-dataset.json — one record per DB row (score/verdict/raw from
     weekly_snapshots; entry/SL/TP from Wilder ATR14 on the daily cache),
     plus SPY weekly ADX14 canonical (true-Wilder W-FRI) and DB-derived
     width-addition counts.
  2. §2 ranking table markdown (Risk% + ATR14% dual columns) — the W35 M3 /
     W36 M1 format, from code.
  3. §5 width-addition table markdown + DB-derived counts (m1: additions
     >=60 text must derive from DB, not a hardcoded string).

KEY INVARIANTS (keep when editing)
  * ATR14: pure-Wilder RMA14; bars cleaned with dropna semantics equal to the
    daily pipeline calc_atr14_from_df (drop rows where Close/High/Low/Volume
    is None or NaN) — QCOM/LIN/HD 2025-09-04 leading NaN stub must NOT poison.
  * Risk%   = (Entry - SL) / Entry x 100      (stop distance)
  * ATR14%  = ATR14 / Close x 100             (true volatility)
  * SPY weekly ADX14: canonical true-Wilder on W-FRI weekly bars resampled
    from the daily SPY cache (adx_wilder.weekly_adx_from_cache). pandas_ta
    ta.adx is NON-CANONICAL for this figure (W36 B1: 18.93 vs 15.09).
  * Width-addition >=60 counts come from DB score_total, never hardcoded.

USAGE
  python3 weekly_report_gen.py --week 2026-09-04 --cache-dir <dir> --out <dir>
  # cache-dir: dir holding ohlcv_<TICKER>.json for the universe tickers
  # (shared ~/.hermes/shared/data-cache/<week> plus backfilled additions,
  # same convention as the W36 workspace-local cache). When omitted, the
  # shared data-cache/<week> is used and missing tickers are reported, not
  # fetched (deterministic run; backfill is a separate explicit step).

OUTPUT PRINTS (used by the report narrative; treat as authoritative)
  SPY weekly ADX14 canonical / signals >=60 / additions >=60 / nan rows fixed
"""
import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# ── paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))       # .../backtest
HERMES_SCRIPTS = os.path.dirname(SCRIPT_DIR)                  # ~/.hermes/scripts
if HERMES_SCRIPTS not in sys.path:
    sys.path.insert(0, HERMES_SCRIPTS)
from adx_wilder import weekly_adx_from_cache, load_cache_ohlcv_df, resample_weekly  # noqa: E402

DB_PATH = os.path.expanduser("~/.hermes/shared/data/renee_indicators.db")
SHARED_CACHE_ROOT = os.path.expanduser("~/.hermes/shared/data-cache")
UNIVERSE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "universe_config.json")
META_PATH = os.path.join(SCRIPT_DIR, "ticker_meta.json")
REPORTS_DIR = os.path.expanduser(
    "~/.hermes/shared/reports/renee/trend-momentum")

BRACKET_ORDER = [">=90", "80-89", "70-79", "60-69", "50-59", "<50"]

# pandas_ta ta.adx informational cross-check (NON-canonical weekly smoothing)
try:
    import pandas_ta as ta
    HAVE_TA = True
except Exception:  # pragma: no cover
    ta = None
    HAVE_TA = False


# ══════════════════════════════════════════════════════════════════════
# Metadata (company/sector) — durable ticker_meta.json seeded from W36
# ══════════════════════════════════════════════════════════════════════
def load_meta():
    try:
        with open(META_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def meta_for(meta, ticker):
    m = meta.get(ticker)
    if m:
        return m.get("company") or ticker, m.get("sector") or "Unknown"
    return ticker, "Unknown"


# ══════════════════════════════════════════════════════════════════════
# Wilder ATR14 helpers (pure python; dropna-consistent with daily pipeline
# calc_atr14_from_df — daily_trend_momentum.py L985-986)
# ══════════════════════════════════════════════════════════════════════
def _rma_series(values, length):
    arr = list(values)
    if len(arr) < length + 1:
        return arr
    alpha = 1.0 / length
    out = [sum(arr[:length]) / length]
    for v in arr[length:]:
        out.append((v - out[-1]) * alpha + out[-1])
    return out


def atr_wilder(rows, length=14):
    trs = []
    prev_close = None
    for r in rows:
        h, l, c = r["high"], r["low"], r["close"]
        if prev_close is None:
            trs.append(h - l)
        else:
            trs.append(max(h - l, abs(h - prev_close), abs(l - prev_close)))
        prev_close = c
    rma = _rma_series(trs, length)
    return rma[-1] if rma else None


def _is_bad(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def load_clean_ohlcv(cache_dir, ticker):
    """Load daily OHLCV dropping NaN/None rows (Close/High/Low/Volume)."""
    p = os.path.join(cache_dir, f"ohlcv_{ticker}.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            data = json.load(f).get("ohlcv") or []
    except Exception:
        return None
    out = []
    for r in data:
        if any(_is_bad(r.get(k)) for k in ("high", "low", "close", "volume")):
            continue
        out.append(r)
    return out if out else None


def entry_sl_tp(close, atr):
    """Single-point entry ladder (Renee methodology): entry = close+0.5ATR,
    SL = entry-0.75ATR, TP1 = entry+1.5ATR. Risk% = (entry-sl)/entry x 100,
    ATR14% = atr/close x 100."""
    if not atr or atr <= 0 or not close or close <= 0:
        return None
    entry = close + 0.5 * atr
    sl = entry - 0.75 * atr
    tp = entry + 1.5 * atr
    risk = entry - sl
    reward = tp - entry
    return {
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "atr14": round(atr, 2),
        "risk_pct": round(risk / entry * 100, 2),
        "atr14_pct": round(atr / close * 100, 2),
        "rr": round(reward / risk, 2) if risk > 0 else 0,
        "close": round(close, 2),
    }


# ══════════════════════════════════════════════════════════════════════
# Dataset assembly
# ══════════════════════════════════════════════════════════════════════
def load_universe():
    try:
        with open(UNIVERSE_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        base = cfg.get("base_universe") or []
        adds = cfg.get("width_scan_additions") or []
        return base, adds
    except Exception:
        return [], []


def ta_adx_weekly_noncache(date_key):
    """NON-canonical pandas_ta ta.adx on W-FRI bars (informational only)."""
    if not HAVE_TA:
        return None
    df = load_cache_ohlcv_df(date_key, ticker="SPY")
    if df.empty:
        return None
    wk = resample_weekly(df)
    try:
        res = ta.adx(wk["High"], wk["Low"], wk["Close"], length=14)
        col = [c for c in res.columns if "ADX_" in c]
        return float(res[col[0]].iloc[-1]) if col else None
    except Exception:
        return None


def build_dataset(week, cache_dir, out_path=None):
    """Assemble the W37+ weekly dataset from DB + cache. Returns dict."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    db_rows = cur.execute(
        "SELECT * FROM weekly_snapshots WHERE week_end=? ORDER BY score_total DESC",
        (week,)).fetchall()
    con.close()
    if not db_rows:
        raise SystemExit(f"[✗] no weekly_snapshots rows for week_end={week}")

    meta = load_meta()
    base, adds = load_universe()
    add_set = {str(t).upper().replace(".", "-") for t in adds}

    rows = []
    missing_entry = []
    nan_rows_fixed = []
    for r in db_rows:
        t = r["ticker"]
        company, sector = meta_for(meta, t)
        ohlcv = load_clean_ohlcv(cache_dir, t)
        es = None
        if ohlcv:
            close = ohlcv[-1]["close"]
            atr = atr_wilder(ohlcv)
            es = entry_sl_tp(close, atr)
        raw = {
            "rsi": r["rsi"],
            "adx": r["adx"],
            "plus_di": r["plus_di"],
            "minus_di": r["minus_di"],
            "volume_ratio": r["volume_ratio"],
            "close_price": r["close_price"],
        }
        entry_block = None
        if es is None:
            missing_entry.append(t)
        else:
            entry_block = es
            # Detect a leading NaN stub row that was dropped (QCOM/LIN/HD
            # 2025-09-04 cache signature) so the report can disclose the fix.
            p = os.path.join(cache_dir, f"ohlcv_{t}.json")
            if os.path.exists(p):
                try:
                    with open(p) as f:
                        full = json.load(f).get("ohlcv") or []
                    if full and any(_is_bad(full[0].get(k))
                                    for k in ("high", "low", "close", "volume")):
                        nan_rows_fixed.append(t)
                except Exception:
                    pass
        rows.append({
            "ticker": t,
            "company": company,
            "sector": sector,
            "score_total": r["score_total"],
            "bracket": r["signal_bracket"],
            "verdict": r["signal_verdict"],
            "dmi_direction": r["dmi_direction"],
            "scores": {
                "macd": r["score_macd"], "rsi": r["score_rsi"],
                "ma": r["score_ma"], "adx": r["score_adx"],
                "volume": r["score_volume"],
            },
            "raw": raw,
            "entry": entry_block,
        })

    # DB-derived signal counts
    brackets = {k: 0 for k in BRACKET_ORDER}
    for r in rows:
        brackets[r["bracket"]] = brackets.get(r["bracket"], 0) + 1
    ge60 = sum(v for k, v in brackets.items()
               if k in (">=90", "80-89", "70-79", "60-69"))
    add_rows = [r for r in rows if r["ticker"] in add_set]
    adds_ge60 = sum(1 for r in add_rows if (r["score_total"] or 0) >= 60)

    # Canonical SPY weekly ADX14 (true-Wilder, W-FRI from cache) + report gate
    spy_adx = weekly_adx_from_cache(week, ticker="SPY", root=SHARED_CACHE_ROOT)
    spy_block = None
    if spy_adx is not None:
        spy_block = {
            "value": round(spy_adx["adx"], 2),
            "prev": None if spy_adx["prev_adx"] is None
                    else round(spy_adx["prev_adx"], 2),
            "direction": spy_adx["direction"],
            "weekly_bars": spy_adx["weekly_bars"],
            "method": spy_adx["method"],
            "basis": spy_adx["basis"],
        }
        ta_v = ta_adx_weekly_noncache(week)
        spy_block["ta_adx_noncache"] = None if ta_v is None else round(ta_v, 2)
        if spy_block["ta_adx_noncache"] is not None:
            spy_block["diff_ta_vs_canonical"] = round(
                abs(spy_block["ta_adx_noncache"] - spy_block["value"]), 3)
        else:
            spy_block["diff_ta_vs_canonical"] = None

    ds = {
        "week": week,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "weekly_report_gen.py (W37 generator-layer fix)",
        "universe": {
            "base_count": len(base),
            "additions_count": len(adds),
            "db_rows": len(rows),
        },
        "spy_weekly_adx14": spy_block,
        "signals": {"brackets": brackets, "ge60": ge60},
        "width_additions": {
            "tickers": sorted(add_set),
            "db_present": len(add_rows),
            "ge60": adds_ge60,
        },
        "missing_entry": sorted(missing_entry),
        "nan_stub_rows_fixed": sorted(set(nan_rows_fixed)),
        "rows": rows,
    }

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(ds, f, ensure_ascii=False)
        print(f"WROTE {out_path}")

    # Narrative-authoritative prints
    print(f"week={week} db_rows={len(rows)} base={len(base)} additions={len(adds)}")
    print(f"signals ge60={ge60} brackets={brackets}")
    print(f"width additions present={len(add_rows)} ge60={adds_ge60} "
          f"(total {len(adds)})")
    if ds["missing_entry"]:
        print(f"⚠️ missing entry rows: {ds['missing_entry']}")
    print(f"nan stub rows fixed: {ds['nan_stub_rows_fixed']}")
    if spy_block:
        print(f"SPY weekly ADX14 canonical={spy_block['value']} "
              f"prev={spy_block['prev']} dir={spy_block['direction']} "
              f"(weekly_bars={spy_block['weekly_bars']})")
        if spy_block.get("ta_adx_noncache"):
            print(f"  [informational] ta.adx (non-canonical)="
                  f"{spy_block['ta_adx_noncache']} diff="
                  f"{spy_block['diff_ta_vs_canonical']}")
    return ds


# ══════════════════════════════════════════════════════════════════════
# Renderers (data-driven markdown blocks)
# ══════════════════════════════════════════════════════════════════════
def _sig_label(v):
    if v == "BUY":
        return "🟢 BUY"
    if v == "BUY (bullish trend)":
        return "🟢 BUY↑"
    if v == "WATCH (bearish trend)":
        return "👀 WATCH↓"
    if v == "WATCH (bullish trend)":
        return "👀 WATCH↑"
    return "❌ NO SIGNAL"


def _f2(v):
    return f"{v:.2f}" if isinstance(v, (int, float)) and not _is_bad(v) else "N/A"


def _pct1(v):
    return f"{v:.1f}%" if isinstance(v, (int, float)) and not _is_bad(v) else "N/A"


def _rr(v):
    return f"{v:.1f}" if isinstance(v, (int, float)) and not _is_bad(v) else "N/A"


def render_section2(rows):
    """§2 full ranking table — Risk% + ATR14% dual columns (W35 M3 / W36 M1)."""
    L = []
    L.append("| # | Ticker | Company | Sector | Score | Signal | Entry $ | TP1 $ | SL $ | R:R | Risk% | ATR14% |")
    L.append("|:-:|:------:|---------|--------|:-----:|:------:|:-------:|:-----:|:----:|:---:|:----:|:------:|")
    for i, r in enumerate(rows, 1):
        e = r.get("entry") or {}
        co = (r.get("company") or r["ticker"]).replace("|", "/")
        sec = (r.get("sector") or "Unknown").replace("|", "/")
        L.append(f"| {i} | {r['ticker']} | {co} | {sec} | "
                 f"**{r['score_total']:.1f}** | {_sig_label(r['verdict'])} | "
                 f"{_f2(e.get('entry'))} | {_f2(e.get('tp'))} | {_f2(e.get('sl'))} | "
                 f"{_rr(e.get('rr'))} | {_pct1(e.get('risk_pct'))} | "
                 f"{_pct1(e.get('atr14_pct'))} |")
    return "\n".join(L)


def render_additions_block(ds):
    """§5 width-addition table with DB-derived counts (m1 fix)."""
    add_set = set(ds["width_additions"]["tickers"])
    rows = [r for r in ds["rows"] if r["ticker"] in add_set]
    rows = sorted(rows, key=lambda r: -(r["score_total"] or 0))
    L = []
    L.append("| Ticker | Company | Sector | Score | Verdict | ADX | RSI | Vol Ratio |")
    L.append("|--------|---------|--------|:-----:|:-------:|:---:|:---:|:---------:|")
    for r in rows:
        raw = r["raw"]
        entry = r.get("entry")
        # Missing entry: say the plan was attempted and missed. Do not invent
        # Entry/TP/SL or ATR14. Rows that already have an entry block keep
        # the current columns, including the scored verdict.
        if not entry:
            verdict = "attempted + miss"
        else:
            verdict = _sig_label(r["verdict"])
        L.append(f"| {r['ticker']} | {r['company']} | {r['sector']} | "
                 f"{r['score_total']:.1f} | {verdict} | "
                 f"{raw.get('adx')} | {raw.get('rsi')} | {raw.get('volume_ratio')}x |")
    ge60 = ds["width_additions"]["ge60"]
    total = ds["width_additions"]["tickers"]
    ge60_tickers = [r["ticker"] for r in rows if (r["score_total"] or 0) >= 60]
    below = [r["ticker"] for r in rows if (r["score_total"] or 0) < 60]
    stat = (f"DB-derived: {ge60}/{len(total)} width additions >=60 "
            f"(ge60={sorted(ge60_tickers)}; below60={sorted(below)})")
    return "\n".join(L), stat


def main():
    ap = argparse.ArgumentParser(description="W37+ weekly T&M dataset generator")
    ap.add_argument("--week", required=True,
                    help="Week end date key (YYYY-MM-DD, Friday; matches "
                         "weekly_snapshots.week_end and data-cache dir).")
    ap.add_argument("--cache-dir", default=None,
                    help="Dir holding ohlcv_<TICKER>.json for the universe. "
                         "Default: shared data-cache/<week>.")
    ap.add_argument("--out", default=None,
                    help="Output dataset JSON path. Default: "
                         "shared reports/trend-momentum/<week>-dataset.json")
    args = ap.parse_args()

    cache_dir = args.cache_dir or os.path.join(SHARED_CACHE_ROOT, args.week)
    if not os.path.isdir(cache_dir):
        raise SystemExit(f"[✗] cache dir not found: {cache_dir}")
    out = args.out or os.path.join(REPORTS_DIR, f"{args.week}-dataset.json")
    ds = build_dataset(args.week, cache_dir, out_path=out)

    print("\n" + "=" * 60)
    print(f"§2 table rows: {len(ds['rows'])}")
    print(render_section2(ds["rows"][:3]))  # sample
    print("...")
    adds_md, stat = render_additions_block(ds)
    print("§5 additions stat:", stat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
