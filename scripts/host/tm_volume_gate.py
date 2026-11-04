#!/usr/bin/env python3
"""Volume confirmation gate for T&M BUY rows.

Demotes effective BUY to WATCH when volume confirmation fails. Never changes
tm_score or Option 6 weights. E5: T&M sleeve only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_VOLUME_THRESHOLD = 12
DEFAULT_MIN_RATIO = 1.0


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _volume_breakdown_score(row: dict) -> float | None:
    breakdown = row.get("score_breakdown")
    if not isinstance(breakdown, dict):
        return None
    vol = breakdown.get("volume")
    if isinstance(vol, dict):
        for key in ("score", "points", "value"):
            if key in vol:
                return _to_float(vol[key])
        return None
    return _to_float(vol)


def volume_confirmed(
    row: dict,
    *,
    threshold: float = DEFAULT_VOLUME_THRESHOLD,
    min_ratio: float = DEFAULT_MIN_RATIO,
) -> bool:
    """True when volume_ratio exceeds min_ratio or volume leg meets threshold."""
    ratio = _to_float(row.get("volume_ratio"))
    if ratio is None:
        raw = row.get("raw_indicators")
        if isinstance(raw, dict):
            ratio = _to_float(raw.get("volume_ratio"))
    if ratio is not None and ratio > min_ratio:
        return True
    vol_score = _volume_breakdown_score(row)
    if vol_score is not None and vol_score >= threshold:
        return True
    return False


def _effective_bracket(row: dict) -> str:
    for key in ("effective_bracket", "bracket", "theoretical_bracket", "signal"):
        raw = row.get(key)
        if isinstance(raw, str) and raw.strip():
            text = raw.strip().upper()
            if text[0:1].isdigit():
                continue  # score band like 60-69
            return text
    daily_b = str(row.get("daily_bracket") or "").strip().upper()
    if daily_b in ("BUY", "WATCH", "SELL", "NO_SIGNAL", "AVOID"):
        return daily_b
    score = _to_float(row.get("tm_score"))
    if score is None:
        score = _to_float(row.get("daily_score"))
    if score is None:
        return "NO_SIGNAL"
    if score >= 60:
        return "BUY"
    if score >= 50:
        return "WATCH"
    return "NO_SIGNAL"


def apply_volume_gate(
    row: dict,
    *,
    threshold: float = DEFAULT_VOLUME_THRESHOLD,
    min_ratio: float = DEFAULT_MIN_RATIO,
) -> tuple[str, str | None]:
    """Return (bracket, reason). Demotes BUY->WATCH when volume fails.

    ``threshold``/``min_ratio`` reach the actual demotion decision (they only
    drive ``volume_confirmed``; the CLI overrides were silently ignored here).
    """
    bracket = _effective_bracket(row)
    if bracket != "BUY":
        return bracket, None
    if volume_confirmed(row, threshold=threshold, min_ratio=min_ratio):
        return bracket, None
    return (
        "WATCH",
        f"volume_gate: confirmation failed (ratio<= {min_ratio:g} and "
        f"volume leg score< {threshold:g} of 20)",
    )
def apply_volume_gate_to_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        bracket, reason = apply_volume_gate(item)
        item["effective_bracket"] = bracket
        if reason:
            item["volume_gate_reason"] = reason
        out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T&M volume BUY gate (batch JSON)")
    parser.add_argument("--in", dest="in_path", required=True, help="Input JSON array")
    parser.add_argument("--out", default="", help="Output JSON path (stdout if empty)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_VOLUME_THRESHOLD,
        help="Minimum volume leg score (of 20)",
    )
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=DEFAULT_MIN_RATIO,
        help="Minimum volume_ratio (vol/21MA)",
    )
    args = parser.parse_args(argv)

    try:
        raw = json.loads(Path(args.in_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[tm_volume_gate] cannot read input: {exc}", file=sys.stderr)
        return 2

    if not isinstance(raw, list):
        print("[tm_volume_gate] input must be JSON array of rows", file=sys.stderr)
        return 2

    rows = [r for r in raw if isinstance(r, dict)]
    out_rows: list[dict] = []
    for row in rows:
        item = dict(row)
        if volume_confirmed(item, threshold=args.threshold, min_ratio=args.min_ratio):
            confirmed = True
        else:
            confirmed = False
        # Thread the CLI overrides into the demotion itself (they only
        # reported a flag before; BUY rows could stay BUY while the run said
        # volume_confirmed: false).
        bracket, reason = apply_volume_gate(
            item, threshold=args.threshold, min_ratio=args.min_ratio
        )
        item["volume_confirmed"] = confirmed
        item["effective_bracket"] = bracket
        if reason:
            item["volume_gate_reason"] = reason
        out_rows.append(item)

    payload = json.dumps(out_rows, indent=2, sort_keys=True)
    payload += "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
