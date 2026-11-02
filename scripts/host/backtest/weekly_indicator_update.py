#!/usr/bin/env python3
"""
 Indicator — market close .

:
1. optimal periods (JSON fallback → hardcoded defaults)
2. yfinance 96 
3. pandas_ta (optimal periods)
4. score_engine (5 sub-scores + total)
5. INSERT SQLite weekly_snapshots
6. DELETE 20 
7. summary + JSON

:
  python3 weekly_indicator_update.py # (Sat/Sun only)
  python3 weekly_indicator_update.py --force # ()
  python3 weekly_indicator_update.py --dry-run # ( DB)

: Cron Sunday 22:00 (no_agent=True)
"""

import importlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf

# ── ─────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_SCRIPTS = os.path.dirname(SCRIPT_DIR)  # ~/.hermes/scripts (adx_wilder home)
if HERMES_SCRIPTS not in sys.path:
    sys.path.insert(0, HERMES_SCRIPTS)
from adx_wilder import true_wilder_adx_series, weekly_adx_from_cache  # noqa: E402
SHARED_DIR = os.path.expanduser("~/.hermes/shared")
DATA_DIR = os.path.join(SHARED_DIR, "data")
REPORTS_DIR = os.path.join(SHARED_DIR, "reports", "renee", "trend-momentum")
DB_PATH = os.path.join(DATA_DIR, "renee_indicators.db")
OPTIMAL_PATH = os.path.expanduser(
    "~/.hermes/shared/reports/renee/backtest/2026-06-15-optimal_periods.json"
)

# ── Periods (fallback) ───────────────────────────────────
# Zoe B1 (2026-08-02): ADX period 7→14 — W31 breakthrough fix.
# Daily pipeline (daily_trend_momentum.py) uses ADX(14); weekly must match.
DEFAULT_OPTIMAL = {
    "macd": {"fast": 12, "slow": 34, "signal": 12},
    "rsi": 9,
    "ma": [10, 50, 200],
    "adx": 14,
    "volume": 5,
    "bb": {"period": 20, "std": 2},
}

# ── Stock Universe (94 tickers, NO ETFs) ────────────────────────────
STOCK_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "DIS", "NFLX",
    "PYPL", "ADBE", "CRM", "INTC", "AMD", "BA", "CAT", "XOM",
    "CVX", "KO", "PEP", "MRK", "ABBV", "PFE", "BAC", "MA",
    "COST", "NKE", "CSCO", "T", "VZ", "NEE", "LIN", "SCHW",
    "AXP", "GS", "BLK", "TMO", "LLY", "UNP", "HON", "RTX",
    "LOW", "SBUX", "IBM", "DUK", "SO", "ORCL", "QCOM", "TXN",
    "MU", "LRCX", "F", "GM", "CMG", "ABNB", "UBER",
    "SHOP", "PANW", "NOW", "PLTR", "HOOD", "SOFI", "MSTR",
    "COIN", "MCD", "MDLZ", "CL", "EL", "DE", "C", "WFC",
    "USB", "PNC", "TFC", "SPGI", "MCO", "VRTX", "GILD", "AMGN",
    "REGN", "BIIB", "ISRG", "BSX", "MDT", "ABT", "GE", "MMM",
]

# ── Persistent error recovery ──────────────────────────────────────
# Tickers that fail data fetch for N+ consecutive weeks get logged here.
# Use: check_errors / error log / manual review after 3 consecutive failures.
# Active persistent failures (as of 2026-06-27):
#   SQ — yfinance data fetch fails consistently (see error logs)
PERSISTENT_ERROR_TICKERS = {
    "SQ": "yfinance data fetch fails consistently — removed from STOCK_UNIVERSE on 2026-06-28",
}

# ── Universe config (Zoe W34 #4 / width-scan, t_0b957f77) ──────────
# STOCK_UNIVERSE above is the FALLBACK baseline. The live universe is read
# from universe_config.json (base_universe + width_scan_additions), written
# by width_scan.py --merge. Config-driven — no hardcoded list at runtime.
UNIVERSE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "universe_config.json")


def load_universe():
    """Load the full universe from universe_config.json.

    base_universe + width_scan_additions, deduped (ticker order preserved).
    Falls back to the hardcoded STOCK_UNIVERSE only if the config is missing
    or unreadable (backward compat).
    """
    try:
        with open(UNIVERSE_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        base = cfg.get("base_universe") or []
        additions = cfg.get("width_scan_additions") or []
        seen, out = set(), []
        for t in list(base) + list(additions):
            t = str(t).strip().upper().replace(".", "-")
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        if out:
            return out
    except (json.JSONDecodeError, IOError) as e:
        print(f"[⚠] universe config read failed ({e}) — fallback to STOCK_UNIVERSE")
    return list(STOCK_UNIVERSE)


# ── ─────────────────────────────────────────────────────────

def load_optimal_periods():
    """ optimal periods JSON,fallback hardcoded defaults."""
    if os.path.exists(OPTIMAL_PATH):
        try:
            with open(OPTIMAL_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            periods = {
                "macd": data["macd"]["optimal"],
                "rsi": data["rsi"]["optimal"],
                "ma": data["ma"]["optimal"],
                "adx": 14,  # Zoe B1 (2026-08-02): ADX 7→14 override — W31 breakthrough; matches daily pipeline
                "volume": data["volume"]["optimal"],
                "bb": {"period": 20, "std": 2}, # BB 
            }
            print(f"[ℹ] optimal periods {OPTIMAL_PATH}")
            return periods
        except (KeyError, json.JSONDecodeError, IOError) as e:
            print(f"[⚠] optimal periods ({e}),fallback defaults")
    else:
        print(f"[ℹ] {OPTIMAL_PATH} , hardcoded defaults")
    return dict(DEFAULT_OPTIMAL)


def get_week_end():
    """Return the most recent COMPLETE week's Saturday date string (YYYY-MM-DD).
    
    On Saturday/Sunday, the current week's data is incomplete — return the
    previous Saturday instead to avoid phantom future-dated snapshots.
    """
    today = datetime.now(timezone.utc)
    days_ahead = (5 - today.weekday()) % 7  # 0 if today is Saturday
    if days_ahead == 0:
        # Today is Saturday — week not complete, use previous Saturday
        saturday = today - timedelta(days=7)
    else:
        saturday = today - timedelta(days=7 - days_ahead)
    return saturday.strftime("%Y-%m-%d")


def weekly_spy_adx_true_wilder(spy_weekly, length: int = 14):
    """Canonical SPY weekly ADX(14) — TRUE WILDER method (adx_wilder.py /
    verify_adx.py `_rma`), W-FRI weekly bars.

    W36 B1 (Zoe REJECT 2026-09-06): get_regime() previously used pandas_ta
    `ta.adx` default smoothing -> 18.93 on the 09-04 basis vs canonical
    true-Wilder 15.09 (|diff| 3.84). ta.adx is NON-CANONICAL for the weekly
    SPY ADX — do NOT reintroduce it. Returns float or None.
    """
    try:
        adx_series = true_wilder_adx_series(
            spy_weekly["High"], spy_weekly["Low"], spy_weekly["Close"], length=length
        )
    except Exception:
        return None
    valid = adx_series.dropna()
    if valid.empty:
        return None
    return float(valid.iloc[-1])


def get_regime(spy_weekly):
    """
     — SPY ADX + VIX.
    Returns: 'trending' | 'ranging' | 'volatile'

    SPY ADX: canonical true-Wilder ADX(14) via weekly_spy_adx_true_wilder()
    (adx_wilder.py, same method as verify_adx.py). NOT pandas_ta ta.adx.
    Method + window annotated in the printed main() output.
    """
    # Fetch VIX
    try:
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="5d")
        vix_close = float(vix_data["Close"].iloc[-1]) if not vix_data.empty else 20.0
    except Exception:
        vix_close = 20.0

    # Calculate SPY ADX — canonical true-Wilder ADX(14) (W36 B1 fix; do NOT
    # revert to pandas_ta ta.adx default smoothing — non-canonical 18.93 vs
    # true 15.09 on the 09-04 basis).
    spy_adx = weekly_spy_adx_true_wilder(spy_weekly)
    if spy_adx is None:
        spy_adx = 20.0

    if spy_adx >= 30:
        return "trending"
    elif vix_close >= 25:
        return "volatile"
    else:
        return "ranging"


def should_run(force=False):
    """/, --force."""
    if force:
        return True
    today = datetime.now(timezone.utc)
    # Saturday=5, Sunday=6
    return today.weekday() in (5, 6)


def fetch_weekly_data(ticker, periods_needed=1500):
    """
     yfinance (5≈1500),resample .
     SMA200 ( ≈ 200).
     (df_weekly, success_bool).
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{periods_needed}d")
        if df.empty or len(df) < 200: # ~200 
            return None, False

        # Resample to weekly (end of week = Friday)
        weekly = df.resample("W-FRI").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        })
        weekly.dropna(inplace=True)
        # FIX 2026-09-01 (W35 catch-up): on weekday --force runs yfinance includes the
        # in-progress current week (label = next Friday, in the future). Drop trailing
        # partial buckets so week_end = last COMPLETED week (Friday trading date).
        today = datetime.now(timezone.utc).date()
        while len(weekly) > 0 and hasattr(weekly.index[-1], "date") and weekly.index[-1].date() > today:
            weekly = weekly.iloc[:-1]
        if len(weekly) < 20:
            return None, False
        return weekly, True
    except Exception as e:
        print(f"[⚠] {ticker}: yfinance — {e}")
        return None, False


def calc_indicators(weekly, opt):
    """
     pandas_ta , dict.
    :
      weekly: DataFrame with OHLCV columns
      opt: periods config dict
    :
      dict with raw indicator values, or None if insufficient data
    """
    if weekly is None or len(weekly) < max(opt["ma"][2], 20):
        return None

    close = weekly["Close"]
    high = weekly["High"]
    low = weekly["Low"]
    volume = weekly["Volume"]

    # ── RSI ──
    rsi_series = ta.rsi(close, length=opt["rsi"])
    rsi_val = rsi_series.iloc[-1] if rsi_series is not None else None

    # ── MACD ──
    macd_result = ta.macd(
        close,
        fast=opt["macd"]["fast"],
        slow=opt["macd"]["slow"],
        signal=opt["macd"]["signal"],
    )
    if macd_result is not None and len(macd_result.columns) >= 3:
        macd_col = [c for c in macd_result.columns if "MACD_" in c and "MACDh" not in c and "MACDs" not in c]
        macdh_col = [c for c in macd_result.columns if "MACDh" in c]
        macds_col = [c for c in macd_result.columns if "MACDs" in c]
        if macd_col and macdh_col and macds_col:
            macd_line = float(macd_result[macd_col[0]].iloc[-1])
            macd_hist = float(macd_result[macdh_col[0]].iloc[-1])
            macd_signal = float(macd_result[macds_col[0]].iloc[-1])
            macd_hist_series = macd_result[macdh_col[0]].tail(10).tolist()
        else:
            return None
    else:
        return None

    # ── SMA ──
    sma_periods = opt["ma"]  # [10, 50, 200]
    sma_series = ta.sma(close, length=sma_periods[2]) # SMA
    if sma_series is None:
        return None

    sma_short = float(ta.sma(close, length=sma_periods[0]).iloc[-1]) if len(close) >= sma_periods[0] else None
    sma_mid = float(ta.sma(close, length=sma_periods[1]).iloc[-1]) if len(close) >= sma_periods[1] else None
    sma_long = float(sma_series.iloc[-1]) if len(close) >= sma_periods[2] else None

    if any(v is None for v in (sma_short, sma_mid, sma_long)):
        return None

    # ── ADX ──
    adx_result = ta.adx(high, low, close, length=opt["adx"])
    if adx_result is not None:
        adx_col = [c for c in adx_result.columns if "ADX_" in c]
        dmp_col = [c for c in adx_result.columns if "DMP_" in c]
        dmn_col = [c for c in adx_result.columns if "DMN_" in c]
        adx_val = float(adx_result[adx_col[0]].iloc[-1]) if adx_col else None
        plus_di = float(adx_result[dmp_col[0]].iloc[-1]) if dmp_col else None
        minus_di = float(adx_result[dmn_col[0]].iloc[-1]) if dmn_col else None
    else:
        adx_val = plus_di = minus_di = None

    # ── Bollinger Bands ──
    bb_result = ta.bbands(close, length=opt["bb"]["period"], std=opt["bb"]["std"])
    if bb_result is not None and len(bb_result.columns) >= 3:
        bbu_col = [c for c in bb_result.columns if "BBU_" in c]
        bbm_col = [c for c in bb_result.columns if "BBM_" in c]
        bbl_col = [c for c in bb_result.columns if "BBL_" in c]
        if bbu_col and bbm_col and bbl_col:
            bb_upper = float(bb_result[bbu_col[0]].iloc[-1])
            bb_middle = float(bb_result[bbm_col[0]].iloc[-1])
            bb_lower = float(bb_result[bbl_col[0]].iloc[-1])
        else:
            bb_upper = bb_middle = bb_lower = None
    else:
        bb_upper = bb_middle = bb_lower = None

    # ── Volume ratio ──
    vol_period = opt["volume"]
    if len(volume) >= vol_period:
        avg_vol = volume.iloc[-vol_period:].mean()
        vol_ratio = float(volume.iloc[-1] / avg_vol) if avg_vol > 0 else 1.0
    else:
        vol_ratio = 1.0

    # ── OBV trend ──
    obv_series = ta.obv(close, volume)
    if obv_series is not None and len(obv_series) >= 5:
        obv_trend = 1 if obv_series.iloc[-1] > obv_series.iloc[-5] else (-1 if obv_series.iloc[-1] < obv_series.iloc[-5] else 0)
    else:
        obv_trend = 0

    # ── MFI (Money Flow Index) ──
    mfi_series = ta.mfi(high, low, close, volume, length=14)
    mfi_value = float(mfi_series.iloc[-1]) if mfi_series is not None and not mfi_series.empty else None

    # ── Price change (for OBV context) ──
    change_pct = float(close.pct_change().iloc[-1]) if len(close) >= 2 else 0.0

    return {
        "close_price": float(close.iloc[-1]) if close is not None and len(close) > 0 else None,
        "rsi": float(rsi_val) if rsi_val is not None else None,
        "macd_line": float(macd_line),
        "macd_hist": float(macd_hist),
        "macd_signal": float(macd_signal),
        "macd_hist_series": macd_hist_series,
        "sma_short": float(sma_short),
        "sma_mid": float(sma_mid),
        "sma_long": float(sma_long),
        "adx": float(adx_val) if adx_val is not None else None,
        "plus_di": float(plus_di) if plus_di is not None else None,
        "minus_di": float(minus_di) if minus_di is not None else None,
        "volume_ratio": vol_ratio,
        "obv_trend": obv_trend,
        "mfi_value": mfi_value,
        "change_pct": change_pct,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
    }


def insert_snapshot(conn, ticker, week_end, opt, raw, scores, total, regime="trending", dmi_direction="neutral"):
    """INSERT weekly_snapshots."""
    period_json = json.dumps(opt, ensure_ascii=False)
    conn.execute(
        """INSERT OR REPLACE INTO weekly_snapshots
        (ticker, week_end, period_config, rsi, macd_line, macd_signal, macd_hist,
         sma_short, sma_mid, sma_long, adx, plus_di, minus_di, volume_ratio, obv_trend,
         bb_upper, bb_middle, bb_lower, close_price,
         score_macd, score_rsi, score_ma, score_adx, score_volume, score_total,
         signal_bracket, signal_verdict, regime, dmi_direction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ticker,
            week_end,
            period_json,
            raw.get("rsi"),
            raw.get("macd_line"),
            raw.get("macd_signal"),
            raw.get("macd_hist"),
            raw.get("sma_short"),
            raw.get("sma_mid"),
            raw.get("sma_long"),
            raw.get("adx"),
            raw.get("plus_di"),
            raw.get("minus_di"),
            raw.get("volume_ratio"),
            raw.get("obv_trend"),
            raw.get("bb_upper"),
            raw.get("bb_middle"),
            raw.get("bb_lower"),
            raw.get("close_price"),
            scores["macd"],
            scores["rsi"],
            scores["ma"],
            scores["adx"],
            scores["volume"],
            total,
            scores.get("bracket"),
            scores.get("verdict"),
            regime,
            dmi_direction,
        ),
    )


def filter_new_discovery(scan_data: dict, week_end: str, max_age_days: int = 8) -> tuple[list, str]:
    """Keep width-scan discoveries only when the scan is inside the freshness window.

    ``scan_time`` (ISO) is compared to ``datetime.now(timezone.utc)``. Aware
    timestamps are converted to UTC; naive timestamps are treated as UTC.
    Age greater than ``max_age_days`` drops the list.     When ``scan_time`` is
    missing, discoveries are kept if ``scan_data["week_end"]`` is this run's
    ``week_end`` or exactly 7 days before it. Scores are not recomputed.
    Unusable input returns ``([], "stale_dropped")``.
    """
    if not isinstance(scan_data, dict):
        return [], "stale_dropped"
    discoveries = scan_data.get("discoveries", [])
    if not isinstance(discoveries, list):
        return [], "stale_dropped"

    raw_time = scan_data.get("scan_time")
    has_scan_time = raw_time is not None and str(raw_time).strip() != ""
    if has_scan_time:
        if not isinstance(raw_time, str):
            return [], "stale_dropped"
        text = raw_time.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            scanned = datetime.fromisoformat(text)
        except ValueError:
            return [], "stale_dropped"
        if scanned.tzinfo is None:
            scanned = scanned.replace(tzinfo=timezone.utc)
        else:
            scanned = scanned.astimezone(timezone.utc)
        age = datetime.now(timezone.utc) - scanned
        if age > timedelta(days=max_age_days):
            return [], "stale_dropped"
        return discoveries, "ok"

    scan_week = scan_data.get("week_end")
    if not isinstance(scan_week, str) or not isinstance(week_end, str):
        return [], "stale_dropped"
    try:
        scan_day = datetime.strptime(scan_week, "%Y-%m-%d").date()
        run_day = datetime.strptime(week_end, "%Y-%m-%d").date()
    except ValueError:
        return [], "stale_dropped"
    delta = run_day - scan_day
    if delta == timedelta(0) or delta == timedelta(days=7):
        return discoveries, "ok"
    return [], "stale_dropped"


# ── ───────────────────────────────────────────────────────────

def main():
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv

    if not should_run(force):
        print("[⏹] (Sat/Sun),skip. --force .")
        return 0

    week_end = get_week_end()
    print(f"📅 Week end: {week_end}")
    print(f"{'🧪 DRY RUN — DB' if dry_run else '🚀 '}")

 # 1. optimal periods
    opt = load_optimal_periods()

 # 2. score_engine + reload stale .pyc cache
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
    from backtest import score_engine as _se
    importlib.reload(_se)
    from backtest.score_engine import compute_all, get_signal_bracket, get_signal_verdict

 # 3. DB (WAL mode) + migration
    if not dry_run:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        # Migration: add new columns if not exist (idempotent)
        for col_def in [
            "plus_di REAL",
            "minus_di REAL",
            "obv_trend INTEGER",
            "regime TEXT DEFAULT 'trending'",
            "dmi_direction TEXT DEFAULT 'neutral'",
            "close_price REAL",
        ]:
            try:
                conn.execute(f"ALTER TABLE weekly_snapshots ADD COLUMN {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists
    else:
        conn = None

 # 4. 
    results = []
    errors = 0
    latest_friday = None
    regime = "trending"  # default
    # Per-ticker error tracking for persistent failures
    ticker_error_count = {}

 # fetch SPY 
    print(f"\n[🌍] (regime) ...")
    spy_weekly, spy_ok = fetch_weekly_data("SPY")
    spy_adx14 = None
    spy_adx_basis = "n/a"
    spy_adx_prev = None
    spy_adx_direction = None
    if spy_ok and spy_weekly is not None and len(spy_weekly) >= 20:
        regime = get_regime(spy_weekly)
        spy_adx14 = weekly_spy_adx_true_wilder(spy_weekly)
        spy_adx_basis = "W-FRI weekly bars (yfinance fetch)"
        # Prefer the CANONICAL cache basis when the Friday cache exists — the
        # same basis the weekly report cites (data as-of Friday cache) and the
        # basis verify_weekly_adx.py / weekly_report_gen.py gate against.
        try:
            last_date = spy_weekly.index[-1]
            friday = (last_date.strftime("%Y-%m-%d")
                      if hasattr(last_date, "strftime") else str(last_date.date()))
            cache_res = weekly_adx_from_cache(friday, ticker="SPY")
            if cache_res is not None:
                spy_adx14 = cache_res["adx"]
                spy_adx_basis = f"cache {friday} W-FRI (canonical report basis)"
                spy_adx_prev = cache_res["prev_adx"]
                spy_adx_direction = cache_res["direction"]
        except Exception:
            pass
    print(f" : {regime}")
    if spy_adx14 is not None:
        print(f"     SPY weekly ADX14 (true-Wilder) = {spy_adx14:.2f}  "
              f"[basis: {spy_adx_basis}; canonical per adx_wilder.py / verify_adx.py — "
              f"NOT pandas_ta ta.adx]")

    # Universe is config-driven (base_universe + width_scan_additions) — Zoe W34 #4
    universe = load_universe()
    print(f"📋 Universe: {len(universe)} tickers (config-driven, base + width-scan additions)")

    for i, ticker in enumerate(universe, 1):
        print(f"[{i:2d}/{len(universe)}] {ticker:5s} ... ", end="", flush=True)

        weekly, ok = fetch_weekly_data(ticker)
        if not ok or weekly is None:
            print("❌ skip (data error)")
            errors += 1
            # Track persistent errors
            ticker_error_count[ticker] = ticker_error_count.get(ticker, 0) + 1
            if ticker_error_count[ticker] >= 3 and ticker_error_count[ticker] % 3 == 0:
                note = PERSISTENT_ERROR_TICKERS.get(ticker, "no note")
                print(f"      ⚠️  {ticker} failed {ticker_error_count[ticker]}x consecutive. {note}")
            continue

 # latest Friday date
        if latest_friday is None:
            latest_friday = weekly.index[-1]  # last row date (Friday Timestamp)
            # Use the actual last trading day as week_end (not +1 day)
            # On Saturday/Sunday, this gives us Friday's date which is current
            week_end = latest_friday.strftime("%Y-%m-%d") if hasattr(latest_friday, 'strftime') else str(latest_friday.date())
            print(f"\n[📅] : {week_end}( {latest_friday.strftime('%Y-%m-%d') if hasattr(latest_friday, 'strftime') else latest_friday} Friday)")
            print(f"[{i:2d}/{len(universe)}] {ticker:5s} ... ", end="", flush=True)

        raw = calc_indicators(weekly, opt)
        if raw is None or raw["rsi"] is None or raw["adx"] is None:
            print("❌ skip (insufficient indicators)")
            errors += 1
            continue

 # period_config (ma list )
        period_config = {
            "macd": opt["macd"],
            "rsi": opt["rsi"],
            "ma": opt["ma"],
            "adx": opt["adx"],
            "volume": opt["volume"],
            "bb": opt["bb"],
        }
        raw["regime"] = regime  # for apply_regime_adjustment()
        scored = compute_all(raw, period_config)
        scores = scored["scores"]
        total = scored["total"]  # clipped published 0–100 → score_total
        weighted_total_raw = scored.get("weighted_total_raw", total)
        bracket = scored["bracket"]
        verdict = scored["verdict"]

        if not dry_run:
            insert_snapshot(
                conn, ticker, week_end, opt, raw, {
                    **scores,
                    "bracket": bracket,
                    "verdict": verdict,
                },
                total,
                regime=regime,
                dmi_direction=scored.get("dmi_direction", "neutral"),
            )

        results.append({
            "ticker": ticker,
            "scores": scores,
            "total": total,
            "base_5indicator_total": scored.get("base_5indicator_total", total),
            "weighted_total_raw": weighted_total_raw,
            "bracket": bracket,
            "verdict": verdict,
        })
        bracket_icon = "🟢" if total >= 60 else ("🟡" if total >= 50 else "⚪")
        print(f"✅ score={total:5.1f} {bracket_icon} {verdict}")

 # 5. DELETE 20 
    if not dry_run and conn:
        deleted = conn.execute(
            "DELETE FROM weekly_snapshots WHERE week_end < date('now', '-20 weeks', 'weekday 6')"
        ).rowcount
        conn.commit()
        print(f"\n[🗑] {deleted} 20 ")
    else:
        deleted = 0

 # 6. output
    print("\n" + "=" * 60)
    print(f"📊 Indicator — {week_end}")
    print("=" * 60)
    total_processed = len(results)
    total_errors = errors
    print(f" : {total_processed}/{len(universe)} tickers")
    print(f" : {total_errors}")
    # Persistent error summary
    persistent_fails = {t: c for t, c in ticker_error_count.items() if c >= 3}
    if persistent_fails:
        print(f"   ⚠️  Persistent failures (≥3x consecutive):")
        for t, c in sorted(persistent_fails.items()):
            note = PERSISTENT_ERROR_TICKERS.get(t, "")
            print(f"      {t}: {c}x consecutive{f' — {note}' if note else ''}")

 # 
    brackets = {">=90": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "<50": 0}
    for r in results:
        b = r["bracket"]
        brackets[b] = brackets.get(b, 0) + 1

    signals_60plus = sum(v for k, v in brackets.items() if k in (">=90", "80-89", "70-79", "60-69"))
    print(f"\n📈 (score ≥60 = BUY, 50-59 = MONITOR [W27 m1]): {signals_60plus}")
    for bracket_name, count in sorted(brackets.items()):
        bar = "█" * count if count <= 40 else "█" * 40 + f" ({count})"
        label = "MONITOR" if bracket_name == "50-59" else ("BUY" if bracket_name in (">=90","80-89","70-79","60-69") else "NO SIG")
        print(f"   {bracket_name:5s}: {count:3d}  {bar}  ({label})")

    # Top 5
    sorted_results = sorted(results, key=lambda x: x["total"], reverse=True)
    print(f"\n🏆 Top 5 Picks:")
    for r in sorted_results[:5]:
        s = r["scores"]
        print(
            f"   {r['ticker']:5s} — total={r['total']:5.1f} "
            f"(macd={s['macd']:5.1f} rsi={s['rsi']:5.1f} ma={s['ma']:5.1f} "
            f"adx={s['adx']:5.1f} vol={s['volume']:5.1f})"
        )

 # 7. summary JSON
    if not dry_run:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        # Width-scan new discoveries (Zoe W34 #4 / t_0b957f77) — read the latest
        # scan output written by width_scan.py. Structurally populated from now on.
        new_discovery = []
        new_discovery_status = None
        width_scan_meta = None
        scan_path = os.path.join(DATA_DIR, "width_scan_latest.json")
        if os.path.exists(scan_path):
            try:
                with open(scan_path, "r", encoding="utf-8") as _f:
                    scan_data = json.load(_f)
                new_discovery, new_discovery_status = filter_new_discovery(
                    scan_data, week_end
                )
                meta_src = scan_data if isinstance(scan_data, dict) else {}
                width_scan_meta = {
                    "scan_time": meta_src.get("scan_time"),
                    "week_end": meta_src.get("week_end"),
                    "source": meta_src.get("source"),
                    "stats": meta_src.get("stats"),
                }
            except Exception:
                pass

        # Load previous bracket history for rolling WR (Rubric #69)
        prev_summary = {}
        prev_path = os.path.join(REPORTS_DIR, "latest-weekly-summary.json")  # FIX 2026-08-08: was latest-summary.json (never written) → bracket_history never accumulated
        if os.path.exists(prev_path):
            try:
                with open(prev_path, "r", encoding="utf-8") as _f:
                    prev_summary = json.load(_f)
            except Exception:
                pass
        bracket_history = prev_summary.get("bracket_history", [])
        # FIX 2026-08-22: dedupe by week_end — a same-week re-run (e.g. W33 addendum
        # rerun) previously appended a duplicate entry, inflating rolling_4wk averages.
        # Strategy: append the new week, then collapse any week_end that appears more
        # than once to its LAST occurrence, then keep the last 4 weeks.
        bracket_history.append({
            "week_end": week_end,
            "brackets": brackets,
            "signals_60plus": signals_60plus,
        })
        seen = {}
        for w in bracket_history:
            seen[w.get("week_end")] = w  # last occurrence wins
        bracket_history = list(seen.values())
        # Keep last 4 weeks (stable order by insertion)
        bracket_history = bracket_history[-4:]
        
        summary = {
            "week_end": week_end,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_scanned": total_processed,
            "total_errors": total_errors,
            "signals_by_bracket": brackets,
            "signals_60plus": signals_60plus,
            "spy_weekly_adx14": {
                "value": round(spy_adx14, 2) if spy_adx14 is not None else None,
                "prev": round(spy_adx_prev, 2) if spy_adx_prev is not None else None,
                "direction": spy_adx_direction,
                "basis": spy_adx_basis,
                "method": "true-Wilder ADX14 on W-FRI weekly bars "
                          "(adx_wilder.py / verify_adx.py; NOT pandas_ta ta.adx)",
            },
            "bracket_history": bracket_history,
            "bracket_rolling_4wk": _calc_rolling_wr(bracket_history),
            "top_5_tickers_with_scores": [
                {
                    "ticker": r["ticker"],
                    "total": r["total"],
                    "base_5indicator_total": r.get("base_5indicator_total", r["total"]),
                    "weighted_total_raw": r.get("weighted_total_raw", r["total"]),
                    "scores": r["scores"],
                    "bracket": r["bracket"],
                    "verdict": r["verdict"],
                }
                for r in sorted_results[:5]
            ],
            "period_config_used": {
                "macd": opt["macd"],
                "rsi": opt["rsi"],
                "ma": opt["ma"],
                "adx": opt["adx"],
                "volume": opt["volume"],
                "bb": opt["bb"],
            },
            "new_discovery": new_discovery,
            "width_scan": width_scan_meta,
        }
        if new_discovery_status is not None:
            summary["new_discovery_status"] = new_discovery_status
        summary_path = os.path.join(REPORTS_DIR, "latest-weekly-summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n[💾] Summary : {summary_path}")

 # 8. 
    if conn:
        conn.close()

    print(f"\n{'=' * 60}")
    print(f"{'✅ DRY RUN ()' if dry_run else '✅ '}")
    print(f"{'=' * 60}")
    return 0


def _calc_rolling_wr(bracket_history: list) -> dict:
    """Calculate rolling 4-week win rate per bracket (Rubric #69)."""
    if not bracket_history:
        return {}
    rolling = {}
    for bracket_name in [">=90", "80-89", "70-79", "60-69", "50-59", "<50"]:
        counts = [w["brackets"].get(bracket_name, 0) for w in bracket_history]
        avg = sum(counts) / len(counts) if counts else 0
        rolling[bracket_name] = {
            "avg_count": round(avg, 1),
            "trend": "up" if len(counts) >= 2 and counts[-1] > counts[0] else (
                "down" if len(counts) >= 2 and counts[-1] < counts[0] else "flat"
            ),
        }
    return rolling


if __name__ == "__main__":
    sys.exit(main())
