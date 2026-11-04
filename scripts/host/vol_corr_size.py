#!/usr/bin/env python3
"""Volatility × correlation position-size clamp.

Post-score sizing overlay — never edits tm_score or valuation_score. E5: applies
per sleeve independently; no blended caps.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASELINE_CAP = 0.20
ABS_FLOOR = 0.05


def _vol_multiplier(ann_vol: float) -> float:
    """Continuous, non-increasing vol multiplier (higher vol → smaller cap).

    Segments: <15% → 1.25 · 15–30% → 1.0 → 0.625 · 30–50% → 0.625 → 0.25 ·
    >50% → hold 0.25 (the multiplier never rises again as vol worsens).
    Continuous at the 30% and 50% boundaries is a hard invariant — the 0.30
    boundary previously stepped 0.625 → 0.75 and ABOVE 0.50 stepped 0.25 →
    0.50, doubling the cap for higher-risk books. The 15% boundary steps
    1.25 → 1.0 BY DESIGN (the low-vol boost tier ends there).
    """
    if ann_vol < 0.15:
        return 1.25
    if ann_vol < 0.30:
        # linear 1.0 @ 15% -> 0.625 @ 30%
        t = (ann_vol - 0.15) / 0.15
        return 1.0 - 0.375 * t
    if ann_vol <= 0.50:
        # linear 0.625 @ 30% -> 0.25 @ 50% (continuous with the first leg)
        t = (ann_vol - 0.30) / 0.20
        return 0.625 - 0.375 * t
    return 0.25


def _corr_multiplier(avg_corr: float) -> float:
    if avg_corr >= 0.80:
        return 0.70
    if avg_corr >= 0.60:
        return 0.85
    if avg_corr >= 0.40:
        return 1.0
    if avg_corr >= 0.20:
        return 1.05
    return 1.10


def position_cap_pct(
    ann_vol: float,
    avg_corr: float,
    *,
    baseline: float = BASELINE_CAP,
) -> float:
    """Max position size as fraction of book after vol and corr overlays."""
    if ann_vol < 0:
        ann_vol = 0.0
    if avg_corr < 0:
        avg_corr = 0.0
    if avg_corr > 1:
        avg_corr = 1.0

    cap = baseline * _vol_multiplier(ann_vol) * _corr_multiplier(avg_corr)
    return round(max(cap, ABS_FLOOR), 4)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vol×corr position cap calculator")
    parser.add_argument("--ann-vol", type=float, required=True, help="Annualized vol")
    parser.add_argument("--avg-corr", type=float, required=True, help="Avg corr vs book")
    parser.add_argument(
        "--baseline",
        type=float,
        default=BASELINE_CAP,
        help="Base name cap (default 0.20)",
    )
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    cap = position_cap_pct(args.ann_vol, args.avg_corr, baseline=args.baseline)
    result = {
        "ann_vol": args.ann_vol,
        "avg_corr": args.avg_corr,
        "baseline": args.baseline,
        "position_cap_pct": cap,
        "vol_multiplier": round(_vol_multiplier(args.ann_vol), 4),
        "corr_multiplier": round(_corr_multiplier(args.avg_corr), 4),
    }

    payload = json.dumps(result, indent=2, sort_keys=True)
    payload += "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
