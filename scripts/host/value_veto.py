#!/usr/bin/env python3
"""Extra value-sleeve vetoes — never modifies valuation_score.

Blocks Candidate / Buy when quality, solvency, or dilution checks fail.
E5: value sleeve only; no T&M blend.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FINANCIAL_SECTORS = frozenset(
    {"Banks", "Financials", "Financial Services", "Insurance"}
)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "🚨"}


def _sector(row: dict) -> str:
    return str(row.get("sector") or row.get("Sector") or "").strip()


def _is_financial(row: dict) -> bool:
    if _truthy(row.get("bank")):
        return True
    return _sector(row) in FINANCIAL_SECTORS


def evaluate_vetoes(row: dict) -> dict:
    """Return {vetoes: [...], allowed_candidate: bool}."""
    vetoes: list[str] = []

    current_ratio = _to_float(row.get("current_ratio"))
    if current_ratio is not None and current_ratio < 1.5:
        vetoes.append(f"current_ratio={current_ratio:g}<1.5")

    cumulative_fcf = _to_float(row.get("cumulative_fcf_5y"))
    if cumulative_fcf is not None and cumulative_fcf < 0:
        vetoes.append(f"cumulative_fcf_5y={cumulative_fcf:g}<0")

    if not _is_financial(row):
        interest_coverage = _to_float(row.get("interest_coverage"))
        if interest_coverage is not None and interest_coverage < 2.0:
            vetoes.append(f"interest_coverage={interest_coverage:g}<2.0")

    if not _truthy(row.get("mna_flag")):
        dilution = _to_float(row.get("share_count_dilution_5y"))
        if dilution is not None and dilution > 0.20:
            vetoes.append(f"share_count_dilution_5y={dilution:g}>0.20")

    roe_avg = _to_float(row.get("roe_10y_avg"))
    if roe_avg is not None and roe_avg < 0.08:
        vetoes.append(f"roe_10y_avg={roe_avg:g}<0.08")

    f_score = _to_float(row.get("f_score"))
    if f_score is not None and f_score <= 3:
        vetoes.append(f"f_score={f_score:g}<=3")

    if _truthy(row.get("accounting_alert")) or _truthy(row.get("accounting_flag")):
        vetoes.append("accounting_alert")

    return {
        "vetoes": vetoes,
        "allowed_candidate": len(vetoes) == 0,
    }


def evaluate_pack(pack: dict) -> dict:
    """Evaluate all ranking rows in a width-style pack."""
    rows_out: list[dict] = []
    for row in _iter_rows(pack):
        verdict = evaluate_vetoes(row)
        rows_out.append(
            {
                "ticker": row.get("ticker") or row.get("Ticker"),
                **verdict,
            }
        )
    return {"rows": rows_out}


def _iter_rows(pack: dict) -> list[dict]:
    rows: list[dict] = []
    for key in ("rankings", "rows"):
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Value sleeve extra vetoes")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--row-json", help="Single row JSON object")
    group.add_argument("--pack", help="Width pack JSON path")
    parser.add_argument("--out", default="", help="Write result JSON here")
    args = parser.parse_args(argv)

    try:
        if args.row_json:
            row = json.loads(args.row_json)
            if not isinstance(row, dict):
                raise ValueError("row must be object")
            result = evaluate_vetoes(row)
        else:
            pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
            if not isinstance(pack, dict):
                raise ValueError("pack root must be object")
            result = evaluate_pack(pack)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[value_veto] {exc}", file=sys.stderr)
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
