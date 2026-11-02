#!/usr/bin/env python3
"""Independent paper books for T&M and value sleeves (E5: never blend).

Book T — daily T&M pack JSON: net BUY rows (score >= 60, bullish DMI when
DI is present on the row or under ``raw_indicators``). A ``daily_verdict``
of choppy / NO SIGNAL is not a buy — same gate as the live daily report.
Equal-weight long from ``as_of`` entry marks to ``mark_as_of``.

Book V — weekly valuation-width JSON: Candidate / green ``width_verdict`` only.
Equal-weight long with the same MTM formula.

Each sleeve reports its own metrics and ``final_score``; running ``both`` prints
side-by-side results and never emits a blended desk score.

Optional manual / ad-hoc use — no cron job ID is assigned here.

Usage:
  python3 sleeve_paper_book.py --sleeve tm --tm-json pack.json --marks marks.json
  python3 sleeve_paper_book.py --sleeve value --value-json width.json --marks marks.json
  python3 sleeve_paper_book.py --sleeve both --tm-json t.json --value-json v.json \\
      --marks-json '{"AAPL":150}' --as-of 2026-09-01 --mark-as-of 2026-09-10 --out out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_ALLOWED_DD = 8.0
DEFAULT_PENALTY = 1.0
TM_SCORE_MIN = 60
NORMALIZED_START = 100.0


@dataclass
class BookResult:
    sleeve: str
    tickers: list[str]
    trade_count: int
    return_pct: float
    max_drawdown: float
    equity_curve: list[dict[str, Any]]
    risk_adjusted_score: float | None
    final_score: float | None
    disqualified: bool = False
    disqualify_reason: str | None = None


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        out = float(str(val).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if not (out == out):  # NaN
        return None
    return out


def _norm_ticker(raw: Any) -> str:
    return str(raw or "").strip().upper()


def _parse_day(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    return text[:10]


def _row_price(row: Mapping[str, Any]) -> float | None:
    for key in ("last", "price", "close", "entry", "Entry"):
        val = _to_float(row.get(key))
        if val is not None and val > 0:
            return val
    return None


def _iter_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    for key in ("rows", "results", "signals", "selected", "candidates", "passers", "buys"):
        block = payload.get(key)
        if isinstance(block, list) and block:
            return [r for r in block if isinstance(r, dict)]
    if isinstance(payload.get("tickers"), list):
        out: list[dict[str, Any]] = []
        for item in payload["tickers"]:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str):
                out.append({"ticker": item})
        if out:
            return out
    return []


_DMI_PLUS_KEYS = ("dmi_plus", "+di", "plus_di", "DI+")
_DMI_MINUS_KEYS = ("dmi_minus", "-di", "minus_di", "DI-")


def _dmi_sides(mapping: Mapping[str, Any] | None) -> tuple[float | None, float | None]:
    """Read +DI / -DI from one mapping. Missing keys stay None."""
    if not isinstance(mapping, Mapping):
        return None, None
    plus = None
    minus = None
    for key in _DMI_PLUS_KEYS:
        if key in mapping:
            plus = _to_float(mapping.get(key))
            break
    for key in _DMI_MINUS_KEYS:
        if key in mapping:
            minus = _to_float(mapping.get(key))
            break
    return plus, minus


def _dmi_bullish(row: Mapping[str, Any]) -> bool:
    """When DMI fields exist, require +DI > -DI; otherwise pass.

    Top-level DI wins. If the row has neither side, look in
    ``raw_indicators`` (live daily packs store DI there).
    """
    plus, minus = _dmi_sides(row)
    if plus is None and minus is None:
        raw = row.get("raw_indicators")
        plus, minus = _dmi_sides(raw if isinstance(raw, Mapping) else None)
    if plus is None and minus is None:
        return True
    if plus is None or minus is None:
        return False
    return plus > minus


def _verdict_blocks_tm_buy(row: Mapping[str, Any]) -> bool:
    """True when the live daily verdict already refused a trade.

    Matches ``NO SIGNAL (choppy market)`` and engine ``NO_SIGNAL``.
    Does not change the SPY ADX threshold; it only reads the verdict
    the old daily generator already wrote.
    """
    verdict = str(row.get("daily_verdict") or row.get("option_g_verdict") or "")
    text = verdict.upper().replace("_", " ")
    if "CHOPPY" in text:
        return True
    return "NO SIGNAL" in text


def _is_tm_buy_row(row: Mapping[str, Any]) -> bool:
    """True for a paper-book BUY: score≥60, bullish DMI, verdict still a buy.

    Live packs store ``daily_bracket`` as a score band (``60-69`` / ``>=90``)
    and put Option G in ``daily_verdict``. A choppy / NO SIGNAL verdict is
    not a buy, matching the daily report.
    """
    bracket = str(
        row.get("bracket")
        or row.get("signal")
        or row.get("action")
        or ""
    ).strip().upper()
    # Ignore score-band labels like 60-69 / 80-89 (not BUY/WATCH words)
    if bracket and bracket[0].isdigit():
        bracket = ""
    daily_bracket = str(row.get("daily_bracket") or "").strip().upper()
    if daily_bracket in ("BUY", "WATCH", "SELL", "NO_SIGNAL", "AVOID", "SHORT"):
        bracket = daily_bracket
    if bracket in ("SELL", "AVOID", "NO_SIGNAL", "SHORT"):
        return False
    if bracket == "WATCH":
        return False
    if _verdict_blocks_tm_buy(row):
        return False
    score = _to_float(row.get("tm_score"))
    if score is None:
        score = _to_float(row.get("daily_score"))
    if score is None or score < TM_SCORE_MIN:
        return False
    if not _dmi_bullish(row):
        return False
    return True


def _is_value_candidate_row(row: Mapping[str, Any]) -> bool:
    """Book V is Candidate / green only — never Watch/Avoid via loose status."""
    verdict = str(row.get("width_verdict") or row.get("verdict") or "").strip().lower()
    if verdict in (
        "watch",
        "avoid",
        "hold",
        "sell",
        "🔴",
        "🟡",
        "red",
        "yellow",
    ):
        return False
    if verdict in ("green", "candidate", "🟢"):
        return True
    # Fallback only when no width_verdict: require explicit Candidate status
    status = str(row.get("status") or row.get("bucket") or "").strip().lower()
    return status == "candidate"


def _net_buy_tickers(rows: Sequence[Mapping[str, Any]], *, is_buy) -> list[str]:
    """Keep tickers with net long intent (BUY minus explicit SELL in same pack)."""
    buys: set[str] = set()
    sells: set[str] = set()
    for row in rows:
        ticker = _norm_ticker(row.get("ticker") or row.get("symbol"))
        if not ticker:
            continue
        bracket = str(row.get("bracket") or row.get("signal") or row.get("action") or "").upper()
        if "SELL" in bracket or bracket in ("AVOID", "SHORT"):
            sells.add(ticker)
            continue
        if is_buy(row):
            buys.add(ticker)
    return sorted(buys - sells)


def select_tm_tickers(tm_json: Mapping[str, Any]) -> list[str]:
    rows = _iter_rows(tm_json)
    return _net_buy_tickers(rows, is_buy=_is_tm_buy_row)


def select_value_tickers(value_json: Mapping[str, Any]) -> list[str]:
    rows = _iter_rows(value_json)
    return _net_buy_tickers(rows, is_buy=_is_value_candidate_row)


def _price_from_map(marks: Mapping[str, Any], ticker: str) -> float | None:
    for key in (ticker, ticker.replace(".L", "")):
        val = _to_float(marks.get(key))
        if val is not None and val > 0:
            return val
    return None


def _entry_prices(
    tickers: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    entry_marks: Mapping[str, Any],
) -> dict[str, float]:
    row_by_ticker = {_norm_ticker(r.get("ticker") or r.get("symbol")): r for r in rows}
    out: dict[str, float] = {}
    for ticker in tickers:
        price = _price_from_map(entry_marks, ticker)
        if price is None:
            row = row_by_ticker.get(ticker, {})
            price = _row_price(row)
        if price is None or price <= 0:
            raise ValueError(f"missing entry mark for {ticker}")
        out[ticker] = price
    return out


def _normalize_marks(raw: Any) -> tuple[dict[str, dict[str, float]], list[str]]:
    """Return date->ticker->price map and sorted date keys."""
    if not isinstance(raw, dict):
        raise ValueError("marks must be a JSON object")
    # Flat ticker->price
    if raw and all(isinstance(v, (int, float, str)) for v in raw.values()):
        prices = {}
        for k, v in raw.items():
            p = _to_float(v)
            if p is not None and p > 0:
                prices[_norm_ticker(k)] = p
        if not prices:
            raise ValueError("marks map is empty")
        return {"__flat__": prices}, ["__flat__"]

    dated: dict[str, dict[str, float]] = {}
    for day_raw, block in raw.items():
        day = _parse_day(day_raw)
        if not day or not isinstance(block, dict):
            continue
        bucket: dict[str, float] = {}
        for k, v in block.items():
            p = _to_float(v)
            if p is not None and p > 0:
                bucket[_norm_ticker(k)] = p
        if bucket:
            dated[day] = bucket
    if not dated:
        raise ValueError("dated marks map is empty")
    return dated, sorted(dated)


def _equity_at_prices(
    tickers: Sequence[str],
    entry_prices: Mapping[str, float],
    mark_prices: Mapping[str, float],
    *,
    start_equity: float = NORMALIZED_START,
) -> float:
    usable = [
        t
        for t in tickers
        if entry_prices.get(t) and mark_prices.get(t) and mark_prices[t] > 0
    ]
    if not usable:
        return start_equity
    weight = 1.0 / len(usable)
    total = 0.0
    for ticker in usable:
        entry = entry_prices[ticker]
        mark = mark_prices[ticker]
        total += weight * (mark / entry)
    return start_equity * total


def _max_drawdown(curve: Sequence[Mapping[str, Any]]) -> float:
    if len(curve) < 2:
        return 0.0
    peak = float(curve[0]["equity"])
    max_dd = 0.0
    for point in curve:
        eq = float(point["equity"])
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return round(max_dd, 4)


def _risk_adjusted(return_pct: float, max_dd: float, *, allowed_dd: float, penalty: float) -> float:
    excess = max(0.0, max_dd - allowed_dd)
    return round(return_pct - excess * penalty, 4)


def build_equity_curve(
    tickers: Sequence[str],
    entry_prices: Mapping[str, float],
    dated_marks: Mapping[str, Mapping[str, float]],
    mark_dates: Sequence[str],
    *,
    as_of: str,
    mark_as_of: str,
    flat_marks: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    curve: list[dict[str, Any]] = []
    start = {"date": as_of, "equity": round(NORMALIZED_START, 4)}
    curve.append(start)

    if flat_marks is not None:
        eq = _equity_at_prices(tickers, entry_prices, flat_marks)
        curve.append({"date": mark_as_of, "equity": round(eq, 4)})
        return curve

    for day in mark_dates:
        if day in ("__flat__", as_of):
            continue
        marks = dated_marks[day]
        eq = _equity_at_prices(tickers, entry_prices, marks)
        curve.append({"date": day, "equity": round(eq, 4)})
    if len(curve) == 1 and mark_as_of:
        raise ValueError("no mark dates resolved for equity curve")
    return curve


def run_book(
    *,
    sleeve: str,
    tickers: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    entry_marks: Mapping[str, Any],
    mark_marks: Mapping[str, Any] | None = None,
    dated_marks: Mapping[str, Mapping[str, float]] | None = None,
    mark_dates: Sequence[str] | None = None,
    as_of: str,
    mark_as_of: str,
    allowed_dd: float = DEFAULT_ALLOWED_DD,
    penalty: float = DEFAULT_PENALTY,
) -> BookResult:
    if not tickers:
        return BookResult(
            sleeve=sleeve,
            tickers=[],
            trade_count=0,
            return_pct=0.0,
            max_drawdown=0.0,
            equity_curve=[{"date": as_of, "equity": NORMALIZED_START}],
            risk_adjusted_score=None,
            final_score=None,
            disqualified=True,
            disqualify_reason="empty book (trade_count=0)",
        )

    entry_prices = _entry_prices(tickers, rows, entry_marks)

    if dated_marks is not None and mark_dates is not None:
        curve = build_equity_curve(
            tickers,
            entry_prices,
            dated_marks,
            mark_dates,
            as_of=as_of,
            mark_as_of=mark_as_of,
        )
    else:
        if mark_marks is None:
            raise ValueError("mark prices required")
        curve = build_equity_curve(
            tickers,
            entry_prices,
            {},
            [],
            as_of=as_of,
            mark_as_of=mark_as_of,
            flat_marks=mark_marks,
        )

    start_eq = float(curve[0]["equity"])
    end_eq = float(curve[-1]["equity"])
    return_pct = round((end_eq / start_eq - 1.0) * 100.0, 4) if start_eq else 0.0
    max_dd = _max_drawdown(curve)
    ras = _risk_adjusted(return_pct, max_dd, allowed_dd=allowed_dd, penalty=penalty)

    return BookResult(
        sleeve=sleeve,
        tickers=list(tickers),
        trade_count=len(tickers),
        return_pct=return_pct,
        max_drawdown=max_dd,
        equity_curve=curve,
        risk_adjusted_score=ras,
        final_score=ras,
        disqualified=False,
    )


def run_tm_book(
    tm_json: Mapping[str, Any],
    *,
    entry_marks: Mapping[str, Any],
    mark_marks: Mapping[str, Any] | None = None,
    dated_marks: Mapping[str, Mapping[str, float]] | None = None,
    mark_dates: Sequence[str] | None = None,
    as_of: str,
    mark_as_of: str,
    allowed_dd: float = DEFAULT_ALLOWED_DD,
    penalty: float = DEFAULT_PENALTY,
) -> BookResult:
    tickers = select_tm_tickers(tm_json)
    rows = _iter_rows(tm_json)
    return run_book(
        sleeve="tm",
        tickers=tickers,
        rows=rows,
        entry_marks=entry_marks,
        mark_marks=mark_marks,
        dated_marks=dated_marks,
        mark_dates=mark_dates,
        as_of=as_of,
        mark_as_of=mark_as_of,
        allowed_dd=allowed_dd,
        penalty=penalty,
    )


def run_value_book(
    value_json: Mapping[str, Any],
    *,
    entry_marks: Mapping[str, Any],
    mark_marks: Mapping[str, Any] | None = None,
    dated_marks: Mapping[str, Mapping[str, float]] | None = None,
    mark_dates: Sequence[str] | None = None,
    as_of: str,
    mark_as_of: str,
    allowed_dd: float = DEFAULT_ALLOWED_DD,
    penalty: float = DEFAULT_PENALTY,
) -> BookResult:
    tickers = select_value_tickers(value_json)
    rows = _iter_rows(value_json)
    return run_book(
        sleeve="value",
        tickers=tickers,
        rows=rows,
        entry_marks=entry_marks,
        mark_marks=mark_marks,
        dated_marks=dated_marks,
        mark_dates=mark_dates,
        as_of=as_of,
        mark_as_of=mark_as_of,
        allowed_dd=allowed_dd,
        penalty=penalty,
    )


def load_json_path(path: str) -> Any:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_marks(*, marks_path: str | None, marks_json: str | None) -> tuple[Any, dict[str, float] | None, dict[str, dict[str, float]] | None, list[str] | None]:
    raw: Any
    if marks_json:
        raw = json.loads(marks_json)
    elif marks_path:
        raw = load_json_path(marks_path)
    else:
        raise ValueError("one of --marks or --marks-json is required")

    dated, dates = _normalize_marks(raw)
    if dates == ["__flat__"]:
        return raw, dated["__flat__"], None, None
    return raw, None, dated, dates


def _resolve_as_of(payload: Mapping[str, Any] | None, fallback: str | None) -> str:
    if payload:
        for key in ("as_of", "date", "week"):
            val = _parse_day(payload.get(key))
            if val:
                return val
    if fallback:
        return fallback
    return date.today().isoformat()


def format_side_by_side(tm: BookResult | None, value: BookResult | None) -> str:
    lines = ["Sleeve paper books (E5: scores are never blended)"]
    for label, book in (("T&M (tm)", tm), ("Value (value)", value)):
        if book is None:
            continue
        fs = "None" if book.final_score is None else f"{book.final_score:.2f}"
        lines.append(
            f"{label}: tickers={len(book.tickers)} return={book.return_pct:.2f}% "
            f"max_dd={book.max_drawdown:.2f}% final_score={fs}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independent sleeve paper books (E5).")
    parser.add_argument("--sleeve", choices=("tm", "value", "both"), required=True)
    parser.add_argument("--tm-json", help="Daily T&M pack JSON path")
    parser.add_argument("--value-json", help="Weekly valuation-width JSON path")
    parser.add_argument("--marks", dest="marks_path", help="Ticker price map JSON file")
    parser.add_argument("--marks-json", help="Inline ticker price map JSON")
    parser.add_argument("--as-of", help="Entry / book start date (YYYY-MM-DD)")
    parser.add_argument("--mark-as-of", help="Final mark date (YYYY-MM-DD)")
    parser.add_argument("--out", help="Write JSON results to this path")
    parser.add_argument("--allowed-dd", type=float, default=DEFAULT_ALLOWED_DD)
    parser.add_argument("--penalty", type=float, default=DEFAULT_PENALTY)
    args = parser.parse_args(list(argv) if argv is not None else None)

    sleeve = args.sleeve
    if sleeve in ("tm", "both") and not args.tm_json:
        print("[❌] --tm-json required for tm/both", file=sys.stderr)
        return 1
    if sleeve in ("value", "both") and not args.value_json:
        print("[❌] --value-json required for value/both", file=sys.stderr)
        return 1

    try:
        _, flat_marks, dated_marks, mark_dates = load_marks(
            marks_path=args.marks_path,
            marks_json=args.marks_json,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[❌] marks: {exc}", file=sys.stderr)
        return 1

    tm_payload = load_json_path(args.tm_json) if args.tm_json else None
    value_payload = load_json_path(args.value_json) if args.value_json else None
    as_of = args.as_of or _resolve_as_of(tm_payload or value_payload, None)
    if dated_marks is not None and mark_dates:
        mark_as_of = args.mark_as_of or mark_dates[-1]
    else:
        mark_as_of = args.mark_as_of or as_of

    entry_marks: dict[str, float] = {}
    if dated_marks is not None:
        entry_marks = dict(dated_marks.get(as_of, {}))

    common = dict(
        entry_marks=entry_marks,
        mark_marks=flat_marks,
        dated_marks=dated_marks,
        mark_dates=mark_dates,
        as_of=as_of,
        mark_as_of=mark_as_of,
        allowed_dd=args.allowed_dd,
        penalty=args.penalty,
    )

    out: dict[str, Any] = {"as_of": as_of, "mark_as_of": mark_as_of, "e5_note": "never blend tm and value scores"}
    tm_result = value_result = None

    try:
        if sleeve in ("tm", "both"):
            assert tm_payload is not None
            tm_result = run_tm_book(tm_payload, **common)
            out["tm"] = asdict(tm_result)
        if sleeve in ("value", "both"):
            assert value_payload is not None
            value_result = run_value_book(value_payload, **common)
            out["value"] = asdict(value_result)
    except (ValueError, KeyError) as exc:
        print(f"[❌] {exc}", file=sys.stderr)
        return 1

    if sleeve == "both":
        print(format_side_by_side(tm_result, value_result))
    else:
        book = tm_result or value_result
        assert book is not None
        fs = "None" if book.final_score is None else f"{book.final_score:.2f}"
        print(
            f"{book.sleeve}: tickers={book.trade_count} return={book.return_pct:.2f}% "
            f"max_dd={book.max_drawdown:.2f}% final_score={fs}"
        )

    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
