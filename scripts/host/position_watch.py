#!/usr/bin/env python3
"""Nightly audited OPEN-position watch — remaining shares + SL/TP1/TP2.

Read-only. Does not place broker orders or rewrite the journal.
Yahoo unadjusted OHLC is validated and cached; invalid evidence fails closed.
Adopted lot risk plans are read from an immutable sidecar. Score/time exit
rules stay file-only so this job does not repeat the 22:15 Telegram.

Stdout is unique attention bullets only (no_agent Telegram). The markdown file
is the SSOT. Missing T&M JSON is not a failure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

HOST_DIR = Path(__file__).resolve().parent
if str(HOST_DIR) not in sys.path:
    sys.path.insert(0, str(HOST_DIR))

from market_data import (  # noqa: E402
    MarketCache,
    MarketRequest,
    YahooMarketData,
    YFinanceTransport,
)
from risk_plan import (  # noqa: E402
    CHANDELIER_POLICY_VERSION,
    LEGACY_POLICY_VERSION,
    PLAN_ROW_TOKEN,
    POLICY_VERSION,
    ZONE_POLICY_VERSION,
    RiskPlan,
    RiskPlanError,
    check_nav_gates,
    has_fixed_tp2,
    load_plan_store,
    parse_journal_fill,
    planned_stop_risk,
    propose_chandelier_trail_sl,
    reconcile_plan,
    trail_exit_triggered,
)
from time_stop import (  # noqa: E402
    TIME_STOP_LATCH_PATH,
    latch_key,
    mark_time_stop_latched,
    mfe_close_r_from_bars,
    time_stop_eligible,
)
from time_stop import count_trading_days  # noqa: E402

COMMENT_HEADING = "## Position comments"
COMMENT_STUB = """## Position comments

Not investment advice. Do not edit the script table or Final audit above.
Assigned specialists must comment per role. If daily/weekly reports omit a name, investigate here—do not only write miss.
Each writer covers Insight, Direction, SL, TP, Target, On hold.
Renee: trend only. Eliza: value only. Christina: rates/bonds only. Emily: commodities only.
No orders, no journal edits, never blend tm_score with value sleeve scores.
"""

def _hermes_home() -> str:
    return os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")


def _reports_inbox() -> str:
    return os.environ.get("REPORTS_INBOX") or os.path.expanduser("~/workspace/reports/inbox")


_HERMES = _hermes_home()
JOURNAL_PATH = os.path.join(_HERMES, "trade_journal.csv")
TM_DIR = os.path.join(_HERMES, "shared/reports/renee/daily-trend-momentum")
WIDTH_DIR = os.path.join(_HERMES, "shared/reports/eliza/valuation-width")
WORKSPACE_DIR = os.path.join(_HERMES, "profiles/renee/workspace/position-watch")
SHARED_DIR = os.path.join(_HERMES, "shared/reports/renee/position-watch")
INBOX_DIR = os.path.join(_reports_inbox(), "position-watch")
RISK_PLAN_PATH = os.path.join(_HERMES, "risk_plans.json")
MARKET_CACHE_DIR = os.path.join(_HERMES, "shared/audit/market-data")
ALERT_STATE_PATH = os.path.join(_HERMES, "shared/audit/position-watch-alerts.json")
TIME_STOP_LATCH_DEFAULT = TIME_STOP_LATCH_PATH

SKIP_STATUS = ("VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED")
ACK = "PARTIAL_EXIT_ACK"
KELLY_OVERRIDE = "KELLY_OVERRIDE"
DEFAULT_GBP_USD = 1.31
DEFAULT_PORTFOLIO_GBP = 50000.0
DASH = "—"
# Same bands as host position_sizing_check.py (score -> max fraction of book).
KELLY_BRACKETS = {
    (90, float("inf")): 0.05,
    (80, 89): 0.04,
    (70, 79): 0.03,
    (60, 69): 0.02,
    (0, 59): 0.01,
}


def _to_float(val) -> float | None:
    if val is None:
        return None
    raw = str(val).strip().replace(",", "")
    if not raw or raw in (DASH, "-", "N/A", "n/a"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _cell(val: str) -> str:
    text = " ".join(str(val).replace("|", "/").split())
    return text if text else DASH


def _has_usd(row: dict) -> bool:
    total = _to_float(row.get("Total USD"))
    price = _to_float(row.get("Price USD"))
    return bool((total is not None and total > 0) or (price is not None and price > 0))


def _native_ccy(buy_rows: list[dict], sell_rows: list[dict]) -> str:
    """Infer execution currency from BUY fills only."""
    currencies = {"USD" if _has_usd(row) else "GBP" for row in buy_rows}
    return sorted(currencies)[0] if currencies else "GBP"


def _currency_conflict(buy_rows: list[dict]) -> bool:
    return len({"USD" if _has_usd(row) else "GBP" for row in buy_rows}) > 1


def _native_price(row: dict, native_ccy: str) -> float | None:
    """Return a price in the same currency as journal SL/TP levels."""
    if native_ccy == "GBP":
        return _to_float(row.get("Price"))
    price_usd = _to_float(row.get("Price USD"))
    if price_usd is not None and price_usd > 0:
        return price_usd
    total_usd = _to_float(row.get("Total USD"))
    shares = _to_float(row.get("Shares"))
    if total_usd is not None and total_usd > 0 and shares is not None and shares > 0:
        return total_usd / shares
    return None


def _uniq_level(rows: list[dict], key: str) -> tuple[float | None, bool]:
    vals: list[float] = []
    seen: set[float] = set()
    for row in rows:
        num = _to_float(row.get(key))
        if num is None:
            continue
        if num not in seen:
            seen.add(num)
            vals.append(num)
    if not vals:
        return None, False
    if len(vals) > 1:
        return None, True
    return vals[0], False


def _fmt_px(num: float | None, ccy: str | None = None) -> str:
    if num is None:
        return DASH
    if ccy == "GBP":
        return f"£{num:,.2f}"
    if ccy == "USD":
        return f"${num:,.2f}"
    return f"{num:,.2f}"


def _fmt_pct(num: float | None) -> str:
    if num is None:
        return DASH
    return f"{num:+.1f}%"


def _fmt_score(num: float | None) -> str:
    if num is None:
        return "N/A"
    if abs(num - round(num)) < 1e-9:
        return str(int(round(num)))
    return f"{num:.1f}"


def kelly_limit(score: float | None) -> float:
    if score is None:
        return 0.05
    for (low, high), limit in KELLY_BRACKETS.items():
        if low <= score <= high:
            return limit
    return 0.01


@dataclass
class OpenPosition:
    ticker: str
    remaining: int
    entry: float
    native_ccy: str
    cost_usd: float
    cost_gbp: float
    sl: float | None
    tp1: float | None
    tp2: float | None
    sl_conflict: bool = False
    tp1_conflict: bool = False
    tp2_conflict: bool = False
    entry_date: str = ""
    ack: bool = False
    kelly_override: bool = False
    etf: bool = False
    last: float | None = None
    tm_score: float | None = None
    row_ids: list[str] = field(default_factory=list)
    high: float | None = None
    low: float | None = None
    market_valid: bool = False
    market_source: str = "T&M"
    market_issues: list[str] = field(default_factory=list)
    currency_conflict: bool = False
    active_sl: float | None = None
    plan_tp1: float | None = None
    plan_tp2: float | None = None
    plan_state: str = "JOURNAL_ONLY"
    level_source: str = "JOURNAL"
    plan_issues: list[str] = field(default_factory=list)
    trailed: bool = False
    yahoo_symbol: str = ""
    gap_through_sl: bool = False
    plan_rebased: bool = False
    zone_status: str = ""
    zone_mode: str = ""
    zone_lo: float | None = None
    zone_hi: float | None = None
    proposed_trail: float | None = None
    trail_propose_issues: list[str] = field(default_factory=list)
    trail_shadow_legacy: bool = False
    trail_shadow_compare: dict[str, str] | None = None
    policy_version: str = ""
    risk_per_share: float | None = None
    market_bars: tuple = ()
    market_splits: tuple = ()
    notes: list[str] = field(default_factory=list)


def load_journal(journal_path: str) -> list[dict]:
    path = Path(journal_path)
    if not path.is_file():
        raise FileNotFoundError(journal_path)
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _linked_plan_row_id(row: dict) -> str:
    linked = str(row.get("PlanRowID") or "").strip()
    if linked:
        return linked
    notes = str(row.get("Notes") or "")
    idx = notes.find(PLAN_ROW_TOKEN)
    if idx < 0:
        return ""
    rest = notes[idx + len(PLAN_ROW_TOKEN) :].strip()
    return rest.split()[0] if rest else ""


def _parse_row_date(row: dict) -> str:
    return (row.get("Date") or "").strip()


def compute_open_positions(
    rows: list[dict], gbp_usd_rate: float = DEFAULT_GBP_USD
) -> list[OpenPosition]:
    buys: dict[str, list[dict]] = defaultdict(list)
    sells: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        ticker = (row.get("Ticker") or "").strip().upper()
        action = (row.get("Action") or "").strip().upper()
        status = (row.get("Status") or "").strip().upper()
        if not ticker or status in SKIP_STATUS:
            continue
        if action == "BUY":
            buys[ticker].append(row)
        elif action == "SELL" and status == "CLOSED":
            sells[ticker].append(row)

    out: list[OpenPosition] = []
    for ticker in sorted(set(buys) | set(sells)):
        buy_rows = buys.get(ticker, [])
        sell_rows = sells.get(ticker, [])
        open_buys = [
            row
            for row in buy_rows
            if (row.get("Status") or "").strip().upper() == "OPEN"
        ]
        if not open_buys:
            continue
        ccy_conflict = _currency_conflict(buy_rows)
        lots: list[dict] = []
        by_id: dict[str, int] = {}
        for row in open_buys:
            shares = int(round(_to_float(row.get("Shares")) or 0.0))
            lots.append({"row": row, "remaining": max(shares, 0)})
            row_id = str(row.get("RowID") or "").strip()
            if row_id:
                by_id[row_id] = len(lots) - 1
        for sell in sorted(sell_rows, key=_parse_row_date):
            qty = int(round(_to_float(sell.get("Shares")) or 0.0))
            if qty <= 0:
                continue
            linked = _linked_plan_row_id(sell)
            if linked in by_id:
                lot = lots[by_id[linked]]
                take = min(lot["remaining"], qty)
                lot["remaining"] -= take
                qty -= take
            for lot in lots:
                if qty <= 0:
                    break
                take = min(lot["remaining"], qty)
                lot["remaining"] -= take
                qty -= take

        for lot in lots:
            remaining = lot["remaining"]
            if remaining <= 0:
                continue
            row = lot["row"]
            native = "USD" if _has_usd(row) else "GBP"
            px = _native_price(row, native)
            if px is None:
                continue
            if native == "GBP":
                cost_gbp = remaining * px
                cost_usd = cost_gbp * gbp_usd_rate
            else:
                cost_usd = remaining * px
                cost_gbp = cost_usd / gbp_usd_rate if gbp_usd_rate else 0.0
            notes = str(row.get("Notes") or "")
            row_id = str(row.get("RowID") or "").strip()
            sl = _to_float(row.get("SL"))
            tp1 = _to_float(row.get("TP1"))
            tp2 = _to_float(row.get("TP2"))
            out.append(
                OpenPosition(
                    ticker=ticker,
                    remaining=remaining,
                    entry=px,
                    native_ccy=native,
                    currency_conflict=ccy_conflict,
                    cost_usd=round(cost_usd, 2),
                    cost_gbp=round(cost_gbp, 2),
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    sl_conflict=False,
                    tp1_conflict=False,
                    tp2_conflict=False,
                    entry_date=_parse_row_date(row),
                    ack=ACK in notes,
                    kelly_override=KELLY_OVERRIDE in notes,
                    etf=ticker.endswith(".L") or ticker.endswith(".LN"),
                    trailed=False,
                    yahoo_symbol=ticker,
                    row_ids=[row_id] if row_id else [],
                )
            )
    return out


def _tm_score_from_row(row: dict) -> float | None:
    if "tm_score" in row and row.get("tm_score") is not None:
        return _to_float(row.get("tm_score"))
    return _to_float(row.get("daily_score"))


def load_same_date_tm(tm_dir: str, session: date) -> tuple[dict[str, dict], str]:
    """Join only YYYY-MM-DD*-data.json. Missing -> empty map."""
    folder = Path(tm_dir)
    stamp = session.isoformat()
    if not folder.is_dir():
        return {}, "missing"
    exact = folder / f"{stamp}-data.json"
    candidates: list[Path] = []
    if exact.is_file():
        candidates = [exact]
    else:
        candidates = sorted(
            p
            for p in folder.glob(f"{stamp}*-data.json")
            if "latest" not in p.name.lower()
        )
    if not candidates:
        return {}, "missing"
    path = candidates[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "missing"
    results = data if isinstance(data, list) else data.get("results") or []
    by_ticker: dict[str, dict] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        by_ticker[ticker] = {
            "tm_score": _tm_score_from_row(row),
            "last": _to_float(row.get("price")),
        }
    return by_ticker, path.name


def _walk_e5(obj) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        raw = obj.get("e5_overlap")
        if isinstance(raw, list):
            found.extend(str(x).strip().upper() for x in raw if str(x).strip())
        elif isinstance(raw, str) and raw.strip():
            found.append(raw.strip().upper())
        for val in obj.values():
            found.extend(_walk_e5(val))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk_e5(item))
    return found


def load_e5_overlap(width_dir: str, session: date) -> list[str]:
    iso = session.isocalendar()
    week = f"{iso.year}-W{iso.week:02d}"
    folder = Path(width_dir)
    if not folder.is_dir():
        return []
    for name in (
        f"{week}-valuation-width-revised.json",
        f"{week}-valuation-width.json",
    ):
        path = folder / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        return sorted(set(_walk_e5(data)))
    return []


def join_tm(positions: list[OpenPosition], tm: dict[str, dict]) -> None:
    for pos in positions:
        row = tm.get(pos.ticker) or {}
        pos.last = row.get("last")
        pos.tm_score = row.get("tm_score")
        if pos.etf:
            pos.tm_score = None
            pos.last = None


def _expected_exchange(ticker: str) -> str | None:
    if ticker.endswith(".L") or ticker.endswith(".LN"):
        return "LSE"
    return None


def _overlay_open_buy(pos: OpenPosition, row: dict, row_id: str) -> OpenPosition:
    notes = str(row.get("Notes") or "")
    shares = _to_float(row.get("Shares")) or 0.0
    px = _native_price(row, pos.native_ccy)
    sl = _to_float(row.get("SL"))
    tp1 = _to_float(row.get("TP1"))
    tp2 = _to_float(row.get("TP2"))
    date_s = (row.get("Date") or "").strip()
    return replace(
        pos,
        row_ids=[row_id],
        remaining=int(round(shares)),
        entry=px if px is not None else pos.entry,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        sl_conflict=False,
        tp1_conflict=False,
        tp2_conflict=False,
        entry_date=date_s or pos.entry_date,
        ack=ACK in notes,
        kelly_override=KELLY_OVERRIDE in notes,
        notes=[],
        plan_issues=[],
        market_issues=[],
        active_sl=sl,
        plan_tp1=tp1,
        plan_tp2=tp2,
        trailed=False,
        plan_rebased=False,
        gap_through_sl=False,
        yahoo_symbol=pos.ticker,
        zone_status="",
        zone_mode="",
        zone_lo=None,
        zone_hi=None,
    )


def _attach_one_plan(
    pos: OpenPosition,
    plan: RiskPlan,
    journal_rows: list[dict],
    *,
    allow_legacy_fallback: bool,
) -> None:
    source_row = next(
        (
            row
            for row in journal_rows
            if str(row.get("RowID") or "").strip() == plan.plan_id
        ),
        None,
    )
    try:
        journal_fill = parse_journal_fill(source_row or {})
    except RiskPlanError:
        pos.plan_state = "BLOCKED"
        pos.plan_issues = ["PLAN_JOURNAL_BINDING_INVALID"]
        return
    if (
        plan.fill.row_id != journal_fill.row_id
        or plan.fill.ticker != journal_fill.ticker
        or plan.fill.currency != journal_fill.currency
        or plan.fill.shares != journal_fill.shares
        or plan.fill.price != journal_fill.price
        or plan.fill.source_field != journal_fill.source_field
    ):
        pos.plan_state = "BLOCKED"
        pos.plan_issues = ["PLAN_JOURNAL_BINDING_MISMATCH"]
        return
    view = reconcile_plan(
        plan,
        journal_rows,
        allow_legacy_fallback=allow_legacy_fallback,
    )
    pos.plan_state = view.state
    pos.plan_issues = list(view.issues)
    pos.yahoo_symbol = plan.fill.yahoo_symbol or pos.ticker
    pos.trailed = any(event.kind == "TRAIL_SL" for event in plan.events)
    pos.plan_rebased = view.rebased
    pos.zone_status = str(plan.policy.get("zone_status") or "")
    pos.zone_mode = str(plan.policy.get("zone_mode") or "")
    pos.zone_lo = _to_float(plan.policy.get("zone_lo"))
    pos.zone_hi = _to_float(plan.policy.get("zone_hi"))
    pos.policy_version = plan.policy_version
    pos.risk_per_share = float(plan.levels.risk_per_share)
    if view.state != "BLOCKED":
        pos.level_source = "PLAN"
        pos.active_sl = float(view.active_sl)
        pos.plan_tp1 = float(view.tp1)
        # Chandelier: TP2 is an unused placeholder equal to TP1 — hide as target.
        if has_fixed_tp2(plan.policy_version):
            pos.plan_tp2 = float(view.tp2)
        else:
            pos.plan_tp2 = None
        pos.remaining = view.remaining_shares


def _reprice_cost(pos: OpenPosition) -> None:
    rate = pos.cost_usd / pos.cost_gbp if pos.cost_gbp else DEFAULT_GBP_USD
    if pos.native_ccy == "GBP":
        pos.cost_gbp = round(pos.remaining * pos.entry, 2)
        pos.cost_usd = round(pos.cost_gbp * rate, 2)
    else:
        pos.cost_usd = round(pos.remaining * pos.entry, 2)
        pos.cost_gbp = round(pos.cost_usd / rate, 2) if rate else 0.0


def join_risk_plans(
    positions: list[OpenPosition],
    plans: dict[str, RiskPlan],
    journal_rows: list[dict],
) -> None:
    """Attach adopted lot plans; one OPEN BUY RowID becomes one watch row."""
    expanded: list[OpenPosition] = []
    for pos in positions:
        pos.active_sl = pos.sl
        pos.plan_tp1 = pos.tp1
        pos.plan_tp2 = pos.tp2
        ids = [row_id for row_id in pos.row_ids if row_id]
        if not ids:
            pos.plan_state = "JOURNAL_ONLY"
            pos.plan_issues = ["RISK_PLAN_MISSING"]
            expanded.append(pos)
            continue
        if len(ids) == 1:
            plan = plans.get(ids[0])
            if plan is None:
                pos.plan_state = "JOURNAL_ONLY"
                pos.plan_issues = ["RISK_PLAN_MISSING"]
            else:
                _attach_one_plan(
                    pos,
                    plan,
                    journal_rows,
                    allow_legacy_fallback=plan.policy_version == LEGACY_POLICY_VERSION,
                )
                _reprice_cost(pos)
            expanded.append(pos)
            continue
        by_id = {
            str(row.get("RowID") or "").strip(): row
            for row in journal_rows
            if str(row.get("RowID") or "").strip()
        }
        for row_id in ids:
            source = by_id.get(row_id)
            lot = (
                _overlay_open_buy(pos, source, row_id)
                if source is not None
                else replace(
                    pos,
                    row_ids=[row_id],
                    notes=[],
                    plan_issues=[],
                    market_issues=[],
                )
            )
            plan = plans.get(row_id)
            if plan is None:
                lot.plan_state = "JOURNAL_ONLY"
                lot.plan_issues = ["RISK_PLAN_MISSING"]
            else:
                _attach_one_plan(
                    lot,
                    plan,
                    journal_rows,
                    allow_legacy_fallback=False,
                )
            _reprice_cost(lot)
            expanded.append(lot)
    positions[:] = expanded


def join_market(
    positions: list[OpenPosition],
    market: YahooMarketData | None,
    session: date,
) -> None:
    """Replace T&M Last with validated Yahoo OHLC when a provider is enabled."""
    for pos in positions:
        if pos.currency_conflict:
            pos.market_valid = False
            pos.market_issues = ["BUY_CURRENCY_CONFLICT"]
            pos.last = None
            continue
        if market is None:
            pos.market_valid = False
            pos.market_source = "T&M"
            continue
        tm_close = Decimal(str(pos.last)) if pos.last is not None else None
        try:
            created = date.fromisoformat(pos.entry_date) if pos.entry_date else None
        except ValueError:
            created = None
        active_sl = None
        if pos.active_sl is not None:
            active_sl = Decimal(str(pos.active_sl))
        elif pos.sl is not None:
            active_sl = Decimal(str(pos.sl))
        evidence = market.get_validated_evidence(
            MarketRequest(
                symbol=pos.yahoo_symbol or pos.ticker,
                expected_session=session,
                expected_currency=pos.native_ccy,
                plan_created_session=created,
                tm_close=tm_close,
                active_sl=active_sl,
                expected_exchange=_expected_exchange(pos.ticker),
            )
        )
        pos.market_valid = evidence.valid_for_breach
        pos.market_source = "Yahoo"
        issues = list(evidence.issues)
        if pos.plan_rebased:
            issues = [item for item in issues if item != "UNREBASED_SPLIT"]
        blocking = [item for item in issues if item != "GAP_THROUGH_SL"]
        pos.market_issues = issues
        pos.market_valid = evidence.bar is not None and not blocking
        pos.gap_through_sl = bool(evidence.gap_through_sl and pos.market_valid)
        pos.market_bars = evidence.bars
        pos.market_splits = evidence.splits
        if pos.market_valid and evidence.bar is not None:
            pos.last = float(evidence.bar.close)
            pos.high = float(evidence.bar.high)
            pos.low = float(evidence.bar.low)
        else:
            pos.last = None
            pos.high = None
            pos.low = None


def join_trail_proposals(
    positions: list[OpenPosition],
    plans: dict[str, RiskPlan],
    session: date,
) -> None:
    """Stateless chandelier trail proposals — never writes the sidecar.

    atr-chandelier-v1: real PROPOSED_TRAIL (adoptable via TRAIL_SL after owner
    confirms). atr-r-v2 / atr-zone-v1: file-only SHADOW comparison using voted
    k=4.0 defaults — does not change the live plan.
    """
    for pos in positions:
        if pos.plan_state in {"BLOCKED", "CLOSED"} or pos.remaining <= 0:
            continue
        plan_id = pos.row_ids[0] if pos.row_ids else ""
        plan = plans.get(plan_id)
        if plan is None:
            continue
        is_chandelier = plan.policy_version == CHANDELIER_POLICY_VERSION
        is_legacy_shadow = plan.policy_version in {
            POLICY_VERSION,
            ZONE_POLICY_VERSION,
        }
        if not is_chandelier and not is_legacy_shadow:
            continue
        if not pos.market_valid:
            pos.trail_propose_issues.append("MARKET_INVALID")
            continue
        if not pos.market_bars:
            pos.trail_propose_issues.append("BARS_MISSING")
            continue
        payload, reason = propose_chandelier_trail_sl(
            plan,
            pos.market_bars,
            through_session=session,
            splits=pos.market_splits,
            plan_rebased=pos.plan_rebased,
            shadow_for_legacy=is_legacy_shadow,
        )
        if reason and reason != "NO_RAISE":
            pos.trail_propose_issues.append(reason)
        if payload is None:
            continue
        if payload.get("compare_only") == "NO_RAISE":
            # Shadow ran but would not raise — file-only compare, not proposable.
            pos.trail_shadow_compare = payload
            pos.trail_shadow_legacy = True
            continue
        pos.proposed_trail = float(Decimal(payload["new_sl"]))
        pos.trail_shadow_legacy = is_legacy_shadow


def dist_pct(level: float | None, last: float | None) -> float | None:
    if level is None or last is None or last == 0:
        return None
    return (level - last) / last * 100.0


def dist_sl_pct(level: float | None, last: float | None) -> float | None:
    if level is None or last is None or last == 0:
        return None
    return (last - level) / last * 100.0


@dataclass
class WatchFlag:
    kind: str
    telegram: bool
    text: str


def _gbp_amount(native: Decimal, native_ccy: str, gbp_usd: float) -> Decimal:
    rate = Decimal(str(gbp_usd))
    if native_ccy == "USD" and rate > 0:
        return native / rate
    return native


def _stop_risk_gbp(pos: OpenPosition, gbp_usd: float) -> Decimal:
    sl = pos.active_sl if pos.active_sl is not None else pos.sl
    if sl is None or pos.remaining <= 0:
        return Decimal("0")
    try:
        risk_per_share = Decimal(str(pos.entry)) - Decimal(str(sl))
        if risk_per_share <= 0:
            return Decimal("0")
        native = planned_stop_risk(pos.remaining, risk_per_share)
    except RiskPlanError:
        return Decimal("0")
    return _gbp_amount(native, pos.native_ccy, gbp_usd)


def _stress_gap_gbp(pos: OpenPosition, gbp_usd: float) -> Decimal:
    if not pos.gap_through_sl or pos.last is None or pos.remaining <= 0:
        return Decimal("0")
    gap = Decimal(str(pos.entry)) - Decimal(str(pos.last))
    if gap <= 0:
        return Decimal("0")
    return _gbp_amount(Decimal(str(pos.remaining)) * gap, pos.native_ccy, gbp_usd)


def build_flags(
    positions: list[OpenPosition],
    session: date,
    e5: list[str],
    shadow: bool = False,
    gbp_usd: float = DEFAULT_GBP_USD,
    time_stop_latch_path: str | None = TIME_STOP_LATCH_DEFAULT,
) -> list[WatchFlag]:
    flags: list[WatchFlag] = []
    for pos in positions:
        blocking_market = [item for item in pos.market_issues if item != "GAP_THROUGH_SL"]
        if blocking_market:
            exchange_closed_only = blocking_market == ["EXCHANGE_CLOSED"]
            flags.append(
                WatchFlag(
                    "data",
                    not shadow and not exchange_closed_only,
                    f"Market data unavailable: {pos.ticker} ({', '.join(pos.market_issues)})",
                )
            )
        if pos.gap_through_sl and pos.market_valid:
            gap_telegram = (
                (not shadow)
                and pos.level_source == "PLAN"
                and pos.plan_state not in {"BLOCKED", "CLOSED"}
            )
            flags.append(
                WatchFlag(
                    "gap-SL",
                    gap_telegram,
                    f"Gap through SL at open: {pos.ticker} close={_fmt_px(pos.last, pos.native_ccy)} "
                    f"SL={_fmt_px(pos.active_sl if pos.active_sl is not None else pos.sl, pos.native_ccy)}",
                )
            )
        if pos.plan_issues:
            missing_only = pos.plan_issues == ["RISK_PLAN_MISSING"]
            flags.append(
                WatchFlag(
                    "risk-plan",
                    not shadow and not missing_only,
                    f"Risk plan {pos.plan_state}: {pos.ticker} ({', '.join(pos.plan_issues)})",
                )
            )
        if pos.zone_status and pos.zone_lo is not None:
            zone_bits = [f"status={pos.zone_status}"]
            if pos.zone_mode:
                zone_bits.append(f"mode={pos.zone_mode}")
            zone_bits.append(
                "zone="
                f"{_fmt_px(pos.zone_lo, pos.native_ccy)}..{_fmt_px(pos.zone_hi, pos.native_ccy)}"
            )
            flags.append(
                WatchFlag(
                    "ZONE",
                    False,
                    f"Congestion zone: {pos.ticker} ({', '.join(zone_bits)})",
                )
            )
        if pos.trail_shadow_compare is not None:
            cmp = pos.trail_shadow_compare
            trail_k = cmp.get("trail_k") or "4.0"
            flags.append(
                WatchFlag(
                    "TRAIL",
                    False,
                    f"SHADOW_CHANDELIER_COMPARE: {pos.ticker} raw_sl="
                    f"{_fmt_px(float(Decimal(cmp['new_sl'])), pos.native_ccy)} "
                    f"active={_fmt_px(pos.active_sl if pos.active_sl is not None else pos.sl, pos.native_ccy)} "
                    f"hc={_fmt_px(float(Decimal(cmp['highest_close'])), pos.native_ccy)} "
                    f"atr={_fmt_px(float(Decimal(cmp['atr14'])), pos.native_ccy)} "
                    f"(NO_RAISE; k={trail_k} compare-only)",
                )
            )
        if pos.proposed_trail is not None:
            if pos.trail_shadow_legacy:
                flags.append(
                    WatchFlag(
                        "TRAIL",
                        False,
                        f"SHADOW_CHANDELIER_TRAIL: {pos.ticker} new_sl="
                        f"{_fmt_px(pos.proposed_trail, pos.native_ccy)} "
                        f"(active={_fmt_px(pos.active_sl if pos.active_sl is not None else pos.sl, pos.native_ccy)}; "
                        f"k=4.0 compare-only — not adoptable until atr-chandelier-v1)",
                    )
                )
            else:
                flags.append(
                    WatchFlag(
                        "TRAIL",
                        False,
                        f"PROPOSED_TRAIL: {pos.ticker} new_sl="
                        f"{_fmt_px(pos.proposed_trail, pos.native_ccy)} "
                        f"(active={_fmt_px(pos.active_sl if pos.active_sl is not None else pos.sl, pos.native_ccy)}; "
                        f"confirm TRAIL_SL to adopt)",
                    )
                )
        if pos.trail_propose_issues:
            flags.append(
                WatchFlag(
                    "TRAIL",
                    False,
                    f"TRAIL_PROPOSE_SKIP: {pos.ticker} ({','.join(pos.trail_propose_issues)})",
                )
            )
        if pos.currency_conflict:
            flags.append(
                WatchFlag(
                    "lot",
                    not shadow,
                    f"BUY lot currency mismatch: {pos.ticker}",
                )
            )
        sl_present = pos.active_sl if pos.active_sl is not None else pos.sl
        if sl_present is None and not pos.sl_conflict:
            flags.append(WatchFlag("missing-SL", True, f"Missing SL: {pos.ticker}"))
        if pos.sl_conflict or pos.tp1_conflict or pos.tp2_conflict:
            bits = []
            if pos.sl_conflict:
                bits.append("SL")
            if pos.tp1_conflict:
                bits.append("TP1")
            if pos.tp2_conflict:
                bits.append("TP2")
            flags.append(
                WatchFlag("lot", True, f"SL/TP inconsistent across lots: {pos.ticker} ({', '.join(bits)})")
            )
        active_sl = pos.active_sl if pos.active_sl is not None else pos.sl
        tp1 = pos.plan_tp1 if pos.plan_tp1 is not None else pos.tp1
        tp2 = pos.plan_tp2 if pos.plan_tp2 is not None else pos.tp2
        if pos.policy_version == CHANDELIER_POLICY_VERSION:
            tp2 = None  # runner managed by trail, not fixed TP2
        comparison_allowed = (
            pos.plan_state not in {"BLOCKED", "CLOSED"}
            and pos.remaining > 0
            and pos.market_valid
        )
        breach_telegram = (
            (not shadow)
            and pos.level_source == "PLAN"
            and pos.plan_state not in {"BLOCKED", "CLOSED"}
        )
        # Journal TP alerts stay Telegram-capable; only cut-loss is PLAN-gated.
        tp_telegram = (not shadow) and pos.plan_state not in {"BLOCKED", "CLOSED"}
        tp1_active = pos.plan_state not in {
            "TP1_EXECUTED",
            "PARTIAL_LEGACY",
            "CLOSED",
        }
        tp2_active = (
            tp2 is not None
            and has_fixed_tp2(pos.policy_version or "atr-r-v2")
            and pos.remaining > 0
            and pos.plan_state != "CLOSED"
        )
        sl_inverted = (
            active_sl is not None
            and active_sl >= pos.entry
            and not pos.trailed
            and pos.plan_state != "TP1_EXECUTED"
        )
        if sl_inverted:
            flags.append(
                WatchFlag(
                    "SL-inverted",
                    not shadow,
                    f"SL inverted / trailing not marked: {pos.ticker} entry={pos.entry:.2f} SL={active_sl:.2f}",
                )
            )
        if (
            comparison_allowed
            and pos.policy_version == CHANDELIER_POLICY_VERSION
            and active_sl is not None
            and pos.last is not None
            and pos.trailed
            and trail_exit_triggered(pos.last, active_sl)
        ):
            flags.append(
                WatchFlag(
                    "TRAIL",
                    False,
                    f"TRAIL_EXIT_CLOSE: {pos.ticker} close={pos.last:.2f} "
                    f"trail={active_sl:.2f}",
                )
            )
        bad_tp: set[str] = set()
        for label, level in (("TP1", tp1), ("TP2", tp2)):
            if level is not None and level <= pos.entry:
                bad_tp.add(label)
        if bad_tp:
            flags.append(
                WatchFlag(
                    "TP-inverted",
                    not shadow,
                    f"TP inverted: {pos.ticker} ({', '.join(sorted(bad_tp))})",
                )
            )
        if (
            pos.last is not None
            and active_sl is not None
            and comparison_allowed
            and not sl_inverted
            and pos.last <= active_sl
        ):
            flags.append(
                WatchFlag(
                    "SL-breach",
                    breach_telegram,
                    f"Close breached SL: {pos.ticker} close={pos.last:.2f} SL={active_sl:.2f}",
                )
            )
        if (
            pos.last is not None
            and tp1 is not None
            and comparison_allowed
            and tp1_active
            and "TP1" not in bad_tp
            and pos.last >= tp1
        ):
            flags.append(
                WatchFlag(
                    "past-TP",
                    tp_telegram,
                    f"Close past TP1: {pos.ticker} close={pos.last:.2f} TP1={tp1:.2f}",
                )
            )
        if (
            pos.last is not None
            and tp2 is not None
            and comparison_allowed
            and tp2_active
            and "TP2" not in bad_tp
            and pos.last >= tp2
        ):
            flags.append(
                WatchFlag(
                    "past-TP",
                    tp_telegram,
                    f"Close past TP2: {pos.ticker} close={pos.last:.2f} TP2={tp2:.2f}",
                )
            )
        touched_sl = (
            comparison_allowed
            and pos.low is not None
            and active_sl is not None
            and pos.low <= active_sl
        )
        touched_tp1 = (
            comparison_allowed
            and tp1_active
            and pos.high is not None
            and tp1 is not None
            and pos.high >= tp1
        )
        touched_tp2 = (
            comparison_allowed
            and tp2_active
            and pos.high is not None
            and tp2 is not None
            and pos.high >= tp2
        )
        if touched_sl and (touched_tp1 or touched_tp2):
            flags.append(
                WatchFlag(
                    "intraday",
                    False,
                    f"AMBIGUOUS_INTRADAY: {pos.ticker} touched SL and TP same session; order/fill not inferred",
                )
            )
        else:
            if touched_sl and pos.last is not None and pos.last > active_sl:
                flags.append(
                    WatchFlag(
                        "intraday",
                        False,
                        f"SL_INTRADAY_TOUCH: {pos.ticker} low={pos.low:.2f} SL={active_sl:.2f}",
                    )
                )
            for label, level, touched in (
                ("TP1", tp1, touched_tp1),
                ("TP2", tp2, touched_tp2),
            ):
                if touched and pos.last is not None and level is not None and pos.last < level:
                    flags.append(
                        WatchFlag(
                            "intraday",
                            False,
                            f"{label}_INTRADAY_TOUCH: {pos.ticker} high={pos.high:.2f} {label}={level:.2f}",
                        )
                    )
        if pos.tm_score is not None and pos.tm_score < 50:
            flags.append(
                WatchFlag(
                    "exit",
                    False,
                    f"T&M <50: {pos.ticker} tm_score={_fmt_score(pos.tm_score)} (same as 22:15 exit rules)",
                )
            )
        mfe: Decimal | None = None
        if (
            pos.risk_per_share is not None
            and pos.risk_per_share > 0
            and pos.market_bars
            and pos.entry_date
        ):
            entry_sess = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                try:
                    entry_sess = datetime.strptime(pos.entry_date.strip(), fmt).date()
                    break
                except ValueError:
                    continue
            if entry_sess is not None:
                mfe = mfe_close_r_from_bars(
                    fill_price=Decimal(str(pos.entry)),
                    risk_per_share=Decimal(str(pos.risk_per_share)),
                    bars=pos.market_bars,
                    entry_session=entry_sess,
                    through_session=session,
                )
        eligible, days = time_stop_eligible(
            entry_date=pos.entry_date,
            session=session,
            mfe_close=mfe,
            latch_path=time_stop_latch_path,
            ticker=pos.ticker,
        )
        if eligible and days is not None:
            latched_ok = True
            if time_stop_latch_path:
                try:
                    mark_time_stop_latched(
                        time_stop_latch_path,
                        latch_key(pos.ticker, pos.entry_date),
                        session=session,
                    )
                except OSError:
                    latched_ok = False
            if latched_ok:
                flags.append(
                    WatchFlag(
                        "exit",
                        False,
                        f"10-day time stop: {pos.ticker} ~{days} trading days since {pos.entry_date} (same as 22:15 exit job)",
                    )
                )
        book = DEFAULT_PORTFOLIO_GBP
        pct = pos.cost_gbp / book if book else 0.0
        limit = kelly_limit(pos.tm_score)
        if pos.kelly_override:
            pass
        elif pct > limit:
            flags.append(
                WatchFlag(
                    "Kelly",
                    False,
                    f"Kelly over cap: {pos.ticker} {pct:.1%} vs cap {limit:.0%} "
                    f"(£{pos.cost_gbp:,.0f} / £{book:,.0f}; tm_score={_fmt_score(pos.tm_score)})",
                )
            )
        if pos.ack:
            flags.append(
                WatchFlag(
                    "ACK",
                    False,
                    f"PARTIAL_EXIT_ACK: {pos.ticker} remaining {pos.remaining} still OPEN",
                )
            )
        pos.notes = []
        if pos.ack:
            pos.notes.append("ACK")
        if pos.kelly_override:
            pos.notes.append("KELLY_OVERRIDE")
        if pos.etf:
            pos.notes.append("ETF")
        if (pos.active_sl if pos.active_sl is not None else pos.sl) is None:
            pos.notes.append("no-SL")
        if pos.last is None:
            pos.notes.append("no-Last")
        if pos.trailed:
            pos.notes.append("TRAIL_SL")
        if pos.proposed_trail is not None:
            tag = "SHADOW_TRAIL" if pos.trail_shadow_legacy else "PROPOSED_TRAIL"
            pos.notes.append(f"{tag}={pos.proposed_trail:.2f}")
        if pos.gap_through_sl:
            pos.notes.append("GAP_THROUGH_SL")
        if pos.plan_rebased:
            pos.notes.append("REBASED")
        if pos.policy_version == CHANDELIER_POLICY_VERSION:
            pos.notes.append("CHANDELIER")
        if pos.plan_state != "JOURNAL_ONLY":
            pos.notes.append(pos.plan_state)

    nav = Decimal(str(DEFAULT_PORTFOLIO_GBP))
    nav_lots = [
        {
            "risk": _stop_risk_gbp(pos, gbp_usd),
            "stress_gap": _stress_gap_gbp(pos, gbp_usd),
        }
        for pos in positions
    ]
    if nav_lots:
        for code in check_nav_gates(nav_lots, nav):
            flags.append(WatchFlag("NAV", False, f"NAV gate: {code}"))

    open_set = {p.ticker for p in positions}
    hit = sorted(t for t in e5 if t in open_set)
    if hit:
        flags.append(
            WatchFlag(
                "E5",
                False,
                "E5 overlap WARN: " + ", ".join(hit) + " (value pack parallel; never blend scores)",
            )
        )
    return flags


def build_final_audit(
    positions: list[OpenPosition],
    flags: list[WatchFlag],
    tm_source: str,
    tm: dict[str, dict],
) -> list[tuple[str, str]]:
    """Scripted gate — not Hermes review-team MoA / Zoe revise."""
    rows: list[tuple[str, str]] = []

    def add(status: str, text: str) -> None:
        rows.append((status, text))

    add("PASS", "Author = position_watch.py generator; no LLM / no review-team MoA / no *-revised.md")
    add(
        "PASS",
        "Three timelines: 22:05 close overall · 21:25 T&M screen · 23:00 this file = journal OPEN book (pack SL ≠ journal SL)",
    )
    if positions:
        book = ", ".join(f"{p.ticker} {p.remaining}" for p in positions)
        bad = [p.ticker for p in positions if p.remaining <= 0]
        add("FAIL" if bad else "PASS", f"remaining = buy−sell(VOID skip): {book}")
    else:
        add("N/A", "remaining: no OPEN positions")
    add("PASS", "VOID skip: " + "/".join(SKIP_STATUS))
    if tm_source == "missing":
        add("N/A", "same-date T&M JSON missing -> Last / tm_score = — / N/A (do not use prior-day latest)")
    else:
        add("PASS", f"same-date T&M join: {tm_source}")
    yahoo_positions = [p for p in positions if p.market_source == "Yahoo"]
    closed_market = [
        p.ticker
        for p in yahoo_positions
        if not p.market_valid and set(p.market_issues) <= {"EXCHANGE_CLOSED"}
    ]
    bad_market = [
        p.ticker
        for p in yahoo_positions
        if not p.market_valid and p.ticker not in closed_market
    ]
    if yahoo_positions:
        if bad_market:
            add(
                "FAIL",
                "Yahoo unadjusted OHLC: session/currency/split/T&M cross-check"
                f" blocked={','.join(bad_market)}",
            )
        elif closed_market:
            add(
                "N/A",
                "Yahoo session closed (weekend/holiday): " + ",".join(closed_market),
            )
        else:
            add("PASS", "Yahoo unadjusted OHLC: session/currency/split/T&M cross-check")
    else:
        leak_last = [p.ticker for p in positions if p.last is not None and p.ticker not in tm]
        add(
            "FAIL" if leak_last else "PASS",
            "Last = same-day T&M JSON price only"
            + (f" leak={','.join(leak_last)}" if leak_last else ""),
        )
    etf_scored = [p.ticker for p in positions if p.etf and p.tm_score is not None]
    add(
        "FAIL" if etf_scored else "PASS",
        "ETF/LSE `.L` tm_score = N/A (no T&M score on ETFs)"
        + (f" leak={','.join(etf_scored)}" if etf_scored else ""),
    )
    add("PASS", "Columns use tm_score only; no value sleeve blend / no bare score")
    add("PASS", "Table omits ATR14 / Risk% columns; sidecar policy = atr-r-v2 / shadow atr-zone-v1")
    add("PASS", "After TP1 keep SL0 / trailed SL; no automatic breakeven")
    e5_flags = [f for f in flags if f.kind == "E5"]
    if e5_flags:
        add("PASS", "E5 overlap WARN only · never blend packs")
    else:
        add("N/A", "E5 overlap: no OPEN overlap with this week width pack")
    add("PASS", "Journal read-only; no orders")
    blocked_plans = [p.ticker for p in positions if p.plan_state == "BLOCKED"]
    missing_plans = [p.ticker for p in positions if "RISK_PLAN_MISSING" in p.plan_issues]
    if blocked_plans:
        add("FAIL", "risk-plan blocked: " + ", ".join(blocked_plans))
    elif missing_plans:
        add("N/A", "risk-plan migration pending: " + ", ".join(missing_plans))
    else:
        add("PASS", "risk-plan event chain / remaining shares reconciled")
    tel_kinds = {f.kind for f in flags if f.telegram}
    file_only = {f.kind for f in flags if not f.telegram}
    add(
        "PASS",
        "Telegram = unique attention flags ("
        + (", ".join(sorted(tel_kinds)) or "silent")
        + "); file-only="
        + (", ".join(sorted(file_only)) or "none"),
    )
    acked = [p for p in positions if p.ack]
    if acked:
        add(
            "PASS",
            "PARTIAL_EXIT_ACK still OPEN: " + ", ".join(f"{p.ticker} {p.remaining}" for p in acked),
        )
    else:
        add("N/A", "PARTIAL_EXIT_ACK: none")
    kelly = [f for f in flags if f.kind == "Kelly"]
    if kelly:
        add("PASS", f"Kelly overlay (remaining×entry / £{DEFAULT_PORTFOLIO_GBP:,.0f}): {len(kelly)} flags")
    else:
        add("N/A", "Kelly overlay: none over cap")
    add("PASS", "Not investment advice")
    return rows


def render_markdown(
    session: date,
    positions: list[OpenPosition],
    flags: list[WatchFlag],
    tm_source: str,
    audit: list[tuple[str, str]] | None = None,
) -> str:
    cost_gbp = sum(p.cost_gbp for p in positions)
    cost_usd = sum(p.cost_usd for p in positions)
    tm_label = tm_source if tm_source != "missing" else "missing"
    lines = [
        f"# OPEN position watch {session.isoformat()}",
        "Not investment advice · journal OPEN book (not T&M screen, not close wrap)",
        "",
        f"Cost at entry: £{cost_gbp:,.2f} / ${cost_usd:,.2f} (remaining × entry)",
        f"Source: trade_journal.csv · T&M JSON {tm_label}",
        f"OPEN: {len(positions)}",
        "",
        "## Open positions",
        "",
        "| Ticker | Shares | Ccy | Entry | Last | Active SL | TP1 | TP2 | Dist SL | Dist TP1 | tm_score | Notes |",
        "|--------|--------|-----|-------|------|-----------|-----|-----|---------|----------|----------|-------|",
    ]
    if not positions:
        lines.append(
            f"| {DASH} | {DASH} | {DASH} | {DASH} | {DASH} | {DASH} | "
            f"{DASH} | {DASH} | {DASH} | {DASH} | N/A | |"
        )
    for pos in positions:
        last = pos.last
        entry_s = _fmt_px(pos.entry, pos.native_ccy)
        last_s = _fmt_px(last, pos.native_ccy) if last is not None else DASH
        sl_level = pos.active_sl if pos.active_sl is not None else pos.sl
        tp1_level = pos.plan_tp1 if pos.plan_tp1 is not None else pos.tp1
        if pos.policy_version == CHANDELIER_POLICY_VERSION:
            tp2_level = None  # runner via trail; do not show journal TP2
        else:
            tp2_level = pos.plan_tp2 if pos.plan_tp2 is not None else pos.tp2
        sl_s = _fmt_px(sl_level, pos.native_ccy)
        tp1_s = _fmt_px(tp1_level, pos.native_ccy)
        tp2_s = _fmt_px(tp2_level, pos.native_ccy) if tp2_level is not None else DASH
        notes = _cell(" ".join(pos.notes))
        if notes == DASH:
            notes = ""
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(pos.ticker),
                    str(pos.remaining),
                    pos.native_ccy,
                    _cell(entry_s),
                    _cell(last_s),
                    _cell(sl_s),
                    _cell(tp1_s),
                    _cell(tp2_s),
                    _cell(_fmt_pct(dist_sl_pct(sl_level, last))),
                    _cell(_fmt_pct(dist_pct(tp1_level, last))),
                    _fmt_score(pos.tm_score),
                    notes,
                ]
            )
            + " |"
        )
    lines.extend(["", "## Attention items", ""])
    if not positions:
        lines.append("No OPEN positions today")
    elif not flags:
        lines.append("No extra attention today (all rule flags empty)")
    else:
        for flag in flags:
            lines.append(f"- **{flag.kind}:** {flag.text}")
    lines.extend(
        [
            "",
            "## Out of scope",
            "",
            "- No orders; do not edit journal",
            "- No value pack / no averaging tm+value",
            "- No ATR14 / Risk% columns; pack SL ≠ journal SL",
            "",
            "## Final audit",
            "",
            "Scripted gate (no review-team MoA / Zoe challenge). FAIL = re-run script; do not LLM-edit numbers.",
            "",
        ]
    )
    for status, text in audit or []:
        lines.append(f"- **{status}:** {text}")
    if audit:
        lines.append("")
    lines.extend(["", COMMENT_STUB.rstrip(), ""])
    return "\n".join(lines)


def _comment_offset(text: str) -> int:
    marker = "\n" + COMMENT_HEADING
    idx = text.find(marker)
    if idx >= 0:
        return idx + 1
    if text.startswith(COMMENT_HEADING):
        return 0
    return -1


def merge_position_comment(generated: str, previous: str) -> str:
    """Keep a filled ## Position comments section when rewriting the same dated file."""
    old_at = _comment_offset(previous)
    new_at = _comment_offset(generated)
    old = previous[old_at:].strip() if old_at >= 0 else ""
    stub = COMMENT_STUB.strip()
    head = generated[:new_at].rstrip() if new_at >= 0 else generated.rstrip()
    section = old if old and old != stub else stub
    return head + "\n\n" + section + "\n"


def telegram_lines(
    flags: list[WatchFlag],
    *,
    session: date | None = None,
    state_path: str | None = None,
) -> list[str]:
    bullets = [flag.text for flag in flags if flag.telegram]
    if not state_path or session is None:
        return bullets
    path = Path(state_path)
    state: dict = {"schema_version": "1", "sent": {}}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            print(
                "[position-watch] alert state unreadable; suppressing Telegram",
                file=sys.stderr,
            )
            return []
        if (
            not isinstance(loaded, dict)
            or loaded.get("schema_version") != "1"
            or not isinstance(loaded.get("sent"), dict)
        ):
            print(
                "[position-watch] alert state invalid; suppressing Telegram",
                file=sys.stderr,
            )
            return []
        state = loaded
    stamp = session.isoformat()
    sent = state["sent"]
    today = set(sent.get(stamp) or [])
    fresh: list[str] = []
    for text in bullets:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in today:
            fresh.append(text)
            today.add(key)
    sent[stamp] = sorted(today)
    cutoff = date.fromordinal(session.toordinal() - 14).isoformat()
    state["sent"] = {key: value for key, value in sent.items() if key >= cutoff}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except OSError as exc:
        print(f"[position-watch] alert state write failed: {exc}", file=sys.stderr)
        try:
            os.unlink(tmp_name)
        except (OSError, UnboundLocalError):
            pass
        return []
    return fresh


def write_layers(markdown: str, session: date, dirs: list[str]) -> list[str]:
    name = f"{session.isoformat()}-position-watch.md"
    written: list[str] = []
    for folder in dirs:
        path = Path(folder)
        path.mkdir(parents=True, exist_ok=True)
        dest = path / name
        body = markdown
        if dest.is_file():
            previous = dest.read_text(encoding="utf-8")
            body = merge_position_comment(markdown, previous)
        dest.write_text(body, encoding="utf-8")
        written.append(str(dest))
    return written


def run(
    journal_path: str,
    session: date,
    tm_dir: str,
    width_dir: str,
    out_dirs: list[str],
    gbp_usd: float = DEFAULT_GBP_USD,
    write: bool = True,
    risk_plan_path: str | None = None,
    market: YahooMarketData | None = None,
    shadow: bool = False,
    alert_state_path: str | None = None,
    time_stop_latch_path: str | None = TIME_STOP_LATCH_DEFAULT,
) -> tuple[int, str, list[str]]:
    try:
        rows = load_journal(journal_path)
    except FileNotFoundError:
        print(f"[position-watch] journal missing: {journal_path}", file=sys.stderr)
        return 2, "", []
    except OSError as exc:
        print(f"[position-watch] journal unreadable: {exc}", file=sys.stderr)
        return 2, "", []
    positions = compute_open_positions(rows, gbp_usd)
    tm, tm_source = load_same_date_tm(tm_dir, session)
    join_tm(positions, tm)
    plans: dict[str, RiskPlan] = {}
    plan_error = ""
    if risk_plan_path:
        try:
            plans = load_plan_store(risk_plan_path)
        except RiskPlanError as exc:
            plan_error = str(exc)
    join_risk_plans(positions, plans, rows)
    if plan_error:
        for pos in positions:
            pos.plan_state = "BLOCKED"
            pos.plan_issues = ["PLAN_STORE_INVALID"]
    join_market(positions, market, session)
    join_trail_proposals(positions, plans, session)
    e5 = load_e5_overlap(width_dir, session)
    flags = build_flags(
        positions,
        session,
        e5,
        shadow=shadow,
        gbp_usd=gbp_usd,
        time_stop_latch_path=time_stop_latch_path,
    )
    audit = build_final_audit(positions, flags, tm_source, tm)
    markdown = render_markdown(session, positions, flags, tm_source, audit)
    written: list[str] = []
    if write:
        written = write_layers(markdown, session, out_dirs)
    bullets = telegram_lines(flags, session=session, state_path=alert_state_path)
    print(
        f"[position-watch] {session.isoformat()} OPEN={len(positions)} "
        f"flags={len(flags)} tm={tm_source} wrote={len(written)}",
        file=sys.stderr,
    )
    if bullets:
        print("\n".join(bullets))
    return 0, markdown, bullets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OPEN position watch (SL/TP)")
    parser.add_argument("--journal", default=JOURNAL_PATH)
    parser.add_argument("--date", default="", help="Session/fire UTC date YYYY-MM-DD")
    parser.add_argument("--tm-dir", default=TM_DIR)
    parser.add_argument("--width-dir", default=WIDTH_DIR)
    parser.add_argument("--gbp-usd", type=float, default=DEFAULT_GBP_USD)
    parser.add_argument("--risk-plans", default=RISK_PLAN_PATH)
    parser.add_argument("--market-cache-dir", default=MARKET_CACHE_DIR)
    parser.add_argument("--alert-state", default=ALERT_STATE_PATH)
    parser.add_argument("--time-stop-latch", default=TIME_STOP_LATCH_DEFAULT)
    parser.add_argument("--no-market", action="store_true")
    parser.add_argument(
        "--shadow",
        action="store_true",
        help="Write full audit but suppress new market/risk-plan Telegram classes",
    )
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--workspace-dir", default=WORKSPACE_DIR)
    parser.add_argument("--shared-dir", default=SHARED_DIR)
    parser.add_argument("--inbox-dir", default=INBOX_DIR)
    args = parser.parse_args(argv)
    if args.date:
        session = date.fromisoformat(args.date)
    else:
        session = datetime.now(timezone.utc).date()
    out_dirs = [args.workspace_dir, args.shared_dir, args.inbox_dir]
    market = None
    if not args.no_market:
        market = YahooMarketData(
            YFinanceTransport(),
            cache=MarketCache(args.market_cache_dir),
        )
    code, _md, _bullets = run(
        journal_path=args.journal,
        session=session,
        tm_dir=args.tm_dir,
        width_dir=args.width_dir,
        out_dirs=out_dirs,
        gbp_usd=args.gbp_usd,
        write=not args.no_write,
        risk_plan_path=args.risk_plans,
        market=market,
        shadow=args.shadow,
        alert_state_path=args.alert_state,
        time_stop_latch_path=args.time_stop_latch,
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
