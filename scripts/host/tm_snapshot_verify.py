#!/usr/bin/env python3
"""Verify T&M narrative claims against engine pack snapshot.

Compares claimed values to pack rows within tolerance. T&M sleeve only —
never attaches P/E, F-Score, or value-sleeve fields.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

DEFAULT_PRICE_TOL = 0.01  # 1% relative
DEFAULT_SCORE_TOL = 0.5  # absolute points

FORBIDDEN_CLAIM_FIELDS = frozenset({
    "pe",
    "p/e",
    "f_score",
    "f-score",
    "fscore",
    "valuation_score",
    "valuation_composite",
    "quality_adjusted_score",
    "width_verdict",
    "fv_range",
})


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def extract_pack_rows(pack: dict) -> dict[str, dict]:
    """Normalize pack to ``ticker -> row`` (T&M fields only in comparisons)."""
    rows: list[dict] = []
    for key in ("results", "rankings", "rows"):
        block = pack.get(key)
        if isinstance(block, list):
            rows.extend(block)
    out: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            out[ticker] = row
    return out


def _normalize_field(field: str) -> str:
    return str(field or "").strip().lower().replace("-", "_")


def _is_price_field(field: str) -> bool:
    norm = _normalize_field(field)
    return norm in {"close", "last", "price", "adj_close", "adj close"}


def _is_score_field(field: str) -> bool:
    norm = _normalize_field(field)
    if norm in {"tm_score", "daily_score", "score"}:
        return True
    return norm.startswith("score_breakdown.")


def _pack_value(row: dict, field: str) -> Any:
    norm = _normalize_field(field)
    if norm.startswith("score_breakdown."):
        key = norm.split(".", 1)[1]
        breakdown = row.get("score_breakdown") or {}
        if isinstance(breakdown, dict):
            return breakdown.get(key)
    aliases = {
        "close": ("close", "last", "Close", "Last"),
        "last": ("last", "close", "Last", "Close"),
        "price": ("price", "close", "last"),
        "tm_score": ("tm_score", "daily_score"),
        "daily_score": ("daily_score", "tm_score"),
    }
    if norm in aliases:
        for key in aliases[norm]:
            if key in row and row[key] is not None:
                return row[key]
    return row.get(field) or row.get(norm)


def values_match(field: str, claimed: Any, actual: Any, price_tol: float, score_tol: float) -> bool:
    c = _to_float(claimed)
    a = _to_float(actual)
    if c is None or a is None:
        return str(claimed).strip() == str(actual).strip()
    if _is_price_field(field):
        if a == 0:
            return abs(c - a) <= score_tol
        return abs(c - a) / abs(a) <= price_tol
    if _is_score_field(field):
        return abs(c - a) <= score_tol
    # Unknown numeric field: use score tolerance (points)
    return abs(c - a) <= score_tol


def verify_claims(
    pack_rows: dict[str, dict],
    claims: list[dict],
    *,
    price_tol: float = DEFAULT_PRICE_TOL,
    score_tol: float = DEFAULT_SCORE_TOL,
) -> list[dict]:
    """Return discrepancy records (empty list = all matched)."""
    discrepancies: list[dict] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        ticker = str(claim.get("ticker") or "").strip().upper()
        field = str(claim.get("field") or "").strip()
        norm_field = _normalize_field(field)
        if norm_field in FORBIDDEN_CLAIM_FIELDS:
            discrepancies.append({
                "ticker": ticker,
                "field": field,
                "status": "rejected",
                "detail": "value-sleeve field not allowed in T&M snapshot verify",
            })
            continue
        if not ticker or not field:
            discrepancies.append({
                "ticker": ticker or "?",
                "field": field or "?",
                "status": "rejected",
                "detail": "claim missing ticker or field",
            })
            continue
        row = pack_rows.get(ticker)
        if row is None:
            discrepancies.append({
                "ticker": ticker,
                "field": field,
                "claimed_value": claim.get("claimed_value"),
                "actual_value": None,
                "status": "missing_ticker",
                "detail": "ticker not in engine pack",
            })
            continue
        actual = _pack_value(row, field)
        claimed_value = claim.get("claimed_value")
        if values_match(field, claimed_value, actual, price_tol, score_tol):
            continue
        discrepancies.append({
            "ticker": ticker,
            "field": field,
            "claimed_value": claimed_value,
            "actual_value": actual,
            "status": "mismatch",
            "detail": "claimed value outside tolerance vs pack",
        })
    return discrepancies


def load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify T&M narrative claims vs engine pack")
    parser.add_argument("--pack", required=True, help="Engine pack JSON path")
    parser.add_argument("--claims", required=True, help="Narrative claims JSON list path")
    parser.add_argument("--out", help="Write discrepancies JSON here")
    parser.add_argument(
        "--price-tol",
        type=float,
        default=DEFAULT_PRICE_TOL,
        help="Relative tolerance for prices (default 0.01 = 1%%)",
    )
    parser.add_argument(
        "--score-tol",
        type=float,
        default=DEFAULT_SCORE_TOL,
        help="Absolute tolerance for scores in points (default 0.5)",
    )
    args = parser.parse_args(argv)

    pack_path = Path(args.pack)
    claims_path = Path(args.claims)
    if not pack_path.is_file():
        print(f"[tm_snapshot_verify] ERROR: pack not found: {pack_path}", file=sys.stderr)
        return 2
    if not claims_path.is_file():
        print(f"[tm_snapshot_verify] ERROR: claims not found: {claims_path}", file=sys.stderr)
        return 2

    pack = load_json(pack_path)
    claims = load_json(claims_path)
    if not isinstance(claims, list):
        print("[tm_snapshot_verify] ERROR: claims must be a JSON list", file=sys.stderr)
        return 2

    pack_rows = extract_pack_rows(pack)
    discrepancies = verify_claims(
        pack_rows,
        claims,
        price_tol=args.price_tol,
        score_tol=args.score_tol,
    )

    result = {
        "sleeve": "tm",
        "pack": str(pack_path),
        "claims_count": len(claims),
        "discrepancy_count": len(discrepancies),
        "discrepancies": discrepancies,
    }

    if discrepancies:
        print(f"[tm_snapshot_verify] {len(discrepancies)} discrepancy(ies):")
        for d in discrepancies:
            print(
                f"  {d['ticker']} {d['field']}: {d.get('detail')} "
                f"(claimed={d.get('claimed_value')!r} actual={d.get('actual_value')!r})"
            )
    else:
        print("[tm_snapshot_verify] OK — all claims match pack within tolerance")

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return 1 if discrepancies else 0


if __name__ == "__main__":
    sys.exit(main())
