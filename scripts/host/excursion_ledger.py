#!/usr/bin/env python3
"""Read-only MAE/MFE excursion ledger for closed lots.

Replays validated daily bars between entry and exit. Writes JSON + markdown
artifacts only — never touches risk_plans.json or the journal.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

HOST_DIR = Path(__file__).resolve().parent
if str(HOST_DIR) not in sys.path:
    sys.path.insert(0, str(HOST_DIR))

from market_data import (  # noqa: E402
    DailyBar,
    MarketCache,
    MarketDataError,
    MarketRequest,
    YahooMarketData,
    YFinanceTransport,
    wilder_atr,
)
from risk_plan import (  # noqa: E402
    RiskPlanError,
    load_plan_store,
    parse_journal_fill,
)

def _hermes_home() -> str:
    return os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")


def _reports_inbox() -> str:
    return os.environ.get("REPORTS_INBOX") or os.path.expanduser("~/workspace/reports/inbox")


_HERMES = _hermes_home()
JOURNAL_PATH = os.path.join(_HERMES, "trade_journal.csv")
RISK_PLAN_PATH = os.path.join(_HERMES, "risk_plans.json")
MARKET_CACHE_DIR = os.path.join(_HERMES, "shared/audit/market-data")
SHARED_DIR = os.path.join(_HERMES, "shared/reports/renee/excursion-ledger")
INBOX_DIR = os.path.join(_reports_inbox(), "excursion-ledger")
SKIP_STATUS = {"VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED"}


@dataclass(frozen=True)
class ExcursionRow:
    ticker: str
    buy_row_id: str
    entry_session: str
    exit_session: str
    sessions_held: int
    fill: str
    risk_per_share: str
    r_source: str
    mae_r: str
    mfe_high_r: str
    mfe_close_r: str
    capture_ratio: str | None
    realised_r: str | None
    issues: tuple[str, ...]


def _decimal(value, name: str) -> Decimal:
    try:
        out = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"{name}: invalid decimal") from exc
    if not out.is_finite():
        raise ValueError(f"{name}: non-finite")
    return out


def _parse_day(raw: str) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def load_rows(path: str) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _closed_round_trips(rows: Sequence[dict]) -> list[tuple[dict, list[dict]]]:
    """Pair CLOSED BUY lots with subsequent CLOSED SELLs of the same ticker (FIFO)."""
    open_buys: dict[str, list[list[object]]] = {}
    trips: list[tuple[dict, list[dict]]] = []
    for row in rows:
        action = str(row.get("Action") or "").strip().upper()
        status = str(row.get("Status") or "").strip().upper()
        ticker = str(row.get("Ticker") or "").strip().upper()
        if not ticker or status in SKIP_STATUS:
            continue
        try:
            shares = abs(float(str(row.get("Shares") or "0").replace(",", "") or 0))
        except ValueError:
            continue
        if shares <= 0:
            continue
        if action == "BUY" and status == "CLOSED":
            open_buys.setdefault(ticker, []).append([row, shares, []])
        elif action == "SELL" and status == "CLOSED":
            remaining = shares
            while remaining > 0 and open_buys.get(ticker):
                lot = open_buys[ticker][0]
                take = min(float(lot[1]), remaining)
                lot[2].append(row)
                lot[1] = float(lot[1]) - take
                remaining -= take
                if float(lot[1]) <= 1e-9:
                    trips.append((lot[0], list(lot[2])))  # type: ignore[arg-type]
                    open_buys[ticker].pop(0)
    return trips


def _exit_session(sells: Sequence[dict]) -> date | None:
    dates = [_parse_day(str(s.get("Date") or "")) for s in sells]
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def _realised_exit_price(sells: Sequence[dict], currency: str) -> Decimal | None:
    """Best-effort average exit from Price USD / Price; Notes prose is ignored."""
    total_px = Decimal("0")
    total_sh = Decimal("0")
    for sell in sells:
        shares = _decimal(sell.get("Shares") or "0", "Shares")
        if shares <= 0:
            continue
        if currency == "USD":
            raw = str(sell.get("Price USD") or "").strip()
            if not raw:
                continue
            px = _decimal(raw, "Price USD")
        else:
            raw = str(sell.get("Price") or "").strip()
            if not raw:
                continue
            px = _decimal(raw, "Price")
        total_px += px * shares
        total_sh += shares
    if total_sh <= 0:
        return None
    return total_px / total_sh


def compute_excursion(
    *,
    fill_price: Decimal,
    risk_per_share: Decimal,
    bars: Sequence[DailyBar],
    entry_session: date,
    exit_session: date,
    exit_price: Decimal | None,
) -> tuple[Decimal, Decimal, Decimal, Decimal | None, Decimal | None, int, tuple[str, ...]]:
    issues: list[str] = []
    window = [b for b in bars if entry_session <= b.session <= exit_session]
    if not window:
        raise MarketDataError("no bars in holding window")
    sessions = sorted({b.session for b in window})
    low = min(b.low for b in window)
    high = max(b.high for b in window)
    best_close = max(b.close for b in window)
    if risk_per_share <= 0:
        raise MarketDataError("risk_per_share must be positive")
    mae_r = (fill_price - low) / risk_per_share
    mfe_high_r = (high - fill_price) / risk_per_share
    mfe_close_r = (best_close - fill_price) / risk_per_share
    realised_r = None
    capture = None
    if exit_price is not None:
        realised_r = (exit_price - fill_price) / risk_per_share
        if mfe_high_r > 0:
            capture = realised_r / mfe_high_r
        else:
            issues.append("MFE_HIGH_NON_POSITIVE")
    else:
        issues.append("EXIT_PRICE_MISSING")
    return (
        mae_r,
        mfe_high_r,
        mfe_close_r,
        capture,
        realised_r,
        len(sessions),
        tuple(issues),
    )


def _risk_from_plan_or_atr(
    buy: dict,
    plans: dict,
    bars: Sequence[DailyBar],
    entry_session: date,
) -> tuple[Decimal, Decimal, str, tuple[str, ...]]:
    """Return fill, risk_per_share, r_source, issues."""
    issues: list[str] = []
    row_id = str(buy.get("RowID") or "").strip()
    plan = plans.get(row_id) if row_id else None
    if plan is not None:
        return plan.fill.price, plan.levels.risk_per_share, "risk_plan", ()
    try:
        fill = parse_journal_fill(buy)
    except RiskPlanError as exc:
        raise MarketDataError(f"fill parse failed: {exc}") from exc
    # Prefer pre-fill ATR session when enough history exists.
    prior = [b for b in bars if b.session < entry_session]
    try:
        if prior:
            atr_session = prior[-1].session
            atr = wilder_atr(prior, through_session=atr_session)
        else:
            atr = wilder_atr(bars, through_session=entry_session)
            issues.append("ATR_USED_ENTRY_SESSION")
    except MarketDataError as exc:
        raise MarketDataError(f"ATR unavailable: {exc}") from exc
    risk = atr * Decimal("1.5")
    return fill.price, risk, "atr-r-1.5x-replay", tuple(issues)


def build_ledger(
    rows: Sequence[dict],
    *,
    market: YahooMarketData | None,
    plans: dict,
    session: date,
) -> list[ExcursionRow]:
    out: list[ExcursionRow] = []
    for buy, sells in _closed_round_trips(rows):
        ticker = str(buy.get("Ticker") or "").strip().upper()
        entry = _parse_day(str(buy.get("Date") or buy.get("FilledAt") or ""))
        exit_day = _exit_session(sells)
        issues: list[str] = []
        if entry is None or exit_day is None:
            out.append(
                ExcursionRow(
                    ticker=ticker,
                    buy_row_id=str(buy.get("RowID") or ""),
                    entry_session=str(entry or ""),
                    exit_session=str(exit_day or ""),
                    sessions_held=0,
                    fill="",
                    risk_per_share="",
                    r_source="",
                    mae_r="",
                    mfe_high_r="",
                    mfe_close_r="",
                    capture_ratio=None,
                    realised_r=None,
                    issues=("DATE_UNPARSEABLE",),
                )
            )
            continue
        currency = "USD" if str(buy.get("Price USD") or "").strip() or str(
            buy.get("Total USD") or ""
        ).strip() else "GBP"
        yahoo = ticker
        bars: tuple[DailyBar, ...] = ()
        if market is not None:
            evidence = market.get_validated_evidence(
                MarketRequest(
                    symbol=yahoo,
                    expected_session=exit_day,
                    expected_currency=currency,
                    plan_created_session=entry,
                )
            )
            bars = evidence.bars
            # Always surface evidence issues, even when bars are present
            # (e.g. UNREBASED_SPLIT / currency mismatch on a usable series).
            issues.extend(evidence.issues)
            if not bars:
                issues.append("BARS_MISSING")
        else:
            issues.append("MARKET_DISABLED")
        if not bars or "UNREBASED_SPLIT" in issues:
            out.append(
                ExcursionRow(
                    ticker=ticker,
                    buy_row_id=str(buy.get("RowID") or ""),
                    entry_session=entry.isoformat(),
                    exit_session=exit_day.isoformat(),
                    sessions_held=0,
                    fill="",
                    risk_per_share="",
                    r_source="",
                    mae_r="",
                    mfe_high_r="",
                    mfe_close_r="",
                    capture_ratio=None,
                    realised_r=None,
                    issues=tuple(sorted(set(issues))),
                )
            )
            continue
        try:
            fill_px, risk, r_source, r_issues = _risk_from_plan_or_atr(
                buy, plans, bars, entry
            )
            issues.extend(r_issues)
            exit_px = _realised_exit_price(sells, currency)
            mae, mfe_h, mfe_c, capture, realised, held, x_issues = compute_excursion(
                fill_price=fill_px,
                risk_per_share=risk,
                bars=bars,
                entry_session=entry,
                exit_session=exit_day,
                exit_price=exit_px,
            )
            issues.extend(x_issues)
            out.append(
                ExcursionRow(
                    ticker=ticker,
                    buy_row_id=str(buy.get("RowID") or ""),
                    entry_session=entry.isoformat(),
                    exit_session=exit_day.isoformat(),
                    sessions_held=held,
                    fill=str(fill_px),
                    risk_per_share=str(risk),
                    r_source=r_source,
                    mae_r=str(mae),
                    mfe_high_r=str(mfe_h),
                    mfe_close_r=str(mfe_c),
                    capture_ratio=str(capture) if capture is not None else None,
                    realised_r=str(realised) if realised is not None else None,
                    issues=tuple(sorted(set(issues))),
                )
            )
        except (MarketDataError, ValueError, RiskPlanError) as exc:
            issues.append(f"COMPUTE_FAILED:{type(exc).__name__}")
            out.append(
                ExcursionRow(
                    ticker=ticker,
                    buy_row_id=str(buy.get("RowID") or ""),
                    entry_session=entry.isoformat(),
                    exit_session=exit_day.isoformat(),
                    sessions_held=0,
                    fill="",
                    risk_per_share="",
                    r_source="",
                    mae_r="",
                    mfe_high_r="",
                    mfe_close_r="",
                    capture_ratio=None,
                    realised_r=None,
                    issues=tuple(sorted(set(issues))),
                )
            )
    _ = session  # reserved for future same-day filter
    return out


def render_markdown(rows: Sequence[ExcursionRow], session: date) -> str:
    lines = [
        f"# Excursion ledger — {session.isoformat()}",
        "",
        "Read-only MAE/MFE in R units. Non-investment advice.",
        "",
        "| Ticker | Entry | Exit | Days | MAE_R | MFE_high_R | MFE_close_R | Capture | Realised_R | Issues |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.ticker,
                    row.entry_session or "—",
                    row.exit_session or "—",
                    str(row.sessions_held),
                    row.mae_r or "—",
                    row.mfe_high_r or "—",
                    row.mfe_close_r or "—",
                    row.capture_ratio or "—",
                    row.realised_r or "—",
                    ",".join(row.issues) if row.issues else "—",
                ]
            )
            + " |"
        )
    if not rows:
        lines.append("| — | — | — | 0 | — | — | — | — | — | NO_CLOSED_TRIPS |")
    lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only closed-lot excursion ledger")
    parser.add_argument("--journal", default=JOURNAL_PATH)
    parser.add_argument("--risk-plans", default=RISK_PLAN_PATH)
    parser.add_argument("--date", default="", help="Report stamp YYYY-MM-DD")
    parser.add_argument("--no-market", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    session = date.fromisoformat(args.date) if args.date else date.today()
    try:
        rows = load_rows(args.journal)
    except OSError as exc:
        print(f"[excursion-ledger] journal unavailable: {exc}", file=sys.stderr)
        return 2
    plans = {}
    try:
        plans = load_plan_store(args.risk_plans)
    except (OSError, RiskPlanError) as exc:
        print(f"[excursion-ledger] risk plans skipped: {exc}", file=sys.stderr)
    market = None
    if not args.no_market:
        market = YahooMarketData(
            YFinanceTransport(),
            cache=MarketCache(MARKET_CACHE_DIR),
        )
    ledger = build_ledger(rows, market=market, plans=plans, session=session)
    doc = {
        "schema_version": "1",
        "session": session.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": [asdict(row) for row in ledger],
    }
    md = render_markdown(ledger, session)
    print(md)
    if not args.no_write:
        stem = f"{session.isoformat()}-excursion-ledger"
        for folder in (SHARED_DIR, INBOX_DIR):
            _atomic_write(Path(folder) / f"{stem}.md", md)
            _atomic_write(
                Path(folder) / f"{stem}.json",
                json.dumps(doc, indent=2, sort_keys=True) + "\n",
            )
    print(
        f"[excursion-ledger] session={session} trips={len(ledger)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
