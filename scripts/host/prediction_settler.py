#!/usr/bin/env python3
"""Lock and settle sleeve predictions (E5: separate hit rates per sleeve).

Each prediction carries its own sleeve (``tm`` | ``value``), direction, horizon,
and optional invalidation rule. ``settle()`` compares entry vs mark prices;
desk-level accuracy is never merged — reports ``tm_hit_rate`` and
``value_hit_rate`` independently.

Optional manual / ad-hoc use — no cron job ID is assigned here.

Usage:
  python3 prediction_settler.py --predictions preds.jsonl --marks marks.json --out out.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_EPS = 1e-4
VALID_SLEEVES = frozenset({"tm", "value"})
VALID_DIRECTIONS = frozenset({"long", "short", "flat"})
VALID_STATUS = frozenset({"pending", "settled", "invalid"})


@dataclass
class Prediction:
    sleeve: str
    ticker: str
    direction: str
    as_of: str
    horizon_end: str
    target: float | None = None
    invalid_if: str | None = None
    status: str = "pending"
    entry_price: float | None = None
    mark_price: float | None = None
    hit: bool | None = None
    return_pct: float | None = None
    settle_reason: str | None = None


@dataclass
class SettlementReport:
    predictions: list[Prediction] = field(default_factory=list)
    tm_settled: int = 0
    tm_hits: int = 0
    tm_hit_rate: float | None = None
    value_settled: int = 0
    value_hits: int = 0
    value_hit_rate: float | None = None
    e5_note: str = "tm_hit_rate and value_hit_rate are never blended"


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        out = float(str(val).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if not (out == out):
        return None
    return out


def _norm_ticker(raw: Any) -> str:
    return str(raw or "").strip().upper()


def _norm_sleeve(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("t&m", "tm", "trend", "trend-momentum"):
        return "tm"
    if s in ("value", "val", "p-val", "width"):
        return "value"
    return s


def _parse_day(raw: Any) -> str:
    text = str(raw or "").strip()
    return text[:10] if text else ""


def parse_prediction(raw: Mapping[str, Any]) -> Prediction:
    sleeve = _norm_sleeve(raw.get("sleeve"))
    if sleeve not in VALID_SLEEVES:
        raise ValueError(f"invalid sleeve: {raw.get('sleeve')!r}")
    direction = str(raw.get("direction") or "").strip().lower()
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"invalid direction: {raw.get('direction')!r}")
    ticker = _norm_ticker(raw.get("ticker"))
    if not ticker:
        raise ValueError("missing ticker")
    as_of = _parse_day(raw.get("as_of"))
    horizon_end = _parse_day(raw.get("horizon_end"))
    if not as_of or not horizon_end:
        raise ValueError(f"as_of and horizon_end required for {ticker}")
    status = str(raw.get("status") or "pending").strip().lower()
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status: {status}")
    target = _to_float(raw.get("target"))
    entry_price = _to_float(raw.get("entry_price"))
    mark_price = _to_float(raw.get("mark_price"))
    return Prediction(
        sleeve=sleeve,
        ticker=ticker,
        direction=direction,
        target=target,
        as_of=as_of,
        horizon_end=horizon_end,
        invalid_if=(str(raw.get("invalid_if")).strip() if raw.get("invalid_if") else None),
        status=status,
        entry_price=entry_price,
        mark_price=mark_price,
        hit=_bool_or_none(raw.get("hit")),
        return_pct=_to_float(raw.get("return_pct")),
        settle_reason=(str(raw.get("settle_reason")).strip() if raw.get("settle_reason") else None),
    )


def _bool_or_none(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    text = str(val).strip().lower()
    if text in ("true", "1", "yes", "hit"):
        return True
    if text in ("false", "0", "no", "miss"):
        return False
    return None


def _check_invalid_if(pred: Prediction, *, mark_price: float, entry_price: float) -> str | None:
    rule = (pred.invalid_if or "").strip().lower()
    if not rule:
        return None
    ret = (mark_price - entry_price) / entry_price if entry_price else 0.0
    if rule in ("halt", "halted", "trading_halt"):
        return rule
    if rule.startswith("move>"):
        try:
            thresh = float(rule.split(">", 1)[1].strip().rstrip("%")) / 100.0
            if abs(ret) > thresh:
                return rule
        except ValueError:
            return rule
    if rule.startswith("move<"):
        try:
            thresh = float(rule.split("<", 1)[1].strip().rstrip("%")) / 100.0
            if abs(ret) < thresh:
                return rule
        except ValueError:
            return rule
    return None


def settle(
    pred: Prediction,
    *,
    entry_price: float | None = None,
    mark_price: float | None = None,
    eps: float = DEFAULT_EPS,
) -> Prediction:
    """Settle one prediction. Returns a copy with status/hit fields updated.

    Missing or non-positive entry/mark prices leave the row ``pending``
    (``settle_reason`` deferred) so callers can retry later. True ``invalid``
    is reserved for already-invalid rows, ``invalid_if`` triggers, and the
    intentional flat-direction exception path.
    """
    out = Prediction(**asdict(pred))
    if out.status == "invalid":
        out.hit = None
        out.settle_reason = out.settle_reason or "already invalid"
        return out

    entry = entry_price if entry_price is not None else out.entry_price
    mark = mark_price if mark_price is not None else out.mark_price
    if entry is None or mark is None or entry <= 0:
        # Do not permanently invalidate — weekly rewrite must be able to retry.
        out.status = "pending"
        out.hit = None
        out.settle_reason = "deferred: missing entry_price or mark_price"
        return out

    out.entry_price = entry
    out.mark_price = mark
    ret = (mark - entry) / entry
    out.return_pct = round(ret * 100.0, 4)

    invalid_reason = _check_invalid_if(out, mark_price=mark, entry_price=entry)
    if invalid_reason:
        out.status = "invalid"
        out.hit = None
        out.settle_reason = f"invalid_if triggered: {invalid_reason}"
        return out

    direction = out.direction
    if direction == "long":
        out.hit = mark > entry
        out.settle_reason = "long: mark>entry" if out.hit else "long: mark<=entry"
    elif direction == "short":
        out.hit = mark < entry
        out.settle_reason = "short: mark<entry" if out.hit else "short: mark>=entry"
    else:  # flat
        if abs(ret) < eps:
            out.hit = True
            out.settle_reason = f"flat: |return|<{eps}"
        else:
            out.status = "invalid"
            out.hit = None
            out.settle_reason = f"flat: |return|>={eps}"

    if out.status != "invalid":
        out.status = "settled"
    return out


def load_predictions(path: str) -> list[Prediction]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"predictions not found: {path}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []
    preds: list[Prediction] = []
    if path.endswith(".jsonl") or "\n" in text and text.lstrip().startswith("{"):
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_no}: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"line {line_no}: expected object")
            preds.append(parse_prediction(raw))
    else:
        raw = json.loads(text)
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    raise ValueError("prediction list items must be objects")
                preds.append(parse_prediction(item))
        elif isinstance(raw, dict):
            block = raw.get("predictions")
            if isinstance(block, list):
                for item in block:
                    preds.append(parse_prediction(item))
            else:
                preds.append(parse_prediction(raw))
        else:
            raise ValueError("predictions JSON must be list or object")
    return preds


def load_marks(path: str | None, inline: str | None) -> dict[str, float]:
    if inline:
        raw = json.loads(inline)
    elif path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        raise ValueError("one of --marks or --marks-json is required")
    if not isinstance(raw, dict):
        raise ValueError("marks must be a JSON object")
    out: dict[str, float] = {}
    for k, v in raw.items():
        p = _to_float(v)
        if p is not None and p > 0:
            out[_norm_ticker(k)] = p
    return out


def _norm_date(s: Any) -> str | None:
    """Extract a ``YYYY-MM-DD`` prefix for horizon comparisons; None if absent."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", str(s or "").strip())
    return match.group(1) if match else None


def settle_all(
    predictions: Sequence[Prediction],
    marks: Mapping[str, float],
    *,
    eps: float = DEFAULT_EPS,
    as_of: str | None = None,
) -> SettlementReport:
    """Settle every prediction; E5 sleeves are never blended.

    Horizon gate (fail-closed): ``as_of`` defaults to today (UTC) when the
    caller omits it — direct callers settle nothing before the horizon is
    due. A prediction may only settle once its mark is taken at or after
    ``horizon_end``; rows that are not yet due, or whose ``horizon_end`` is
    unparseable, stay ``pending`` (``deferred: ...``) so a later pass retries.

    One-shot lock: rows already ``settled`` (hit recorded) are passed through
    unchanged — settlement is never re-phased by later marks.
    """
    settled_preds: list[Prediction] = []
    tm_settled = tm_hits = value_settled = value_hits = 0
    as_of_date = _norm_date(as_of) or datetime.now(timezone.utc).strftime(
        "%Y-%m-%d"
    )

    def _count(pred: Prediction) -> None:
        nonlocal tm_settled, tm_hits, value_settled, value_hits
        if pred.status != "settled" or pred.hit is None:
            return
        if pred.sleeve == "tm":
            tm_settled += 1
            if pred.hit:
                tm_hits += 1
        elif pred.sleeve == "value":
            value_settled += 1
            if pred.hit:
                value_hits += 1

    for pred in predictions:
        # One-shot lock: already-settled rows are never re-settled.
        if pred.status == "settled" and pred.hit is not None:
            settled_preds.append(pred)
            _count(pred)
            continue

        if as_of_date is not None:
            horizon = _norm_date(pred.horizon_end)
            if horizon is None:
                out = Prediction(**asdict(pred))
                out.status = "pending"
                out.hit = None
                out.settle_reason = (
                    f"deferred: horizon_end unparseable ({pred.horizon_end!r})"
                )
                settled_preds.append(out)
                continue
            if as_of_date < horizon:
                out = Prediction(**asdict(pred))
                out.status = "pending"
                out.hit = None
                out.settle_reason = (
                    f"deferred: before horizon_end {horizon} (as_of {as_of_date})"
                )
                settled_preds.append(out)
                continue

        mark = marks.get(pred.ticker)
        entry = pred.entry_price
        result = settle(pred, entry_price=entry, mark_price=mark, eps=eps)
        settled_preds.append(result)
        _count(result)

    report = SettlementReport(predictions=settled_preds)
    report.tm_settled = tm_settled
    report.tm_hits = tm_hits
    report.tm_hit_rate = round(tm_hits / tm_settled, 4) if tm_settled else None
    report.value_settled = value_settled
    report.value_hits = value_hits
    report.value_hit_rate = round(value_hits / value_settled, 4) if value_settled else None
    return report


def format_report(report: SettlementReport) -> str:
    lines = [
        "Prediction settlement (E5: hit rates never blended)",
        f"tm: {report.tm_hits}/{report.tm_settled} hit_rate={report.tm_hit_rate}",
        f"value: {report.value_hits}/{report.value_settled} hit_rate={report.value_hit_rate}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Settle sleeve predictions (E5).")
    parser.add_argument("--predictions", required=True, help="Predictions JSON or JSONL path")
    parser.add_argument("--marks", dest="marks_path", help="Ticker mark prices JSON file")
    parser.add_argument("--marks-json", help="Inline ticker mark prices JSON")
    parser.add_argument("--eps", type=float, default=DEFAULT_EPS, help="Flat direction tolerance")
    parser.add_argument(
        "--as-of",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Marks date (YYYY-MM-DD) for the horizon gate; default: today UTC",
    )
    parser.add_argument("--out", help="Write JSON report path")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        preds = load_predictions(args.predictions)
        marks = load_marks(args.marks_path, args.marks_json)
        report = settle_all(preds, marks, eps=args.eps, as_of=args.as_of)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[❌] {exc}", file=sys.stderr)
        return 1

    print(format_report(report))

    payload = {
        "tm_hit_rate": report.tm_hit_rate,
        "tm_settled": report.tm_settled,
        "tm_hits": report.tm_hits,
        "value_hit_rate": report.value_hit_rate,
        "value_settled": report.value_settled,
        "value_hits": report.value_hits,
        "e5_note": report.e5_note,
        "predictions": [asdict(p) for p in report.predictions],
    }
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
