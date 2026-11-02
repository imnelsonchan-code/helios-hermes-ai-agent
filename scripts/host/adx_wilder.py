#!/usr/bin/env python3
"""adx_wilder.py — canonical TRUE-WILDER ADX implementation (single source of truth).

Shared by:
  * verify_adx.py            — daily SPY ADX pre-publish gate (Zoe W32 rec #2)
  * weekly_indicator_update.py get_regime() — weekly SPY ADX regime (B1 fix, W37)
  * verify_weekly_adx.py     — weekly SPY ADX pre-publish gate (W37 generator fix)
  * weekly_report_gen.py     — W37+ weekly report dataset/§2 generator

WHY (incident history, keep appended):
  08-04: cached 20.8 vs true-Wilder 20.1 (diff 0.7)
  08-06: pipeline carried 23.2 (rolling-mean _adx) vs true-Wilder 21.7 (diff 1.5)
  08-07: cached 22.1 == true-Wilder 22.09 (match, no flag)
  W36 B1 (09-06, Zoe REJECT): weekly_indicator_update.get_regime() used
    pandas_ta ta.adx (default smoothing) -> 18.93 on W-FRI bars; canonical
    true-Wilder (this module) -> 15.09 on the 09-04 cache. ta.adx is
    NON-CANONICAL for the weekly report; weekly must use this module.

METHOD (matches Wilder's original; validated 2026-08-08 vs pandas_ta ta.adx):
  TR = max(high-low, |high-prevC|, |low-prevC|)
  +DM = up where up>dn & up>0 ; -DM = dn where dn>up & dn>0
  ATR = RMA(TR,14) ; +DI = 100*RMA(+DM)/ATR ; -DI = 100*RMA(-DM)/ATR
  DX  = 100*|+DI - -DI| / (+DI + -DI)
  ADX = RMA(DX,14)     (RMA seeded with SMA of the first 14 values after a
                        leading-NaN skip — see _rma)

BARS: pass W-FRI weekly bars for weekly checks (resample_weekly), daily bars
for daily checks. The window is ALWAYS annotated by callers.
"""
import json
import os

import numpy as np
import pandas as pd

DEFAULT_LENGTH = 14


# ══════════════════════════════════════════════════════════════════════
# True-Wilder ADX (manual, no pandas_ta)
# ══════════════════════════════════════════════════════════════════════
def _rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder's running moving average (RMA), seeded with the SMA of the
    first `length` values *after* the leading NaN (index 0 of a diff-based
    series). Matches pandas_ta's ta.adx behaviour (validated 2026-08-08).
    """
    out = series.copy()
    out.iloc[:] = np.nan
    if len(series) < length:
        return out
    # Skip a leading NaN (e.g. first diff of a diff-series) — seed from 1..length.
    seed_vals = series.iloc[1:length + 1]
    seed_vals = seed_vals.dropna()
    if seed_vals.empty:
        return out
    seed = float(seed_vals.mean())
    out.iloc[length] = seed
    for i in range(length + 1, len(series)):
        out.iloc[i] = (out.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
    return out


def true_wilder_adx_series(high, low, close, length: int = 14) -> pd.Series:
    """Return full ADX series using true Wilder smoothing (matches ta.adx)."""
    high = high.astype(float)
    low = low.astype(float)
    close = close.astype(float)

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)

    up = high.diff()
    dn = -low.diff()

    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=high.index)

    atr = _rma(tr, length)
    plus_di = 100.0 * _rma(plus_dm, length) / atr.replace(0, np.nan)
    minus_di = 100.0 * _rma(minus_dm, length) / atr.replace(0, np.nan)

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum

    adx = _rma(dx, length)
    return adx


def true_wilder_adx_value(high, low, close, length: int = 14) -> float:
    """Latest true-Wilder ADX value, or NaN if insufficient data."""
    adx = true_wilder_adx_series(high, low, close, length=length)
    valid = adx.dropna()
    if valid.empty:
        return float("nan")
    return float(valid.iloc[-1])


# ══════════════════════════════════════════════════════════════════════
# Bar preparation helpers
# ══════════════════════════════════════════════════════════════════════
def resample_weekly(df: pd.DataFrame, freq: str = "W-FRI") -> pd.DataFrame:
    """Aggregate a DAILY OHLCV DataFrame to weekly bars with the pipeline's
    W-FRI convention (week labelled by its Friday; same as
    weekly_indicator_update.fetch_weekly_data).

    Accepts either Open/High/Low/Close/Volume (weekly pipeline) or
    open/high/low/close/volume (data-cache) column casing. Drops NaN rows
    before and after resampling (leading all-NaN stub bars are removed —
    e.g. QCOM/LIN/HD 2025-09-04 cache stub).

    Returns a DataFrame with columns Open/High/Low/Close/Volume.
    """
    if df is None or df.empty:
        raise ValueError("resample_weekly: empty df")
    cols = {}
    for lower, upper in (("open", "Open"), ("high", "High"), ("low", "Low"),
                         ("close", "Close"), ("volume", "Volume")):
        if upper in df.columns:
            cols[upper] = df[upper]
        elif lower in df.columns:
            cols[upper] = df[lower]
        else:
            raise KeyError(f"resample_weekly: missing column {upper!r}/{lower!r}")
    wk = pd.DataFrame(cols)
    # Drop NaN rows (non-trading days / incomplete bars) — mirrors daily
    # pipeline calc_atr14_from_df dropna(subset=[Close,High,Low,Volume]).
    wk = wk.dropna(subset=["Close", "High", "Low", "Volume"])
    agg = wk.resample(freq).agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum",
    })
    agg = agg.dropna(subset=["Close", "High", "Low", "Volume"])
    agg.index.name = "date"
    return agg


CACHE_ROOT = os.path.expanduser("~/.hermes/shared/data-cache")


def load_cache_ohlcv_df(date_key: str, ticker: str = "SPY",
                        root: str = None) -> pd.DataFrame:
    """Load an OHLCV daily cache file as a DataFrame (columns
    open/high/low/close/volume lowercase, UTC DatetimeIndex).

    Returns an empty DataFrame when the cache file is missing/unreadable.
    """
    root = root or CACHE_ROOT
    path = os.path.join(root, date_key, f"ohlcv_{ticker}.json")
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        with open(path) as f:
            data = json.load(f)
        ohlcv = (data or {}).get("ohlcv") or []
        df = pd.DataFrame(ohlcv)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
        df = df.set_index("date")
        df = df[["open", "high", "low", "close", "volume"]]
        return df.sort_index()
    except Exception:
        return pd.DataFrame()


def weekly_adx_from_cache(date_key: str, ticker: str = "SPY", length: int = 14,
                          root: str = None, min_weekly_bars: int = None):
    """Canonical true-Wilder weekly ADX(14) from the daily data cache.

    Resamples daily OHLCV to W-FRI weekly bars (pipeline convention), computes
    the FULL true-Wilder ADX series and returns the last two values (for
    same-basis direction). This is the canonical weekly SPY ADX the weekly
    report header must use (W36 B1: cache 09-04 basis -> 15.09, prev 15.46).

    Returns dict or None when cache/data insufficient.
    """
    if min_weekly_bars is None:
        min_weekly_bars = 2 * length + 1
    df = load_cache_ohlcv_df(date_key, ticker, root=root)
    if df.empty or len(df) < 60:  # ~3 months of daily bars minimum
        return None
    wk = resample_weekly(df)
    if len(wk) < min_weekly_bars:
        return None
    adx = true_wilder_adx_series(wk["High"], wk["Low"], wk["Close"], length=length)
    valid = adx.dropna()
    if valid.empty:
        return None
    last = float(valid.iloc[-1])
    prev = float(valid.iloc[-2]) if len(valid) >= 2 else None
    return {
        "date_key": date_key,
        "ticker": ticker,
        "length": length,
        "daily_bars": int(len(df)),
        "weekly_bars": int(len(wk)),
        "adx": last,
        "prev_adx": prev,
        "direction": None if prev is None else ("UP" if last > prev else "DOWN"),
        "method": f"true-Wilder ADX({length}) on W-FRI weekly bars (adx_wilder.py)",
        "basis": f"cache {date_key} daily OHLCV resampled W-FRI",
    }
