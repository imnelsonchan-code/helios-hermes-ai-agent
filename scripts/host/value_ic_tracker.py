#!/usr/bin/env python3
"""Value sleeve IC tracker — Spearman rank IC vs injected forward returns.

Parallel to Renee ``scoring_ic_tracker.py`` but **value sleeve only**.
Never blends ``valuation_score`` with ``quality_adjusted_score`` or T&M scores.
Forward returns are injected via ``--returns-json`` (no yfinance in unit path).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

LOOKAHEAD_IC_THRESHOLD = 0.10
HORIZON_KEYS = frozenset({"4w", "12w", "1w", "8w", "26w"})


def _rank_values(values: list[float]) -> list[float]:
    """1-based average ranks with tie handling."""
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_ic(scores: dict[str, float], returns: dict[str, float]) -> float | None:
    """Spearman rank correlation between *scores* and *returns* (common tickers only)."""
    pairs: list[tuple[float, float]] = []
    for ticker, score in scores.items():
        if ticker not in returns:
            continue
        ret = returns[ticker]
        if score is None or ret is None:
            continue
        try:
            s_val = float(score)
            r_val = float(ret)
        except (TypeError, ValueError):
            continue
        if math.isnan(s_val) or math.isnan(r_val):
            continue
        pairs.append((s_val, r_val))
    if len(pairs) < 3:
        return None
    score_vals = [p[0] for p in pairs]
    ret_vals = [p[1] for p in pairs]
    rank_s = _rank_values(score_vals)
    rank_r = _rank_values(ret_vals)
    n = len(pairs)
    mean_s = sum(rank_s) / n
    mean_r = sum(rank_r) / n
    num = sum((rank_s[i] - mean_s) * (rank_r[i] - mean_r) for i in range(n))
    den_s = sum((rank_s[i] - mean_s) ** 2 for i in range(n))
    den_r = sum((rank_r[i] - mean_r) ** 2 for i in range(n))
    if den_s == 0 or den_r == 0:
        return None
    return num / math.sqrt(den_s * den_r)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def extract_value_rows(report: dict) -> list[dict]:
    """Collect ranking rows from valuation-width JSON (tracks A/B or top-level)."""
    rows: list[dict] = []
    top = report.get("rankings")
    if isinstance(top, list):
        rows.extend(top)
    tracks = report.get("tracks")
    if isinstance(tracks, dict):
        for track_key in ("A", "B"):
            track = tracks.get(track_key, {})
            if isinstance(track, dict):
                rankings = track.get("rankings")
                if isinstance(rankings, list):
                    rows.extend(rankings)
    return rows


def row_valuation_score(row: dict) -> float | None:
    """Five-factor value score only — never tm_score or blended fields."""
    vs = _to_float(row.get("valuation_score"))
    if vs is not None:
        return vs
    vc = _to_float(row.get("valuation_composite"))
    if vc is not None:
        return round(vc * 100)
    cs = _to_float(row.get("composite_score"))
    if cs is not None:
        return round(cs * 100)
    return None


def row_quality_adjusted_score(row: dict) -> float | None:
    """Optional quality-adjusted series — separate from valuation_score."""
    raw = row.get("quality_adjusted_score")
    if raw is None:
        return None
    val = _to_float(raw)
    if val is None:
        return None
    if val <= 1.5:
        return round(val * 100)
    return val


def scores_from_rows(rows: list[dict], field: str) -> dict[str, float]:
    extractor = row_valuation_score if field == "valuation_score" else row_quality_adjusted_score
    out: dict[str, float] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        score = extractor(row)
        if score is not None:
            out[ticker] = score
    return out


def parse_returns_payload(data: Any) -> dict[str, dict[str, float]]:
    """Normalize returns JSON to ``{horizon: {ticker: return}}``."""
    if not isinstance(data, dict) or not data:
        return {}
    sample = next(iter(data.values()))
    if isinstance(sample, dict):
        if any(str(k).lower() in HORIZON_KEYS or str(k).endswith("w") for k in data):
            horizons: dict[str, dict[str, float]] = {}
            for horizon, mapping in data.items():
                if not isinstance(mapping, dict):
                    continue
                tick_map: dict[str, float] = {}
                for ticker, ret in mapping.items():
                    val = _to_float(ret)
                    if val is not None:
                        tick_map[str(ticker).strip().upper()] = val
                if tick_map:
                    horizons[str(horizon)] = tick_map
            return horizons
    flat: dict[str, float] = {}
    for ticker, ret in data.items():
        val = _to_float(ret)
        if val is not None:
            flat[str(ticker).strip().upper()] = val
    return {"single": flat} if flat else {}


def compute_ic_series(
    rows: list[dict],
    horizons: dict[str, dict[str, float]],
) -> tuple[list[dict], list[str]]:
    """Return IC series entries and look-ahead warning strings."""
    series: list[dict] = []
    warnings: list[str] = []
    score_fields = ["valuation_score"]
    if any(row_quality_adjusted_score(r) is not None for r in rows):
        score_fields.append("quality_adjusted_score")

    for score_field in score_fields:
        scores = scores_from_rows(rows, score_field)
        for horizon, ret_map in sorted(horizons.items()):
            ic = spearman_ic(scores, ret_map)
            n = len(set(scores) & set(ret_map))
            entry = {
                "sleeve": "value",
                "score_field": score_field,
                "horizon": horizon,
                "ic": ic,
                "n": n,
            }
            series.append(entry)
            if ic is not None and abs(ic) > LOOKAHEAD_IC_THRESHOLD:
                warnings.append(
                    f"LOOKAHEAD_SUSPECT: |IC|={abs(ic):.3f} > {LOOKAHEAD_IC_THRESHOLD} "
                    f"for {score_field} @ {horizon} (Vibe-Trading style warning only)"
                )
    return series, warnings


def load_json(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def format_ic_line(entry: dict) -> str:
    ic = entry.get("ic")
    ic_s = f"{ic:+.4f}" if ic is not None else "n/a"
    return (
        f"{entry['score_field']:24s} {entry['horizon']:6s} "
        f"IC={ic_s} n={entry['n']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Value sleeve Spearman IC vs injected forward returns"
    )
    parser.add_argument(
        "--width-json",
        required=True,
        help="Valuation-width JSON with rankings/rows",
    )
    parser.add_argument(
        "--returns-json",
        required=True,
        help="Ticker->return map or {horizon: {ticker: return}} (e.g. 4w/12w)",
    )
    parser.add_argument(
        "--out",
        help="Optional path to write full result JSON",
    )
    args = parser.parse_args(argv)

    width_path = Path(args.width_json)
    if not width_path.is_file():
        print(f"[value_ic_tracker] ERROR: width JSON not found: {width_path}", file=sys.stderr)
        return 2

    report = load_json(width_path)
    rows = extract_value_rows(report)
    if not rows:
        print("[value_ic_tracker] ERROR: no ranking rows in width JSON", file=sys.stderr)
        return 2

    returns_data = load_json(args.returns_json)
    horizons = parse_returns_payload(returns_data)
    if not horizons:
        print("[value_ic_tracker] ERROR: empty returns map", file=sys.stderr)
        return 2

    series, warnings = compute_ic_series(rows, horizons)
    result = {
        "sleeve": "value",
        "width_json": str(width_path),
        "returns_json": str(args.returns_json),
        "series": series,
        "look_ahead_warnings": warnings,
    }

    print("[value_ic_tracker] VALUE sleeve IC (never blended with T&M or quality series):")
    for entry in series:
        print(format_ic_line(entry))
    for warn in warnings:
        print(f"  ⚠ {warn}")

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
