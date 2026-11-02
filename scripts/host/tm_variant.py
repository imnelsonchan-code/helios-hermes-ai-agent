#!/usr/bin/env python3
"""T&M pack variant stamping and shadow bracket gates.

Shadow-only experiment packs — never rewrite live Option 6 weights or tm_score
except equal_weights adds shadow_tm_score. E5: T&M sleeve only; no value blend.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

VARIANT_KEYS = frozenset({"control", "no_option_g", "dmi_off", "equal_weights"})
SCORING_CONTRACT = "option6_v4.4"
# Option G: demote BUY->WATCH when SPY ADX is strictly below this (daily control only).
OPTION_G_SPY_ADX_THRESHOLD = 25
BRACKETS = ("NO_SIGNAL", "WATCH", "BUY")
_BREAKDOWN_LEGS = ("macd", "rsi", "ma", "adx", "volume")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _bracket_from_score(score: float | None) -> str:
    if score is None:
        return "NO_SIGNAL"
    if score >= 60:
        return "BUY"
    if score >= 50:
        return "WATCH"
    return "NO_SIGNAL"


def _apply_dmi_shift(bracket: str, dmi_shift: int | None) -> str:
    if dmi_shift is None or dmi_shift == 0:
        return bracket
    idx = BRACKETS.index(bracket)
    idx = max(0, min(len(BRACKETS) - 1, idx + int(dmi_shift)))
    return BRACKETS[idx]


def _leg_score(breakdown: dict, leg: str) -> float | None:
    raw = breakdown.get(leg)
    if raw is None:
        return None
    if isinstance(raw, dict):
        for key in ("score", "points", "value"):
            if key in raw:
                return _to_float(raw[key])
        return None
    return _to_float(raw)


def shadow_equal_weights_score(row: dict) -> float | None:
    """Recompute tm_score with equal 20pt legs; never mutates tm_score."""
    breakdown = row.get("score_breakdown")
    if not isinstance(breakdown, dict):
        return None
    legs = [leg for leg in _BREAKDOWN_LEGS if leg in breakdown]
    if len(legs) != 5:
        return None
    total = 0.0
    for leg in legs:
        pts = _leg_score(breakdown, leg)
        if pts is None:
            return None
        total += max(0.0, min(20.0, pts))
    return round(total, 2)


def stamp_variant(pack: dict, variant_key: str) -> dict:
    """Return a shallow copy of pack with meta.variant_key stamped."""
    if variant_key not in VARIANT_KEYS:
        raise ValueError(f"unknown variant_key: {variant_key}")
    out = copy.deepcopy(pack)
    meta = dict(out.get("meta") or {})
    meta["variant_key"] = variant_key
    if variant_key == "control":
        meta["scoring_contract"] = SCORING_CONTRACT
    out["meta"] = meta
    return out


def apply_shadow_gates(
    row: dict,
    variant_key: str,
    *,
    spy_adx: float | None = None,
    timeframe: str = "daily",
    adx_threshold: float | None = None,
) -> str:
    """Return effective bracket after shadow gates; tm_score unchanged.

    Option G (SPY ADX < ``OPTION_G_SPY_ADX_THRESHOLD`` demotes BUY->WATCH)
    applies only for ``control`` on **daily** packs. Weekly T&M has no Option G.
    When ``spy_adx`` is missing (None), Option G is skipped — no demote.
    Caller must decide fail-closed policy if ADX is required.
    ``adx_threshold`` defaults to ``OPTION_G_SPY_ADX_THRESHOLD`` when None.
    """
    if variant_key not in VARIANT_KEYS:
        raise ValueError(f"unknown variant_key: {variant_key}")

    threshold = (
        OPTION_G_SPY_ADX_THRESHOLD if adx_threshold is None else float(adx_threshold)
    )
    tf = str(timeframe or "daily").strip().lower()
    if variant_key == "equal_weights":
        shadow = shadow_equal_weights_score(row)
        if shadow is not None:
            row["shadow_tm_score"] = shadow
        score = shadow if shadow is not None else _to_float(row.get("tm_score"))
    else:
        score = _to_float(row.get("tm_score"))

    bracket = _bracket_from_score(score)

    if variant_key != "dmi_off":
        dmi_shift = row.get("dmi_shift")
        try:
            shift = int(dmi_shift) if dmi_shift is not None else None
        except (TypeError, ValueError):
            shift = None
        bracket = _apply_dmi_shift(bracket, shift)

    if (
        variant_key == "control"
        and tf == "daily"
        and spy_adx is not None
        and spy_adx < threshold
        and bracket == "BUY"
    ):
        bracket = "WATCH"

    return bracket


def _iter_rows(pack: dict) -> list[dict]:
    rows: list[dict] = []
    for key in ("results", "rankings", "signals", "rows"):
        block = pack.get(key)
        if isinstance(block, list):
            rows.extend(r for r in block if isinstance(r, dict))
    tracks = pack.get("tracks")
    if isinstance(tracks, dict):
        for track in tracks.values():
            if isinstance(track, dict):
                rankings = track.get("rankings")
                if isinstance(rankings, list):
                    rows.extend(r for r in rankings if isinstance(r, dict))
    return rows


def apply_variant_to_pack(
    pack: dict,
    variant_key: str,
    *,
    spy_adx: float | None = None,
    timeframe: str = "daily",
    adx_threshold: float | None = None,
) -> dict:
    """Stamp variant and annotate rows with effective_bracket (shadow).

    ``adx_threshold`` defaults to ``OPTION_G_SPY_ADX_THRESHOLD``. Missing
    ``spy_adx`` skips Option G demote (caller decides fail-closed).
    """
    out = stamp_variant(pack, variant_key)
    for row in _iter_rows(out):
        bracket = apply_shadow_gates(
            row,
            variant_key,
            spy_adx=spy_adx,
            timeframe=timeframe,
            adx_threshold=adx_threshold,
        )
        row["effective_bracket"] = bracket
        if variant_key == "equal_weights":
            shadow = shadow_equal_weights_score(row)
            if shadow is not None:
                row["shadow_tm_score"] = shadow
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T&M variant stamp + shadow gates")
    parser.add_argument("--pack", required=True, help="Input pack JSON path")
    parser.add_argument(
        "--variant",
        required=True,
        choices=sorted(VARIANT_KEYS),
        help="Shadow variant key",
    )
    parser.add_argument(
        "--spy-adx",
        type=float,
        default=None,
        help="SPY ADX for Option G (control + daily only); missing skips demote",
    )
    parser.add_argument(
        "--adx-threshold",
        type=float,
        default=OPTION_G_SPY_ADX_THRESHOLD,
        help=(
            f"Option G demote when spy_adx < threshold "
            f"(default {OPTION_G_SPY_ADX_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--timeframe",
        default="daily",
        choices=("daily", "weekly"),
        help="daily applies Option G; weekly never suppresses BUY for ADX",
    )
    parser.add_argument("--out", default="", help="Write stamped pack JSON here")
    args = parser.parse_args(argv)

    try:
        pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[tm_variant] cannot read pack: {exc}", file=sys.stderr)
        return 2

    if not isinstance(pack, dict):
        print("[tm_variant] pack root must be object", file=sys.stderr)
        return 2

    try:
        out = apply_variant_to_pack(
            pack,
            args.variant,
            spy_adx=args.spy_adx,
            timeframe=args.timeframe,
            adx_threshold=args.adx_threshold,
        )
    except ValueError as exc:
        print(f"[tm_variant] {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(out, indent=2, sort_keys=True)
    payload += "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
