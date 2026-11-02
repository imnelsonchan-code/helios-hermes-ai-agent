#!/usr/bin/env python3
"""
 — (v4.6 - Production Ready).
"""

import json
import hashlib
import math
import os
from datetime import datetime
from scipy.stats import binomtest, norm

# ── Weight config (P2: live weighting layer) ─────────────────────────
WEIGHT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "renee_weight_config.json")

def load_weight_config():
    """
    Load indicator weights from renee_weight_config.json.
    Returns None if file absent or empty -> score_total() uses unweighted default.
    Format: {"macd": 1.4, "rsi": 1.4, "ma": 1.4, "adx": 1.2, "volume": 1.4}
    """
    if not os.path.exists(WEIGHT_CONFIG_PATH):
        return None
    try:
        with open(WEIGHT_CONFIG_PATH) as f:
            cfg = json.load(f)
        if not cfg or not isinstance(cfg, dict):
            return None
        return cfg
    except Exception:
        return None

SWEEP_STATUS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    ".sweep_status")

def save_weight_config(weights):
    """Persist optimal weights (called by sweep pipeline after human approval)."""
    with open(WEIGHT_CONFIG_PATH, "w") as f:
        json.dump(weights, f, indent=2)

def write_sweep_status(status, val_sharpe=None, config_hash=None, details=None):
    """
    Write .sweep_status file with PASS/FAIL + metadata.

    status: 'PASS' or 'FAIL'
    val_sharpe: validation Sharpe ratio (float, optional)
    config_hash: SHA256 of weight config used (str, optional)
    details: arbitrary dict for additional context (optional)
    """
    import hashlib as _hashlib
    record = {
        "status": status.upper(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "val_sharpe": val_sharpe,
        "config_hash": config_hash,
        "details": details or {},
    }
    with open(SWEEP_STATUS_PATH, "w") as f:
        json.dump(record, f, indent=2, default=str)

def check_sweep_status():
    """
    Read .sweep_status and validate contents.

    Returns dict with fields: status, timestamp, val_sharpe, config_hash, details
    Returns None if file is missing or unreadable.
    Raises ValueError if status is not PASS or timestamp is missing.
    """
    if not os.path.exists(SWEEP_STATUS_PATH):
        return None
    try:
        with open(SWEEP_STATUS_PATH) as f:
            record = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if "status" not in record or record["status"] not in ("PASS", "FAIL"):
        raise ValueError(f"Invalid sweep_status: missing/invalid status field")
    if "timestamp" not in record:
        raise ValueError(f"Invalid sweep_status: missing timestamp")
    return record

# ── Period ──────────────────────────────────────────
# Zoe B1 (2026-08-02): adx 7->14 — W31 breakthrough; live pipeline passes
# period_config explicitly from weekly_indicator_update.py (also 14).
DEFAULT_PERIODS = {
    "variant_group": "optimal",
    "macd": {"fast": 12, "slow": 34, "signal": 12},
    "rsi": 9,
    "ma": [10, 50, 200],
    "adx": 14,
    "volume": 5,
    "bb": {"period": 20, "std": 2},
}

# ── ─────────────────────────────────────────────────────────

def score_macd(period_config, macd_line, macd_hist, macd_signal,
               macd_hist_series=None):
    """
 MACD (0-20) — Magnitude-based Scaling (v4.6)
    """
    if macd_hist_series is not None and len(macd_hist_series) > 0:
        max_abs = max(abs(v) for v in macd_hist_series)
        if max_abs == 0:
            return 10
            
        norm_mag = min(abs(macd_hist) / max_abs, 1.0)
        
        if macd_hist > 0:
            return round(10 + (9 * norm_mag))
        elif macd_hist < 0:
            return round(10 - (10 * norm_mag))
        else:
            return 10
    return 10

def score_rsi(period_config, rsi_value):
    """
 RSI (0-20) — v4.5 (Eliminate 20-point spike)

    DESIGN DECISION (formally documented — Zoe 2026-09-01 M1, t_b5acc944):
    the RSI sub-score curve is intentionally NON-MONOTONIC. It rewards BOTH
    momentum strength (70-75 sweet spot -> 17-19, highest) AND deep oversold
    (<30 -> 12, mean-reversion sweet spot). This is the validated backtest
    design ("oversold = bullish mean-reversion"): an RSI falling below 30 is
    treated as a bounce candidate, NOT as a momentum weakness penalty.

    CONSEQUENCE (by design, disclosed in the report Signal Legend): a stock
    whose raw RSI FALLS into deeper oversold (e.g. 32.1->18.1) gets a HIGHER
    sub-score (1->12, +11) — a "score gainer" can be a "price falling" stock.
    In a Trend & Momentum system this direction looks contradictory, so:
      - the driver column leads with the RAW RSI delta (market direction),
        e.g. "RSI 32.1->18.1 (−14.0) [sub +11]" — never the sub-score alone;
      - consumers must NOT read [sub ±N] as momentum direction.
    Alternative (b) — capping momentum sub-score ≤ oversold sub-score — was
    NOT chosen: it would change backtest-validated scoring. See the Signal
    Legend / score_engine docs before re-scoring.
    """
    if rsi_value < 30:
        return 12
    elif rsi_value > 75:
        return 5
    else:
        percentile = (rsi_value - 30) / 45
        return round(percentile * 19)

def score_ma(period_config, sma_short, sma_mid, sma_long):
    """
 MA (0-20)
    """
    if any(math.isnan(v) for v in (sma_short, sma_mid, sma_long)):
        return 4
    if sma_short > sma_mid > sma_long:
        gap_ratio = (sma_short - sma_long) / sma_long
        if gap_ratio >= 0.30: return 20
        elif gap_ratio >= 0.05: return 19
        else: return 18
    elif sma_short > sma_mid and sma_short < sma_long:
        return 14
    elif sma_short < sma_mid < sma_long:
        gap_ratio = (sma_long - sma_short) / sma_long
        if gap_ratio > 0.05: return 5
        else: return 8
    else:
        return 4

def score_adx(period_config, adx_value):
    """
 ADX (0-20) — v4.5 (Quadratic Scaling)
    """
    if adx_value < 0: return 0
    max_adx_range = 60.0
    normalized_adx = min(adx_value, max_adx_range) / max_adx_range
    return round((normalized_adx ** 2) * 20)

def score_volume(period_config, volume_ratio, obv_trend=None, mfi_value=None, obv_pct_change=None):
    """
 Volume (0-20)
    """
    if volume_ratio > 1.5:
        capped = min(volume_ratio, 3.0)
        vr_pts = round(7 + (capped - 1.5) / 1.5 * 3)
    elif volume_ratio >= 1.0:
        vr_pts = round(5 + (volume_ratio - 1.0) / 0.5 * 2)
    else:
        vr_pts = round(1 + (max(0, volume_ratio - 0.3) / 0.7 * 3)) if volume_ratio >= 0.3 else 1

    obv_pts = 0
    if obv_pct_change is not None and obv_trend is not None:
        dir_bonus = 5 if obv_trend == 1 else 0
        mag = min(abs(obv_pct_change) * 25, 5.0)
        obv_pts = min(round(dir_bonus + mag), 10)
    elif obv_trend is not None:
        obv_pts = 5 if obv_trend == 1 else 0

    mfi_pts = 0
    if mfi_value is not None:
        if mfi_value > 80: mfi_pts = 8
        elif mfi_value > 60: mfi_pts = 10
        elif mfi_value > 40: mfi_pts = 6
        elif mfi_value > 20: mfi_pts = 4
        else: mfi_pts = 2

    total = vr_pts + obv_pts + mfi_pts
    return max(0, min(20, round(total * 20 / 30)))

def adjust_adx_by_dmi(adx_pts, plus_di, minus_di):
    if plus_di is None or minus_di is None or adx_pts < 8:
        return adx_pts
    dmi = plus_di - minus_di
    dmi_clamped = max(-50, min(50, dmi))
    return max(0, min(20, adx_pts + round(dmi_clamped / 10)))

def score_total(scores_dict, weights=None):
    """
    Sum component scores into total.
    weights=None  -> unweighted sum (backward compatible, default behavior).
    weights=dict  -> weighted sum: sum(scores[k] * weights.get(k, 1.0) for k in scores),
                    each component capped at 20pt before weighting.
    """
    if weights is None:
        return sum(scores_dict.values())
    capped = {k: min(20, float(v)) for k, v in scores_dict.items()}
    return sum(capped[k] * weights.get(k, 1.0) for k in capped)

def get_signal_bracket(score_total):
    # 08-20 P1 (Zoe T&M t_85a14c20): round to 1dp before bracket comparison.
    # Floating-point totals like 59.99999999999999 (TFC, 08-20 stale report)
    # must classify as "60-69", not phantom-migrate to "<60".
    score_total = round(float(score_total), 1)
    if score_total >= 90: return ">=90"
    elif score_total >= 80: return "80-89"
    elif score_total >= 70: return "70-79"
    elif score_total >= 60: return "60-69"
    elif score_total >= 50: return "50-59"
    else: return "<50"

def get_signal_verdict(score_total, dmi_direction="neutral"):
    # 08-20 P1: same rounding before threshold checks (bracket consistency).
    score_total = round(float(score_total), 1)
    if score_total >= 60: base = "BUY"
    elif score_total >= 50: base = "WATCH"
    else: base = "NO_SIGNAL"
    if dmi_direction == "bearish" and base == "BUY": return "WATCH (bearish trend)"
    if dmi_direction == "bearish" and base == "WATCH": return "NO_SIGNAL (bearish trend)"
    if dmi_direction == "bullish" and base == "WATCH": return "BUY (bullish trend)"
    if dmi_direction == "bullish" and base == "NO_SIGNAL": return "WATCH (bullish trend)"
    return base

def compute_all(raw_indicators, period_config):
    # 1. Robust Input Sanitization (Fixes NaN -> int bug)
    raw = {}
    for k, v in raw_indicators.items():
        if isinstance(v, float) and math.isnan(v):
            raw[k] = None
        else:
            raw[k] = v

    # 2. Individual Component Scores
    macd_pts = score_macd(period_config, raw.get("macd_line"), raw.get("macd_hist"), raw.get("macd_signal"), raw.get("macd_hist_series"))
    rsi_pts = score_rsi(period_config, raw.get("rsi"))
    ma_pts = score_ma(period_config, raw.get("sma_short"), raw.get("sma_mid"), raw.get("sma_long"))
    adx_pts = score_adx(period_config, raw.get("adx"))
    vol_pts = score_volume(period_config, raw.get("volume_ratio"), raw.get("obv_trend"), raw.get("mfi_value"), raw.get("obv_pct_change"))

    # 2.5. DMI Direction Modifier — adjust ADX by DI+/-DI oscillator (v4.7)
    # Only activates when both plus_di/minus_di are available and ADX >= 8.
    # Adds up to ±5pt based on DMI oscillator: bullish trends get a boost,
    # bearish trends get penalized. This discriminates against strong-ADX
    # stocks that are trending in the wrong direction (monotonicity fix).
    adx_pts_raw = adx_pts
    adx_pts = adjust_adx_by_dmi(adx_pts, raw.get("plus_di"), raw.get("minus_di"))

    # 3. Summation (Unweighted by default; weighted if config present)
    scores = {
        "macd": macd_pts, "rsi": rsi_pts, "ma": ma_pts, "adx": adx_pts, "volume": vol_pts
    }
    weights = load_weight_config()
    total = score_total(scores, weights)

    # CLIP+RAW: published total is clipped 0–100; weighted_total_raw is uncapped audit.
    # Do NOT rescale by 100/136 — clip only.
    weighted_total_raw = round(float(total), 1)
    total = round(min(100.0, max(0.0, weighted_total_raw)), 1)

    # 4. Adjustments
    # P1 fix (W33 addendum): apply_obv_divergence_adj / apply_regime_adjustment
    # were dead code (no-op / unreachable "sideways" branch) — removed. Regime
    # handling lives in the daily/weekly pipeline (Option G suppression), not here.

    # 5. Verdict & Metadata
    plus_di = raw.get("plus_di")
    minus_di = raw.get("minus_di")
    dmi_direction = "neutral"
    if plus_di is not None and minus_di is not None:
        if plus_di < minus_di: dmi_direction = "bearish"
        elif plus_di > minus_di: dmi_direction = "bullish"

    saturation = (macd_pts >= 18 and adx_pts >= 18 and rsi_pts >= 14 and total >= 80)

    return {
        "scores": scores,
        "total": total,  # clipped published score (0–100)
        "weighted_total_raw": weighted_total_raw,  # uncapped weighted sum (may be >100)
        # P1 fix (W33 addendum): base_5indicator_total must be the RAW 5-indicator
        # sum (0-100, unweighted) — was copying the weighted total, making the
        # "Base" column identical to "Adjusted" whenever weights != 1.0 (34/34
        # Adj==Base bug). Backtest reweight_scores() uses the same raw sum basis.
        "base_5indicator_total": sum(scores.values()),
        "bracket": get_signal_bracket(total),
        "verdict": get_signal_verdict(total, dmi_direction),
        "dmi_direction": dmi_direction,
        "indicator_saturation_warning": saturation,
        "composite_hash": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest(),
    }
