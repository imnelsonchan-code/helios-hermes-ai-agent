#!/usr/bin/env python3
"""Daily Trend & Momentum Report — 2026-06-18 (Thursday)
Watchlist only scoring with all modifiers + comparison to previous day."""

import argparse, hashlib, importlib, json, os, shutil, sys, math, sqlite3
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

# ══════════════════════════════════════════════════════════════════════
# Pure-pandas indicator implementations (pandas_ta unavailable on py3.11)
# ══════════════════════════════════════════════════════════════════════
def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_g = gain.rolling(period).mean()
    avg_l = loss.rolling(period).mean()
    rs = avg_g / avg_l.replace(0, 0.001)
    return 100.0 - (100.0 / (1.0 + rs))

def _sma(series, period):
    return series.rolling(period).mean()

def _ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def _macd(close, fast=12, slow=26, signal=9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    macd_signal = _ema(macd_line, signal)
    macd_hist = macd_line - macd_signal
    out = pd.DataFrame({
        f"MACD_{fast}_{slow}_{signal}": macd_line,
        f"MACDh_{fast}_{slow}_{signal}": macd_hist,
        f"MACDs_{fast}_{slow}_{signal}": macd_signal,
    })
    return out

def _rma(series, length):
    """Wilder's running moving average (RMA), seeded with the SMA of the
    first `length` values *after* the leading NaN. Matches pandas_ta ta.adx
    (validated 0.0000 diff on 1y, 2026-08-08 — see verify_adx.py)."""
    out = series.copy()
    out.iloc[:] = np.nan
    if len(series) < length:
        return out
    seed_vals = series.iloc[1:length + 1]
    seed_vals = seed_vals.dropna()
    if seed_vals.empty:
        return out
    seed = float(seed_vals.mean())
    out.iloc[length] = seed
    for i in range(length + 1, len(series)):
        out.iloc[i] = (out.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
    return out

def _adx(high, low, close, length=14):
    """True-Wilder ADX(14) + DMP/DMN (RMA smoothing).

    REFACTORED 2026-08-09 (t_3f881e2e, W32 B1 follow-up): previously used
    rolling-mean (SMA) smoothing, producing inflated ADX (SPY 25.2 on 08-07
    vs true-Wilder 22.1). Now matches pandas_ta ta.adx / verify_adx.py, so
    per-stock daily ADX is consistent with the weekly pandas_ta ADX(14).
    """
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

    adx_val = _rma(dx, length)

    out = pd.DataFrame({
        f"ADX_{length}": adx_val,
        f"DMP_{length}": plus_di,
        f"DMN_{length}": minus_di,
    })
    return out

def _atr(high, low, close, length=14):
    """True-Wilder ATR(14) (RMA smoothing).

    REFACTORED 2026-08-09 (t_40a88ab7): previously used SMA smoothing
    (tr.rolling(length).mean()), producing ATR14 divergence of -2.8% to +7.4%
    vs pandas_ta ta.atr (measured on 08-07 cache: SPY 9.131 vs 8.877, AAPL
    -4.2%, PANW +4.9%, JPM +6.5%). Now uses the same `_rma` helper as `_adx()`,
    matching pandas_ta ta.atr / verify_adx.py (0.0000 diff verified). Keeps
    Series return shape so callers (calc_atr14_from_df) are unchanged.
    """
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return _rma(tr, length)

def _obv(close, volume):
    return (volume * (close.diff() > 0).astype(int) - volume * (close.diff() < 0).astype(int)).cumsum()

def _mfi(high, low, close, volume, length=14):
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    direction = (tp.diff() > 0).astype(int)
    pos_mf = raw_mf * direction
    neg_mf = raw_mf * (1 - direction)
    mr = pos_mf.rolling(length).sum() / neg_mf.rolling(length).sum().replace(0, np.nan)
    mfi_s = 100 - (100 / (1 + mr))
    return mfi_s
# ══════════════════════════════════════════════════════════════════════

SCRIPT_DIR = os.path.expanduser("~/.hermes/scripts")
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "backtest"))

from score_engine import compute_all, get_signal_bracket, get_signal_verdict
from daily_data_cache import get_vix, get_spy_adx, get_run_id, get_or_fetch_info, get_or_fetch_batch_ohlcv, CACHE_ROOT
from pipeline_guard import guard_daily_report_generation, guard_report_generation

# 1.0.1 (t_b5acc944, Zoe 09-01): market-close guard in freshness watchdog +
# data.json float rounding (1/2/4dp key-aware) + rolling-WR live-resolve
# breakdown footnote + RSI oversold design Signal Legend + --date/--note/
# --refresh CLI for post-close regeneration.
# 1.0.2 (t_7915ddcc, Zoe 09-02): technical_screen Rule 5 volatility-floor
# hysteresis (admit 2.0% / retain incumbent 1.8% — PFE 1.987% knife-edge
# flicker) + screen-failure cause disclosure in the universe-change note +
# near-miss/hysteresis notes + header label "Daily (Watchlist + Screen-Pass)"
# with universe composition + single-stock material-move standard
# (|1D%| >= 5.0%, ranking flag + Key Ticker Notes table) + gold header
# explicit GC=F level / GLD 1D% reference labels.
# 1.0.3 (t_8cd84165, Zoe 09-03 M1/m1/m2): 
#   M1 (Option B — Renee methodology decision): T&M report ATR SL is a
#     SEPARATE single-point-entry methodology (Entry = Close + 0.5×ATR14
#     trigger; SL = Entry − 0.75×ATR14 = 0.75-ATR risk from the trigger point;
#     mathematically lands at Close − 0.25×ATR14). NOT the technical-snapshot
#     zone-floor construction (floor − 1×ATR, zone-midpoint R:R). Section 2
#     header now carries an explicit basis note so readers never compare SL /
#     R:R across the two products. Formula unchanged.
#   m1: bond context header source label fixed — data is Treasury.gov H.15
#     daily yield curve (fred_data.py Treasury XML), NOT FRED DGS2. Label now
#     "(Treasury H.15, <date>)" + DGS2 prev-day lag reference (rubric #77
#     canonical = FRED DGS2; same underlying series, FRED republishes T+1).
#     data.json bond_context gains a "source" field (self-describing).
#   m2: gold 🔴 material-move threshold standardized as a named constant
#     (GOLD_MATERIAL_MOVE_PCT = 1.5, symmetric with daily-social §9 trigger)
#     and emitted into data.json + the gold header so readers see why GLD
#     +1.85% flags while the equity universe uses |1D%| ≥ 5.0%.
# 1.0.4 (t_94cfd4c8, Zoe 09-04 M1/m1/m3 — generator fixes):
# M1: "" column RENAMED to "Adj" + Full Ranking header now
#     auto-emits the methodology disclosure (source = this run's own scoring
# results; window = non-rolling; update frequency = ;
#     sample = today's universe members; single-member sector = that member's
#     Adj round) so readers never read it as a sector rotation /
#     relative-strength signal. Sector map computation extracted to
#     compute_sector_momentum_map() (stale "watchlist only" comment fixed).
#   m1: gold header now outputs GLD ETF level ($406.77-class) IN PARALLEL
#     with the GC=F continuous level, with the level/return instrument split
# disclosed (GC=F roll macro reference only; tradable = GLD; 1D%
#     benchmark = GLD, same instrument as the GLD level).
#   m3: Top 10 Score Gainer/Loser tables gained a 1D% column with inline
#     flags — ⚠️ when scoreΔ direction opposes 1D% direction, and
# [sub↔raw ] when the RSI sub-score delta opposes the raw RSI delta
#     (non-monotonic RSI zone design) — plus an auto-emitted flag legend.
# 1.0.5 (t_6ed3ff15, Zoe 09-07 M1): SAME-AS-OF 1D% prev-close lock.
#   Root cause: 09-07 (Labor Day holiday) re-fetch silently back-adjusted BAC
#   history between fetches (Yahoo dividend/split adjustment: 09-03 close
#   63.04 → 62.72 while the 09-04 as-of close stayed 62.68). calc_indicators
#   derives 1D% from the df's last-two bars, so the published 1D% flipped
#   -0.57% → -0.06% on an UNCHANGED data-as-of — a published number rewritten
#   by re-fetch. Fix: when today's data-as-of equals the previous published
#   report's data-as-of, the PUBLISHED row is canonical — 1D% is carried over
#   VERBATIM (identical at every precision) while the as-of close is
#   effectively unchanged (≤0.1% tolerance; BAC + 1-cent revisions like GILD
#   150.99→151.00); if the as-of close is materially revised, the published
#   prior close (price / (1 + change_pct)) is locked and 1D% = close /
#   locked_ref - 1. Re-fetch can never rewrite the reference again. Lock
#   applies BEFORE every raw['change_pct'] consumer (Full Ranking, Gainer/
#   Loser, Material Moves, Key Notes, data.json).
#   load_prev_daily_report() now exposes as_of / row_close / row_chg.
CONFIG_VERSION = "1.0.5"  # bump when data cache or scoring logic changes

# ── Bracket WR Backtest Reference (Zoe Rubric #69 compliance) ──
# Every bracket WR claim MUST cite: date range, version, signal count (n), MaxDD.
# Source: v2_1_backtest_corrected.py walk-forward, backtest_v2_1_results DB,
# calibrated to overall Option 6 MaxDD = -6.4% (W30 revised report).
BRACKET_WR_BACKTEST = {
    "_source": {
        "date_range": "walk-forward Jan-Jul 2026",
        "version": "v2.1, Option 6",
        "methodology": "v2_1_backtest_corrected.py walk-forward, backtest_v2_1_results",
        "overall_maxdd": -6.4,
        "overall_wr": 49.1,
        "overall_n": 1996,
    },
    ">='90'":  {"wr": None, "n": 0,    "maxdd": None, "note": "ZERO signals — WR unverifiable"},
    "80-89":   {"wr": 93.2, "n": 44,   "maxdd": -1.4},
    "70-79":   {"wr": 62.7, "n": 150,  "maxdd": -4.7},
    "60-69":   {"wr": 65.3, "n": 377,  "maxdd": -4.4},
    "<60":     {"wr": 42.1, "n": 1425, "maxdd": -7.3,
               "note": "= live 50-59 + <50 merged (legacy 5-bucket)"},
}
BRACKET_WR_ORDER = [">='90'", "80-89", "70-79", "60-69", "<60"]
# Live rolling-WR table brackets (t_c36bf49b W35 P0). Uses proper ">=90"
# (not the legacy ">='90'" typo) and splits <60 into 50-59 (WATCH) + <50
# (NO_SIGNAL) so the live table matches weekly_snapshots signal_bracket values.
LIVE_BRACKET_ORDER = [">=90", "80-89", "70-79", "60-69", "50-59", "<50"]

# ── Paths ──
REPORT_DIR = os.path.expanduser("~/.hermes/profiles/renee/workspace/reports/daily-trend-momentum")
SHARED_DIR = os.path.expanduser("~/.hermes/shared/reports/renee/daily-trend-momentum")

# ── Company / Sector fallbacks (M1 fix: yfinance .info has longName/shortName, NOT "company") ──
# Hardcoded known-miss fallbacks (GM/MMM/SCHW/PAYX/EW reported blank in 08-07 run).
# These are belt-and-braces — primary lookup is yfinance longName via get_or_fetch_info.
COMPANY_NAME_FALLBACK = {
    "GM": "General Motors Company",
    "MMM": "3M Company",
    "SCHW": "The Charles Schwab Corporation",
    "PAYX": "Paychex, Inc.",
    "EW": "Edwards Lifesciences Corporation",
    "RTX": "RTX Corporation",
    "UNP": "Union Pacific Corporation",
}
SECTOR_FALLBACK = {
    "MMM": "Industrials",
    "UNP": "Industrials",
}


# ── data.json float rounding (Zoe 09-01 m2, t_b5acc944) ──
# data.json has carried IEEE 754 residue since W27 (daily_score
# 91.39999999999999, dgs10_bp 1.9999999999999574, spread_2s10
# 41.000000000000014). Round every float before json.dump — but KEY-AWARE:
# a blanket 1dp round would destroy raw fractions (change_pct 0.0102 → 0.0
# would turn a 1.02% move into 0%) and price precision. Scores/indicator
# readings → 1dp (matches report display); prices/oscillators/VIX/bond bp →
# 2dp; raw fractions → 4dp.
_ROUND_1DP_KEYS = {
    "daily_score", "base_5indicator_total", "weighted_total_raw", "weekly_score", "spy_adx",
    "rsi", "adx", "plus_di", "minus_di", "mfi_value",
}
_ROUND_2DP_KEYS = {
    "price", "sma_short", "entry_price", "stop_loss", "take_profit", "atr14",
    "risk_pct", "reward_pct", "rr_ratio", "vix_close", "true_wilder_adx",
    "diff", "dgs2", "dgs10", "dgs30", "dgs2_bp", "dgs10_bp", "dgs30_bp",
    "spread_2s10", "spread_change_bp", "gold_close", "gold_gld_close",
    "gold_gld_1d_pct", "macd_line", "macd_hist", "macd_signal", "volume_ratio",
    # gold_context summary keys (Zoe 09-03 m2, t_8cd84165)
    "gc_f_level", "gld_close", "gld_1d_pct", "material_threshold_pct",
}
_ROUND_4DP_KEYS = {"change_pct", "obv_pct_change", "avg_range_raw", "hysteresis_range_raw"}


def _round_payload(o, key=None):
    """Recursively round floats for JSON output, preserving precision by key.

    - scores / indicator readings → 1dp
    - prices / oscillators / VIX / bond bp → 2dp
    - raw fractions (change_pct, obv_pct_change) → 4dp
    - NaN/Inf preserved as-is (json.dump would emit invalid JSON otherwise,
      but the pipeline filters those upstream; never silently corrupt).
    """
    if isinstance(o, dict):
        return {k: _round_payload(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [_round_payload(v, key) for v in o]
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return o
        if key in _ROUND_2DP_KEYS:
            return round(o, 2)
        if key in _ROUND_4DP_KEYS:
            return round(o, 4)
        return round(o, 1)
    return o


def resolve_company_name(ticker, info=None):
    """Resolve company display name: yfinance longName/shortName -> hardcoded fallback -> ticker."""
    if info:
        name = info.get("longName") or info.get("shortName") or info.get("name")
        if name:
            return name
    return COMPANY_NAME_FALLBACK.get(ticker, ticker)


def resolve_sector(ticker, info=None):
    """Resolve sector: yfinance sector -> hardcoded fallback -> ''."""
    if info:
        sec = info.get("sector")
        if sec:
            return sec
    return SECTOR_FALLBACK.get(ticker, "")

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)

# ── Watchlist for ATR14 entry/SL/TP ──
WATCHLIST_JSON = os.path.expanduser("~/.hermes/profiles/renee/workspace/weekly-watchlist.json")

# ── ATR14 Entry/SL/TP Parameters ──
ATR_ENTRY_OFFSET = 0.5
ATR_TP_OFFSET = 1.5
ATR_SL_OFFSET = 0.75

# ── T&M ATR SL basis — Renee methodology decision (Zoe 09-03 M1, t_8cd84165) ──
# The T&M report's ATR ladder is a SINGLE-POINT-ENTRY methodology:
#   Entry = Close + 0.5×ATR14  (breakout/momentum trigger ABOVE the close)
#   SL    = Entry − 0.75×ATR14 (0.75-ATR risk measured from the trigger point)
#   TP    = Entry + 1.5×ATR14
# Mathematically SL lands at Close − 0.25×ATR14, which COINCIDES with the
# technical-snapshot "zone floor" level — but the trade construction is NOT
# the technical-snapshot momentum setup (zone entry floor..ceiling, SL =
# floor − 1×ATR14, R:R on zone-midpoint basis, t_d4dfd3b7). Re-anchoring this
# ladder to Close − 1.25×ATR (Option A) would widen risk from the trigger to
# 1.75×ATR while TP stays +1.5×ATR → R:R < 1 for every row, and a single-point
# trigger has no "zone floor" to anchor to. DECISION = Option B: keep the
# formula, carry an explicit basis note in the Section 2 header so SL/R:R are
# never compared across the two products.
# Section 2 header note (rendered in report builder):
ATR_SL_BASIS_NOTE = (
    "Table SL = Entry - 0.75xATR14 (single-point entry basis). "
    "Not comparable to technical-snapshot zone-floor SL (different R:R basis)."
)

# ── Periods ──
OPT = {
    "macd": {"fast": 19, "slow": 39, "signal": 9},
    "rsi": 14,
    "ma": [10, 50, 200],
    "adx": 14,
    "volume": 5,
    "bb": {"period": 20, "std": 2},
}

# ── Rule 5 volatility-floor hysteresis (Zoe 09-02 challenge, t_7915ddcc) ──
# PFE (09-01 #1, Adj 114.2) was silently dropped on 09-02 when its
# 20-day mean daily range ticked from >= 2.0% to 1.987% — a 0.013pp
# knife-edge (per-ticker-errors.jsonl 22:02:51). A single threshold for both
# admission and removal lets top-ranked candidates flicker in/out across the
# boundary. Fix: two-threshold hysteresis.
#   - Admission (new candidate, not in yesterday's published universe):
#         daily_range >= RULE5_ADMIT_PCT (2.0%)
#   - Retention (incumbent universe member):
#         daily_range >= RULE5_KEEP_PCT  (1.8%)
# An incumbent inside the [1.8%, 2.0%) band is KEPT (no flicker) and only
# removed below 1.8%; a brand-new candidate still needs 2.0% to enter.
# NOTE: technical_screen() only gates which non-watchlist candidates enter
# the daily scoring/ranking universe — it is NOT part of the weekly
# score_engine/backtest path, so this change does not alter backtest WR.
RULE5_ADMIT_PCT = 2.0
RULE5_KEEP_PCT = 1.8

# ── Single-stock material-move flag standard (Zoe 09-02 m2, t_7915ddcc) ──
# Gold's 🔴 material-move flag uses GLD |1D%| >= 1.5% (fetch_macro_context).
# For individual stocks a 1.5% move is noise (typical |1D%| 0.5-3%), so the
# single-stock standard is |1D%| >= 5.0% — PANW -9.28% / similar size moves.
# ONE threshold drives BOTH the Full Ranking 1D% flag AND the Key Ticker
# Notes material-move table so the two can never disagree.
MATERIAL_MOVE_PCT = 5.0

# ── Gold material-move threshold (Zoe 09-03 m2, t_8cd84165) ──
# Gold's 🔴 flag is gold-SPECIFIC: GLD |1D%| >= 1.5%, symmetric with the
# daily-social §9 gold trigger. It is a DIFFERENT standard from the equity
# universe MATERIAL_MOVE_PCT (5.0%) because a commodity ETF moves on a
# different volatility scale. Single named constant so the flag logic, the
# gold header disclosure and data.json can never disagree (09-02 m2
# carryover: +1.52% flag was not explained; 09-03 +1.85% flagged while
# universe material_moves=[] was not explained).
GOLD_MATERIAL_MOVE_PCT = 1.5

# ── Universe — watchlist first, fallback to built-in ──
WATCHLIST_PATH = os.path.expanduser("~/.hermes/profiles/renee/workspace/watchlist.json")

def load_universe():
    tickers = set()
    if os.path.exists(WATCHLIST_PATH):
        try:
            with open(WATCHLIST_PATH) as f:
                data = json.load(f)
            for k in ("momentum_universe", "trend_universe"):
                tickers.update(data.get(k, []))
        except Exception:
            pass
    # Built-in fallback (no ETFs)
    builtin = [
        "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA",
        "JPM","V","JNJ","WMT","PG","UNH","HD","DIS","NFLX",
        "PYPL","ADBE","CRM","INTC","AMD","BA","CAT","XOM",
        "CVX","KO","PEP","MRK","ABBV","PFE","BAC","MA",
        "COST","NKE","CSCO","T","VZ","NEE","LIN","SCHW",
        "AXP","GS","BLK","TMO","LLY","UNP","HON","RTX",
        "LOW","SBUX","IBM","DUK","SO","ORCL","QCOM","TXN",
        "MU","LRCX","F","GM","CMG","ABNB","UBER","SQ",
        "SHOP","PANW","NOW","PLTR","HOOD","SOFI","MSTR",
        "COIN","MCD","MDLZ","CL","EL","DE","C","WFC",
        "USB","PNC","TFC","SPGI","MCO","VRTX","GILD","AMGN",
        "REGN","BIIB","ISRG","BSX","MDT","ABT","GE","MMM",
        "DDOG","MET","KLAC","EMR","EW","PAYX","SHW","CNC","NXPI",
    ]
    tickers.update(builtin)
    # Filter out ETFs
    etfs = {"SPY","QQQ","IWM","DIA","SPYG","SPYV","IVV","VOO","VTI","QQQM"}
    tickers = [t for t in tickers if t not in etfs]
    print(f"[📋] Universe: {len(tickers)} stocks", file=sys.stderr)
    return sorted(tickers)


def technical_screen(df, ticker="?", prev_member=False):
    """
    Stage 1: Breakout Setup Scan (Option B).
    Uses OHLCV dataframe to check if ticker passes trend+momentum criteria.

    Rules:
      1. ADX > 25 + +DI > -DI (bullish trending)
      2. Price > SMA50 > SMA200 (bullish alignment)
      3. 3-month return 10-40% (momentum, not too extended)
      4. Price within 5% of nearest 10/20/50 EMA (not stretched)
      5. Avg daily range floor with hysteresis (Zoe 09-02, t_7915ddcc):
             >= 2.0%  admit a NEW candidate (not in yesterday's universe)
             >= 1.8%  RETAIN an incumbent (yesterday's universe member)
         The two-threshold band stops knife-edge flicker (PFE 1.987% on
         09-02 after being #1 on 09-01). An incumbent in [1.8%, 2.0%) is
         retained and flagged metrics['hysteresis_retained']=True so the
         report can disclose the near-miss.
      6. Price > $10, 50d avg dollar volume > $5M
      7. Consolidation 5-40d, range < 8% (tight base)
      8. Price > 20-day low (short-term strength)
      9. Not > SMA200 by 30% (not over-extended)

    prev_member: True when ticker was in yesterday's PUBLISHED universe
    (previous {date}-data.json) — consult load_prev_daily_comparison().

    Returns dict with pass/fail + reason.
    """
    close = df["Close"].dropna()
    high = df["High"].dropna()
    low = df["Low"].dropna()
    volume = df["Volume"].dropna()

    result = {"pass": False, "reason": "", "metrics": {}}

    if len(close) < 200:
        result["reason"] = f"insufficient_data ({len(close)} bars)"
        return result

    price = float(close.iloc[-1])
    result["metrics"]["price"] = round(price, 2)

    # Rule 6a: Price > $10
    if price <= 10:
        result["reason"] = f"price=${price:.2f} <= $10"
        return result

    # Rule 3: 3-month return 10-40%
    ret_3m = (close.iloc[-1] / close.iloc[-60] - 1) if len(close) >= 60 else 0
    result["metrics"]["3m_return"] = round(ret_3m * 100, 1)
    if ret_3m < 0.10:
        result["reason"] = f"3m_return={ret_3m*100:.1f}% < 10%"
        return result
    if ret_3m > 0.40:
        result["reason"] = f"3m_return={ret_3m*100:.1f}% > 40% (over-extended)"
        return result

    # Rule 2: Price > SMA50 > SMA200
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])
    result["metrics"]["vs_sma50"] = round((price / sma50 - 1) * 100, 1)
    result["metrics"]["vs_sma200"] = round((price / sma200 - 1) * 100, 1)
    if price <= sma50:
        result["reason"] = f"price=${price:.2f} <= SMA50=${sma50:.2f}"
        return result
    if sma50 <= sma200:
        result["reason"] = f"SMA50=${sma50:.2f} <= SMA200=${sma200:.2f} (bearish alignment)"
        return result

    # Rule 1: ADX > 25 + +DI > -DI
    try:
        adx_df = _adx(high, low, close, length=14)
        if adx_df is None or adx_df.empty:
            result["reason"] = "ADX compute failed"
            return result
        adx_col = [c for c in adx_df.columns if "ADX_" in c][0]
        dmp_col = [c for c in adx_df.columns if "DMP_" in c][0]
        dmn_col = [c for c in adx_df.columns if "DMN_" in c][0]
        adx_val = float(adx_df[adx_col].iloc[-1])
        plus_di = float(adx_df[dmp_col].iloc[-1])
        minus_di = float(adx_df[dmn_col].iloc[-1])
        result["metrics"]["adx"] = round(adx_val, 1)
        result["metrics"]["plus_di"] = round(plus_di, 1)
        result["metrics"]["minus_di"] = round(minus_di, 1)
        if adx_val <= 25:
            result["reason"] = f"ADX={adx_val:.1f} <= 25 (no trend)"
            return result
        if plus_di <= minus_di:
            result["reason"] = f"+DI={plus_di:.1f} <= -DI={minus_di:.1f} (bearish DI)"
            return result
    except Exception as e:
        result["reason"] = f"ADX error: {e}"
        return result

    # Rule 8: Price > 20-day low
    low_20 = float(low.iloc[-20:].min())
    if price <= low_20:
        result["reason"] = f"price=${price:.2f} <= 20d_low=${low_20:.2f}"
        return result

    # Rule 6b: Dollar volume > $5M
    avg_vol = float(volume.iloc[-50:].mean()) if len(volume) >= 50 else 0
    dollar_vol = price * avg_vol
    result["metrics"]["dollar_vol_m"] = round(dollar_vol / 1e6, 1)
    if dollar_vol < 5e6:
        result["reason"] = f"dollar_vol=${dollar_vol/1e6:.1f}M < $5M"
        return result

    # Rule 9: Not > SMA200 by 30%
    pct_vs_sma200 = (price - sma200) / sma200
    if pct_vs_sma200 > 0.30:
        result["reason"] = f"price {pct_vs_sma200*100:.0f}% above SMA200 > 30%"
        return result

    # Rule 7: Consolidation 5-40d, range < 8%
    lookback = min(60, len(close))
    best_consol = {"days": 0, "range_pct": 0}
    for start in range(lookback - 5, 5, -1):
        chunk_high = float(high.iloc[-start:].max())
        chunk_low = float(low.iloc[-start:].min())
        chunk_range = (chunk_high - chunk_low) / chunk_low * 100
        if chunk_range < 8 and 5 <= start <= 40:
            if start > best_consol["days"]:
                best_consol = {"days": start, "range_pct": round(chunk_range, 1)}
    result["metrics"]["consol_days"] = best_consol["days"]
    result["metrics"]["consol_range"] = best_consol["range_pct"]
    if best_consol["days"] == 0:
        result["reason"] = "no consolidation (range>8% or <5d or >40d)"
        return result

    # Rule 5: Avg daily range floor — two-threshold hysteresis
    # (Zoe 09-02 challenge, t_7915ddcc). The old single 2.0% threshold made
    # PFE (09-01 #1, Adj 114.2) silently vanish on 09-02 when its 20-day mean
    # daily range printed 1.987% — a 0.013pp knife-edge. Admission for NEW
    # candidates stays >= 2.0%; incumbents (yesterday's published universe)
    # are retained down to 1.8% so the boundary cannot flicker a top-ranked
    # stock in/out day-over-day. Reason strings use .3f — the old .1f made
    # the error log self-contradict ("avg_daily_range=2.0% < 2%").
    daily_range = float(((high - low) / low * 100).iloc[-20:].mean())
    result["metrics"]["avg_range"] = round(daily_range, 1)
    result["metrics"]["avg_range_raw"] = round(daily_range, 4)
    result["metrics"]["range_rule5"] = (
        "retain_incumbent" if prev_member else "admit_new_candidate")
    if daily_range < RULE5_KEEP_PCT:
        result["reason"] = (f"avg_daily_range={daily_range:.3f}% < "
                            f"{RULE5_KEEP_PCT:.1f}% (remove threshold; "
                            f"below hysteresis band)")
        return result
    if daily_range < RULE5_ADMIT_PCT and not prev_member:
        result["reason"] = (f"avg_daily_range={daily_range:.3f}% < "
                            f"{RULE5_ADMIT_PCT:.1f}% (admit threshold; new "
                            f"candidate — hysteresis band "
                            f"{RULE5_KEEP_PCT:.1f}-{RULE5_ADMIT_PCT:.1f}% "
                            f"only retains existing universe members)")
        result["metrics"]["near_miss_rule5"] = True
        return result
    if prev_member and daily_range < RULE5_ADMIT_PCT:
        # Incumbent in the [KEEP, ADMIT) band — retained to prevent
        # knife-edge flicker. Flag for the caller/report disclosure.
        result["metrics"]["hysteresis_retained"] = True
        result["metrics"]["hysteresis_range_raw"] = round(daily_range, 4)

    # Rule 4: Within 5% of nearest 10/20/50 EMA
    def ema(n):
        s = close.ewm(span=n, adjust=False).mean()
        return float(s.iloc[-1]) if len(s) >= n else None

    ema_dists = []
    for n in [10, 20, 50]:
        val = ema(n)
        if val and val > 0:
            d = abs(price - val) / val
            ema_dists.append((n, d))
    if ema_dists:
        min_ema_dist = min(d for _, d in ema_dists)
        closest_ema = [n for n, d in ema_dists if d == min_ema_dist][0]
        result["metrics"]["closest_ema"] = closest_ema
        result["metrics"]["min_ema_dist"] = round(min_ema_dist * 100, 1)
        if min_ema_dist > 0.05:
            result["reason"] = f"furthest from EMAs ({min_ema_dist*100:.1f}% > 5%)"
            return result

    result["pass"] = True
    result["reason"] = "passed"
    return result


def quick_screen(tickers, min_price=5.0, min_mcap=2e9, min_volume=500_000):
    """
    Stage 1: Quick screen using yfinance info dict (no history fetch).
    Returns set of tickers that pass basic liquidity/quality filters.

    Watchlist tickers ALWAYS pass (they're pre-vetted).
    Uses time.sleep(0.3) between calls to avoid yfinance rate limiting.
    """
    import yfinance as yf
    import time as _time
    passed = set()
    total = len(tickers)
    for i, t in enumerate(tickers, 1):
        sys.stderr.write(f"\r[🔍] Screening {i}/{total} ... ")
        sys.stderr.flush()
        try:
            info = get_or_fetch_info(t)
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                # yfinance rate-limited or empty response — skip this ticker
                _time.sleep(0.5)
                continue
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            mcap = info.get("marketCap") or 0
            vol = info.get("volume") or info.get("regularMarketVolume") or 0
            if price >= min_price and mcap >= min_mcap and vol >= min_volume:
                passed.add(t)
        except Exception:
            pass
        _time.sleep(0.3)  # rate limit buffer
    sys.stderr.write(f"\r[🔍] Screening done: {len(passed)}/{total} passed\n")
    return passed

def calc_indicators_daily(df, opt, ticker="?"):
    """Calculate all indicators on daily OHLCV data. Returns raw dict or None.
    Logs per-ticker errors to JSONL for debugging (NaN / insufficient data)."""
    if df is None or len(df) < max(opt["ma"][2], 20):
        log_ticker_error(
            ticker, step="calc_indicators", error_type="insufficient_data",
            message=f"df_len={len(df) if df is not None else 0}, min_req={max(opt['ma'][2], 20)}",
            raw_snapshot={"df_len": len(df) if df is not None else 0}
        )
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # RSI
    rsi_series = _rsi(close, period=opt["rsi"])
    rsi_val = rsi_series.iloc[-1] if rsi_series is not None else None

    # MACD
    macd_result = _macd(close, fast=opt["macd"]["fast"], slow=opt["macd"]["slow"], signal=opt["macd"]["signal"])
    if macd_result is None or len(macd_result.columns) < 3:
        log_ticker_error(
            ticker, step="calc_indicators", error_type="macd_failed",
            message=f"macd_result={'None' if macd_result is None else f'cols={len(macd_result.columns)}'}",
            raw_snapshot={"close_last": float(close.iloc[-1]), "close_len": len(close)}
        )
        return None
    macd_col = [c for c in macd_result.columns if "MACD_" in c and "MACDh" not in c and "MACDs" not in c]
    macdh_col = [c for c in macd_result.columns if "MACDh" in c]
    macds_col = [c for c in macd_result.columns if "MACDs" in c]
    if not (macd_col and macdh_col and macds_col):
        log_ticker_error(
            ticker, step="calc_indicators", error_type="macd_columns_missing",
            message=f"col_search: macd={'found' if macd_col else 'missing'}, macdh={'found' if macdh_col else 'missing'}, macds={'found' if macds_col else 'missing'}",
            raw_snapshot={"macd_columns": list(macd_result.columns)}
        )
        return None
    macd_line = float(macd_result[macd_col[0]].iloc[-1])
    macd_hist = float(macd_result[macdh_col[0]].iloc[-1])
    macd_signal = float(macd_result[macds_col[0]].iloc[-1])
    macd_hist_series = macd_result[macdh_col[0]].tail(min(100, len(macd_result))).tolist()

    # SMA — drop trailing NaN first (yfinance may include today's NaN bar)
    close_clean = close.dropna()
    sma_periods = opt["ma"]
    if len(close_clean) >= sma_periods[2]:
        sma_short_val = _sma(close_clean, period=sma_periods[0]).iloc[-1]
        sma_mid_val = _sma(close_clean, period=sma_periods[1]).iloc[-1]
        sma_long_val = _sma(close_clean, period=sma_periods[2]).iloc[-1]
        if any(pd.isna(v) for v in (sma_short_val, sma_mid_val, sma_long_val)):
            log_ticker_error(
                ticker, step="calc_indicators", error_type="sma_nan",
                message=f"sma_short={'nan' if pd.isna(sma_short_val) else 'ok'}, sma_mid={'nan' if pd.isna(sma_mid_val) else 'ok'}, sma_long={'nan' if pd.isna(sma_long_val) else 'ok'}",
                raw_snapshot={"close_clean_len": len(close_clean), "close_last": float(close_clean.iloc[-1])}
            )
            return None
        sma_short = float(sma_short_val)
        sma_mid = float(sma_mid_val)
        sma_long = float(sma_long_val)
    else:
        log_ticker_error(
            ticker, step="calc_indicators", error_type="sma_insufficient_data",
            message=f"close_clean_len={len(close_clean)}, sma_periods={sma_periods}",
            raw_snapshot={"close_clean_len": len(close_clean), "sma_long_period": sma_periods[2]}
        )
        return None

    # ADX
    adx_result = _adx(high, low, close, length=opt["adx"])
    if adx_result is not None:
        adx_col = [c for c in adx_result.columns if "ADX_" in c]
        dmp_col = [c for c in adx_result.columns if "DMP_" in c]
        dmn_col = [c for c in adx_result.columns if "DMN_" in c]
        adx_val = float(adx_result[adx_col[0]].iloc[-1]) if adx_col else None
        plus_di = float(adx_result[dmp_col[0]].iloc[-1]) if dmp_col else None
        minus_di = float(adx_result[dmn_col[0]].iloc[-1]) if dmn_col else None
    else:
        adx_val = plus_di = minus_di = None

    # Volume ratio
    vol_period = opt["volume"]
    if len(volume) >= vol_period:
        avg_vol = volume.iloc[-vol_period:].mean()
        vol_ratio = float(volume.iloc[-1] / avg_vol) if avg_vol > 0 else 1.0
    else:
        vol_ratio = 1.0

    # OBV trend + proportional strength
    obv_series = _obv(close, volume)
    obv_pct_change = 0.0
    if obv_series is not None and len(obv_series) >= 5:
        obv_trend = 1 if obv_series.iloc[-1] > obv_series.iloc[-5] else (-1 if obv_series.iloc[-1] < obv_series.iloc[-5] else 0)
        obv_pct_change = float((obv_series.iloc[-1] - obv_series.iloc[-5]) / abs(obv_series.iloc[-5])) if obv_series.iloc[-5] != 0 else 0.0
    else:
        obv_trend = 0

    # MFI (Money Flow Index, 14-period)
    mfi_value = None
    try:
        mfi_series = _mfi(high, low, close, volume, length=14)
        if mfi_series is not None and not mfi_series.empty:
            mfi_value = round(float(mfi_series.iloc[-1]), 1)
    except Exception:
        pass

    close_clean_cp = close.dropna()
    if len(close_clean_cp) >= 2:
        change_pct = float(close_clean_cp.pct_change().iloc[-1])
    else:
        change_pct = 0.0

    return {
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
        "obv_pct_change": obv_pct_change,
        "mfi_value": mfi_value,
        "change_pct": change_pct,
    }

def get_regime_daily():
    """Determine market regime from SPY daily ADX + VIX (cached data).
    
    Phase 3 ADX Regime Filter:
    - trending:  SPY ADX >= 28 (strong directional trend)
    - ranging:   SPY ADX 25-28 (moderate, ambiguous)
    - choppy:    SPY ADX < 25 (weak/no trend — raise individual ADX threshold)
    - volatile:  VIX >= 25 regardless of ADX
    
    Uses cached SPY ADX + VIX from daily_data_cache.
    
    Returns (regime, spy_adx, vix_close).

    08-11 Zoe BLOCKER (t_b18a2102) hardening: this function must NEVER
    silently return regime="ranging"/ADX=0 on failure. The 08-11 first run
    swallowed a pandas_ta ImportError into ("ranging", 0, 0), which bypassed
    Option G (choppy-only suppression) and produced 19 false BUY signals.
    Any invalid ADX now raises so main() aborts before scoring/publishing.
    """
    try:
        # Use cached data — determinism guarantee
        vix_close = get_vix()
        spy_adx, spy_close = get_spy_adx(period="1y", length=14)
        if spy_adx is None or not (spy_adx > 0):
            raise ValueError(
                f"SPY ADX invalid (adx={spy_adx}) — cannot determine market "
                f"regime; refusing to default to 'ranging' (would bypass "
                f"Option G and flood false BUY signals)")
        # Phase 3: Choppy (SPY ADX < 25) gets distinct handling
        if vix_close >= 25:
            regime = "volatile"
        elif spy_adx >= 28:
            regime = "trending"
        elif spy_adx >= 25:
            regime = "ranging"
        else:
            regime = "choppy"
        return regime, round(spy_adx, 1), round(vix_close, 2)
    except Exception as e:
        raise RuntimeError(f"market regime determination failed: {e}") from e


# ── ATR14 helpers (for entry/SL/TP on watchlist stocks) ──


def load_watchlist_tickers():
    """Load Track A + Track B tickers from weekly-watchlist.json"""
    if not os.path.exists(WATCHLIST_JSON):
        print(f"[⚠] Watchlist JSON not found: {WATCHLIST_JSON}", file=sys.stderr)
        return set()
    try:
        with open(WATCHLIST_JSON) as f:
            data = json.load(f)
        tickers = set()
        for track in ("track_a", "track_b"):
            for entry in data.get(track, {}).get("entries", []):
                tickers.add(entry["ticker"])
        print(f"[📋] Watchlist: {len(tickers)} tickers loaded (Track A+B)", file=sys.stderr)
        return tickers
    except Exception as e:
        print(f"[⚠] Watchlist load failed: {e}", file=sys.stderr)
        return set()


# ══════════════════════════════════════════════════════════════════════
# PREVIOUS-DAY BASELINE + RULE 5 HYSTERESIS MEMBERSHIP (Zoe 09-02, t_7915ddcc)
# ══════════════════════════════════════════════════════════════════════
# The technical_screen Rule 5 hysteresis needs to know whether a candidate
# was in YESTERDAY's PUBLISHED universe (previous {date}-data.json in
# SHARED_DIR). The prev baseline was previously loaded only AFTER the
# scoring loop — too late for the screen decision. This loader is called
# BEFORE the loop; the compare/report code reuses the same structures.
_BRACKET_ZERO = {">=90": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "<50": 0}


def find_prev_daily_report(today_str):
    """Find the most recent published {date}-data.json strictly before today.

    Returns (prev_date, prev_path) or (None, None) when no daily baseline
    exists (first deployment run — weekly_snapshots fallback applies).
    """
    daily_files = []
    try:
        for fn in os.listdir(SHARED_DIR):
            if not fn.endswith("-data.json"):
                continue
            cand = fn[: -len("-data.json")]
            # Strip optional -momentum-snapshot suffix to extract the date
            if "-momentum-snapshot" in cand:
                cand = cand[: cand.index("-momentum-snapshot")]
            try:
                datetime.strptime(cand, "%Y-%m-%d")
            except ValueError:
                continue  # non-date-prefixed file
            if cand < today_str:
                daily_files.append((cand, os.path.join(SHARED_DIR, fn)))
    except OSError:
        pass
    daily_files.sort(key=lambda x: x[0], reverse=True)
    return daily_files[0] if daily_files else (None, None)


def load_prev_daily_report(prev_path):
    """Parse a published {date}-data.json into prev-day comparison structures.

    Returns dict:
      scores      ticker -> daily_score (Adj)
      verdicts    ticker -> uppercase verdict ('' when missing)
      breakdowns  ticker -> score_breakdown dict (when present)
      raws        ticker -> raw RSI (when present)
      brackets    bracket -> count
      buy_effective  count of BUY verdicts (Option G aware)
      tickers     set of tickers in the prev universe (membership source for
                  Rule 5 hysteresis)
      ranked      list of tickers sorted by daily_score DESC (rank 1 = #1)
      rank_index ticker -> 1-based rank (for " Adj X #N" disclosure)
    Empty dict on failure — callers treat it as no-baseline.
    """
    out = {
        "scores": {}, "verdicts": {}, "breakdowns": {}, "raws": {},
        "brackets": dict(_BRACKET_ZERO), "buy_effective": 0,
        "tickers": set(), "ranked": [], "rank_index": {},
        # 1.0.5 (t_6ed3ff15): expose the published row's data-as-of + per-ticker
        # price and 1D% so the same-as-of prev-close lock (apply_same_asof_1d_lock)
        # can anchor on the PUBLISHED reference — a re-fetch can never rewrite
        # an already-published prior close (BAC 09-07 M1 regression).
        "as_of": "", "row_close": {}, "row_chg": {},
    }
    try:
        with open(prev_path, encoding="utf-8") as f:
            prev_data = json.load(f)
        out["as_of"] = prev_data.get("data_as_of") or prev_data.get("date") or ""
        for r in prev_data.get("results", []):
            t = r.get("ticker")
            if t is None:
                continue
            # Capture price/1D% BEFORE the score check so every published row
            # (score or not) can serve as a prev-close anchor.
            _price = r.get("price")
            if _price is not None:
                out["row_close"][t] = _price
            pri = r.get("raw_indicators")
            if isinstance(pri, dict):
                if pri.get("change_pct") is not None:
                    out["row_chg"][t] = pri.get("change_pct")
                if pri.get("rsi") is not None:
                    out["raws"][t] = pri.get("rsi")
            sc = r.get("daily_score")
            if sc is None:
                continue
            out["scores"][t] = sc
            b = r.get("daily_bracket") or get_signal_bracket(sc)
            out["brackets"][b] = out["brackets"].get(b, 0) + 1
            v = (r.get("daily_verdict") or "").upper()
            out["verdicts"][t] = v
            sb = r.get("score_breakdown")
            if isinstance(sb, dict) and "macd" in sb:
                out["breakdowns"][t] = sb
            if "BUY" in v and "NO" not in v:
                out["buy_effective"] += 1
            out["tickers"].add(t)
        ranked = sorted(out["scores"].items(), key=lambda kv: kv[1], reverse=True)
        out["ranked"] = [t for t, _ in ranked]
        out["rank_index"] = {t: i + 1 for i, (t, _) in enumerate(ranked)}
    except Exception:
        return {k: (dict(v) if isinstance(v, dict) else v)
                for k, v in out.items()}  # tolerate partial
    return out


def load_prev_daily_comparison(today_str):
    """Load the FULL prev-day baseline (daily report, weekly_snapshots fallback).

    Replaces the inline block that used to sit after the scoring loop. Loaded
    BEFORE scoring so Rule 5 hysteresis can see yesterday's universe members.

    Returns dict with: date, path, daily_files(bool), plus all keys of
    load_prev_daily_report(). No daily report + no weekly data -> empty.
    """
    prev_date, prev_path = find_prev_daily_report(today_str)
    out = {
        "date": "", "path": None, "daily_files": False,
        "scores": {}, "verdicts": {}, "breakdowns": {}, "raws": {},
        "brackets": dict(_BRACKET_ZERO), "buy_effective": 0,
        "tickers": set(), "ranked": [], "rank_index": {},
        # 1.0.5 (t_6ed3ff15): same-as-of 1D% lock needs the prev report's
        # data-as-of + published row price/1D%. Empty in the weekly fallback.
        "as_of": "", "row_close": {}, "row_chg": {},
    }
    if prev_date:
        loaded = load_prev_daily_report(prev_path)
        loaded["date"] = prev_date
        loaded["path"] = prev_path
        loaded["daily_files"] = True
        out = loaded
        print(f"[📋] Loaded {len(out['scores'])} previous scores from DAILY report {prev_date} "
              f"(brackets {[out['brackets'].get(b, 0) for b in ['>=90', '80-89', '70-79', '60-69', '50-59', '<50']]})",
              file=sys.stderr)
        return out

    # Fallback: weekly_snapshots SQLite (first run after deployment / no daily report yet)
    DB_PATH = os.path.expanduser("~/.hermes/shared/data/renee_indicators.db")
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            # Guard: reject phantom future week_end (Rubric #82 — phantom future baseline)
            cur = conn.execute(
                "SELECT MAX(week_end) FROM weekly_snapshots WHERE week_end < ?",
                (today_str,)
            )
            latest_week = cur.fetchone()[0]
            if latest_week:
                out["date"] = latest_week
                cur = conn.execute(
                    "SELECT ticker, score_total, signal_bracket FROM weekly_snapshots WHERE week_end = ?",
                    (latest_week,)
                )
                for row in cur:
                    out["scores"][row[0]] = row[1]
                    b = row[2] if row[2] else get_signal_bracket(row[1])
                    out["brackets"][b] = out["brackets"].get(b, 0) + 1
                    out["tickers"].add(row[0])
                ranked = sorted(out["scores"].items(), key=lambda kv: kv[1], reverse=True)
                out["ranked"] = [t for t, _ in ranked]
                out["rank_index"] = {t: i + 1 for i, (t, _) in enumerate(ranked)}
                print(f"[⚠] No daily report found — FALLBACK to weekly_snapshots {latest_week} "
                      f"(should only happen on first run)", file=sys.stderr)
            conn.close()
        except Exception as e:
            print(f"[⚠] DB load failed: {e}", file=sys.stderr)
    return out


def published_prior_close(price, change_pct):
    """Implied prior trading-day close from a PUBLISHED row.

    A published row stores (as-of close `price`, `change_pct`) with
    change_pct = price / prior_close - 1. Inverting gives the prior close the
    row was anchored to at PUBLICATION time.

    1.0.5 (t_6ed3ff15, Zoe 09-07 M1): this is the value the same-as-of 1D%
    lock treats as canonical. A later yfinance re-fetch can silently
    back-adjust history (dividend/split scaling — BAC 09-03 close rewritten
    63.04 → 62.72 between the 09-04 and 09-07 fetches), which would otherwise
    move the last-bar pct_change even when the as-of close is unchanged.
    Returns None when the inversion is impossible (missing/non-finite values,
    change_pct <= -1).
    """
    if price is None or change_pct is None:
        return None
    try:
        price = float(price)
        chg = float(change_pct)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(price) or not math.isfinite(chg) or (1.0 + chg) <= 0.0:
        return None
    return price / (1.0 + chg)


def apply_same_asof_1d_lock(results, prev_row_close, prev_row_chg,
                            close_tol_rel=0.001):
    """Lock 1D% to the PUBLISHED row when data-as-of is unchanged.

    Zoe 09-07 M1 (t_6ed3ff15): on a holiday / weekend / same-day re-run the
    current data-as-of equals the previous published report's data-as-of, so
    every published 1D% must stay identical (31/31 re-verify vs the 09-04
    report). calc_indicators derives 1D% from the fetched df's last two bars;
    when that fetch returns back-adjusted history (Yahoo corporate-action
    adjustment between fetches), the reference close moves and the published
    number silently changes (BAC 09-07: -0.57% -> -0.06% with the same 62.68
    as-of close).

    The PUBLISHED report is canonical. For each result row that exists in the
    previous published report:
      - as-of close effectively unchanged (|close-prev_price|/prev_price <=
        close_tol_rel, default 0.1%): 1D% = PUBLISHED change_pct VERBATIM.
        This reproduces the published table exactly (4dp round-trip), so a
        re-fetch can never rewrite an already-published number — even a tiny
        close revision (GILD 150.99 -> 151.00, 1 cent) must not drift the
        published cell.
      - as-of close materially revised (correction beyond tolerance): the
        PUBLISHED prior close reference is locked (price / (1 + change_pct))
        and 1D% = corrected close / locked_ref - 1. The reference never moves
        even when the numerator is corrected.
    Rows without a published anchor are left untouched (df-derived value
    stands).

    Mutates results[*]['raw']['change_pct'] IN PLACE. Must run BEFORE any
    consumer of raw['change_pct'] (Full Ranking, Gainer/Loser 1D% cells,
    Material Moves, Key Ticker Notes, data.json serialization).

    Returns a list of audit dicts:
      {ticker, mode ('carryover'|'ref_lock'), asof_close, locked_ref_close,
       old_chg, new_chg}
    """
    locked = []
    prev_row_close = prev_row_close or {}
    prev_row_chg = prev_row_chg or {}
    for r in results:
        raw = r.get("raw") or {}
        if "change_pct" not in raw:
            continue
        ticker = r.get("ticker")
        close = r.get("close")
        if (close is None or ticker is None
                or ticker not in prev_row_close
                or ticker not in prev_row_chg):
            continue
        prev_price = prev_row_close[ticker]
        prev_chg = prev_row_chg[ticker]
        try:
            prev_price = float(prev_price)
            prev_chg = float(prev_chg)
            close = float(close)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(prev_price) and math.isfinite(prev_chg)
                and math.isfinite(close)) or prev_price <= 0.0:
            continue
        old_chg = raw["change_pct"]
        ref = published_prior_close(prev_price, prev_chg)
        if ref is None or ref <= 0.0:
            continue
        if abs(close - prev_price) / prev_price <= close_tol_rel:
            # As-of close effectively unchanged → verbatim carryover of the
            # published 1D% (identical at every precision; BAC fix path).
            new_chg = prev_chg
            mode = "carryover"
        else:
            # As-of close materially revised → published REFERENCE locked,
            # numerator follows the corrected close.
            new_chg = close / ref - 1.0
            mode = "ref_lock"
        raw["change_pct"] = new_chg
        locked.append({
            "ticker": ticker,
            "mode": mode,
            "asof_close": round(close, 4),
            "locked_ref_close": round(ref, 4),
            "old_chg": old_chg,
            "new_chg": round(new_chg, 6),
        })
    return locked


def calc_atr14_from_df(df):
    """Calculate ATR14 from an OHLCV DataFrame. Returns (atr_val, price) or (None, None)."""
    if df is None or df.empty or len(df) < 20:
        return None, None
    try:
        # Flatten MultiIndex columns if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Drop NaN rows (non-trading / today's incomplete bar)
        df = df.dropna(subset=['Close', 'High', 'Low', 'Volume'])
        if df.empty or len(df) < 20:
            return None, None
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        atr_series = _atr(high, low, close, length=14)
        if atr_series is None or atr_series.empty:
            return None, None
        atr_val = float(atr_series.iloc[-1])
        price = float(close.iloc[-1])
        return atr_val, price
    except Exception:
        return None, None


def compute_entry_sl_tp(price, atr14, regime=None):
    """Compute entry, SL, TP from ATR14.
    
    Entry = close + 0.5 × ATR14 (confirm uptrend momentum)
    SL = entry - 0.75 × ATR14 (min 0.5×ATR14 floor)
    TP = entry + 1.5 × ATR14
    
    Regime-based adjustments (Zoe #71):
    - volatile:  SL tightened from 0.75×ATR to 0.5×ATR (tighter risk)
    - trending:  TP loosened from 1.5×ATR to 2.0×ATR (let winners run)

    SL BASIS (Renee methodology decision, Zoe 09-03 M1 / t_8cd84165):
    This ladder is a SINGLE-POINT-ENTRY construction — the SL is measured
    0.75×ATR from the single trigger entry (Close + 0.5×ATR), i.e. it lands
    at Close − 0.25×ATR. It is NOT the technical-snapshot momentum-setup
    zone construction (zone floor − 1×ATR, R:R on zone midpoint). Section 2
    carries an explicit basis note (ATR_SL_BASIS_NOTE); never compare SL/R:R
    across the two products.
    """
    if atr14 is None or atr14 <= 0 or price is None or price <= 0:
        return None
    sl_offset = ATR_SL_OFFSET
    tp_offset = ATR_TP_OFFSET
    if regime == "volatile":
        sl_offset = 0.5  # tighten SL in volatile markets (Zoe #71)
    elif regime == "trending":
        tp_offset = 2.0  # loosen TP in trending markets (Zoe #71)
    entry = price + ATR_ENTRY_OFFSET * atr14
    stop_loss = entry - max(sl_offset * atr14, 0.5 * atr14)
    take_profit = entry + tp_offset * atr14
    risk = entry - stop_loss
    reward = take_profit - entry
    return {
        "entry_price": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "atr14": round(atr14, 2),
        "risk_pct": round(risk / entry * 100, 2),
        "reward_pct": round(reward / entry * 100, 2),
        "rr_ratio": round(reward / risk, 2) if risk > 0 else 0,
    }


# ── SHA256 Hash Helpers ──


def compute_file_sha256(filepath):
    """Compute SHA256 hex digest of a file. Returns hex string or None."""
    try:
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except (OSError, IOError) as e:
        print(f"[⚠] Hash compute failed for {filepath}: {e}", file=sys.stderr)
        return None


def save_sha256_file(json_path):
    """Compute SHA256 of a JSON file and write .sha256 alongside it.
    Returns the hex digest string, or None on failure."""
    sha_hex = compute_file_sha256(json_path)
    if sha_hex is None:
        return None
    sha_path = json_path + ".sha256"
    with open(sha_path, "w", encoding="utf-8") as f:
        f.write(sha_hex + "  " + os.path.basename(json_path) + "\n")
    print(f"[🔑] SHA256 saved: {sha_path}", file=sys.stderr)
    return sha_hex


def verify_sha256_file(json_path):
    """Verify JSON file integrity against its .sha256 sidecar.
    Returns True if valid, False if mismatch, None if no .sha256 file found.
    On mismatch, blocks report generation with an error."""
    sha_path = json_path + ".sha256"
    if not os.path.exists(sha_path):
        print(f"[⚠] No .sha256 found for {json_path} — skipping verify", file=sys.stderr)
        return None
    try:
        with open(sha_path, "r") as f:
            expected_line = f.read().strip()
        expected = expected_line.split()[0] if expected_line else ""
    except Exception as e:
        print(f"[⚠] Could not read {sha_path}: {e}", file=sys.stderr)
        return None
    actual = compute_file_sha256(json_path)
    if actual is None:
        return None
    if actual == expected:
        print(f"[✅] Hash OK: {os.path.basename(json_path)}", file=sys.stderr)
        return True
    else:
        print(f"[❌] HASH MISMATCH: {json_path}", file=sys.stderr)
        print(f"      Expected: {expected}", file=sys.stderr)
        print(f"      Actual:   {actual}", file=sys.stderr)
        return False


# ── Per-Ticker Error Log (NaN/Debugging) ──
ERROR_LOG_PATH = os.path.expanduser("~/.hermes/shared/reports/renee/debug/per-ticker-errors.jsonl")


def log_ticker_error(ticker, step, error_type, message="", raw_snapshot=None):
    """Log a per-ticker error to JSONL. Does NOT block pipeline — errors are logged, pipeline continues."""
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker,
            "step": step,
            "error_type": error_type,
            "message": message,
            "raw_data_snapshot": raw_snapshot,
        }
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # don't let error-logging itself crash the pipeline


# ── Verify-after-write helper (t_5034ab16 W33) ──
def _verify_write(filepath, is_json=False, min_size=50):
    """Re-read a file after writing to confirm it was saved correctly.
    Returns True if the file exists, is >= min_size bytes, and (if is_json) is valid JSON.
    Returns False on any failure.
    """
    try:
        if not os.path.exists(filepath):
            return False
        sz = os.path.getsize(filepath)
        if sz < min_size:
            return False
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) < min_size:
            return False
        if is_json:
            json.loads(content)
        return True
    except (OSError, json.JSONDecodeError, ValueError):
        return False


# ── Macro context: Treasury H.15 bond yields (same-day) + gold GC=F ──
# P0-3 + P1-5 fix (t_1dacac8d): bond context must use the SAME trading day's
# close (or be explicitly labeled T-1 with a reason); the gold reference
# must use the LATEST GC=F close, never a stale value. Signal label is derived
# from the actual bp move — a +5bp day is , never .
# m1 fix (Zoe 09-03, t_8cd84165): the data source is Treasury.gov H.15 daily
# yield curve (fred_data.py fetches the Treasury XML), NOT FRED DGS2. FRED
# DGS2 (rubric #77 canonical) republishes the SAME underlying series with a
# T+1 business-day lag. The generator's out dict carries a "source" field so
# the report header + data.json label the source correctly (previously
# mislabeled "(FRED, ...)").
BOND_SOURCE_LABEL = ("Treasury H.15 (US Treasury daily yield curve XML "
                     "via fred_data.py)")


def classify_bond_regime(dgs2_bp, dgs10_bp, dgs30_bp, spread_change_bp):
    """Classify the bond-curve regime from same-day bp moves (Zoe 08-28 m1).

    Returns (regime_label, zh_label, signal) where regime_label is one of:
      bull-steepening / bull-flattening / bear-steepening / bear-flattening /
      twist / flat
    The classification uses the classic 2s10s spread-change framing:
      - avg bp move > 0  → bear (rates up)
      - avg bp move < 0  → bull (rates down)
      - spread narrowing → flattening ; widening → steepening
      - 2Y/10Y moving opposite directions with material bp moves → twist
    Example (08-28): DGS2 +14bp > DGS10 +6bp > DGS30 +3bp, spread −8bp
    → avg +7.7bp (bear) + narrowing (−8bp) → bear-flattening (risk-off /
    hawkish signal).
    """
    if (dgs2_bp is None or dgs10_bp is None or dgs30_bp is None
            or spread_change_bp is None):
        return ("N/A", "N/A", "N/A")
    # Twist: short and long ends move opposite ways (material bp each).
    if dgs2_bp * dgs10_bp < 0 and abs(dgs2_bp) >= 5 and abs(dgs10_bp) >= 5:
        return ("twist", "twist",
                "2Y " + f"{dgs2_bp:+.0f}bp / 10Y {dgs10_bp:+.0f}bp opposite")
    avg_bp = (dgs2_bp + dgs10_bp + dgs30_bp) / 3.0
    bear = avg_bp > 0.5
    bull = avg_bp < -0.5
    flat_rates = not (bear or bull)
    if spread_change_bp > 3.0:
        shape = "steepening"
    elif spread_change_bp < -3.0:
        shape = "flattening"
    else:
        shape = "flat"
    if flat_rates or shape == "flat":
        return ("flat", "flat", "minor yield/spread move")
    if bear and shape == "flattening":
        return ("bear-flattening", "bear-flattening",
                "risk-off / hawkish — short end up > long, spread narrows")
    if bull and shape == "flattening":
        return ("bull-flattening", "bull-flattening",
                "rates down, short end down > long — spread narrows")
    if bear and shape == "steepening":
        return ("bear-steepening", "bear-steepening",
                "rates up, long end up > short — spread widens")
    return ("bull-steepening", "bull-steepening",
            "rates down, long end down > short — spread widens")


def fetch_macro_context(today):
    """Fetch same-trading-day Treasury H.15 yields (2Y/10Y/30Y) via
    fred_data.py (Treasury.gov daily yield curve XML — m1 source fix
    t_8cd84165: this is NOT FRED DGS2; FRED republishes the same series T+1)
    and latest GC=F gold close + GLD 1D% via yfinance.

    Returns dict with keys: source, as_of, as_of_label, dgs2, dgs10, dgs30,
    dgs2_bp, dgs10_bp, dgs30_bp, spread_2s10, dgs2_lag_note, gold_close,
    gold_date, gold_gld_1d_pct, gold_gld_close, gold_gld_material,
    gold_material_threshold_pct, lines.
    as_of == today when same-day close is available; otherwise T-1 labeled
    with the reason. Returns None on hard failure (report continues without
    the block).
    """
    out = {"as_of": None, "lines": []}
    try:
        import subprocess
        fred_script = os.path.expanduser("~/.hermes/scripts/fred_data.py")
        res = subprocess.run(
            [sys.executable, fred_script],
            capture_output=True, text=True, timeout=60,
        )
        if res.returncode != 0:
            raise RuntimeError(res.stderr[-300:] or "fred_data.py failed")
        records = json.loads(res.stdout)
        if not records:
            raise RuntimeError("empty Treasury H.15 records")
        latest = records[-1]
        prev = records[-2] if len(records) >= 2 else None
        latest_date = (latest["date"][:10] if isinstance(latest["date"], str)
                       else str(latest["date"])[:10])
        as_of = latest_date
        as_of_label = latest_date
        if as_of != today:
            # m1 fix (Zoe 09-03, t_8cd84165): source is Treasury H.15, NOT FRED.
            as_of_label = (f"{latest_date} (T-1 — same-day Treasury H.15 not yet "
                           f"published at run time)")

        def _num(rec, tenor):
            try:
                return float(rec["yields"].get(tenor))
            except (TypeError, ValueError):
                return None

        dgs2 = _num(latest, "2 yr")
        dgs10 = _num(latest, "10 yr")
        dgs30 = _num(latest, "30 yr")
        p2 = _num(prev, "2 yr") if prev else None
        p10 = _num(prev, "10 yr") if prev else None
        p30 = _num(prev, "30 yr") if prev else None

        def _bp(cur, pv):
            return (cur - pv) * 100 if (cur is not None and pv is not None) else None

        dgs2_bp = _bp(dgs2, p2)
        dgs10_bp = _bp(dgs10, p10)
        dgs30_bp = _bp(dgs30, p30)
        spread = (dgs10 - dgs2) * 100 if (dgs10 is not None and dgs2 is not None) else None
        spread_prev = (p10 - p2) * 100 if (p10 is not None and p2 is not None) else None
        spread_change_bp = (spread - spread_prev) if (spread is not None and spread_prev is not None) else None

        # Zoe 08-28 m1: explicit bond regime classification (bull/twist/bear/
        # flattening) so downstream (Alice macro) can read the field directly.
        regime_label, regime_zh, regime_signal = classify_bond_regime(
            dgs2_bp, dgs10_bp, dgs30_bp, spread_change_bp)

        # m1 fix (Zoe 09-03, t_8cd84165): DGS2 prev-day lag reference. FRED DGS2
        # (rubric #77 canonical) and Treasury H.15 2Y are the SAME underlying
        # series; FRED republishes with a T+1 business-day lag. When the H.15
        # same-day record is available (as_of == today), the latest FRED DGS2
        # observation is the PREVIOUS trading day's value. Emit both the date and
        # value so the report header + data.json can disclose the lag instead of
        # mislabeling the live H.15 value as "FRED" (09-03 incident).
        dgs2_lag_note = None
        if p2 is not None and prev is not None:
            _prev_date = (prev["date"][:10] if isinstance(prev["date"], str)
                          else str(prev["date"])[:10])
            if as_of == today and _prev_date != today:
                dgs2_lag_note = (
                    f"FRED DGS2 {_prev_date} = {p2:.2f}% (rubric #77 canonical; "
                    f"{today} H.15 live shown above, FRED republishes T+1)")

        out.update({
            "source": BOND_SOURCE_LABEL,
            "as_of": as_of, "as_of_label": as_of_label,
            "dgs2": dgs2, "dgs10": dgs10, "dgs30": dgs30,
            "dgs2_bp": dgs2_bp, "dgs10_bp": dgs10_bp, "dgs30_bp": dgs30_bp,
            "spread_2s10": spread,
            "spread_change_bp": spread_change_bp,
            "dgs2_lag_note": dgs2_lag_note,
            "bond_regime": regime_label,
            "bond_regime_zh": regime_zh,
            "bond_regime_signal": regime_signal,
        })

 # Signal from the actual bp move — never call a +5bp day .
        def _sig(bp):
            if bp is None:
                return "N/A"
            if bp >= 5:
                return "sharp rise"
            if bp <= -5:
                return "sharp fall"
            if bp >= 3:
                return "rise"
            if bp <= -3:
                return "fall"
            return "flat"

        lines = []
        if dgs2 is not None:
            lines.append(f"| DGS2 (2Y) | {dgs2:.2f}% | "
                         + (f"{dgs2_bp:+.0f}bp" if dgs2_bp is not None else "—")
                         + f" | {_sig(dgs2_bp)} |")
        if dgs10 is not None:
            lines.append(f"| DGS10 (10Y) | {dgs10:.2f}% | "
                         + (f"{dgs10_bp:+.0f}bp" if dgs10_bp is not None else "—")
                         + f" | {_sig(dgs10_bp)} |")
        if dgs30 is not None:
            lines.append(f"| DGS30 (30Y) | {dgs30:.2f}% | "
                         + (f"{dgs30_bp:+.0f}bp" if dgs30_bp is not None else "—")
                         + f" | {_sig(dgs30_bp)} |")
        if spread is not None:
            slope = "OK: no inversion / no bear twist" if spread > 0 else ("WARN: inversion" if spread < 0 else "flat")
            # spread is stored in bp units (e.g. 50.0); display as percent (0.50%)
            lines.append(f"| 10Y-2Y spread | {spread/100:+.2f}% | positive slope | {slope} |")
        if regime_label != "N/A":
            # Zoe 08-28 m1: explicit bond regime classification row so
            # downstream Alice macro can read it directly from the report.
            spread_chg_s = (f"{spread_change_bp:+.0f}bp" if spread_change_bp is not None else "—")
            lines.append(f"| **Bond Regime** | **{regime_zh}** | spread {spread_chg_s} | {regime_signal} |")
        out["lines"] = lines
    except Exception as e:
        print(f"[⚠] macro context fetch failed: {e}", file=sys.stderr)
        return None

    # Gold GC=F latest close (P1-5: must be latest, e.g. $4,661.60 on 08-21)
    try:
        df = yf.download("GC=F", period="10d", interval="1d", progress=False, auto_adjust=False)
        if df is not None and len(df) > 0:
            close = df["Close"].dropna()
            if len(close) > 0:
                # FutureWarning-safe: close.iloc[-1] may be a single-element
                # Series (yfinance dtype variants) — unwrap before float().
                last_close = close.iloc[-1]
                if hasattr(last_close, "iloc"):
                    last_close = last_close.iloc[0]
                out["gold_close"] = float(last_close)
                out["gold_date"] = str(close.index[-1].date())
    except Exception as e:
        print(f"[⚠] gold fetch failed: {e}", file=sys.stderr)
        out["gold_close"] = None
        out["gold_date"] = None

    # Gold GLD 1D% (Zoe 08-28 m3): 1D% MUST use GLD (ETF, no roll inflation),
    # never GC=F continuous. GC=F level is kept for the absolute price; the
    # daily change benchmark is GLD. Material-move threshold is the named
    # constant GOLD_MATERIAL_MOVE_PCT = 1.5 (Zoe 09-03 m2, t_8cd84165) —
    # emitted into the ctx so data.json + gold header are self-describing.
    try:
        df = yf.download("GLD", period="10d", interval="1d", progress=False, auto_adjust=False)
        if df is not None and len(df) >= 2:
            close = df["Close"].dropna()
            if len(close) >= 2:
                last = close.iloc[-1]
                prev = close.iloc[-2]
                if hasattr(last, "iloc"):
                    last = last.iloc[0]
                if hasattr(prev, "iloc"):
                    prev = prev.iloc[0]
                gld_1d = (float(last) / float(prev) - 1.0) * 100.0
                out["gold_gld_1d_pct"] = round(gld_1d, 2)
                out["gold_gld_close"] = float(last)
                out["gold_gld_material"] = abs(gld_1d) >= GOLD_MATERIAL_MOVE_PCT
                out["gold_material_threshold_pct"] = GOLD_MATERIAL_MOVE_PCT
    except Exception as e:
        print(f"[⚠] gold GLD 1D% fetch failed: {e}", file=sys.stderr)
        out["gold_gld_1d_pct"] = None
        out["gold_gld_material"] = False
    return out


def gold_context_summary(macro_ctx):
    """Build a self-describing gold_context block for data.json (Zoe 09-03 m2,
    t_8cd84165): GC=F level + GLD 1D% + the gold-specific material-move
    threshold, so consumers see WHY a GLD move flagged (e.g. +1.85%) while the
    equity universe uses a different 5.0% gate. Returns None when macro_ctx is
    unavailable or has no gold data."""
    if not macro_ctx or not macro_ctx.get("gold_close"):
        return None
    return {
        "source": "GC=F level (futures, yfinance) + GLD 1D% (ETF canonical)",
        "gold_date": macro_ctx.get("gold_date"),
        "gc_f_level": macro_ctx.get("gold_close"),
        "gld_close": macro_ctx.get("gold_gld_close"),
        "gld_1d_pct": macro_ctx.get("gold_gld_1d_pct"),
        "material": bool(macro_ctx.get("gold_gld_material")),
        "material_threshold_pct": GOLD_MATERIAL_MOVE_PCT,
        "material_threshold_note": (
            f"gold-specific: GLD |1D%| ≥ {GOLD_MATERIAL_MOVE_PCT:.1f}% "
            f"(symmetric with daily-social §9); equity universe uses "
            f"MATERIAL_MOVE_PCT = {MATERIAL_MOVE_PCT:.1f}% — two different gates"),
    }


# ══════════════════════════════════════════════════════════════════════
# RSI LABEL DIRECTION + DRIVER CAUSATION (Zoe W34 #2b, t_e6ad7a37)
# ══════════════════════════════════════════════════════════════════════
# Rubric #81 family, 3rd recurrence (07-15 → 08-18 → 08-21): the 08-21 T&M
# report labelled UNH RSI=31.4 / PNC RSI=35.6 (oversold zone) as
# "overbought". Root cause: the label was derived from the RSI SUB-SCORE.
# score_rsi maps RSI<30→12 AND RSI>75→5, so a low RSI score can mean EITHER
# weak RSI (30-42) OR overbought (RSI>75). Labeling by score inverts the
# direction for low-RSI stocks. Labels MUST derive from the RAW RSI value.
#
# Driver semantics (M2): the Driver column lists the score-change CAUSE
# (pull-up factors for gainers / pull-down factors for losers), derived from
# per-indicator score DELTAS vs the previous day — never current indicator
# STATE. A gainer whose RSI is still weak but rose from 30→34 says
# "RSI +4 (oversold bounce)", not "RSI ".

RSI_OVERSOLD_LABEL = "RSI oversold"
RSI_OVERBOUGHT_LABEL = "RSI overbought"
RSI_MOMENTUM_LABEL = "RSI momentum"
RSI_WEAK_LABEL = "RSI "

# ── RSI scoring-zone labels (Zoe 08-27 M2, t_692f4462) ──
# The RSI sub-score curve is NON-monotonic (score_rsi):
# rsi < 30 → 12 (oversold mean-reversion) <30 → "oversold "
# 30–40 → 1–5 () 30–40 → ""
# 40–70 → 6–16 (/) 40–60 → "", 60–70 → "momentum"
# 70–75 → 17–19 (, bullish ) 70–75 → "momentum "
# rsi > 75 → 5 () >75 → "overbought "
# A single "overbought"/"oversold" word conflated two OPPOSITE scoring
# outcomes (MRK 72.0 → sub 18 vs GILD 80.5 → sub 5, both "overbought").
# Labels are now zone-precise so the reader can tell sweet-spot from penalty.
RSI_MOMENTUM_STRONG_LABEL = "RSI momentum " # 70–75 sweet spot (highest sub-score)
RSI_OVERBOUGHT_PENALTY_LABEL = "RSI overbought " # >75 penalty
RSI_OVERSOLD_SWEET_LABEL = "RSI oversold " # <30 mean-reversion sweet spot
RSI_LOW_LABEL = "RSI " # 30–40 low band

# Zone boundaries for the PRECISE labels (distinct from the guardrail zones
# above — the old label thresholds 35/70 were only for the auto-check):
RSI_OVERBOUGHT_PENALTY_ZONE = 75.0   # >75 → penalty
RSI_MOMENTUM_STRONG_ZONE = 70.0      # 70–75 → sweet spot (sub 17–19)
RSI_OVERSOLD_SWEET_ZONE = 30.0       # <30 → oversold sweet (sub 12)
RSI_LOW_BAND_ZONE = 40.0             # 30–40 → low band (sub 1–5)

# Zoe auto-check zones (label direction guardrails):
#   rsi < 35  containing "overbought"  → FLAG
#   rsi > 65  containing "oversold"    → FLAG
RSI_OVERSOLD_ZONE = 35.0
RSI_OVERBOUGHT_ZONE = 65.0
# Label thresholds (stricter than the guardrail zones so the mapping itself
# can never trip the auto-check): oversold < 35, overbought > 70.
RSI_OVERSOLD_THRESHOLD = 35.0
RSI_OVERBOUGHT_THRESHOLD = 70.0


def rsi_state_label(raw_rsi):
    """Map a RAW RSI value to its zone-precise state label (Zoe 08-27 M2).

    The RSI sub-score curve is non-monotonic, so labels must be zone-precise:
      rsi > 75 → "RSI overbought " (penalty sub-score 5)
      rsi 70–75 → "RSI momentum " (sweet spot, sub-score 17–19)
      rsi < 30 → "RSI oversold " (mean-reversion sweet spot, sub 12)
      rsi 30–40 → "RSI " (low band, sub 1–5)
      rsi 60–70  → "RSI momentum"         (momentum band)
      rsi 40–60 → "RSI " (weak/neutral)
    None → None. Never derived from the RSI sub-score.
    """
    if raw_rsi is None:
        return None
    if raw_rsi > RSI_OVERBOUGHT_PENALTY_ZONE:
        return RSI_OVERBOUGHT_PENALTY_LABEL
    if raw_rsi >= RSI_MOMENTUM_STRONG_ZONE:
        return RSI_MOMENTUM_STRONG_LABEL
    if raw_rsi < RSI_OVERSOLD_SWEET_ZONE:
        return RSI_OVERSOLD_SWEET_LABEL
    if raw_rsi < RSI_LOW_BAND_ZONE:
        return RSI_LOW_LABEL
    if raw_rsi >= 60:
        return RSI_MOMENTUM_LABEL
    return RSI_WEAK_LABEL


def rsi_label_direction_violation(raw_rsi, label):
    """Zoe W34 #2b auto label-direction check.

    Returns a violation string when:
      rsi < 35  and the label/text contains "overbought", or
      rsi > 65  and the label/text contains "oversold".
    Returns None when direction is correct (or rsi/label missing).
    """
    if raw_rsi is None or not label:
        return None
    low = raw_rsi < RSI_OVERSOLD_ZONE
    high = raw_rsi > RSI_OVERBOUGHT_ZONE
    if low and "overbought" in label:
        return (f"rsi={raw_rsi:.1f} (oversold zone <{RSI_OVERSOLD_ZONE:.0f}) "
                f"labelled '{label}'")
    if high and "oversold" in label:
        return (f"rsi={raw_rsi:.1f} (overbought zone >{RSI_OVERBOUGHT_ZONE:.0f}) "
                f"labelled '{label}'")
    return None


def driver_from_scores(scores, raw=None):
    """State-based driver (fallback when no previous-day breakdown exists).

    Lists current indicator STATE: MACD strong/weak, RSI state label,
    bull/bear MA, strong/weak trend, high/low vol. Top 3 factors.
    """
    parts = []
    m = scores["macd"]
    if m >= 18:
        parts.append("MACD strong")
    elif m <= 5:
        parts.append("MACD weak")
    raw_rsi = raw.get("rsi") if raw else None
    rsi_lbl = rsi_state_label(raw_rsi)
    if rsi_lbl:
        parts.append(rsi_lbl)
    else:
        r = scores["rsi"]
        if r >= 15:
            parts.append("RSI momentum")
    ma = scores["ma"]
    if ma >= 18:
        parts.append("bull MA")
    elif ma <= 5:
        parts.append("bear MA")
    a = scores["adx"]
    if a >= 16:
        parts.append("strong trend")
    elif a <= 8:
        parts.append("weak trend")
    v = scores["volume"]
    if v >= 15:
        parts.append("high vol")
    elif v <= 6:
        parts.append("low vol")
    return ", ".join(parts[:3]) if parts else "mixed"


def driver_from_change(scores, prev_breakdown, raw=None, direction=1,
                       prev_raw=None):
    """CAUSE-based driver (Zoe W34 M2): derive from per-indicator score
    deltas vs the previous day's score_breakdown.

    direction +1 = gainer/BUY rows → list PULL-UP factors (positive deltas)
    direction -1 = loser rows      → list PULL-DOWN factors (negative deltas)

    Falls back to state-based driver_from_scores when no previous breakdown.

    Zoe 08-27 M2 (t_692f4462): the RSI driver MUST attach the raw RSI
    before→after values whenever the previous day's raw RSI is available.
    Zoe 08-28 M1 root-fix (t_fb574bfa): the PRIMARY number is now the RAW
    RSI delta (e.g. "RSI 80.5→72.0 (−8.5) [sub +13]") with the sub-score
    change in secondary position — never the sub-score delta, whose
    non-monotonic zone curve (70–75 sweet spot / >75 penalty) can point
    opposite to raw RSI direction (GILD sub +13 while raw FELL; HD sub −12
    while raw ROSE). When prev_raw is missing (first run, unit tests),
    fall back to zone-precise short tags.
    """
    raw = raw or {}
    if not prev_breakdown:
        return driver_from_scores(scores, raw)
    ind_labels = [("macd", "MACD"), ("rsi", "RSI"), ("ma", "MA"),
                  ("adx", "ADX"), ("volume", "Vol")]
    deltas = []
    for key, label in ind_labels:
        d = scores[key] - prev_breakdown.get(key, scores[key])
        deltas.append((key, label, d))
    if direction > 0:
        relevant = [(k, l, d) for k, l, d in deltas if d > 0]
        relevant.sort(key=lambda x: -x[2])
    else:
        relevant = [(k, l, d) for k, l, d in deltas if d < 0]
        relevant.sort(key=lambda x: x[2])
    parts = []
    for key, label, d in relevant[:3]:
        txt = f"{label} {d:+d}"
        if key == "volume" and raw.get("volume_ratio") is not None:
            txt += f" ({raw['volume_ratio']:.2f}x)"
        elif key == "rsi":
            raw_rsi = raw.get("rsi")
            if raw_rsi is not None and prev_raw is not None:
                # Zoe 08-28 M1 root-fix (t_fb574bfa): PRIMARY number is the
                # RAW RSI delta, sub-score change moves to secondary position.
                # The RSI scoring zone is NON-monotonic (75 penalty cliff,
                # 70-75 sweet zone, <30 sweet / 30-40 low), so a sub-score
                # delta can point OPPOSITE to raw RSI (GILD sub +13 while raw
                # FELL 80.5→72.0; HD sub −12 while raw ROSE 25.4→30.0). The
                # first number the reader sees must be the market direction.
                txt = (f"RSI {prev_raw:.1f}→{raw_rsi:.1f} "
                       f"({raw_rsi - prev_raw:+.1f}) [sub {d:+d}]")
            elif direction > 0 and raw_rsi is not None:
                # Fallback tags when no prev raw (first run / unit tests):
                # zone-precise, never a bare "overbought".
                if raw_rsi < RSI_OVERSOLD_ZONE:
                    txt += " (oversold bounce)"
                elif raw_rsi > 75.0:
                    txt += " (overbought )"
                elif raw_rsi >= 70.0:
                    txt += " (momentum )"
        parts.append(txt)
    if not parts:
        return driver_from_scores(scores, raw)
    return ", ".join(parts)


def scan_rsi_label_violations(results):
    """Auto label-direction check over every scored row (Zoe W34 #2b)."""
    violations = []
    for r in results:
        raw = r.get("raw", {}) if isinstance(r, dict) else {}
        rsi = raw.get("rsi")
        if rsi is None:
            continue
        label = rsi_state_label(rsi)
        v = rsi_label_direction_violation(rsi, label)
        if v:
            violations.append(f"{r.get('ticker')}: {v}")
    return violations


def scan_driver_label_violations(results, prev_breakdowns=None):
    """Auto-check the CAUSE driver strings (both directions) for RSI
    direction inversions (Zoe W34 #2b — covers gainers AND losers)."""
    violations = []
    prev_breakdowns = prev_breakdowns or {}
    for r in results:
        raw = r.get("raw", {}) if isinstance(r, dict) else {}
        rsi = raw.get("rsi")
        if rsi is None:
            continue
        scores = r.get("scores")
        if not isinstance(scores, dict):
            continue
        for direction in (1, -1):
            d = driver_from_change(scores, prev_breakdowns.get(r.get("ticker")),
                                   raw, direction=direction)
            v = rsi_label_direction_violation(rsi, d)
            if v:
                violations.append(
                    f"{r.get('ticker')} (direction={direction:+d}): {v}")
    return violations


def rsi_driver_direction_violation(scores, prev_breakdown, raw=None,
                                   prev_raw=None):
    """Zoe 08-27 M2 (t_692f4462): driver-direction vs raw-RSI-direction
    cross-check.

    The RSI sub-score curve is NON-monotonic (70–75 → 17–19 sweet spot,
    >75 → 5 penalty; <30 → 12 sweet, 30–40 → 1–5 low), so a positive
    sub-score delta can accompany a FALLING raw RSI (MRK 78.0→72.0 with
    sub +13 on 08-27). The old W34 #2b scan only checked label TEXT vs raw
    RSI — it never checked driver DIRECTION vs raw RSI direction, so the
    footer claimed "0 violations" while MRK/AMGN/HON contradicted.

    Returns a violation string when the raw RSI moved materially (|Δ| >=
    0.5) in the OPPOSITE direction to the RSI sub-score delta; None when
    directions agree or data is missing.
    """
    if not prev_breakdown or raw is None or prev_raw is None:
        return None
    cur_rsi = raw.get("rsi")
    if cur_rsi is None:
        return None
    sub_prev = prev_breakdown.get("rsi")
    sub_cur = scores.get("rsi") if isinstance(scores, dict) else None
    if sub_prev is None or sub_cur is None:
        return None
    sub_delta = sub_cur - sub_prev
    raw_delta = cur_rsi - prev_raw
    if sub_delta == 0 or abs(raw_delta) < 0.5:
        return None
    if sub_delta > 0 and raw_delta < 0:
        return (f"RSI sub {sub_delta:+d} vs raw {prev_raw:.1f}→{cur_rsi:.1f} "
                f"({raw_delta:+.1f}) — sub↑ raw↓ contradiction")
    if sub_delta < 0 and raw_delta > 0:
        return (f"RSI sub {sub_delta:+d} vs raw {prev_raw:.1f}→{cur_rsi:.1f} "
                f"({raw_delta:+.1f}) — sub↓ raw↑ contradiction")
    return None


def scan_driver_direction_violations(results, prev_breakdowns=None,
                                     prev_raws=None):
    """Zoe 08-27 M2: scan every row for driver-direction vs raw-RSI-direction
    contradictions (needs prev-day raw RSI per ticker)."""
    violations = []
    prev_breakdowns = prev_breakdowns or {}
    prev_raws = prev_raws or {}
    for r in results:
        ticker = r.get("ticker")
        v = rsi_driver_direction_violation(
            r.get("scores"), prev_breakdowns.get(ticker),
            r.get("raw"), prev_raws.get(ticker))
        if v:
            violations.append(f"{ticker}: {v}")
    return violations


def compute_sector_momentum_map(results):
    """Zoe 09-04 M1 (t_94cfd4c8): sector 'Adj mean' map.

    sector_momentum[s] = round(mean(Adj score of TODAY'S universe members in
    sector s)) — an intra-universe cross-sectional attribution recomputed
    fresh from THIS run's scoring results each run. It is NOT sector ETF
    relative strength / NOT a broader-market sample / NOT a rolling window.
    A single-member sector value equals that member's Adj round (e.g.
    Basic Materials = LIN only). This is what the Full Ranking "Adj"
    column shows; the header carries the full methodology note.
    """
    sector_scores = {}
    sector_counts = {}
    for r in results:
        sec = r.get("sector", "")
        if sec:
            sector_scores[sec] = sector_scores.get(sec, 0) + r["total"]
            sector_counts[sec] = sector_counts.get(sec, 0) + 1
    return {s: round(sector_scores[s] / sector_counts[s]) for s in sector_scores}


def format_momentum_table_1d_cell(r, score_change, prev_breakdowns=None,
                                  prev_raws=None):
    """Zoe 09-04 m3 (t_94cfd4c8): inline 1D% cell for the Gainer/Loser tables.

    Flags (auto-emitted so table-level readability never depends on header /
    footer notes):
      ⚠️ prefix    when the scoreΔ direction OPPOSES the 1D% direction
                   (score gainer but price DOWN / score loser but price UP) —
                   the composite score is NOT price momentum.
      [sub↔raw opposite] when the RSI sub-score delta opposes the raw RSI delta
                   (VRTX raw 76.2→65.0, Δ−11.2 but sub +10 = leaving the
                   overbought penalty zone; HD raw 26.6→34.9, Δ+8.3 but
                   sub −10 = leaving the oversold sweet spot) — non-monotonic
                   RSI scoring-curve design, not momentum improvement.
    Also keeps the single-stock |1D%| ≥ MATERIAL_MOVE_PCT 🔴/🟢 suffix used
    by the Full Ranking 1D% column (same threshold — never disagrees).
    """
    raw = r.get("raw") or {}
    chg_pct = raw.get("change_pct")
    if chg_pct is None or (isinstance(chg_pct, float) and math.isnan(chg_pct)):
        return "—"
    cell = f"{chg_pct * 100:+.2f}%"
    if abs(chg_pct * 100.0) >= MATERIAL_MOVE_PCT:
        cell += (" 🔴" if chg_pct < 0 else " 🟢")
    if (score_change > 0 and chg_pct < 0) or (score_change < 0 and chg_pct > 0):
        cell = f"⚠️ {cell}"
    v = rsi_driver_direction_violation(
        r.get("scores"), (prev_breakdowns or {}).get(r.get("ticker")),
        raw, (prev_raws or {}).get(r.get("ticker")))
    if v:
        cell += " [sub↔raw opposite]"
    return cell


def g1_session_scaffold(today, regime, spy_adx, option_g_active):
    """NEW-SYSTEM G1 headings for daily T&M (ART-TM-SESSION-D).

    Insert after Header ``---`` and before the old-system Section 1 dump.
    Uses only regime / ADX / today. No news crawl → ``News: miss``.
    Daily Option G note OK. Never desk Risk-on/off.
    """
    adx_s = "N/A" if spy_adx is None else spy_adx
    if option_g_active:
        og_note = "Option G active — effective BUY suppressed (daily; SPY ADX <25)"
    else:
        og_note = "Option G not suppressing effective BUY"
    return "\n".join([
        "## Session summary",
        f"- Session date: {today} · T&M regime: {regime} (SPY ADX {adx_s}) — {og_note}",
        "- Top movers: see live pack ranking below (`tm_score` from this run only; no invented prices)",
        "- Breadth note: brackets / BUY count from run pack",
        f"- **Alice pull:** Market insight — {today} {regime} tape; SPY ADX {adx_s} (1–2 lines)",
        "- ❌ desk Risk-on/off final call",
        "",
        "## Market insight",
        f"- Tape: {today} T&M regime `{regime}` (SPY ADX {adx_s}) — as-of pack",
        f"- Mechanism: {og_note}",
        "- Breadth / leadership: pack ranking (pack truth only)",
        "- ❌ desk Risk-on/off; ❌ desk-wide Macro view (→ Alice · Zoe Z-MI-02)",
        "",
        "## News/Market check (Renee-topic)",
        "- 📰 News: miss",
        f"- 📊 Market tape: {today} regime `{regime}` · SPY ADX {adx_s} · leadership pack ranking",
        "",
        "## Lenses",
        f"- Macro: T&M regime `{regime}` overlay (ADX {adx_s}) — not desk Risk-on/off",
        "- Micro: pack / ticker structure from pack ranking",
        "- Market: volume/range / narrative pack · Conf effect",
        "- Dominant: mixed",
        "",
    ])


def build_suppressed_buy_section(results, regime, spy_adx, prev_scores=None):
    """List non-BUY rows whose published score is >= 60.

    In-memory generator rows use ``total`` / ``verdict``. Saved packs use
    ``daily_score`` / ``daily_verdict``. This widens the visible held-back
    list (previously score >= 90 only). It does not change the ADX < 25 gate.
    """
    if prev_scores is None:
        prev_scores = {}

    def _score(row):
        raw = row.get("total")
        if raw is None:
            raw = row.get("daily_score")
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    cands = []
    for row in results:
        score_f = _score(row)
        if score_f is None or score_f < 60:
            continue
        verdict = str(row.get("verdict") or row.get("daily_verdict") or "")
        verdict_u = verdict.upper()
        if "BUY" in verdict_u and "NO" not in verdict_u:
            continue
        cands.append((score_f, row, verdict))
    cands.sort(key=lambda item: item[0], reverse=True)

    adx_s = "N/A" if spy_adx is None else f"{float(spy_adx):.1f}"
    lines = [
        "### Suppressed BUY-eligible (Option G) — Adj score ≥60 candidates",
    ]
    if regime == "choppy":
        lines.append(f"> SPY ADX {adx_s} — ADX < 25,no trades today(Option G)")
    lines.append(
        "| Ticker | Adj | Base | Bracket | Prev | Raw RSI | Verdict | Entry | SL | TP |"
    )
    lines.append(
        "|--------|:---:|:----:|:-------:|:----:|:------:|:-------:|------:|---:|---:|"
    )
    for score_f, row, verdict in cands:
        ticker = row.get("ticker")
        prev_s = prev_scores.get(ticker) if isinstance(prev_scores, dict) else None
        prev_s_s = f"{prev_s:.1f}" if isinstance(prev_s, (int, float)) else ""
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else None
        if raw is None and isinstance(row.get("raw_indicators"), dict):
            raw = row["raw_indicators"]
        raw = raw or {}
        raw_rsi = raw.get("rsi")
        rsi_s = f"{raw_rsi:.1f}" if isinstance(raw_rsi, (int, float)) else "—"
        base = row.get("base_5indicator_total", score_f)
        try:
            base_s = f"{float(base):.1f}"
        except (TypeError, ValueError):
            base_s = f"{score_f:.1f}"
        bracket = row.get("bracket") or row.get("daily_bracket") or ""

        def _px(key):
            val = row.get(key)
            try:
                num = float(val) if val is not None else None
            except (TypeError, ValueError):
                num = None
            if num is None:
                return "—"
            return f"${num:.2f}"

        lines.append(
            f"| {ticker} | {score_f:.1f} | {base_s} "
            f"| {bracket} | {prev_s_s} | {rsi_s} | {verdict} | "
            f"{_px('entry_price')} | {_px('stop_loss')} | {_px('take_profit')} |"
        )
    if not cands:
        lines.append("| (none) | — | — | — | — | — | — | — | — | — |")
    if regime == "choppy":
        lines.append(
            f"> Option G active (choppy, SPY ADX {adx_s}) suppresses ALL trade signals — "
            "these are the Adj-score (≥60) candidates held back today."
        )
    else:
        lines.append(
            "> Score ≥60 but verdict ≠ BUY (DMI gating) — score-eligible, not executable."
        )
    return "\n".join(lines)


def main():
    # ── CLI (Zoe 09-01 B1b, t_b5acc944) ──
    # --date YYYY-MM-DD : regenerate a DATED report (post-close regeneration
    #                     of {date} from close data).
    # --note TEXT       : annotation appended to the Run ID header + stored as
    #                     data.json run_note (e.g. "post-close regeneration").
    # --refresh         : delete TODAY's cache dir before loading so the run
    #                     REFETCHES close data from yfinance (never touches
    #                     historical date keys — deterministic replay intact).
    _parser = argparse.ArgumentParser(
        description="Daily Trend & Momentum Report generator (Renee)")
    _parser.add_argument("--date", default=None,
                         help="report date YYYY-MM-DD (default: today UTC)")
    _parser.add_argument("--note", default=None,
                         help="annotation for the Run ID (e.g. post-close regeneration)")
    _parser.add_argument("--refresh", action="store_true",
                         help="delete today's cache dir before loading (refetch close data)")
    _args, _ = _parser.parse_known_args()

    report_date = _args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_note = _args.note

    # --date is ONLY for SAME-DAY post-close regeneration (t_b5acc944 B1b).
    # The generator always fetches TODAY's cache key — a past --date would
    # write today's bars under a past filename (data corruption). Historical
    # rebuilds belong to build_snapshot.py / the weekly pipeline, not here.
    if _args.date:
        _today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if _args.date != _today_utc:
            print(f"[❌] --date {_args.date} != today UTC {_today_utc}. "
                  f"The generator supports ONLY same-day post-close regeneration "
                  f"(rerun of today's report from close data). Historical replay "
                  f"is not supported — data would be today's bars under a past "
                  f"filename.", file=sys.stderr)
            sys.exit(2)

    if _args.refresh:
        today_cache_dir = os.path.join(
            CACHE_ROOT, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        if os.path.isdir(today_cache_dir):
            shutil.rmtree(today_cache_dir)
            print(f"[♻️] --refresh: removed today's cache dir {today_cache_dir} — "
                  f"refetching post-close data from yfinance", file=sys.stderr)
        else:
            print(f"[♻️] --refresh: no cache dir {today_cache_dir} to remove",
                  file=sys.stderr)

    # ── Market Close Guard — EARLY gate (Zoe 09-01 B1, t_b5acc944) ──
    # Run BEFORE any fetch/scoring: a current-day run before 20:00 UTC must
    # exit immediately. This is what makes "pre-close generator run is
    # REJECTED" cheap AND prevents polluting today's cache with intraday bars
    # (the 09-01 15:52 run fetched intraday data into the cache; the post-
    # close regeneration then had to bypass it). The SPY volume-based
    # partial-bar check still runs at the full freshness stage below (it
    # needs the batch), so an intraday cache served after 20:00 is still
    # blocked. Historical replay (--date in the past) is exempt.
    from tm_freshness_watchdog import check_market_close_guard
    _early_close = check_market_close_guard({}, today=report_date)
    if not _early_close["ok"]:
        print(f"[❌] MARKET CLOSE GUARD (Zoe 09-01 B1): refusing to run", file=sys.stderr)
        for _r in _early_close["reasons"]:
            print(f"[❌]   - {_r}", file=sys.stderr)
        print(f"[❌] A {report_date} close report must be generated AFTER 20:00 UTC "
              f"(16:00 ET). Run again after close (optionally with --refresh to "
              f"force refetch of close data).", file=sys.stderr)
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════
    # PIPELINE GUARD: Check DAILY baseline freshness (Rubric #82, P0 fix)
    # Baseline = most recent published daily report {date}-data.json in SHARED_DIR.
    # If that daily baseline is > max_trading_days behind today, auto-reject.
    # (weekly_snapshots freshness is checked separately by the weekly pipeline.)
    # ═══════════════════════════════════════════════════════════════
    guard_daily_report_generation(
        report_dir=SHARED_DIR,
        max_trading_days=5,
        fallback="no daily baseline",
    )

    print("[🚀] Daily Trend & Momentum Report", file=sys.stderr)
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting scan...", file=sys.stderr)

    universe = load_universe()

    # ── Environment note (08-11 Zoe BLOCKER t_b18a2102) ──
    # pandas_ta may be unavailable under the default interpreter (numba needs
    # numpy<=2.2; hermes venv has numpy 2.4). get_spy_adx() now falls back to
    # the manual true-Wilder implementation, so ADX is env-independent — but
    # surface a warning so operators know which path executed.
    try:
        import pandas_ta  # noqa: F401
    except Exception as e:
        print(f"[⚠️] pandas_ta unavailable ({e}) — get_spy_adx will use the "
              f"manual true-Wilder fallback (validated 0.0000 diff vs ta.adx).",
              file=sys.stderr)

    # Market regime from SPY daily — HARD-FAIL on invalid ADX (08-11 Zoe
    # BLOCKER t_b18a2102): get_regime_daily() now raises instead of silently
    # returning regime="ranging"/ADX=0, which previously bypassed Option G and
    # produced 19 false BUY signals.
    try:
        regime, spy_adx, vix_close = get_regime_daily()
    except Exception as e:
        print(f"[❌] FATAL: cannot determine market regime — {e}", file=sys.stderr)
        print("[❌] Refusing to score/publish with an unknown regime "
              "(prevents false BUY flood). If pandas_ta is broken, run with: "
              "/tmp/weekly_uv_venv/bin/python daily_trend_momentum.py",
              file=sys.stderr)
        sys.exit(2)
    print(f"[🌍] Regime: {regime} | SPY ADX: {spy_adx} | VIX: {vix_close}", file=sys.stderr)

    # ── ADX live verification (Zoe W32 rec #2, task t_43a4ebb6) ──
    # Before publishing, recompute SPY ADX with true-Wilder smoothing (manual,
    # no pandas_ta) on the SAME cached SPY data and compare against the cached
    # ADX used for the regime. |diff| > 1.0 -> BLOCK publish. The 08-11
    # incident showed a FLAG was printed but ignored, so the wrong regime was
    # still published — a wrong ADX must never reach the published report.
    adx_verify = None
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from verify_adx import verify_spy_adx
        adx_verify = verify_spy_adx(
            date=None,          # most recent cached SPY data (same basis)
            window="1y",        # matches get_spy_adx(period="1y", length=14)
            cached_override=spy_adx,
            length=14,
            threshold=1.0,
            use_cache=False,    # 08-20 P1 (t_85a14c20): verify on FRESH
                                # yfinance, not the cache being validated
        )
        if adx_verify.get("flagged"):
            print(f"[VERIFY_ADX] ⚠️  FLAG — cached SPY ADX {spy_adx} diverges from "
                  f"true-Wilder {adx_verify.get('true_wilder_adx')} "
                  f"(|diff| {adx_verify.get('diff')} > 1.0). Regime may be wrong.",
                  file=sys.stderr)
            print("[❌] FATAL: ADX verification FAILED — refusing to publish "
                  "report with an unverified regime.", file=sys.stderr)
            sys.exit(2)
        else:
            print(f"[VERIFY_ADX] ✅ OK — cached SPY ADX {spy_adx} matches true-Wilder "
                  f"{adx_verify.get('true_wilder_adx')} "
                  f"(|diff| {adx_verify.get('diff')}).", file=sys.stderr)
    except Exception as e:
        adx_verify = {"error": str(e), "flagged": False}
        print(f"[VERIFY_ADX] ⚠️  verify_adx failed (non-blocking): {e}", file=sys.stderr)

    # ── Load weekly watchlist tickers for ATR14 entry/SL/TP ──
    watchlist_tickers = load_watchlist_tickers()
    print(f"[📋] ATR14 will be calculated for {len(watchlist_tickers)} watchlist stocks", file=sys.stderr)

    # ── Load watchlist metadata (company, weekly score, source track) ──
    watchlist_meta = {}  # ticker -> {company, weekly_score, source}
    if os.path.exists(WATCHLIST_JSON):
        try:
            with open(WATCHLIST_JSON) as f:
                wl_data = json.load(f)
            for track_name in ("track_a", "track_b"):
                for entry in wl_data.get(track_name, {}).get("entries", []):
                    ticker = entry["ticker"]
                    watchlist_meta[ticker] = {
                        "company": entry.get("company", ""),
                        "weekly_score": entry.get("score", None),
                        "source": "Track A" if track_name == "track_a" else "Track B",
                    }
            print(f"[📋] Watchlist metadata loaded: {len(watchlist_meta)} entries", file=sys.stderr)
        except Exception as e:
            print(f"[⚠] Watchlist metadata load failed: {e}", file=sys.stderr)

    # ── Batch load OHLCV via daily data cache (deterministic) ──
    scoring_universe = list(universe)
    print(f"[📡] Loading {len(scoring_universe)} tickers (cached batch)...", file=sys.stderr)
    batch_data = {}
    batch_errors = []
    try:
        batch_data = get_or_fetch_batch_ohlcv(scoring_universe, period="1y")
        for t in scoring_universe:
            if t not in batch_data:
                batch_errors.append(t)
    except Exception as e:
        print(f"[⚠] Cached batch load failed: {e}", file=sys.stderr)
        batch_errors = scoring_universe[:]

    # Fallback: individually fetch tickers that failed cache
    for t in batch_errors[:]:
        if t in batch_data:
            continue
        try:
            df = yf.Ticker(t).history(period="250d")
            if not df.empty and len(df) >= 50:
                batch_data[t] = df
                batch_errors.remove(t)
        except Exception:
            batch_errors.append(t)

    print(f"[📡] Downloaded: {len(batch_data)}/{len(scoring_universe)} | Fallback: {len(batch_errors)} failed", file=sys.stderr)

    # ── T&M Freshness Watchdog (t_512ecc00, W34→W35 P0) ──
    # Report-layer as-of check BEFORE scoring: if the batch data's last bar
    # predates the expected trading day, block — a {today}-report must never
    # be built on stale data (08-20 incident: cache dir 2026-08-20/ held
    # 08-19 closes and was read as fresh). Reuses the t_85a14c20
    # expected-trading-day definition (UTC keys + weekend/holiday walk-back).
    from tm_freshness_watchdog import check_report_data_freshness, guard_report_freshness
    freshness = check_report_data_freshness(batch_data, today=report_date)
    if not freshness["fresh"]:
        guard_report_freshness(batch_data, today=report_date, block=True)  # prints + sys.exit(1)
    data_as_of = freshness["as_of"]
    expected_as_of = freshness["expected"]
    _today_str_here = report_date
    data_as_of_s = data_as_of.isoformat() if data_as_of else _today_str_here
    expected_as_of_s = expected_as_of.isoformat() if expected_as_of else _today_str_here
    print(f"[✅ FRESHNESS] data as-of {data_as_of_s} (expected {expected_as_of_s}) — report OK",
          file=sys.stderr)

    # ── Prev-day baseline (loaded BEFORE the screen so Rule 5 hysteresis can
    #    consult yesterday's PUBLISHED universe membership; Zoe 09-02 t_7915ddcc) ──
    _prev = load_prev_daily_comparison(report_date)
    prev_date = _prev.get("date", "")
    prev_path = _prev.get("path")
    daily_files = [_prev["path"]] if _prev.get("daily_files") else []
    prev_scores = _prev["scores"]
    prev_verdicts = _prev["verdicts"]
    prev_breakdowns = _prev["breakdowns"]
    prev_raws = _prev["raws"]
    prev_brackets = _prev["brackets"]
    prev_buy_effective = _prev["buy_effective"]
    prev_tickers = _prev["tickers"]
    prev_ranked = _prev["ranked"]
    prev_rank_index = _prev["rank_index"]

    # ── Score tickers ──
    results = []
    errors = 0
    screened_errors = 0
    atr_missed = 0
    screened_pass = 0
    # Zoe 09-02 challenge (t_7915ddcc): per-ticker screen-failure capture so
    # the universe-change note can disclose WHY a ticker left (never a bare
    # "−PFE" for a technical_screen exclusion) + hysteresis-kept disclosure.
    screen_failures = {}   # ticker -> {reason, metrics, prev_score, prev_rank}
    hysteresis_kept = {}   # ticker -> {avg_range_raw, prev_score, prev_rank}

    for i, ticker in enumerate(scoring_universe, 1):
        is_watchlist = ticker in watchlist_tickers
        print(f"[{i:3d}/{len(scoring_universe)}] {ticker:6s} ... ", end="", flush=True, file=sys.stderr)
        try:
            df = batch_data.get(ticker)
            if df is None or df.empty or len(df) < 50:
                print("❌ no data", file=sys.stderr)
                log_ticker_error(
                    ticker, step="yfinance_fetch", error_type="no_data",
                    message=f"df_empty={df.empty}, df_len={len(df)}, min_req=50",
                )
                errors += 1
                continue

            # Stage 1: Technical screen (fast — uses existing df)
            # prev_member feeds Rule 5 hysteresis (retain incumbents >= 1.8%,
            # admit new candidates >= 2.0%).
            screen_result = technical_screen(
                df, ticker=ticker, prev_member=(ticker in prev_tickers))
            if not screen_result["pass"]:
                if is_watchlist:
                    # Watchlist always gets scored regardless of screen
                    pass
                else:
                    met = screen_result.get("metrics", {})
                    print(f"⏭️ screen: {screen_result['reason']}", file=sys.stderr)
                    # Zoe 09-02 P1 #1: remember WHY — universe-change note will
                    # disclose it instead of a bare "−TICKER".
                    screen_failures[ticker] = {
                        "reason": screen_result["reason"],
                        "metrics": {k: met.get(k) for k in ("price", "3m_return", "dollar_vol", "vs_sma200", "consol_days", "consol_range", "avg_range", "avg_range_raw", "min_ema_dist") if k in met},
                    }
                    _psc = prev_scores.get(ticker)
                    if _psc is not None:
                        screen_failures[ticker]["prev_score"] = _psc
                        screen_failures[ticker]["prev_rank"] = prev_rank_index.get(ticker)
                    log_ticker_error(
                        ticker, step="technical_screen", error_type="screen_failed",
                        message=screen_result["reason"],
                        raw_snapshot={k: met.get(k) for k in ("price", "3m_return", "dollar_vol", "vs_sma200", "consol_days", "consol_range", "avg_range", "min_ema_dist") if k in met}
                    )
                    screened_errors += 1
                    continue
            else:
                # Rule 5 hysteresis retention — disclose the near-miss instead
                # of letting a top-ranked incumbent vanish silently.
                if (not is_watchlist
                        and screen_result.get("metrics", {}).get("hysteresis_retained")):
                    _met = screen_result["metrics"]
                    hysteresis_kept[ticker] = {
                        "avg_range_raw": _met.get("hysteresis_range_raw")
                                        or _met.get("avg_range_raw"),
                        "prev_score": prev_scores.get(ticker),
                        "prev_rank": prev_rank_index.get(ticker),
                    }
                    print(f"🧲 Rule5 hysteresis: {ticker} retained "
                          f"(avg_range {_met.get('avg_range_raw')}% in band)",
                          file=sys.stderr)

            # Stage 2: Full scoring
            screened_pass += 1
            raw = calc_indicators_daily(df, OPT, ticker=ticker)
            if raw is None or raw["rsi"] is None or raw["adx"] is None:
                _raw_msg = f"raw=None" if raw is None else f"raw=rsi={raw.get('rsi')}, adx={raw.get('adx')}"
                log_ticker_error(
                    ticker, step="calc_indicators", error_type="insufficient_indicators",
                    message=_raw_msg,
                    raw_snapshot={"close_len": len(df), "close_last": float(df['Close'].dropna().iloc[-1])}
                )
                print("❌ insufficient indicators", file=sys.stderr)
                errors += 1
                continue
            period_config = {
                "macd": OPT["macd"], "rsi": OPT["rsi"], "ma": OPT["ma"],
                "adx": OPT["adx"], "volume": OPT["volume"], "bb": OPT["bb"],
            }
            scored = compute_all(raw, period_config)
            scores = scored["scores"]
            total = scored["total"]  # clipped published 0–100
            weighted_total_raw = scored.get("weighted_total_raw", total)
            bracket = scored["bracket"]
            verdict = scored["verdict"]
            dmi = scored.get("dmi_direction", "neutral")

            # Option G — Skip Choppy Weeks
            # When SPY ADX < 25 (choppy market), suppress ALL trade signals.
            # Scores preserved for visibility/ranking; only verdict overridden.
            # Backtest: choppy weeks avg -0.16%, choppy WR 54% but total -71%
            if regime == "choppy":
                verdict = "NO SIGNAL (choppy market)"
                scored["verdict"] = verdict

            # ── ATR14 entry / SL / TP for every scored name ──
            close_price = float(df["Close"].dropna().iloc[-1]) if not df.empty else None
            result_entry = {
                "ticker": ticker,
                "scores": scores,
                "total": total,
                # P1 fix (W33 addendum): propagate raw 5-indicator base so the
                # report's "Base" column ≠ "Adjusted" when weights != 1.0.
                "base_5indicator_total": scored.get("base_5indicator_total", total),
                "weighted_total_raw": weighted_total_raw,
                "bracket": bracket,
                "verdict": verdict,
                "dmi_direction": dmi,
                "close": close_price,
                "raw": {k: raw.get(k) for k in ("rsi","macd_line","macd_hist","macd_signal","adx","plus_di","minus_di","volume_ratio","obv_trend","obv_pct_change","mfi_value","change_pct","sma_short")},
            }
            # Entry / SL / TP for every scored name, not only the watchlist.
            # Same ladder: close + 0.5×ATR14, SL 0.75×ATR, TP 1.5×ATR.
            # Choppy does not clear these levels; Option G only rewrites verdict.
            atr_val, price = calc_atr14_from_df(df)
            entry_sl_tp = None
            if atr_val is not None and price is not None:
                entry_sl_tp = compute_entry_sl_tp(price, atr_val, regime=regime)
                if entry_sl_tp is None:
                    log_ticker_error(
                        ticker, step="atr14", error_type="entry_sl_tp_failed",
                        message=f"compute_entry_sl_tp returned None (price={price}, atr={atr_val})",
                        raw_snapshot={"price": price, "atr14": atr_val}
                    )
            else:
                log_ticker_error(
                    ticker, step="atr14", error_type="calc_failed",
                    message=f"atr_val={'None' if atr_val is None else atr_val}, price={'None' if price is None else price}",
                    raw_snapshot={"df_len": len(df), "close_last": float(df['Close'].dropna().iloc[-1]) if not df.empty else None}
                )
                price_approx = df["Close"].iloc[-1] if not df.empty else None
                if price_approx is not None and not pd.isna(price_approx):
                    approx_atr = float(price_approx) * 0.02
                    entry_sl_tp = compute_entry_sl_tp(float(price_approx), approx_atr, regime=regime)
                    if entry_sl_tp:
                        entry_sl_tp["atr14"] = None  # estimated
            if entry_sl_tp:
                result_entry.update(entry_sl_tp)
                # Entry vs SAME-DAY close (Zoe #68). Anchored to today's close,
                # so do not compare with previousClose on gap days.
                entry_price_anomaly = False
                try:
                    entry_price = entry_sl_tp.get("entry_price")
                    same_day_close = close_price
                    if same_day_close and entry_price and same_day_close > 0:
                        deviation = abs(entry_price - same_day_close) / same_day_close
                        if deviation > 0.05:
                            entry_price_anomaly = True
                except Exception:
                    pass
                result_entry["entry_price_anomaly"] = entry_price_anomaly
            else:
                result_entry.update({"entry_price": None, "stop_loss": None, "take_profit": None, "atr14": None, "risk_pct": None, "reward_pct": None, "rr_ratio": None, "entry_price_anomaly": False})
                atr_missed += 1

            # ── Company/sector/source for watchlist stocks ──
            if is_watchlist:
                meta = watchlist_meta.get(ticker, {})
                info = None
                try:
                    info = get_or_fetch_info(ticker)
                    sector = resolve_sector(ticker, info)
                except Exception:
                    sector = resolve_sector(ticker)
                # M1 fix: meta company may be blank — fall back to yfinance longName / hardcoded map
                result_entry["company"] = meta.get("company") or resolve_company_name(ticker, info)
                result_entry["sector"] = sector
                result_entry["weekly_score"] = meta.get("weekly_score")
                result_entry["source"] = meta.get("source", "")
            else:
                try:
                    info = get_or_fetch_info(ticker)
                    # M1 fix: yfinance .info has NO "company" key — use longName/shortName
                    result_entry["company"] = resolve_company_name(ticker, info)
                    result_entry["sector"] = resolve_sector(ticker, info)
                except Exception:
                    result_entry["company"] = resolve_company_name(ticker)
                    result_entry["sector"] = resolve_sector(ticker)
                result_entry["weekly_score"] = None
                result_entry["source"] = ""

            results.append(result_entry)

            icon = "🟢" if total >= 70 else ("🟡" if total >= 50 else "⚪")
            if is_watchlist and result_entry.get("atr14") is not None:
                print(f"✅ {total:5.1f} {icon} {verdict} | ATR=${result_entry['atr14']:.1f} RR=1:{result_entry['rr_ratio']:.1f}", file=sys.stderr)
            else:
                print(f"✅ {total:5.1f} {icon} {verdict}", file=sys.stderr)
        except Exception as e:
            _exc_type = type(e).__name__
            log_ticker_error(
                ticker, step="unknown", error_type=_exc_type,
                message=str(e),
                raw_snapshot={"close_last": float(df['Close'].dropna().iloc[-1]) if 'df' in dir() and df is not None and not df.empty else None}
            )
            print(f"❌ error: {e}", file=sys.stderr)
            errors += 1

    print(f"\n[📊] Scored {len(results)}/{len(scoring_universe)} | Screen pass: {screened_pass} | Screen fail: {screened_errors} | Errors: {errors} | ATR missed: {atr_missed}", file=sys.stderr)

    # ── Same-as-of 1D% prev-close lock (Zoe 09-07 M1, t_6ed3ff15) ──
    # Holiday / weekend / same-day re-run: the current data-as-of equals the
    # previous PUBLISHED report's data-as-of, so every published 1D% must stay
    # identical. A fresh yfinance fetch can silently back-adjust history
    # (BAC 09-03 close rewritten 63.04 → 62.72 between the 09-04 and 09-07
    # fetches), which moved BAC 1D% -0.57% → -0.06% on an unchanged 62.68
    # as-of close. Apply the lock BEFORE any consumer of raw['change_pct']
    # (Full Ranking, Gainer/Loser, Material Moves, Key Notes, data.json).
    change_pct_lock = None
    _prev_as_of = (_prev or {}).get("as_of") or ""
    if _prev_as_of and _prev_as_of == data_as_of_s:
        _locked_rows = apply_same_asof_1d_lock(
            results, _prev.get("row_close"), _prev.get("row_chg"))
        if _locked_rows:
            change_pct_lock = {
                "basis": f"same data-as-of ({data_as_of_s}) == previous "
                         f"published report {prev_date} as-of — 1D% prev-close "
                         f"reference locked to PUBLISHED values",
                "prev_report": prev_date,
                "prev_as_of": _prev_as_of,
                "locked_count": len(_locked_rows),
                "tickers": sorted(x["ticker"] for x in _locked_rows),
            }
            for _lk in _locked_rows:
                try:
                    _old_f = float(_lk["old_chg"])
                except (TypeError, ValueError):
                    _old_f = float("nan")
                _mark = "→" if (math.isfinite(_old_f)
                                and abs(_old_f - _lk["new_chg"]) > 1e-9) else "="
                print(f"[🔒 1D% lock] {_lk['ticker']} "
                      f"[{_lk.get('mode', '?')}]: ref close "
                      f"{_lk['locked_ref_close']:.4f} | chg "
                      f"{_old_f*100:+.4f}% {_mark} "
                      f"{_lk['new_chg']*100:+.4f}% "
                      f"(as-of close {_lk['asof_close']:.2f})",
                      file=sys.stderr)
        else:
            print(f"[🔒 1D% lock] same data-as-of {_prev_as_of} but no rows "
                  f"shared with previous published report — no lock applied",
                  file=sys.stderr)
    elif _prev_as_of and _prev_as_of != data_as_of_s:
        print(f"[1D%] data-as-of advanced {_prev_as_of} → {data_as_of_s} — "
              f"1D% recomputed from the new bar (no lock)",
              file=sys.stderr)

    # ── Compute sector 'Adj mean' (Zoe 09-04 M1, t_94cfd4c8) ──
 # Column renamed from (which read like a sector rotation /
 # relative-strength signal) to Adj: this is round(mean(Adj score
    # of TODAY'S universe members in the sector)) — an intra-universe
    # cross-sectional attribution recomputed fresh from THIS run's scoring
    # results, NOT sector ETF relative strength / NOT a rolling window.
    # Single-member sectors (e.g. BM = LIN, CD = CL) take that member's Adj
    # round. Full methodology disclosure is auto-emitted in the Full Ranking
    # header (source / window / update frequency / sample). See
    # compute_sector_momentum_map().
    sector_momentum_map = compute_sector_momentum_map(results)

    # ── Prev-day baseline ──
    # P0 root cause fix (Rubric #82): baseline MUST be the most recent
    # published DAILY report (its Today brackets), NOT weekly_snapshots.
    # Zoe 09-02 (t_7915ddcc): loaded EARLIER (before the scoring loop) via
    # load_prev_daily_comparison() so technical_screen Rule 5 hysteresis can
    # consult yesterday's universe membership. All prev_* vars, prev_tickers,
    # prev_ranked/prev_rank_index are already in scope here.

    # Build a scored dict for comparison
    scored_dict = {r["ticker"]: r for r in results}
    
    # ── Compare to previous ──
    changes = []
    for r in results:
        t = r["ticker"]
        prev = prev_scores.get(t)
        if prev is not None:
            change = r["total"] - prev
            changes.append({"ticker": t, "today": r["total"], "prev": prev, "change": change})

    changes.sort(key=lambda x: abs(x["change"]), reverse=True)

    # ── Signal changes ──
    new_buys = []
    lost_buys = []
    for c in changes:
        t = c["ticker"]
        r = scored_dict[t]
        # Use verdict for BUY detection (Zoe #2026-07-09 B2/M5)
        verdict = r.get("verdict", "").upper()
        is_buy_today = "BUY" in verdict and "NO" not in verdict
        # M2 fix (Rubric #81): was_buy must use the PREVIOUS DAY's VERDICT, not
        # the prev score. Using score >= 70 was wrong when Option G was active
        # yesterday (BUY=0): stocks with score >= 70 but verdict NO SIGNAL were
        # flagged as "lost BUY" even when unchanged/gaining (MRK 90.4→90.4, etc).
        prev_v = prev_verdicts.get(t, "")
        if prev_v:
            was_buy = "BUY" in prev_v and "NO" not in prev_v
        else:
            # Weekly-snapshot fallback has no verdict data — score proxy only.
            was_buy = c["prev"] >= 70
        if is_buy_today and not was_buy:
            new_buys.append((t, r["total"], r["bracket"], r["verdict"]))
        if was_buy and not is_buy_today:
            lost_buys.append((t, r["total"], c["prev"]))

    # Also catch first-time tickers (no prev score) that are BUY today
    # Zoe #2026-07-10 M1: MET(79) missing because it had no prev score
    for t, r in scored_dict.items():
        if t not in prev_scores:
            verdict = r.get("verdict", "").upper()
            is_buy_today = "BUY" in verdict and "NO" not in verdict
            if is_buy_today and r["total"] >= 70:
                new_buys.append((t, r["total"], r["bracket"], r["verdict"]))

    # Deduplicate new_buys by ticker
    seen = set()
    new_buys_dedup = []
    for item in new_buys:
        if item[0] not in seen:
            seen.add(item[0])
            new_buys_dedup.append(item)
    new_buys = new_buys_dedup

    # ── Bracket distribution ──
    brackets = {">=90": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "<50": 0}
    for r in results:
        b = r["bracket"]
        brackets[b] = brackets.get(b, 0) + 1

    # ── Driver explanation ──
    # RSI label direction + driver causation live in module-level helpers
    # (rsi_state_label / driver_from_scores / driver_from_change, Zoe W34
    # #2b, t_e6ad7a37) so they are unit-testable. Labels derive from the RAW
    # RSI value (never the RSI sub-score — score_rsi maps RSI<30→12 AND
    # RSI>75→5, so a low score can mean weak OR overbought; labeling by score
    # produced the 08-21 UNH/PNC inversion). Driver text derives from
    # per-indicator score deltas vs the previous day (cause, not state):
    # gainers list pull-up factors, losers list pull-down factors.

    # ── Generate Report ──
    signals_70plus = sum(1 for r in results if "BUY" in (r.get("verdict", "") or "").upper() and "NO" not in (r.get("verdict", "") or "").upper())
    # 08-20 P0 (t_85a14c20): report date must be UTC. Was datetime.now()
    # (local TZ, Asia/Hong_Kong) — at 22:00 UTC the local date is already the
    # NEXT day, so files/cache dirs rolled one day early (2026-08-20 cache
    # populated at 08-19 22:05 UTC with 08-19 closes → 08-20 report 100% stale).
    # 09-01 (t_b5acc944): --date override for post-close regeneration.
    today = report_date
    prev_label = prev_date if prev_date else "W25 (2026-06-13)"

    report_lines = []
    report_lines.append(f"# 📈 Daily Trend & Momentum Report — {today}")
    report_lines.append(f"")
    # Zoe 09-02 m1 (t_7915ddcc): label must match the ACTUAL universe
    # composition — 25 watchlist (Track A/B, always scored) + N non-watchlist
 # technical_screen passes (Source , ATR level). The old
    # "Daily (Watchlist Only)" label misled readers into thinking all rows
    # were watchlist when 5 (e.g. GILD/AMGN/VRTX/TMO/PAYX) were screen-pass.
    _n_wl_rows = sum(1 for r in results if r["ticker"] in watchlist_tickers)
    _n_sp_rows = len(results) - _n_wl_rows
    report_lines.append(
        f"> **Report Type:** Daily (Watchlist + Screen-Pass)  |  "
        f"**Universe:** {_n_wl_rows} watchlist (Track A/B) + {_n_sp_rows} screen-pass  |  "
        f"**Generator:** Renee (Trend & Momentum Trader)")
    report_lines.append(f"> **Data:** Daily OHLCV (250d) | Shared Data Cache  |  **Scoring:** 5-Indicator + DMI + OBV + Regime Adj")
    report_lines.append(f"> **Run ID:** `{get_run_id()}`{(' (**' + run_note + '**)') if run_note else ''}  |  **Config Version:** `{CONFIG_VERSION}`  |  **Regime:** `{regime}`")
    # 08-20 P2 (t_85a14c20): surface data as-of + the actual ADX/VIX values
    # used for the regime call (stale-cache auditability).
    # 08-22 (t_512ecc00): data as-of now comes from the freshness watchdog
    # (actual max last-bar across the batch), not just today's date — so a
    # report can never claim an as-of its data doesn't have.
    report_lines.append(f"> **Data as-of:** `{data_as_of_s}` (expected `{expected_as_of_s}`) | **SPY ADX14:** `{spy_adx}`  |  **VIX:** `{vix_close}`")
    # 1.0.5 (t_6ed3ff15): disclose when the same-as-of 1D% prev-close lock
    # fired — holiday/weekend re-run whose data-as-of equals the previous
    # published report's; readers must know 1D% is anchored to published
    # values, not a re-fetched (possibly back-adjusted) reference.
    if change_pct_lock:
        report_lines.append(
            f"> 🔒 **1D% prev-close lock (Zoe 09-07 M1):** data-as-of "
            f"`{change_pct_lock['prev_report']}` report — 1D% "
            f"({change_pct_lock['locked_count']} ticker),re-fetch "
            f"(/ back-adjust).")
    if regime == "choppy":
        report_lines.append(f"> ⚠️ **Choppy market (ADX < 25) — Option G active: ALL signals suppressed**")
    report_lines.append("> **Dual Score:** X = published `tm`/`daily_score` (Option 6 weighted, **clipped 0–100**) | Y = `base_5indicator_total` (raw unweighted 0–100). Audit: `weighted_total_raw` uncapped (may be >100).")
    report_lines.append("> **M1 Scale Disclosure:** published score is **clipped 0–100** (bracket/verdict from clipped total); `weighted_total_raw` is uncapped weighted audit; `base_5indicator_total` is raw unweighted 0–100. No 100/136 rescale.")
    report_lines.append(f"> **Generated:** {datetime.now(timezone.utc).isoformat()}")
    report_lines.append(f"")
    report_lines.append(f"---")
    report_lines.append(f"")
    report_lines.append(g1_session_scaffold(
        today, regime, spy_adx, option_g_active=(regime == "choppy"),
    ).rstrip())
    report_lines.append(f"")
    report_lines.append(f"## 📊 Section 1 — Daily Overview / ")
    report_lines.append(f"")
    report_lines.append(f"### ")

    # ── Macro context (P0-3 + P1-5 fix, t_1dacac8d) ──
    # Bond context must use the SAME trading day's Treasury H.15 close (or be
    # explicitly labeled T-1). Gold reference must use the latest GC=F close.
 # Signal label derives from the actual bp move — never call a +5bp day .
    # m1 fix (Zoe 09-03, t_8cd84165): label the source Treasury H.15 (NOT FRED)
    # and disclose the FRED DGS2 prev-day lag (same underlying series, FRED
    # republishes T+1; rubric #77 canonical = FRED DGS2).
    macro_ctx = None
    try:
        macro_ctx = fetch_macro_context(today)
    except Exception as e:
        print(f"[⚠] fetch_macro_context error: {e}", file=sys.stderr)
        macro_ctx = None
    if macro_ctx and macro_ctx.get("lines"):
        report_lines.append(f"")
        _bond_src = macro_ctx.get("source") or "Treasury H.15"
        report_lines.append(f"** / Bond Context ({_bond_src}, {macro_ctx['as_of_label']}):**")
        report_lines.append(f"")
        report_lines.append(f"| | | (vs prev) | |")
        report_lines.append(f"|:----:|:----:|:--------------:|:----:|")
        report_lines.extend(macro_ctx["lines"])
        _lag = macro_ctx.get("dgs2_lag_note")
        if _lag:
            report_lines.append(f"")
            report_lines.append(f"> {_lag}")
        if macro_ctx.get("gold_close"):
            report_lines.append(f"")
            # Zoe 08-28 m3 (t_fb574bfa): 1D% benchmark MUST be GLD (ETF, no
            # roll inflation), never GC=F continuous. GC=F level retained for
            # absolute price; GLD 1D% shown for the daily move + material tag.
            # Zoe 09-02 m3 (t_7915ddcc): every instrument is EXPLICITLY
            # labeled in the header — no silent mixing of futures level with
            # ETF 1D%. Both numbers stay in one line for context, each tagged.
            # Zoe 09-03 m2 (t_8cd84165): the 🔴 material flag threshold is
            # disclosed inline (GOLD_MATERIAL_MOVE_PCT = 1.5%, gold-specific)
            # so readers never compare it to the equity universe 5.0% gate.
            # Zoe 09-04 m1 (t_94cfd4c8): GLD ETF level emitted IN PARALLEL
            # with the GC=F continuous level — the level/return instrument
            # split is fully disclosed: GC=F continuous level is a roll-
            # distorted macro reference only, the TRADABLE level is GLD, and
            # the 1D% benchmark is GLD (same instrument as the GLD level →
            # level/return reconcile-able).
            _gold_date = macro_ctx.get("gold_date")
            report_lines.append(f"** / Gold ({_gold_date}):**")
            report_lines.append(
                f"- **Level — GC=F continuous futures:** **${macro_ctx['gold_close']:,.2f}**"
                f"(⚠️ roll , macro ;GC=F 1D% roll , 1D%)")
            _gld_level = macro_ctx.get("gold_gld_close")
            if _gld_level is not None:
                report_lines.append(
                    f"- **Level — GLD ETF:** **${_gld_level:,.2f}**"
                    f"({_gold_date} )")
            gld_pct = macro_ctx.get("gold_gld_1d_pct")
            if gld_pct is not None:
                # Zoe 09-03 m2 (t_8cd84165): always disclose the gold-specific
                # material-move threshold so readers know why a GLD move flags
                # while the equity universe uses a different (5.0%) gate.
                _reconcile = ("level/return , reconcile"
                              if _gld_level is not None
                              else "GLD level ")
                gold_line = (f"- **1D% benchmark GLD(ETF):** {gld_pct:+.2f}%"
                             f"({_reconcile})"
                             f" | material-move : GLD |1D%| ≥ "
                             f"{GOLD_MATERIAL_MOVE_PCT:.1f}% (gold-specific; "
                             f"equity universe {MATERIAL_MOVE_PCT:.1f}% )")
                if macro_ctx.get("gold_gld_material"):
                    gold_line += " 🔴 **material move**"
                report_lines.append(gold_line)
    elif macro_ctx is None:
        # Hard fetch failure — surface it instead of silently omitting (Zoe
        # data-layer check wants as-of auditable).
        report_lines.append(f"")
        report_lines.append(f"> ⚠️ **Bond context unavailable** — Treasury H.15 fetch failed; "
                            f"report date {today} (no T-1 substitution without data).")
    report_lines.append(f"")

    # ── Bracket distribution (m1 fix, Zoe 08-27): table fully inside the
 # section with its OWN header — never split across the bond
    # table / gold paragraph (the old header sat before macro context and
    # the data rows landed after it, leaving the rows headerless). ──
    report_lines.append(f"**Bracket / Bracket Distribution:**")
    report_lines.append(f"| Bracket | Today | Previous ({prev_label}) | Change |")
    report_lines.append(f"|---------|:-----:|:---------------------:|:------:|")
    for bk in [">=90", "80-89", "70-79", "60-69", "50-59", "<50"]:
        t = brackets.get(bk, 0)
        p = prev_brackets.get(bk, 0)
        chg = t - p
        chg_str = f"+{chg}" if chg > 0 else str(chg) if chg < 0 else "0"
        report_lines.append(f"| {bk} | {t} | {p} | {chg_str} |")
    prev_total = len(prev_scores) if (prev_scores and daily_files) else sum(prev_brackets.values())
    total_chg = len(results) - prev_total
    total_chg_str = f"+{total_chg}" if total_chg > 0 else str(total_chg) if total_chg < 0 else "0"
    report_lines.append(f"| **Total** | **{len(results)}** | **{prev_total}** | **{total_chg_str}** |")
    report_lines.append(f"")
    # m2 fix (Zoe 08-27): the Change column compares across DIFFERENT
    # universes when tickers entered/left — annotate so readers don't read
    # the net bracket moves as pure score migration.
    today_tickers = {r["ticker"] for r in results}
    # prev_tickers (set) is already loaded from the prev-day baseline before
    # the scoring loop (Rule 5 hysteresis membership source) — same content
    # as the set built from prev_scores below, but already authoritative.
    prev_tickers = set(prev_scores.keys()) if (prev_scores and daily_files) else set()
    removed = sorted(prev_tickers - today_tickers)
    added = sorted(today_tickers - prev_tickers)
    if removed or added:
        univ_parts = []
        if removed:
            univ_parts.append("−" + ", −".join(removed))
        if added:
            univ_parts.append("+" + ", +".join(added))
        report_lines.append(f"> ⚠️ **Universe change ({prev_total}→{len(results)}):** {' '.join(univ_parts)} — "
                            f"Change universe ,/.")
        # Zoe 09-02 P1 #1 (t_7915ddcc): NEVER write a bare "−PFE" when the
        # ticker was dropped by technical_screen — disclose the screen_failed
        # cause + prev-day context (score / rank) so a material omission
        # (e.g. yesterday's #1) can't be framed as a routine rebalance.
        removed_explain = []
        for t in removed:
            sf = screen_failures.get(t)
            if not sf:
                continue
            _sc = sf.get("prev_score")
            _rk = sf.get("prev_rank")
            _ctx = ""
            if _sc is not None:
                _ctx = f"; Adj {_sc:.1f}"
                if _rk:
                    _ctx += f" #{_rk}"
            _near = " ⚠️ **top-10 near-miss**" if (_rk is not None and _rk <= 10) else ""
            removed_explain.append(
                f"{t}: technical_screen ({sf['reason']}; watchlist ){_ctx}{_near}")
        if removed_explain:
            report_lines.append(
                f"> ⚠️ ** (technical_screen):** " + ";".join(removed_explain) + ".")
        # Zoe 09-02 P1 #2: near-miss alert — yesterday top-10 members removed
        # by ANY rule must be flagged, not just Rule 5 removals.
        top10_removed = [t for t in removed
                         if prev_rank_index.get(t) is not None
                         and prev_rank_index[t] <= 10
                         and t not in screen_failures]
        if top10_removed:
            report_lines.append(
                f"> ⚠️ **near-miss:** {', '.join(top10_removed)} top-10 "
                f" universe( technical_screen )—— .")
    # Zoe 09-02 P1 #2 (t_7915ddcc): Rule 5 hysteresis retention disclosure.
    # Incumbents whose 20-day mean daily range fell inside [1.8%, 2.0%) are
    # KEPT (admission threshold only applies to new candidates) — say so,
    # with prev-day rank, instead of letting the reader wonder why a
    # sub-2%-volatility stock is still present (or worse, silently dropping
    # yesterday's #1 as PFE on 09-02).
    if hysteresis_kept:
        _hk_lines = []
        for t in sorted(hysteresis_kept):
            hk = hysteresis_kept[t]
            rng = hk.get("avg_range_raw")
            rng_s = f"{rng:.3f}%" if rng is not None else "?"
            _ctx = ""
            if hk.get("prev_score") is not None:
                _ctx = f"( Adj {hk['prev_score']:.1f}"
                if hk.get("prev_rank"):
                    _ctx += f" #{hk['prev_rank']}"
                _ctx += ")"
            _hk_lines.append(f"{t} 20 {rng_s} ∈ "
                             f"[{RULE5_KEEP_PCT:.1f}%, {RULE5_ADMIT_PCT:.1f}%) {_ctx}")
        report_lines.append(
            f"> 🧲 **Rule 5 hysteresis (Zoe 09-02):** " + ";".join(_hk_lines) +
            f" — admission {RULE5_ADMIT_PCT:.1f}% ; "
            f"universe {RULE5_KEEP_PCT:.1f}%, top-ranked stock "
            f" flicker in/out.")
    report_lines.append(f"")
    # prev BUY = effective BUY count from previous daily verdicts (Option G aware),
    # falling back to bracket-sum only when no daily report exists (first run).
    if prev_scores and daily_files:
        prev_buy = prev_buy_effective
    else:
        prev_buy = sum(v for k, v in prev_brackets.items() if k in (">=90","80-89","70-79"))
    report_lines.append(f"**Total BUY signals:** {signals_70plus} (prev: {prev_buy})")
    # ── End Bracket Distribution ──

    # ── Bracket WR Backtest Reference (Zoe Rubric #69) ──
    # Every bracket WR claim MUST include: date range, version, n, MaxDD.
    src = BRACKET_WR_BACKTEST["_source"]
    report_lines.append(f"")
    report_lines.append(f"### 📈 Bracket Win Rate — Backtest Reference / ")
    report_lines.append(f"")
    report_lines.append(f"> **Source:** {src['date_range']} | **Version:** {src['version']} | **Methodology:** {src['methodology']}")
    report_lines.append(f"> **Overall:** WR={src['overall_wr']:.1f}% (n={src['overall_n']:,}), MaxDD={src['overall_maxdd']:+.1f}%")
    report_lines.append(f"> **Zoe Rubric #69:** Every bracket WR claim cites backtest date range + version + signal count + MaxDD.")
    # M1 (Zoe 08-27 / CLIP+RAW): backtest WR table and live published brackets
    # now share the clipped 0-100 ruler; disclose weighted_total_raw separately
    # so readers do not treat uncapped audit as the published score.
    report_lines.append(f"> **⚠️ M1 Scale:** live published `daily_score` / bracket **clipped 0–100**( backtest WR ruler);`weighted_total_raw` uncapped ( >100).")
    report_lines.append(f"> **⚠️ m2 (Zoe 08-28):** backtest v2.1 **5-bucket**(<60 );live/rolling **6-bucket**(50-59 / <50). backtest '<60'= live '50-59 + <50'****, population—— 60-69 <60 scale + bucket scheme .")
    report_lines.append(f"")
    report_lines.append(f"| Bracket | Backtest WR | n | MaxDD | Status |")
    report_lines.append(f"|---------|:-----------:|:-----:|:-----:|:------:|")
    for bk in BRACKET_WR_ORDER:
        bt = BRACKET_WR_BACKTEST.get(bk, {})
        wr = bt.get("wr")
        n = bt.get("n", 0)
        maxdd = bt.get("maxdd")
        note = bt.get("note", "")
        if wr is None:
            report_lines.append(f"| {bk} | N/A | {n} | N/A | ⚠️ {note} |")
        else:
            status = "🟢" if wr >= 60 else ("🟡" if wr >= 50 else "🔴")
            if note:
                status += f" ⚠️ {note}"
            maxdd_s = f"{maxdd:+.1f}%" if maxdd is not None else "N/A"
            report_lines.append(f"| {bk} | {wr:.1f}% | {n:,} | {maxdd_s} | {status} |")
    report_lines.append(f"")
    # ── End Bracket WR Backtest Reference ──

    # ── Rolling 4-Week Bracket WR (Zoe Rubric #69) — LIVE ──
    # W35 P0 (t_c36bf49b): wired LIVE from weekly_snapshots. The previous
    # implementation read the static backtest latest-weekly-summary.json
    # (stuck at latest_week 07-25) and labeled it "(Live)" — frozen for 4
    # weeks. Now computed from the actual weekly snapshots each run with the
    # SAME methodology as the canonical backtests (SMA10 price proxy, 0.1%
    # slippage, win = net fwd return > 0). The newest snapshot used to be
    # excluded until next week's data resolved its forward return — which
    # made the window look "frozen" for up to a week (Zoe 08-27 B2). Now the
    # pending week is ALSO resolved against the live daily batch SMA10
    # (partial-week fwd return) so the window rolls to the latest week
    # immediately. If no resolvable data exists, the section is RETIRED for
    # that run (never frozen).
    rolling_wr = compute_rolling_4wk_wr_live(live_sma10={
        r["ticker"]: (r.get("raw") or {}).get("sma_short") for r in results
        if (r.get("raw") or {}).get("sma_short") is not None})
    if rolling_wr.get("brackets"):
        report_lines.append(f"### 📊 Rolling 4-Week Bracket WR (Live)")
        report_lines.append(f"")
        report_lines.append(f"| Bracket | Rolling WR | n (4w) | 5d Fwd Ret |")
        report_lines.append(f"|---------|:---------:|:------:|:----------:|")
        for bk in LIVE_BRACKET_ORDER:
            rw = rolling_wr["brackets"].get(bk)
            if rw is None:
                report_lines.append(f"| {bk} | N/A | 0 | N/A |")
                continue
            wr_val = rw.get("rolling_win_rate")
            n_val = rw.get("rolling_total_signals", 0)
            fwd_val = rw.get("rolling_5d_forward_return_pct")
            if wr_val is not None:
                # rolling_win_rate is a FRACTION (0..1) → ×100 for display
                wr_pct = wr_val * 100.0
                status = "🟢" if wr_pct >= 60 else ("🟡" if wr_pct >= 50 else "🔴")
                wr_str = f"{wr_pct:.1f}%"
                fwd_str = f"{fwd_val:+.2f}%" if fwd_val is not None else "N/A"
                report_lines.append(f"| {bk} | {wr_str} {status} | {n_val} | {fwd_str} |")
            else:
                report_lines.append(f"| {bk} | N/A | {n_val} | N/A | ⚠️ no resolved signals |")
        report_lines.append(f"")
        if rolling_wr.get("live_resolved"):
            # Zoe 08-27 B2: window now includes the latest weekly snapshot,
            # resolved against live daily SMA10 — honest label, no false
            # "Auto-rolls daily" claim.
            report_lines.append(
                f"> **Source:** live — `weekly_snapshots` ({rolling_wr.get('window_start')} → "
                f"{rolling_wr.get('window_end')}, last {rolling_wr.get('n_weeks')} resolved weeks; "
                f"no pending week — latest week live-resolved vs daily SMA10). "
                f"SMA10 price proxy + 0.1% slippage, win = net fwd return > 0 (matches "
                f"v2.1 / dmi-gating backtest methodology). "
                f"{rolling_wr.get('live_resolve_note')}."
            )
            # Zoe 08-28 P2 (t_fb574bfa): the latest week is a PARTIAL-week
            # resolve (live daily SMA10 partial fwd return, ~5 days) — WR
            # volatility is amplified (window roll + n contraction), so the
            # latest-week number must NOT be compared to full-week history.
            report_lines.append(
                f"> ⚠️ ** {rolling_wr.get('window_end')} partial-week resolve**"
                f"(live daily SMA10 partial fwd return)— WR ,"
                f"** full-week **."
            )
        else:
            report_lines.append(
                f"> **Source:** live — `weekly_snapshots` ({rolling_wr.get('window_start')} → "
                f"{rolling_wr.get('window_end')}, last {rolling_wr.get('n_weeks')} resolved weeks; "
                f"{rolling_wr.get('pending_week')} pending until next weekly update — "
                f"auto-rolls weekly on snapshot resolution, NOT daily). "
                f"SMA10 price proxy + 0.1% slippage, win = net fwd return > 0 (matches "
                f"v2.1 / dmi-gating backtest methodology)."
            )
        report_lines.append(f"")
    else:
        # Retire: never present a frozen table as live.
        print("[⚠️] Rolling 4-week WR: no resolvable weekly data — section retired for this run.",
              file=sys.stderr)



    # ── Full Ranking — ALL Scored Stocks ──
    # ════════════════════════════════════════
    # Bracket distribution header uses ALL results, so ranking must too.
    # Zoe #2026-07-09 B1: ranking was watchlist-only (25 rows) while
    # bracket counted 29 — internal inconsistency.

    all_rankings = list(results)
    all_rankings.sort(key=lambda x: x["total"], reverse=True)

    report_lines.append(f"### 🔢 Full Ranking — All Stocks ({len(all_rankings)} total)")
    report_lines.append(f"")

    def get_signal_label(r):
        """Determine signal label — verdict field is authoritative, fallback to score + DMI."""
        # Zoe #2026-07-09 B2/M5: use daily_verdict as primary signal source
        verdict = r.get("verdict", "").strip()
        if verdict:
            v_upper = verdict.upper()
            if "BUY" in v_upper and "NO" not in v_upper:
                return "🟢 BUY"
            if "WATCH" in v_upper:
                return "👀 WATCH"
            if "MONITOR" in v_upper:
                return "📋 MONITOR"
            if "NO_SIGNAL" in v_upper or "NO SIGNAL" in v_upper:
                return "❌ NO SIGNAL"
        # Fallback: score + DMI (original logic)
        score = r["total"]
        dmi_bull = r.get("dmi_direction", "") == "bullish"
        if score >= 70 and dmi_bull:
            return "🟢 BUY"
        elif score >= 60:
            return "👀 WATCH"
        elif score >= 50:
            return "📋 MONITOR"
        else:
            return "❌ NO SIGNAL"

    report_lines.append(f"**Signal Legend:** 🟢 BUY (≥70 + DMI↑ OR verdict=BUY) | 👀 WATCH (60-69 / DMI↓ OR verdict=WATCH) | 📋 MONITOR (50-59) | ❌ NO SIGNAL (<50 OR verdict=NO_SIGNAL)")
    # M1 design decision (Zoe 09-01, t_b5acc944): RSI sub-score curve is
    # intentionally non-monotonic — oversold (<30) gets a mean-reversion
    # sweet spot (sub 12), 30–40 low band gets 1–5, 70–75 momentum sweet
    # spot gets 17–19, >75 gets a penalty 5. Consequence: a FALLING RSI into
    # oversold can RAISE the sub-score. This is the documented design, not a
    # bug — but it means a "score gainer" can be a "price falling" stock.
    # The Driver column therefore leads with the RAW RSI delta (market
    # direction); [sub ±N] is the zone jump, secondary. Formal doc (Zoe
    # option a): oversold = bullish mean-reversion.
    report_lines.append(f"**RSI (Zoe 09-01 M1, document):** RSI sub-score intentionally —— <30(oversold )→ mean-reversion(,backtest );30–40()→ ;70–75(momentum )→ ;>75(overbought)→ 5.**:** raw RSI (e.g. 30→26)sub-score —— **' gainer''',,**.Driver primary raw RSI delta(),`[sub ±N]` zone (secondary),.")
    report_lines.append(f"**Dual Score:** published daily_score (clipped 0–100) | base_5indicator_total (raw unweighted 0–100); audit weighted_total_raw uncapped")
    report_lines.append(f"**Order:** Daily score descending")
    # m3 fix (Zoe 08-27, t_692f4462): the Weekly column sources from
    # weekly_snapshots (not this run's data.json) — state it so the Zoe #70
    # cross-section claim is scoped honestly. weekly_score is also written
    # into data.json for future verification coverage.
    report_lines.append(f"> **Weekly (m3):** `weekly_snapshots`( data.json );"
                        f"Zoe #70 cross-section Adj/Base/1D%/bracket, Weekly ("
                        f"weekly_score data.json ).")
 # Zoe 09-04 M1 (t_94cfd4c8): column renamed to Adj and
    # the methodology is now auto-disclosed right above the table — source /
    # window / update frequency / sector sample — so readers never read it
    # as a sector rotation or relative-strength signal (an intra-universe
    # cross-sectional average recomputed fresh each run; single-member
    # sector = that member's Adj round).
    report_lines.append(f"> 🟡 **M1 (Zoe 09-04):** 'Adj' = ** universe"
                        f"({len(all_rankings)} ) sector Adj ,round **."
                        f"Source = run scoring results(`results[].total`,Adj );"
                        f"Window = **(non-rolling)**; = ****;"
                        f"Sector = ** universe **( sector ETF, broader "
                        f"market ). sector( BM = LIN,CD = CL) = Adj "
                        f"round.** cross-sectional score sector attribution, "
                        f"sector / , rotation .**")
    report_lines.append(f"")

    # Add 1D% column (Zoe Rubric #80). Sector column shows the Adj mean of
    # today's same-sector universe members (Zoe 09-04 M1: renamed from
 # — see methodology note above).
    report_lines.append(f"| Rank | Ticker | Company | Sector | Adj | Adj | Base | Weekly | 1D% | Signal | Entry | TP | SL | R:R | Source |")
    report_lines.append(f"|:----:|:-----:|:-----------:|:----------:|:------:|:--:|:----:|:------:|:---:|:------:|:----:|:---:|:---:|:---:|:-----:|")

    for rank, r in enumerate(all_rankings, 1):
        ticker = r["ticker"]
        company = r.get("company", "")[:40]  # M1 fix: full company names (was 24 — cut SCHW/EW)
        # M2 fix: sector momentum lookup uses FULL sector name — [:16] truncation broke
        # "Financial Services"/"Consumer Cyclical"/"Consumer Defensive" (17-18 chars).
        sector = r.get("sector", "")
        sec_mom = sector_momentum_map.get(sector, "")
        sec_mom_s = f"{sec_mom}" if sec_mom else "—"
        daily = r["total"]
        base = r.get("base_5indicator_total", daily)
        weekly = r.get("weekly_score")
        weekly_s = f"{weekly:.1f}" if weekly is not None else "—"
        # 1D% change — use change_pct from raw data (Zoe Rubric #80)
        raw_data = r.get("raw", {})
        chg_pct = raw_data.get("change_pct")
        one_d_pct = f"{chg_pct*100:+.2f}%" if chg_pct is not None and not (isinstance(chg_pct, float) and math.isnan(chg_pct)) else "—"
        # Zoe 09-02 m2 (t_7915ddcc): single-stock material-move flag — same
        # |1D%| >= MATERIAL_MOVE_PCT standard as the Key Ticker Notes table
        # (PANW -9.28% must never pass unflagged). 🔴 down / 🟢 up.
        if (chg_pct is not None
                and not (isinstance(chg_pct, float) and math.isnan(chg_pct))
                and abs(chg_pct * 100.0) >= MATERIAL_MOVE_PCT):
            one_d_pct += (" 🔴" if chg_pct < 0 else " 🟢")
        signal = get_signal_label(r)
        entry_s = f"${r['entry_price']:.1f}" if r.get("entry_price") else "—"
        tp_s = f"${r['take_profit']:.1f}" if r.get("take_profit") else "—"
        sl_s = f"${r['stop_loss']:.1f}" if r.get("stop_loss") else "—"
        rr_s = f"1:{r['rr_ratio']:.1f}" if r.get("rr_ratio") else "—"
        source = r.get("source", "")
        # M2 fix: IEEE 754 artifacts — round scores to 1dp at output (112.79999999999998 -> 112.8)
        report_lines.append(f"| {rank} | {ticker} | {company} | {sector} | {sec_mom_s} | {daily:.1f} | {base:.1f} | {weekly_s} | {one_d_pct} | {signal} | {entry_s} | {tp_s} | {sl_s} | {rr_s} | {source} |")

    report_lines.append(f"")

    # ── End Full Ranking Table ──

    # Top 10 gainers
    gainers = [c for c in changes if c["change"] > 0][:10]
    report_lines.append(f"### Top 10 Score Gainers")
    # Zoe 09-04 m3 (t_94cfd4c8): 1D% column + inline flags (⚠️ scoreΔ vs 1D%
 # opposite; [sub↔raw ] RSI sub-score vs raw delta opposite) — see
    # format_momentum_table_1d_cell().
    report_lines.append(f"| Ticker | Today | Prev | Change | 1D% | Driver |")
    report_lines.append(f"|--------|:-----:|:----:|:------:|:---:|--------|")
    for c in gainers:
        r = scored_dict[c["ticker"]]
        # P0-2 fix (t_1dacac8d): gainers list PULL-UP factors (positive deltas)
        d = driver_from_change(r["scores"], prev_breakdowns.get(r["ticker"]),
                               r.get("raw", {}), direction=1,
                               prev_raw=prev_raws.get(r["ticker"]))
        _cell = format_momentum_table_1d_cell(r, c["change"],
                                              prev_breakdowns, prev_raws)
        # M2 fix: round to 1dp (IEEE 754 artifacts)
        report_lines.append(f"| {c['ticker']} | {c['today']:.1f} | {c['prev']:.1f} | **+{c['change']:.1f}** | {_cell} | {d} |")
    report_lines.append(f"")

    # Top 10 losers
    losers = [c for c in changes if c["change"] < 0][:10]
    report_lines.append(f"### Top 10 Score Losers")
    # Zoe 09-04 m3 (t_94cfd4c8): 1D% column + inline flags (same as gainers).
    report_lines.append(f"| Ticker | Today | Prev | Change | 1D% | Driver |")
    report_lines.append(f"|--------|:-----:|:----:|:------:|:---:|--------|")
    for c in losers:
        r = scored_dict[c["ticker"]]
        # P0-2 fix (t_1dacac8d): losers list PULL-DOWN factors (negative deltas)
        d = driver_from_change(r["scores"], prev_breakdowns.get(r["ticker"]),
                               r.get("raw", {}), direction=-1,
                               prev_raw=prev_raws.get(r["ticker"]))
        _cell = format_momentum_table_1d_cell(r, c["change"],
                                              prev_breakdowns, prev_raws)
        # M2 fix: round to 1dp (IEEE 754 artifacts)
        report_lines.append(f"| {c['ticker']} | {c['today']:.1f} | {c['prev']:.1f} | **{c['change']:.1f}** | {_cell} | {d} |")
    report_lines.append(f"")

    # Zoe 09-04 m3 (t_94cfd4c8): flag legend auto-emitted right after the two
 # tables so the inline ⚠️ / [sub↔raw ] meaning never drifts from the
    # table that carries it (report-layer readability, generator-owned).
    report_lines.append(f"> ⚠️ **m3 inline flags (Zoe 09-04):** `⚠️` = scoreΔ 1D% "
                        f"(score gainer / score loser )—— ≠ , RSI "
                        f" + indicator ( Full Ranking legend)."
                        f"`[sub↔raw opposite]` = RSI sub-score raw RSI delta "
                        f"( VRTX raw 76.2→65.0 −11.2 sub +10 = overbought ;"
                        f"HD raw 26.6→34.9 +8.3 sub −10 = oversold )—— /.")
    report_lines.append(f"")

    # New BUY signals
    report_lines.append(f"### New BUY Signals")
    report_lines.append(f"| Ticker | Score | Signal Type | Driver |")
    report_lines.append(f"|--------|:-----:|:-----------:|--------|")
    for t, sc, bk, v in new_buys:
        r = scored_dict[t]
        d = driver_from_change(r["scores"], prev_breakdowns.get(r["ticker"]),
                               r.get("raw", {}), direction=1,
                               prev_raw=prev_raws.get(r["ticker"]))
        report_lines.append(f"| {t} | {sc:.1f} | {bk} → BUY | {d} |")
    if not new_buys:
        report_lines.append(f"| (none) | — | — | — |")
    report_lines.append(f"")

    # ── Lost BUY Signals (vs prev) — Zoe 08-27 B1 (t_692f4462) ──
    # B1 root cause: this section answered "did any YESTERDAY BUY get lost"
    # while its renamed title ("Suppressed BUY-eligible") implied "which
    # high-score stocks are suppressed TODAY". Two concepts were conflated.
    # Fix: keep this section strictly "Lost BUY Signals (vs prev)" and add a
    # SEPARATE section listing today's score-eligible-but-suppressed (Adj
    # >=90) candidates below.
    report_lines.append(f"### Lost BUY Signals (vs prev)")
    report_lines.append(f"| Ticker | Score | Prev | Cause |")
    report_lines.append(f"|--------|:-----:|:----:|-------|")
    for t, sc, prv in lost_buys:
        r = scored_dict[t]
        # M1 fix (Rubric #81): branch cause on score, not just regime.
        # Score < 70 → indicator-driven drop; score >= 70 in choppy → regime suppression.
        if sc < 70:
            d = "Score dropped below 70 (indicator-driven)"
        elif regime == "choppy":
            d = f"Option G: Choppy market (SPY ADX {spy_adx:.1f})"
        else:
            d = driver_from_change(r["scores"], prev_breakdowns.get(r["ticker"]),
                                   r.get("raw", {}), direction=-1,
                                   prev_raw=prev_raws.get(r["ticker"]))
        report_lines.append(f"| {t} | {sc:.1f} | {prv:.1f} | {d} |")
    if not lost_buys:
        if prev_buy_effective == 0 and (prev_scores and daily_files):
            report_lines.append(f"| (none) | — | — | prev day had 0 BUY verdicts (Option G) — no active BUY to lose |")
        else:
            report_lines.append(f"| (none) | — | — | — |")
    report_lines.append(f"")

    # ── Suppressed BUY-eligible (Option G) — score >= 60, verdict not BUY ──
    # Zoe 08-27 B1: never print a bare "(none)" while high scores sit in the
    # ranking. The visible list is now every non-BUY at >= 60 (the old table
    # stopped at >= 90 and hid the 60–89 names). The ADX < 25 gate is unchanged.
    report_lines.append(build_suppressed_buy_section(
        results, regime, spy_adx, prev_scores,
    ))
    report_lines.append("")

    # Section 2 — Key Ticker Notes
    report_lines.append(f"## Section 2 — Key Ticker Notes")
    report_lines.append(f"")
    report_lines.append(
        f"### ATR Entry/SL/TP — every scored name "
        f"(watchlist still ~{len(watchlist_tickers)} Track A+B)"
    )
    report_lines.append(f"")
    report_lines.append(f"**Entry formula:** Close + 0.5×ATR14 | **SL:** Entry − 0.75×ATR14 (min 0.5× floor) | **TP:** Entry + 1.5×ATR14")
    # M1 basis note (Zoe 09-03, t_8cd84165, Renee methodology decision =
    # Option B): this ladder is a SINGLE-POINT-ENTRY construction (trigger
    # above close, 0.75-ATR stop from the trigger). It is NOT the
    # technical-snapshot zone-floor construction. The note is always emitted
    # so SL/R:R are never compared across products.
    report_lines.append(f"> **SL Basis (Zoe 09-03 M1):** {ATR_SL_BASIS_NOTE}")
    report_lines.append(f"")
    report_lines.append(f"")
    report_lines.append(
        f"Scored names with ATR14: "
        f"{sum(1 for r in results if r.get('atr14') is not None)}/{len(results)} · "
        f"Watchlist tickers with ATR14 available: "
        f"{sum(1 for r in results if r['ticker'] in watchlist_tickers and r.get('atr14') is not None)}/{len(watchlist_tickers)}"
    )
    report_lines.append(f"")

    # Find most interesting tickers: top 5 by absolute change that are notable
    notable = sorted(changes, key=lambda x: abs(x["change"]), reverse=True)
    noted = 0  # counter — named `noted`, NOT `added` (added is the universe
    #            change list above; reusing the name shadowed it and corrupted
    #            universe_meta["added"] — t_7915ddcc)
    for c in notable:
        if noted >= 5:
            break
        t = c["ticker"]
        r = scored_dict[t]
        s = r["scores"]
        raw = r["raw"]
        is_buy = r["total"] >= 70
        is_new = any(x[0] == t for x in new_buys)
        is_lost = any(x[0] == t for x in lost_buys)
        tag = ""
        if is_new: tag = " 🆕 NEW BUY"
        elif is_lost: tag = " ⛔ LOST BUY"
 # P1-5 fix (t_1dacac8d): surge/plunge labels must carry ' Δ'
        # prefix so they can't be confused with 1D% price moves.
        elif c["change"] >= 10: tag = " 🔥 Δ surge"
        elif c["change"] <= -10: tag = " 💥 Δ plunge"
        report_lines.append(f"**{t}** — Score: {r['total']:.1f} ({r['bracket']}){tag}")
        report_lines.append(f"- Breakdown: MACD {s['macd']} | RSI {s['rsi']} | MA {s['ma']} | ADX {s['adx']} | Vol {s['volume']}")
        _rsi_lbl = rsi_state_label(raw.get("rsi")) or "N/A"
        report_lines.append(f"- Raw: RSI={raw.get('rsi','?'):.1f} ({_rsi_lbl}) | ADX={raw.get('adx','?'):.1f} | +DI={raw.get('plus_di','?'):.1f} | -DI={raw.get('minus_di','?'):.1f}")
        chg_str = f"{raw['change_pct']*100:.2f}%" if raw.get('change_pct') and not math.isnan(raw['change_pct']) else 'N/A'
        report_lines.append(f"- Vol ratio: {raw.get('volume_ratio','?'):.2f}x | OBV: {'↑' if raw.get('obv_trend')==1 else '↓' if raw.get('obv_trend')==-1 else '→'} | Chg: {chg_str}")
        report_lines.append(f"- Dir: {r['dmi_direction']} | Verdict: {r['verdict']}")
        if r.get("entry_price") and r.get("atr14"):
            report_lines.append(f"- ATR14: ${r['atr14']:.1f} | Entry: ${r['entry_price']:.1f} | SL: ${r['stop_loss']:.1f} | TP: ${r['take_profit']:.1f} | R:R 1:{r['rr_ratio']:.1f}")
        report_lines.append(f"")
        noted += 1

 # ── / Material Moves (Zoe 09-02 m2, t_7915ddcc) ──
    # Single-stock |1D%| >= MATERIAL_MOVE_PCT standard — SAME threshold that
    # drives the 🔴/🟢 flag in the Full Ranking 1D% column above (and the same
    # flag family as gold's 🔴 material move). Any stock at this magnitude
    # MUST appear here: PANW -9.28% can never again pass without a note.
    material_moves = []
    for r in results:
        _chg = (r.get("raw") or {}).get("change_pct")
        if (_chg is not None
                and not (isinstance(_chg, float) and math.isnan(_chg))
                and abs(_chg * 100.0) >= MATERIAL_MOVE_PCT):
            material_moves.append(r)
    if material_moves:
        material_moves.sort(key=lambda x: (x.get("raw") or {}).get("change_pct", 0))
        report_lines.append(f"### / Material Moves (|1D%| ≥ {MATERIAL_MOVE_PCT:.0f}% — Full Ranking 1D% flag )")
        report_lines.append(f"")
        report_lines.append(f"| Ticker | Price | 1D% | Adj | Verdict | Note |")
        report_lines.append(f"|--------|:-----:|:---:|:---:|:-------:|------|")
        _mm_min = material_moves[0]
        _mm_max = material_moves[-1]
        for r in material_moves:
            t = r["ticker"]
            _chg = (r.get("raw") or {}).get("change_pct")
            chg_pct_v = _chg * 100.0 if _chg is not None else 0.0
            icon = "🔴" if chg_pct_v < 0 else "🟢"
            _note = ""
            if r is _mm_min:
                _note = "" if chg_pct_v < 0 else ""
            elif r is _mm_max:
                _note = "" if chg_pct_v > 0 else ""
            report_lines.append(
                f"| {t} | ${r.get('close','?'):.2f} | {icon} {chg_pct_v:+.2f}% | "
                f"{r['total']:.1f} | {r.get('verdict','')} | {_note} |")
        report_lines.append(f"")
        report_lines.append(f"> Flag : |1D%| ≥ {MATERIAL_MOVE_PCT:.0f}%(Zoe 09-02 m2)— gold 🔴 material move "
                            f" flag family;🔴 = ≥{MATERIAL_MOVE_PCT:.0f}%,🟢 = ≥{MATERIAL_MOVE_PCT:.0f}%.")
        report_lines.append(f"")

    # Also show top 5 BUY signals overall if we haven't covered them
    report_lines.append(f"### Top 5 BUY Signals (Overall)")
    report_lines.append(f"")
    report_lines.append(f"| Ticker | Score | Bracket | Entry | SL | TP | ATR14 | R:R |")
    report_lines.append(f"|--------|:-----:|:-------:|:-----:|:--:|:---:|:----:|:---:|")
    buys_only = sorted([r for r in results if r.get("verdict") == "BUY"], key=lambda x: x["total"], reverse=True)[:5]
    for r in buys_only:
        entry_s = f"${r['entry_price']:.1f}" if r.get("entry_price") else "—"
        sl_s = f"${r['stop_loss']:.1f}" if r.get("stop_loss") else "—"
        tp_s = f"${r['take_profit']:.1f}" if r.get("take_profit") else "—"
        atr_s = f"${r['atr14']:.1f}" if r.get("atr14") else "—"
        rr_s = f"1:{r['rr_ratio']:.1f}" if r.get("rr_ratio") else "—"
        report_lines.append(f"| {r['ticker']} | {r['total']:.1f} | {r['bracket']} | {entry_s} | {sl_s} | {tp_s} | {atr_s} | {rr_s} |")
    if not buys_only:
        report_lines.append(f"")
        report_lines.append(f"> ℹ️ No BUY signals today (regime: {regime})")
    
    report_lines.append(f"---")
    report_lines.append(f"*Generated: {datetime.now(timezone.utc).isoformat()}*")
    report_lines.append(f"*⚠️ *")
    # Entry price anomaly footnote (Zoe #68)
    anomaly_tickers = [r["ticker"] for r in results if r.get("entry_price_anomaly")]
    if anomaly_tickers:
        report_lines.append(f"")
        report_lines.append(f"⚠️ **Entry Price Anomaly (Zoe #68):** {', '.join(anomaly_tickers)} — entry price deviates >5% from same-day close")

    # ── Cross-section consistency check (Zoe #70) ──
    # Verify no ticker's bracket changes by >2 brackets between §1 and §2
    # Both sections source from the same results dict; cross-validate by
    # checking that each ticker's score matches across the sorted list.
    report_lines.append(f"")
    inconsistencies = []
    for r in results:
        expected_bracket = get_signal_bracket(r["total"])
        if r["bracket"] != expected_bracket:
            inconsistencies.append(f"{r['ticker']}: score={r['total']} bracket={r['bracket']}→{expected_bracket}")
    if inconsistencies:
        report_lines.append(f"⚠️ Cross-section inconsistencies ({len(inconsistencies)}): {'; '.join(inconsistencies[:3])}")
    else:
        report_lines.append(f"✅ Cross-section consistency verified (Zoe #70) — {len(results)} stocks match")

    # ── RSI label direction + driver causation auto-check (Zoe W34 #2b) ──
    # Rubric #81 family 3rd recurrence: 08-21 T&M labelled UNH RSI 31.4 /
    # PNC RSI 35.6 (oversold zone) as "overbought". Any rsi<35 label/text
    # containing "overbought" OR rsi>65 label/text containing "oversold"
    # must BLOCK publish — zero label-direction errors may reach reports.
    # Checks BOTH label sources: rsi_state_label output AND the CAUSE driver
    # strings emitted for gainers/losers.
    label_violations = (scan_rsi_label_violations(results)
                        + scan_driver_label_violations(results, prev_breakdowns))
    # Zoe 08-27 M2 (t_692f4462): the W34 #2b scan previously checked only
    # label TEXT vs raw RSI. It never checked driver DIRECTION vs raw RSI
    # direction, so MRK/AMGN/HON (sub +13/+12/+11 while raw FELL -5.9/-5.7/
    # -7.8) slipped through and the footer claimed "0 violations" — a FALSE
    # claim. Add the direction cross-check and report its findings honestly.
    direction_violations = scan_driver_direction_violations(
        results, prev_breakdowns, prev_raws)
    if label_violations:
        report_lines.append("")
        report_lines.append(f"⛔ **RSI label direction errors ({len(label_violations)}):** "
                            + "; ".join(label_violations[:5]))
        print(f"[❌] FATAL: RSI label direction errors detected — refusing to publish "
              f"({len(label_violations)}):", file=sys.stderr)
        for v in label_violations:
            print(f"     - {v}", file=sys.stderr)
        return 1
    report_lines.append("")
    if direction_violations:
        # NOT a hard publish block — the report presents the scoring-curve
        # artifacts (driver primary now shows the RAW RSI delta — M1 fix,
        # t_fb574bfa — so the first number always matches market direction;
        # the [sub ±N] secondary still discloses the non-monotonic sub-score
        # zone jump). The footer must NOT claim "0 violations".
        # m1 fix (Zoe 09-01, t_b5acc944): header count MUST equal the number
        # of listed tickers — the 09-01 footer wrote (7) but displayed only
        # 6 ([:6] truncation). List ALL violations; count = len(list).
        _viol_all = direction_violations
        report_lines.append(
            f"⚠️ **RSI (sub-score Δ vs raw Δ; driver raw ):** "
            f"({len(_viol_all)}): " + "; ".join(_viol_all))
        print(f"[⚠️] RSI driver direction contradictions ({len(_viol_all)}):",
              file=sys.stderr)
        for v in _viol_all:
            print(f"     - {v}", file=sys.stderr)
    else:
        report_lines.append(f"✅ RSI label direction + driver causation verified (Zoe W34 #2b) — "
                            f"{len(results)} stocks, 0 violations")

    report = "\n".join(report_lines)

    # ── 1. Save data JSON FIRST (with full scoring + ATR entry/SL/TP for Alice/Zoe) ──
    data_filename = f"{today}-data.json"
    data_results = []
    for r in sorted(results, key=lambda x: x["total"], reverse=True):
        data_entry = {
            "ticker": r["ticker"],
            "price": r.get("close"),
            "daily_score": r["total"],  # clipped published 0–100
            "daily_bracket": r["bracket"],
            "daily_verdict": r["verdict"],
            "score_breakdown": r["scores"],
            "base_5indicator_total": r.get("base_5indicator_total", r["total"]),
            "weighted_total_raw": r.get("weighted_total_raw", r["total"]),
            "raw_indicators": r["raw"],
            # m3 fix (Zoe 08-27, t_692f4462): expose weekly score (from
            # weekly_snapshots) in data.json so Zoe #70 cross-section
            # verification can cover the Weekly column too.
            "weekly_score": r.get("weekly_score"),
            "entry_price": r.get("entry_price"),
            "stop_loss": r.get("stop_loss"),
            "take_profit": r.get("take_profit"),
            "atr14": r.get("atr14"),
            "risk_pct": r.get("risk_pct"),
            "reward_pct": r.get("reward_pct"),
            "rr_ratio": r.get("rr_ratio"),
            "entry_price_anomaly": r.get("entry_price_anomaly", False),
        }
        data_results.append(data_entry)

    # ── Universe/meta for downstream audits (Zoe 09-02, t_7915ddcc) ──
    # Exposes the SAME facts the report discloses: universe composition
    # (watchlist vs screen-pass), screen_failures with reasons + prev-day
    # context, hysteresis-kept members, material moves. Lets Alice/Zoe verify
    # the report without parsing the prose or per-ticker-errors.jsonl.
    _material_tickers = []
    for r in results:
        _chg = (r.get("raw") or {}).get("change_pct")
        if (_chg is not None
                and not (isinstance(_chg, float) and math.isnan(_chg))
                and abs(_chg * 100.0) >= MATERIAL_MOVE_PCT):
            _material_tickers.append(r["ticker"])
    universe_meta = {
        "watchlist_count": _n_wl_rows,
        "screen_pass_count": _n_sp_rows,
        "removed": removed,
        "added": added,
        "removed_screen_failures": {
            t: {k: v for k, v in screen_failures[t].items() if k != "metrics"}
            for t in sorted(removed) if t in screen_failures
        },
        "hysteresis_kept": {
            t: {"avg_range_raw": hk.get("avg_range_raw"),
                "prev_score": hk.get("prev_score"),
                "prev_rank": hk.get("prev_rank")}
            for t, hk in sorted(hysteresis_kept.items())
        },
        "material_moves": sorted(_material_tickers),
        "material_move_pct_threshold": MATERIAL_MOVE_PCT,
    }

    # Workspace data JSON (wrap in metadata dict for traceability)
    # m2 fix (Zoe 09-01, t_b5acc944): round floats key-aware before write —
    # data.json must never carry IEEE 754 residue (91.39999999999999 etc).
    ws_data_path = os.path.join(REPORT_DIR, data_filename)
    with open(ws_data_path, "w", encoding="utf-8") as f:
        json.dump(_round_payload({
            "run_id": get_run_id(),
            "run_note": run_note,
            "config_version": CONFIG_VERSION,
            "date": today,
            # 08-22 (t_512ecc00): actual data as-of from freshness watchdog
            "data_as_of": data_as_of_s,
            "expected_as_of": expected_as_of_s,
            "regime": regime,
            "spy_adx": spy_adx,
            "vix_close": vix_close,
            "adx_verify": adx_verify,
            # P0-3 fix (t_1dacac8d): expose bond as-of + gold for auditability
            # m1/m2 fix (Zoe 09-03, t_8cd84165): bond_context carries a
            # self-describing "source" field; gold_context carries the
            # gold-specific material threshold (both emitted above).
            "bond_context": (macro_ctx if macro_ctx else None),
            "gold_context": gold_context_summary(macro_ctx),
            "universe_meta": universe_meta,
            # 1.0.5 (t_6ed3ff15): same-as-of 1D% prev-close lock audit trail
            "change_pct_lock": change_pct_lock,
            "results": data_results,
        }), f, ensure_ascii=False, indent=2)
    print(f"[💾] Saved: {ws_data_path}", file=sys.stderr)

    # Shared data JSON
    sh_data_path = os.path.join(SHARED_DIR, data_filename)
    with open(sh_data_path, "w", encoding="utf-8") as f:
        json.dump(_round_payload({
            "run_id": get_run_id(),
            "run_note": run_note,
            "config_version": CONFIG_VERSION,
            "date": today,
            # 08-22 (t_512ecc00): actual data as-of from freshness watchdog
            "data_as_of": data_as_of_s,
            "expected_as_of": expected_as_of_s,
            "regime": regime,
            "spy_adx": spy_adx,
            "vix_close": vix_close,
            "adx_verify": adx_verify,
            # P0-3 fix (t_1dacac8d): expose bond as-of + gold for auditability
            # m1/m2 fix (Zoe 09-03, t_8cd84165): bond_context carries a
            # self-describing "source" field; gold_context carries the
            # gold-specific material threshold (both emitted above).
            "bond_context": (macro_ctx if macro_ctx else None),
            "gold_context": gold_context_summary(macro_ctx),
            "universe_meta": universe_meta,
            # 1.0.5 (t_6ed3ff15): same-as-of 1D% prev-close lock audit trail
            "change_pct_lock": change_pct_lock,
            "results": data_results,
        }), f, ensure_ascii=False, indent=2)
    print(f"[💾] Saved: {sh_data_path}", file=sys.stderr)

    # ── 2. Compute SHA256 + save .sha256 for both copies ──
    ws_sha = save_sha256_file(ws_data_path)
    sh_sha = save_sha256_file(sh_data_path)

    # ── 3. Verify hash on the shared copy (primary reference) ──
    verify_result = verify_sha256_file(sh_data_path)
    if verify_result is False:
        print("[❌] DATA INTEGRITY FAILURE — Hash mismatch on data JSON!", file=sys.stderr)
        print("[❌] Report generation BLOCKED to prevent corrupt output.", file=sys.stderr)
        return 1

    # ── 4. Save full results for future diff (with hash metadata) ──
    full_results_path = os.path.join(SHARED_DIR, "latest-daily-results.json")
    with open(full_results_path, "w", encoding="utf-8") as f:
        json.dump(_round_payload({
            "date": today,
            # 08-22 (t_512ecc00): actual data as-of from freshness watchdog
            "data_as_of": data_as_of_s,
            "expected_as_of": expected_as_of_s,
            "regime": regime,
            "spy_adx": spy_adx,
            "vix_close": vix_close,
            "adx_verify": adx_verify,
            "total_scanned": len(results),
            "total_buy": signals_70plus,
            "watchlist_tickers": sorted(watchlist_tickers),
            "atr_missed": atr_missed,
            "run_id": get_run_id(),
            "run_note": run_note,
            "config_version": CONFIG_VERSION,
            "sha256": sh_sha,
            "results": [
                {
                    "ticker": r["ticker"],
                    "total": r["total"],
                    "base_5indicator_total": r.get("base_5indicator_total", r["total"]),
                    "weighted_total_raw": r.get("weighted_total_raw", r["total"]),
                    "close": r.get("close"),
                    "scores": r["scores"],
                    "bracket": r["bracket"],
                    "verdict": r["verdict"],
                    "dmi_direction": r["dmi_direction"],
                    "entry_price": r.get("entry_price"),
                    "stop_loss": r.get("stop_loss"),
                    "take_profit": r.get("take_profit"),
                    "atr14": r.get("atr14"),
                    "risk_pct": r.get("risk_pct"),
                    "reward_pct": r.get("reward_pct"),
                    "rr_ratio": r.get("rr_ratio"),
                }
                for r in sorted(results, key=lambda x: x["total"], reverse=True)
            ],
        }), f, ensure_ascii=False, indent=2)
    print(f"[💾] Saved: {full_results_path}", file=sys.stderr)

    # ── 5. Save report ──
    # Local workspace
    local_path = os.path.join(REPORT_DIR, f"{today}-report.md")
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[💾] Saved: {local_path}", file=sys.stderr)

    # Shared
    shared_path = os.path.join(SHARED_DIR, f"{today}-report.md")
    with open(shared_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[💾] Saved: {shared_path}", file=sys.stderr)

    # ── 5b. Verify-after-write: confirm all output files are readable and valid ──
    # (verify-after-write rule, t_5034ab16 W33). Every save must be verified
    # by re-reading and checking content. A write that fails silently (e.g.
    # disk full, permission denied, partial write) must BLOCK report completion.
    verify_errors = []

    # Verify data JSON (shared)
    if not _verify_write(sh_data_path, is_json=True, min_size=100):
        verify_errors.append(f"data JSON unreadable/invalid: {sh_data_path}")

    # Verify report.md (shared)
    if not _verify_write(shared_path, min_size=50):
        verify_errors.append(f"report.md unreadable/invalid: {shared_path}")

    # Verify latest-daily-results.json
    if not _verify_write(full_results_path, is_json=True, min_size=50):
        verify_errors.append(f"latest-daily-results unreadable/invalid: {full_results_path}")

    if verify_errors:
        print(f"[❌] VERIFY-AFTER-WRITE FAILED — {len(verify_errors)} file(s) unreadable/invalid:", file=sys.stderr)
        for e in verify_errors:
            print(f"     - {e}", file=sys.stderr)
        print("[❌] Report generation BLOCKED to prevent corrupt/incomplete output.", file=sys.stderr)
        return 1

    print("[✅] All output files verified after write (data.json, report.md, latest-daily-results.json)", file=sys.stderr)

    # ── 6. Print report to stdout ──
    print(report)
    return 0


# ══════════════════════════════════════════════════════════════════════
# ROLLING 4-WEEK BRACKET WIN RATE (Zoe Rubric #69) — LIVE engine
# t_c36bf49b (W34→W35 P0): replaces the frozen backtest
# latest-weekly-summary.json read (stuck at 2026-07-25) AND the never-wired
# bracket_history stub. Computed fresh from weekly_snapshots every run with
# the same methodology as the canonical backtests.
# ══════════════════════════════════════════════════════════════════════

def compute_rolling_4wk_wr_live(db_path=None, n_weeks=4, slippage=0.001,
                                live_sma10=None):
    """
    LIVE rolling 4-week bracket WR from weekly_snapshots (Rubric #69).

    Methodology mirrors the canonical backtests exactly (v2_1_backtest.py /
    dmi_gating_backtest.py):
      - price proxy = sma_short (SMA10)
      - fwd_return = sma_short[next week] / sma_short[this week] - 1
      - net = fwd_return - slippage (0.1% each way)
      - win = net > 0
    Window = the last `n_weeks` weekly snapshots with a resolvable forward
    return (i.e. every week except the most recent snapshot, which has no
    forward data until the next weekly run lands). The window rolls
    automatically as new weekly snapshots are written.

    Zoe 08-27 B2 (t_692f4462): the pending week (latest weekly snapshot)
    is now ALSO resolved when `live_sma10` is provided — a {ticker: current
    daily SMA10} map from the daily batch. That lets the newest week enter
    the rolling window immediately (partial-week forward return vs live
    daily SMA10) instead of staying frozen until the NEXT weekly snapshot
    lands (~7 days). This is the acceptance-key fix for the "rolling WR
    window includes 08-21 week" requirement: with live data through 08-27,
    the 08-21 week resolves on the 08-28 report.

    Returns:
        dict with keys:
          - brackets: {bracket_name: {rolling_win_rate (0..1 or None),
                                      rolling_total_signals,
                                      rolling_total_wins,
                                      rolling_5d_forward_return_pct,
                                      n_weeks, latest_week}}
          - window_start / window_end / pending_week / n_weeks
          - live_resolved (bool) / live_resolve_note (str|None)
          - generated_at, source
        brackets empty -> no resolvable data (caller retires the section
        rather than presenting a frozen table as live).
    """
    meta = {
        "source": "weekly_snapshots live (SMA10 proxy, 0.1% slippage)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brackets": {},
        "n_weeks": 0,
        "window_start": None,
        "window_end": None,
        "pending_week": None,
        "live_resolved": False,
        "live_resolve_note": None,
    }
    if db_path is None:
        db_path = os.path.expanduser("~/.hermes/shared/data/renee_indicators.db")
    if not os.path.exists(db_path):
        print(f"[⚠️] Rolling WR live: DB not found {db_path}", file=sys.stderr)
        return meta
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT week_end, ticker, signal_bracket, sma_short "
            "FROM weekly_snapshots "
            "WHERE sma_short IS NOT NULL AND sma_short > 0 "
            "ORDER BY week_end, ticker"
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[⚠️] Rolling WR live: DB query failed — {e}", file=sys.stderr)
        return meta
    if not rows:
        print("[⚠️] Rolling WR live: weekly_snapshots empty", file=sys.stderr)
        return meta

    # Group by week_end (ASC order)
    by_week = {}
    for week_end, ticker, bracket, sma in rows:
        by_week.setdefault(week_end, {})[ticker] = (bracket, sma)
    weeks = sorted(by_week.keys())
    if len(weeks) < 2:
        print("[⚠️] Rolling WR live: <2 weekly snapshots — no forward data yet",
              file=sys.stderr)
        return meta

    # The most recent snapshot is pending (no forward data). Resolvable weeks
    # are all earlier ones; take the last n_weeks of them.
    pending_week = weeks[-1]
    pairs = [(weeks[i], weeks[i + 1]) for i in range(len(weeks) - 1)]

    # Zoe 08-27 B2: resolve the pending week against live daily SMA10 when
    # available (partial-week forward return). Only the newest week can be
    # pending, so only it gets live resolution.
    live_resolved = False
    if live_sma10:
        # m3 (Zoe 09-01): keep the INPUT universe count (today's daily
        # universe) separate from the resolved intersection — the 09-01
        # report showed "(30 tickers)" and readers could not tell 31-1.
        live_universe = {t for t, s in live_sma10.items() if s and s > 0}
        live_cur = {}
        for ticker, (bracket, sma_this) in by_week[pending_week].items():
            ls = live_sma10.get(ticker)
            if ls and ls > 0:
                live_cur[ticker] = (bracket, float(ls))
        if live_cur:
            pairs.append((pending_week, "__live__"))
            by_week["__live__"] = live_cur
            live_resolved = True

    pairs = pairs[-n_weeks:]
    if not pairs:
        return meta
    meta["pending_week"] = None if live_resolved else pending_week
    meta["window_start"] = pairs[0][0]
    meta["window_end"] = pairs[-1][0]
    meta["n_weeks"] = len(pairs)
    meta["live_resolved"] = live_resolved
    if live_resolved:
        # m3 fix (Zoe 09-01, t_b5acc944): explain the resolved-ticker count —
        # 09-01 report said "(30 tickers)" with no breakdown (08-28 snapshot
        # had 32; 09-01 universe 31; resolved 30 = snapshot ∩ live daily
        # batch). List what could NOT resolve and why, dynamically.
        snap_tickers = set(by_week[pending_week].keys())
        live_tickers = set(live_cur.keys())
        no_live = sorted(snap_tickers - live_tickers)   # in snapshot, no live SMA10
        no_snap = sorted(live_universe - snap_tickers)  # in today's universe, no snapshot row
        breakdown = (f"{len(live_cur)}/{len(snap_tickers)} weekly-snapshot tickers "
                     f"resolved = {pending_week} snapshot ∩ today's "
                     f"{len(live_universe)}-ticker daily universe")
        if no_live:
            if len(no_live) <= 8:
                breakdown += f"; NOT resolvable: {', '.join(no_live)}"
            else:
                breakdown += (f"; NOT resolvable: {len(no_live)} tickers "
                              f"(not in today's daily universe), e.g. "
                              f"{', '.join(no_live[:5])}…")
        if no_snap:
            breakdown += (f"; excluded from snapshot: {', '.join(no_snap)} "
                          f"(no {pending_week} snapshot row)")
        meta["live_resolve_note"] = (
            f"latest week {pending_week} resolved against LIVE daily SMA10 "
            f"({breakdown}; partial-week fwd return — auto-rolls "
            f"weekly on snapshot resolution)")

    per_bracket = {}
    for week, next_week in pairs:
        cur = by_week[week]
        nxt = by_week.get(next_week, {})
        for ticker, (bracket, sma_this) in cur.items():
            if not bracket:
                continue
            nxt_row = nxt.get(ticker)
            if nxt_row is None:
                continue
            sma_next = nxt_row[1]
            if not sma_next or sma_next <= 0:
                continue
            fwd_net = sma_next / sma_this - 1.0 - slippage
            per_bracket.setdefault(bracket, []).append(fwd_net)

    out = {}
    for bracket_name, rets in per_bracket.items():
        wins = sum(1 for r in rets if r > 0)
        wr = wins / len(rets) if rets else None
        out[bracket_name] = {
            "rolling_win_rate": round(wr, 4) if wr is not None else None,
            "rolling_total_signals": len(rets),
            "rolling_total_wins": wins,
            "rolling_5d_forward_return_pct": round(
                sum(rets) / len(rets) * 100.0, 4) if rets else None,
            "n_weeks": meta["n_weeks"],
            "latest_week": meta["window_end"],
        }
    meta["brackets"] = out
    return meta


if __name__ == "__main__":
    sys.exit(main())
