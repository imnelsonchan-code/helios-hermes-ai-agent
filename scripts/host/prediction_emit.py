#!/usr/bin/env python3
"""Emit prediction JSONL from stamped T&M / value packs (train-side helper).

Writes pending predictions for later ``prediction_settler.py`` settlement.
E5: each row carries sleeve=tm|value — never a blended desk prediction.

T&M: BUY rows -> long, horizon default +5 trading days (calendar +7).
Value: Candidate / 🟢 rows -> long, horizon default +28 calendar days (4w).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


def _parse_day(raw: Any) -> date | None:
    text = str(raw or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _to_float(val: Any) -> float | None:
    try:
        out = float(str(val).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if out != out or out <= 0:
        return None
    return out


def _as_of(pack: dict) -> date | None:
    meta = pack.get("meta") if isinstance(pack.get("meta"), dict) else {}
    for key in ("as_of", "data_as_of", "date"):
        d = _parse_day(pack.get(key) or meta.get(key))
        if d:
            return d
    return None


def emit_tm_predictions(pack: dict, *, horizon_days: int = 7) -> list[dict]:
    as_of = _as_of(pack)
    if as_of is None:
        return []
    horizon_end = (as_of + timedelta(days=horizon_days)).isoformat()
    out: list[dict] = []
    rows = pack.get("results") or pack.get("rows") or []
    if not isinstance(rows, list):
        return []
    for row in rows:
        if not isinstance(row, dict):
            continue
        score = _to_float(row.get("tm_score") if row.get("tm_score") is not None else row.get("daily_score"))
        bracket = str(row.get("bracket") or row.get("theoretical_bracket") or "").upper()
        daily_b = str(row.get("daily_bracket") or "").upper()
        if daily_b in ("BUY", "WATCH", "SELL", "NO_SIGNAL", "AVOID"):
            bracket = daily_b
        if bracket in ("WATCH", "SELL", "NO_SIGNAL", "AVOID", "SHORT"):
            continue
        # Live packs use score bands in daily_bracket; theoretical BUY = score≥60
        is_buy = bracket == "BUY" or (score is not None and score >= 60)
        if not is_buy or score is None or score < 60:
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        entry = _to_float(row.get("entry_price") or row.get("last") or row.get("price") or row.get("close"))
        pred = {
            "sleeve": "tm",
            "ticker": ticker,
            "direction": "long",
            "as_of": as_of.isoformat(),
            "horizon_end": horizon_end,
            "status": "pending",
            "entry_price": entry,
            "invalid_if": "tm_score<50",
            "source": "prediction_emit/tm_buy",
            "tm_score": score,
            "option_g_verdict": row.get("option_g_verdict") or row.get("daily_verdict"),
        }
        out.append(pred)
    return out


def emit_value_predictions(pack: dict, *, horizon_days: int = 28) -> list[dict]:
    as_of = _as_of(pack)
    if as_of is None:
        # ISO week packs often only have week label — use Monday of that week if present
        week = str(pack.get("week") or "").strip()
        if week.startswith("20") and "-W" in week:
            try:
                as_of = datetime.strptime(week + "-1", "%G-W%V-%u").date()
            except ValueError:
                as_of = None
    if as_of is None:
        return []
    horizon_end = (as_of + timedelta(days=horizon_days)).isoformat()
    rows: list[dict] = []
    if isinstance(pack.get("rankings"), list):
        rows.extend(pack["rankings"])
    tracks = pack.get("tracks")
    if isinstance(tracks, dict):
        for track in tracks.values():
            if isinstance(track, dict) and isinstance(track.get("rankings"), list):
                rows.extend(track["rankings"])
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        verdict = str(row.get("width_verdict") or "").strip()
        if verdict not in ("Candidate", "green", "🟢"):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        entry = _to_float(row.get("close") or row.get("price") or row.get("last"))
        score = _to_float(row.get("valuation_score"))
        pred = {
            "sleeve": "value",
            "ticker": ticker,
            "direction": "long",
            "as_of": as_of.isoformat(),
            "horizon_end": horizon_end,
            "status": "pending",
            "entry_price": entry,
            "invalid_if": "width_verdict=Avoid",
            "source": "prediction_emit/value_candidate",
            "valuation_score": score,
        }
        out.append(pred)
    return out


def append_jsonl(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[tuple[str, str, str]] = set()
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                prev = json.loads(line)
            except json.JSONDecodeError:
                continue
            existing.add(
                (
                    str(prev.get("sleeve") or "").lower(),
                    str(prev.get("ticker") or "").upper(),
                    str(prev.get("as_of") or "")[:10],
                )
            )
    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            key = (
                str(row.get("sleeve") or "").lower(),
                str(row.get("ticker") or "").upper(),
                str(row.get("as_of") or "")[:10],
            )
            if key in existing:
                continue
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            existing.add(key)
            written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit sleeve prediction JSONL")
    parser.add_argument("--pack", required=True)
    parser.add_argument("--sleeve", choices=("tm", "value"), required=True)
    parser.add_argument("--out", required=True, help="JSONL path (append)")
    parser.add_argument("--horizon-days", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[prediction_emit] read failed: {exc}", file=sys.stderr)
        return 2
    if not isinstance(pack, dict):
        return 2

    if args.sleeve == "tm":
        horizon = args.horizon_days or 7
        rows = emit_tm_predictions(pack, horizon_days=horizon)
    else:
        horizon = args.horizon_days or 28
        rows = emit_value_predictions(pack, horizon_days=horizon)

    n = append_jsonl(Path(args.out), rows)
    print(f"[prediction_emit] sleeve={args.sleeve} appended={n} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
