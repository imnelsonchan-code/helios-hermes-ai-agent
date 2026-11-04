#!/usr/bin/env python3
"""Weekly scoring-eval overlays (no-agent cron entrypoint).

Sunday after width + T&M IC window:
  1. stamp latest valuation-width revised JSON (statement_as_of)
  2. run value_ic_tracker with yfinance 4w/12w forward returns (when available)
  3. run sleeve_paper_book for Book T (latest daily) and Book V (Candidates)
  4. run pit_checklist on stamped meta
  5. emit value Candidate predictions
  6. settle due predictions if marks can be fetched

Never blends sleeves. Empty Candidate weeks -> Book V disqualified (expected).
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

SCRIPTS = Path.home() / ".hermes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pack_meta_stamp import stamp_tm_pack, stamp_value_pack  # noqa: E402
from pit_checklist import run_checklist  # noqa: E402
from prediction_emit import append_jsonl, emit_value_predictions  # noqa: E402
from prediction_settler import parse_prediction, settle_all  # noqa: E402
from sleeve_paper_book import run_tm_book, run_value_book  # noqa: E402
from value_ic_tracker import compute_ic_series, extract_value_rows  # noqa: E402

WIDTH_DIRS = [
    Path.home() / ".hermes" / "shared" / "reports" / "eliza" / "valuation-width",
    Path.home() / ".hermes" / "profiles" / "eliza" / "workspace" / "valuation-width",
]
TM_DIRS = [
    Path.home() / ".hermes" / "shared" / "reports" / "renee" / "daily-trend-momentum",
]
OUT_DIR = Path.home() / ".hermes" / "shared" / "reports" / "scoring-eval"
INBOX_DIR = Path.home() / "workspace" / "reports" / "inbox" / "scoring-eval"
VAL_PRED = OUT_DIR / "predictions-value.jsonl"
TM_PRED = Path.home() / ".hermes" / "shared" / "reports" / "renee" / "scoring-eval" / "predictions-tm.jsonl"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _publish(path: Path, payload: dict) -> None:
    _write_json(path, payload)
    _write_json(INBOX_DIR / path.name, payload)


def _rewrite_jsonl(path: Path, updates: dict[tuple[str, str, str], dict]) -> None:
    """Rewrite JSONL applying settled updates keyed by (sleeve, ticker, as_of)."""
    if not path.is_file() and not updates:
        return
    lines_out: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                lines_out.append(raw)
                continue
            key = (
                str(row.get("sleeve") or "").lower(),
                str(row.get("ticker") or "").upper(),
                str(row.get("as_of") or "")[:10],
            )
            if key in updates:
                # One-shot lock (mirrors settle_all): a row whose settlement
                # is already recorded must never be rewritten by a
                # duplicate-key update from a different emission of the same
                # (sleeve, ticker, as_of) — the last settled row's update used
                # to win and silently erase the locked hit.
                if (
                    str(row.get("status") or "") in ("settled", "invalid")
                    and row.get("hit") is not None
                ):
                    print(
                        "[scoring_eval_weekly] locked row "
                        f"{key}: duplicate-key update not applied"
                    )
                else:
                    row = {**row, **updates[key]}
            lines_out.append(json.dumps(row, ensure_ascii=False))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")


def _latest_width() -> Path | None:
    best: Path | None = None
    for d in WIDTH_DIRS:
        if not d.is_dir():
            continue
        for p in d.glob("*-valuation-width-revised.json"):
            if best is None or p.name > best.name:
                best = p
        for p in d.glob("*-valuation-width.json"):
            # prefer revised; only use draft if no revised for that week
            week = p.name.split("-valuation-width")[0]
            revised = d / f"{week}-valuation-width-revised.json"
            if revised.is_file():
                continue
            if best is None or p.name > best.name:
                best = p
    return best


def _latest_tm() -> Path | None:
    best: Path | None = None
    for d in TM_DIRS:
        if not d.is_dir():
            continue
        for p in d.glob("*-data.json"):
            if best is None or p.name > best.name:
                best = p
    return best


def _forward_returns(tickers: list[str], as_of: date, days: int) -> dict[str, float]:
    """Fetch simple forward returns via yfinance; skip failures silently."""
    try:
        import yfinance as yf
    except ImportError:
        print("[scoring_eval_weekly] yfinance missing — IC skipped")
        return {}
    end = as_of + timedelta(days=days + 10)
    start = as_of - timedelta(days=5)
    out: dict[str, float] = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(start=start.isoformat(), end=end.isoformat(), auto_adjust=True)
            if hist is None or hist.empty or "Close" not in hist:
                continue
            closes = hist["Close"].dropna()
            if len(closes) < 2:
                continue
            # entry = first close on/after as_of; mark = close ~days later
            entry = None
            mark = None
            for idx, px in closes.items():
                d = idx.date() if hasattr(idx, "date") else idx
                if d >= as_of and entry is None:
                    entry = float(px)
                if d >= as_of + timedelta(days=days):
                    mark = float(px)
                    break
            if entry is None or mark is None or entry <= 0:
                continue
            out[ticker] = (mark / entry) - 1.0
        except Exception as exc:  # noqa: BLE001 — vendor/network soft-fail
            print(f"[scoring_eval_weekly] yfinance {ticker}: {exc}")
    return out


def _marks_for_tickers(
    tickers: list[str],
    mark_dates: dict[str, str] | None = None,
) -> dict[str, float]:
    try:
        import yfinance as yf
    except ImportError:
        return {}
    marks: dict[str, float] = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="5d", auto_adjust=True)
            if hist is None or hist.empty:
                continue
            close = hist["Close"].dropna()
            if close.empty:
                continue
            marks[ticker] = float(close.iloc[-1])
            if mark_dates is not None:
                # Quote date (YYYY-MM-DD) of the fetched mark.
                mark_dates[ticker] = str(hist.index[-1])[:10]
        except Exception:  # noqa: BLE001
            continue
    return marks


def _parse_as_of(pack: dict) -> date | None:
    meta = pack.get("meta") if isinstance(pack.get("meta"), dict) else {}
    for key in ("as_of", "date", "data_as_of"):
        raw = str(pack.get(key) or meta.get(key) or "").strip()[:10]
        if raw:
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
    week = str(pack.get("week") or "").strip()
    if week:
        try:
            return datetime.strptime(week + "-1", "%G-W%V-%u").date()
        except ValueError:
            return None
    return None


def main() -> int:
    today = datetime.now(timezone.utc).date()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    width_path = _latest_width()
    tm_path = _latest_tm()
    summary: dict = {
        "job": "scoring_eval_weekly",
        "run_date": today.isoformat(),
        "width_pack": str(width_path) if width_path else None,
        "tm_pack": str(tm_path) if tm_path else None,
        "e5_note": "Book T / Book V / IC / hit rates never blended",
    }

    value_pack = None
    if width_path and width_path.is_file():
        value_pack = stamp_value_pack(json.loads(width_path.read_text(encoding="utf-8")))
        as_of = _parse_as_of(value_pack) or today
        rows = extract_value_rows(value_pack)
        tickers = [str(r.get("ticker") or "").upper() for r in rows if r.get("ticker")]
        tickers = [t for t in tickers if t]
        returns_4w = _forward_returns(tickers, as_of, 28)
        returns_12w = _forward_returns(tickers, as_of, 84)
        horizons = {}
        if returns_4w:
            horizons["4w"] = returns_4w
        if returns_12w:
            horizons["12w"] = returns_12w
        if horizons:
            series, warns = compute_ic_series(rows, horizons)
            summary["value_ic"] = {"series": series, "lookahead_warnings": warns}
            print("[scoring_eval_weekly] Value IC:")
            for s in series:
                ic = s.get("ic")
                ic_s = f"{ic:+.4f}" if isinstance(ic, float) and not math.isnan(ic) else "n/a"
                print(f"  {s.get('score_field', '?'):24} {s.get('horizon', '?'):4} IC={ic_s} n={s.get('n')}")
            for w in warns:
                print(f"  WARN {w}")
        else:
            summary["value_ic"] = {"series": [], "note": "insufficient forward returns (horizon may not have elapsed)"}
            print("[scoring_eval_weekly] Value IC skipped — no forward returns yet")

        pit_meta = {
            "value": {
                "statement_as_of": (value_pack.get("meta") or {}).get("value", {}).get("statement_as_of")
                or value_pack.get("statement_as_of"),
                "as_of": (value_pack.get("meta") or {}).get("as_of"),
            },
            "fred_vintage": None,
        }
        checks = run_checklist(pit_meta)
        summary["pit_checklist"] = checks
        fails = [c for c in checks if c.get("status") == "fail"]
        print(f"[scoring_eval_weekly] PIT fails={len(fails)}")

        preds = emit_value_predictions(value_pack, horizon_days=28)
        append_jsonl(VAL_PRED, preds)
        summary["value_predictions_emitted"] = len(preds)

        # Book V — need mark prices
        marks = _marks_for_tickers(tickers)
        book_v = run_value_book(
            value_pack,
            entry_marks={},
            mark_marks=marks,
            as_of=as_of.isoformat(),
            mark_as_of=today.isoformat(),
        )
        summary["book_v"] = {
            "trade_count": book_v.trade_count,
            "return_pct": book_v.return_pct,
            "max_drawdown": book_v.max_drawdown,
            "final_score": book_v.final_score,
            "disqualified": book_v.disqualified,
            "tickers": book_v.tickers,
        }
        print(
            f"[scoring_eval_weekly] Book V trades={book_v.trade_count} "
            f"ret={book_v.return_pct:.2f}% dd={book_v.max_drawdown:.2f}% "
            f"final={book_v.final_score}"
        )

    if tm_path and tm_path.is_file():
        tm_pack = stamp_tm_pack(json.loads(tm_path.read_text(encoding="utf-8")))
        as_of_tm = _parse_as_of(tm_pack) or today
        tm_rows = tm_pack.get("results") or []
        tm_tickers = [
            str(r.get("ticker") or "").upper()
            for r in tm_rows
            if isinstance(r, dict) and r.get("ticker")
        ]
        marks_tm = _marks_for_tickers(tm_tickers)
        book_t = run_tm_book(
            tm_pack,
            entry_marks={},
            mark_marks=marks_tm,
            as_of=as_of_tm.isoformat(),
            mark_as_of=today.isoformat(),
        )
        summary["book_t"] = {
            "trade_count": book_t.trade_count,
            "return_pct": book_t.return_pct,
            "max_drawdown": book_t.max_drawdown,
            "final_score": book_t.final_score,
            "disqualified": book_t.disqualified,
            "tickers": book_t.tickers,
        }
        print(
            f"[scoring_eval_weekly] Book T trades={book_t.trade_count} "
            f"ret={book_t.return_pct:.2f}% dd={book_t.max_drawdown:.2f}% "
            f"final={book_t.final_score}"
        )

    # Settle due predictions (both sleeves, separate rates).
    # Missing marks stay status=pending (deferred settle_reason) so the next
    # weekly pass can retry; only true invalid/settled rows leave the queue.
    pending: list[dict] = []
    for path in (TM_PRED, VAL_PRED):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status", "pending") != "pending":
                continue
            end = str(row.get("horizon_end") or "")[:10]
            if end and end <= today.isoformat():
                pending.append(row)
    if pending:
        preds = []
        for raw in pending:
            try:
                preds.append(parse_prediction(raw))
            except (TypeError, ValueError) as exc:
                print(f"[scoring_eval_weekly] skip pred: {exc}")
        if preds:
            marks: dict[str, float] = {}
            mark_dates: dict[str, str] = {}
            marks = _marks_for_tickers(tickers, mark_dates)
            # F3 gate: settlement locks hit/return permanently, so the mark
            # itself must be dated at or after horizon_end. yfinance's last
            # 5d close can predate the horizon (Monday-morning run, mid-week
            # holiday) — settling against it would lock an
            # incomplete-horizon result. Undated/missing marks keep the old
            # path (settle_all defers: missing mark_price).
            gated = []
            for pred in preds:
                horizon = str(pred.horizon_end or "")[:10]
                quote = mark_dates.get(pred.ticker)
                if quote and horizon and quote < horizon:
                    print(
                        f"[scoring_eval_weekly] defer {pred.sleeve}/{pred.ticker} "
                        f"as_of={pred.as_of}: mark quote {quote} predates "
                        f"horizon_end {horizon}"
                    )
                    continue
                gated.append(pred)
            if gated:
                report = settle_all(gated, marks, as_of=today.isoformat())
                summary["settlement"] = {
                    "tm_hit_rate": report.tm_hit_rate,
                    "value_hit_rate": report.value_hit_rate,
                    "tm_settled": report.tm_settled,
                    "value_settled": report.value_settled,
                }
                updates: dict[tuple[str, str, str], dict] = {}
                for settled in report.predictions:
                    key = (settled.sleeve, settled.ticker, settled.as_of)
                    updates[key] = {
                        "status": settled.status,
                        "hit": settled.hit,
                        "mark_price": settled.mark_price,
                        "return_pct": settled.return_pct,
                        "settle_reason": settled.settle_reason,
                    }
                _rewrite_jsonl(TM_PRED, {k: v for k, v in updates.items() if k[0] == "tm"})
                _rewrite_jsonl(VAL_PRED, {k: v for k, v in updates.items() if k[0] == "value"})
                settle_path = OUT_DIR / f"{today.isoformat()}-settlement.json"
                _publish(settle_path, summary["settlement"])
                print(
                    f"[scoring_eval_weekly] settle tm_hit={report.tm_hit_rate} "
                    f"value_hit={report.value_hit_rate}"
                )

    out_path = OUT_DIR / f"{today.isoformat()}-weekly-eval.json"
    _publish(out_path, summary)
    print(f"wrote {out_path}")
    print(f"inbox {INBOX_DIR / out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
