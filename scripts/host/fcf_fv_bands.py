#!/usr/bin/env python3
"""Normalized FCF multiple fair-value bands (10/15/20×).

Second-width fv_engine overlay — does not modify valuation_score. E5: value
sleeve only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FV_ENGINE = "fcf_band_10_15_20"
MULTIPLES = {
    "conservative": 10,
    "reasonable": 15,
    "optimistic": 20,
}
CANDIDATE_UPSIDE_FLOOR = 0.15


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _resolve_shares(
    *,
    shares: float | None,
    market_cap: float | None,
    spot: float | None,
) -> float | None:
    if shares is not None and shares > 0:
        return shares
    if market_cap is not None and spot is not None and spot > 0:
        return market_cap / spot
    return None


def compute_fv_range(
    *,
    fcf: float,
    shares: float | None = None,
    market_cap: float | None = None,
    spot: float | None = None,
) -> dict[str, float]:
    """Per-share FV from normalized FCF multiples."""
    if fcf <= 0:
        raise ValueError("fcf must be positive")
    resolved = _resolve_shares(shares=shares, market_cap=market_cap, spot=spot)
    if resolved is None or resolved <= 0:
        raise ValueError("shares or market_cap+spot required")
    per_share_fcf = fcf / resolved
    return {
        band: round(mult * per_share_fcf, 4)
        for band, mult in MULTIPLES.items()
    }


def upside_vs(band_fv: float, spot: float) -> float | None:
    """Return fractional upside (band/spot - 1). None when spot invalid."""
    if spot is None or spot <= 0:
        return None
    return (band_fv / spot) - 1.0


def candidate_ok(
    fv_range: dict[str, float],
    spot: float,
    *,
    band: str = "reasonable",
    min_upside: float = CANDIDATE_UPSIDE_FLOOR,
) -> bool:
    """True when upside vs chosen band meets Candidate floor (+15%)."""
    fv = fv_range.get(band)
    if fv is None:
        return False
    up = upside_vs(fv, spot)
    if up is None:
        return False
    return up >= min_upside


def stamp_fcf_bands(
    row: dict,
    *,
    fcf: float | None = None,
    shares: float | None = None,
    market_cap: float | None = None,
    spot: float | None = None,
    band: str = "reasonable",
) -> dict:
    """Return row copy with fv_engine + fv_range stamped; no valuation_score."""
    out = dict(row)
    fcf_val = _to_float(fcf if fcf is not None else row.get("fcf"))
    if fcf_val is None:
        fcf_val = _to_float(row.get("fcf_ttm"))
    if fcf_val is None:
        fcf_val = _to_float(row.get("fcf_avg_3y"))
    if fcf_val is None:
        fcf_val = _to_float(row.get("fcf_avg_5y"))

    shares_val = _to_float(shares if shares is not None else row.get("shares"))
    mcap_val = _to_float(
        market_cap if market_cap is not None else row.get("market_cap")
    )
    spot_val = _to_float(spot if spot is not None else row.get("spot"))
    if spot_val is None:
        spot_val = _to_float(row.get("price"))

    if fcf_val is None or fcf_val <= 0:
        raise ValueError("positive fcf required")

    fv_range = compute_fv_range(
        fcf=fcf_val,
        shares=shares_val,
        market_cap=mcap_val,
        spot=spot_val,
    )
    out["fv_engine"] = FV_ENGINE
    out["fv_range"] = fv_range
    chosen = fv_range.get(band, fv_range["reasonable"])
    up = upside_vs(chosen, spot_val) if spot_val else None
    out["fcf_band_upside"] = {
        "band": band,
        "upside": round(up, 4) if up is not None else None,
        "candidate_ok": candidate_ok(fv_range, spot_val, band=band) if spot_val else False,
    }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FCF 10/15/20× fair-value bands")
    parser.add_argument("--row-json", default="", help="Input row JSON")
    parser.add_argument("--fcf", type=float, default=None)
    parser.add_argument("--shares", type=float, default=None)
    parser.add_argument("--market-cap", type=float, default=None)
    parser.add_argument("--spot", type=float, default=None)
    parser.add_argument(
        "--band",
        default="reasonable",
        choices=sorted(MULTIPLES.keys()),
        help="Band for candidate_ok check",
    )
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    row: dict = {}
    if args.row_json:
        try:
            loaded = json.loads(args.row_json)
        except json.JSONDecodeError as exc:
            print(f"[fcf_fv_bands] invalid row-json: {exc}", file=sys.stderr)
            return 2
        if not isinstance(loaded, dict):
            print("[fcf_fv_bands] row-json must be object", file=sys.stderr)
            return 2
        row = loaded

    try:
        result = stamp_fcf_bands(
            row,
            fcf=args.fcf,
            shares=args.shares,
            market_cap=args.market_cap,
            spot=args.spot,
            band=args.band,
        )
    except ValueError as exc:
        print(f"[fcf_fv_bands] {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(result, indent=2, sort_keys=True)
    payload += "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
