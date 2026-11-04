#!/usr/bin/env python3
"""Read-only T&M score-decay and time-stop checker.

Price-level SL/TP checks belong to position_watch.py.  This checker never
marks rows CLOSED or appends synthetic SELL fills.

Time stop: days>=10 AND MFE_close < 1R AND not yet latched. Missing MFE
fails closed (no time-stop). Parse failure on entry date does not trip.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parent
if str(HOST_DIR) not in sys.path:
    sys.path.insert(0, str(HOST_DIR))

from time_stop import (  # noqa: E402
    TIME_STOP_LATCH_PATH,
    latch_key,
    mark_time_stop_latched,
    time_stop_eligible,
)

JOURNAL_PATH = os.path.expanduser("~/.hermes/trade_journal.csv")
DAILY_RESULTS_DIR = os.path.expanduser(
    "~/.hermes/shared/reports/renee/daily-trend-momentum"
)
SKIP_STATUS = {"VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED"}

# Re-export for callers/tests that historically imported from this module.
from time_stop import count_trading_days  # noqa: E402,F401


def _to_float(value) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class OpenBookPosition:
    ticker: str
    remaining: int
    entry_date: str


def load_rows(path: str) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def compute_open_book(rows: list[dict]) -> list[OpenBookPosition]:
    """FIFO position cycles so old closed entries do not age a later re-entry."""
    lots: dict[str, list[list[object]]] = defaultdict(list)
    for row in rows:
        ticker = str(row.get("Ticker") or "").strip().upper()
        action = str(row.get("Action") or "").strip().upper()
        status = str(row.get("Status") or "").strip().upper()
        if not ticker or status in SKIP_STATUS:
            continue
        # Only a CLOSED (executed) SELL may reduce the book — an OPEN/PENDING
        # SELL has not filled yet (same rule as position_watch and
        # risk_plan._attributed_sells). BUY rows keep the SKIP_STATUS-only
        # rule: a live OPEN BUY marks an open position, not an unfilled order.
        if action == "SELL" and status != "CLOSED":
            continue
        shares_raw = str(row.get("Shares") or "").strip()
        shares = _to_float(row.get("Shares"))
        if (
            shares is None
            and shares_raw
            and status not in SKIP_STATUS
            and action in ("BUY", "SELL")
        ):
            # A silently-vanished SELL over-states the open book (the old
            # `or 0.0` treated junk shares as a no-op fill). Print loudly,
            # keep the row out of the book math.
            print(
                f"[exit-checker] unparsable Shares on eligible row: "
                f"{ticker} {action} {shares_raw!r}",
                file=sys.stderr,
            )
        if shares is None:
            shares = 0.0
        if shares <= 0:
            continue
        if action == "BUY":
            stamp = str(row.get("Date") or "").strip()
            lots[ticker].append([stamp, shares])
        elif action == "SELL":
            remaining_sell = shares
            while remaining_sell > 0 and lots[ticker]:
                available = float(lots[ticker][0][1])
                consumed = min(available, remaining_sell)
                available -= consumed
                remaining_sell -= consumed
                if available <= 1e-9:
                    lots[ticker].pop(0)
                else:
                    lots[ticker][0][1] = available
    positions: list[OpenBookPosition] = []
    for ticker in sorted(lots):
        remaining = sum(float(lot[1]) for lot in lots[ticker])
        if remaining <= 0:
            continue
        active_dates = [str(lot[0]) for lot in lots[ticker] if str(lot[0])]
        positions.append(
            OpenBookPosition(
                ticker=ticker,
                remaining=int(round(remaining)),
                entry_date=min(active_dates) if active_dates else "",
            )
        )
    return positions


def load_scores(results_dir: str, session: date | None = None) -> tuple[dict[str, float], str]:
    folder = Path(results_dir)
    if not folder.is_dir():
        return {}, "missing"
    candidates: list[Path]
    if session is not None:
        stamp = session.isoformat()
        candidates = sorted(
            path
            for path in folder.glob(f"{stamp}*-data.json")
            if "latest" not in path.name.lower()
        )
    else:
        candidates = sorted(
            path
            for path in folder.glob("*-data.json")
            if "latest" not in path.name.lower()
        )
    if not candidates:
        return {}, "missing"
    source = candidates[-1]
    try:
        doc = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "missing"
    results = doc if isinstance(doc, list) else doc.get("results") or []
    scores: dict[str, float] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        score = _to_float(row.get("tm_score"))
        if score is None:
            score = _to_float(row.get("daily_score"))
        if ticker and score is not None:
            scores[ticker] = score
    return scores, source.name


def find_exit_signals(
    positions: list[OpenBookPosition],
    scores: dict[str, float],
    session: date,
    *,
    mfe_close_r: dict[str, Decimal | float | None] | None = None,
    latch_path: str | None = None,
    write_latch: bool = True,
) -> list[dict]:
    """Score decay always; time stop only when MFE_close < 1R and unlatched.

    ``mfe_close_r`` keys are tickers. Missing / None MFE -> no time stop (fail closed).
    """
    mfe_map = mfe_close_r or {}
    signals: list[dict] = []
    for pos in positions:
        reasons: list[str] = []
        score = scores.get(pos.ticker)
        if score is not None and score < 50:
            reasons.append(f"Signal decay: tm_score={score:g} (<50)")
        raw_mfe = mfe_map.get(pos.ticker)
        mfe_dec: Decimal | None
        if raw_mfe is None:
            mfe_dec = None
        else:
            try:
                mfe_dec = Decimal(str(raw_mfe))
            except Exception:
                mfe_dec = None
        eligible, days = time_stop_eligible(
            entry_date=pos.entry_date,
            session=session,
            mfe_close=mfe_dec,
            latch_path=latch_path,
            ticker=pos.ticker,
        )
        if eligible and days is not None:
            if latch_path and write_latch:
                try:
                    mark_time_stop_latched(
                        latch_path,
                        latch_key(pos.ticker, pos.entry_date),
                        session=session,
                    )
                except OSError:
                    # Fail closed: do not emit if latch cannot be persisted.
                    eligible = False
            if eligible:
                reasons.append(f"Time stop: ~{days} trading days since {pos.entry_date}")
        if reasons:
            signals.append(
                {
                    "ticker": pos.ticker,
                    "remaining": pos.remaining,
                    "tm_score": score,
                    "reasons": reasons,
                }
            )
    return signals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only T&M exit overlay")
    parser.add_argument("--journal", default=JOURNAL_PATH)
    parser.add_argument("--results-dir", default=DAILY_RESULTS_DIR)
    parser.add_argument("--date", default="", help="Session date YYYY-MM-DD")
    parser.add_argument("--latch", default=TIME_STOP_LATCH_PATH)
    parser.add_argument(
        "--mfe-json",
        default="",
        help="Optional JSON object {ticker: mfe_close_r}. Missing -> no time stops.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compatibility flag; does not skip latch persistence",
    )
    args = parser.parse_args(argv)
    session = date.fromisoformat(args.date) if args.date else date.today()
    try:
        rows = load_rows(args.journal)
    except OSError as exc:
        print(f"[exit-checker] journal unavailable: {exc}", file=sys.stderr)
        return 2
    positions = compute_open_book(rows)
    scores, source = load_scores(args.results_dir, session)
    mfe_map: dict[str, Decimal | float | None] = {}
    if args.mfe_json:
        try:
            raw = json.loads(Path(args.mfe_json).read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                mfe_map = {str(k).upper(): v for k, v in raw.items()}
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"[exit-checker] mfe-json unreadable: {exc}", file=sys.stderr)
            return 2
    signals = find_exit_signals(
        positions,
        scores,
        session,
        mfe_close_r=mfe_map,
        latch_path=args.latch,
        write_latch=True,
    )
    print(
        f"[exit-checker] session={session} OPEN={len(positions)} "
        f"signals={len(signals)} scores={source}",
        file=sys.stderr,
    )
    for signal in signals:
        score = signal["tm_score"] if signal["tm_score"] is not None else "N/A"
        print(
            f"{signal['ticker']} remaining={signal['remaining']} tm_score={score}: "
            + "; ".join(signal["reasons"])
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
