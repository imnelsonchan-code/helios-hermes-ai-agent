#!/usr/bin/env python3
"""
Portfolio P&L Tracker + Backtest vs Live Reconciliation — v1.3 (2026-09-14)

Part 1 — Portfolio P&L:
  1. Reads trade_journal.csv
  2. Skips VOID/VOIDED/CANCELLED/CANCEL/PENDING/REVERSED rows
  3. Cost basis = Shares × native fill price (not the unreliable GBP Amount
     column; USD fills resolve from `Price USD` / `Total USD`, GBP rows
     from `Price`)
  4. GBP-native rows (empty/zero Total USD) convert at GBP->USD; USD-native
     rows get a GBP companion at the same rate. Report shows both together.
     Mixed GBP+USD tickers are flagged; rows without a resolvable price are
     excluded and surfaced, never silently dropped.
  5. Partial sells leave remaining shares OPEN (e.g. TST1.L 32)
  6. Silent when healthy; Telegram on drawdown >8%. Win-rate vs backtest
     only alerts when closed-trade n ≥ 10.

Part 2 — Backtest vs Live Reconciliation:
  7. Compares live signal distribution vs v2.3 bracket baseline
  8. Alerts if a bracket diverges >10% (message labels stale v2.3 baseline
     and inlines diverging brackets). After BRACKET_ALERT_SUPPRESS_AFTER_N
     consecutive fires, Telegram is INFO-only (report lines still print).

Telegram alerts do not set a non-zero exit. After a successful report write
the process exits 0 (signal, not job failure). Exit 1 is reserved for hard
failures (e.g. missing journal file).

Usage:
  python3 portfolio_tracker.py
  python3 portfolio_tracker.py --journal path.csv --gbp-usd 1.31
  python3 portfolio_tracker.py --dry-run
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date

JOURNAL_PATH = os.path.expanduser("~/.hermes/trade_journal.csv")
REPORT_DIR = os.path.expanduser("~/.hermes/shared/reports/renee/trade-journal")
HERMES_CLI = os.path.expanduser("~/.local/bin/hermes")
BACKTEST_BASELINE_WR = 0.493  # v2.3 backtest win rate
BACKTEST_BRACKET_DIST = {
    ">=90": 0.22, "80-89": 0.18, "70-79": 0.20,
    "60-69": 0.17, "50-59": 0.12, "<50": 0.11,
}
DIVERGENCE_THRESHOLD = 0.10
DRAWDOWN_ALERT_THRESHOLD = 0.08
DEFAULT_GBP_USD = 1.31
WR_MIN_CLOSED = 10
SKIP_STATUS = ("VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED")
# After this many consecutive bracket-divergence fires, Telegram is INFO-only.
BRACKET_ALERT_SUPPRESS_AFTER_N = 3
BRACKET_ALERT_STATE_PATH = os.path.expanduser(
    "~/.hermes/state/portfolio_bracket_alert.json"
)
STALE_BASELINE_LABEL = "vs stale v2.3 baseline"


def send_telegram_alert(msg: str) -> bool:
    """Send alert via hermes CLI. Returns True on success."""
    try:
        result = subprocess.run(
            [HERMES_CLI, "send", "--to", "telegram", msg],
            timeout=30, capture_output=True, text=True,
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"[⚠] Telegram alert failed: {exc}", file=sys.stderr)
        return False


def load_journal(journal_path: str) -> list[dict]:
    """Load all rows from trade journal CSV."""
    if not os.path.exists(journal_path):
        print(f"[❌] Journal not found: {journal_path}", file=sys.stderr)
        return []

    rows = []
    with open(journal_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _has_usd(row: dict) -> bool:
    """USD fill indicator: positive `Total USD` or positive `Price USD`.

    Mirrors risk_plan.parse_journal_fill: never treats a GBP amount as USD
    (a `0` in `Total USD` stays GBP-native).
    """
    for col in ("Total USD", "Price USD"):
        raw = (row.get(col) or "").strip()
        if raw:
            val = _to_float(raw)
            if val:
                return True
    return False


def _row_price_ccy(row: dict):
    """Resolve ``(price, currency)`` for one journal fill row.

    USD fills take the native per-share price: `Price USD` if present, else
    `Total USD / Shares`. The stale GBP `Price` column must never fabricate a
    USD fill price — position_watch and risk_plan already resolve USD fills
    this way (live journals can carry a stale `Price` on USD rows).
    GBP-native rows (no positive `Total USD` / `Price USD`) use `Price`.

    Returns ``(None, ccy)`` when no price can be resolved; the caller must
    exclude such rows and surface the exclusion, never skip silently.
    """
    shares = _to_float(row.get("Shares")) or 0.0
    total_raw = (row.get("Total USD") or "").strip()
    usd_raw = (row.get("Price USD") or "").strip()
    total_usd = _to_float(total_raw) if total_raw else 0.0
    if (total_usd and total_usd > 0) or usd_raw:
        if usd_raw:
            px = _to_float(usd_raw)
            if px is not None and px > 0:
                return px, "USD"
            # `Price USD` present but unusable ("0"/junk): fall back to
            # Total USD / Shares like position_watch._native_price before
            # declaring the row unresolved.
            if shares > 0 and total_usd > 0:
                return total_usd / shares, "USD"
            return None, "USD"
        if shares > 0:
            return total_usd / shares, "USD"
        return None, "USD"
    px = _to_float(row.get("Price"))
    if px is None or px <= 0:
        return None, "GBP"
    return px, "GBP"


def _native_ccy(buy_rows: list[dict], sell_rows: list[dict]) -> str:
    for row in buy_rows + sell_rows:
        if _has_usd(row):
            return "USD"
    return "GBP"


def compute_pnl(rows: list[dict], gbp_usd_rate: float = DEFAULT_GBP_USD) -> dict:
    """Per-ticker realized P&L with USD and GBP companions.

    VOID-class Status rows are excluded. Remaining shares (buy − sell) stay
    OPEN. Notionals are Shares × native fill price: USD rows resolve from
    `Price USD` or `Total USD`/`Shares` (the stale GBP `Price` column is never
    used to price a USD fill — position_watch and risk_plan resolve USD fills
    the same way), GBP rows from `Price`. GBP Amount is never summed.
    A ticker with both GBP and USD fills converts through one FX rate and is
    flagged ``native_ccy="MIXED"`` / ``mixed_ccy: true``; rows with no
    resolvable price are excluded and counted in ``unresolved_rows`` (never
    silently dropped). Mixed books require ``gbp_usd_rate > 0``.
    """
    buys = defaultdict(list)
    sells = defaultdict(list)

    for row in rows:
        ticker = row.get("Ticker", "").strip().upper()
        action = row.get("Action", "").strip().upper()
        status = row.get("Status", "").strip().upper()
        if not ticker:
            continue
        if status in SKIP_STATUS:
            continue
        if action == "BUY":
            buys[ticker].append(row)
        elif action == "SELL":
            sells[ticker].append(row)

    pnl_by_ticker = {}
    for ticker in sorted(set(buys) | set(sells)):
        buy_rows = buys.get(ticker, [])
        sell_rows = sells.get(ticker, [])
        buy_shares = 0.0
        buy_val = {"GBP": 0.0, "USD": 0.0}
        buy_ccys = set()
        unresolved_buys = 0
        for b in buy_rows:
            sh = _to_float(b.get("Shares")) or 0.0
            px, ccy = _row_price_ccy(b)
            if px is None:
                unresolved_buys += 1
                continue
            buy_shares += sh
            buy_val[ccy] += sh * px
            buy_ccys.add(ccy)
        buy_native = 0.0

        sell_shares = 0.0
        sell_val = {"GBP": 0.0, "USD": 0.0}
        sell_ccys = set()
        unresolved_sells = 0
        for s in sell_rows:
            sh = _to_float(s.get("Shares")) or 0.0
            px, ccy = _row_price_ccy(s)
            if px is None:
                unresolved_sells += 1
                continue
            sell_shares += sh
            sell_val[ccy] += sh * px
            sell_ccys.add(ccy)

        ccys = buy_ccys | sell_ccys
        unresolved_rows = unresolved_buys + unresolved_sells
        mixed_ccy = len(ccys) > 1

        rate = gbp_usd_rate if (gbp_usd_rate and gbp_usd_rate > 0) else None
        if not rate:
            # A zero/invalid rate cannot convert GBP<->USD; legacy behavior
            # silently produced 0.0 companions. Fine for a single-currency
            # book with no cross-currency rows — but mixed books must fail.
            if mixed_ccy:
                raise ValueError(
                    f"{ticker}: mixed-currency fills require gbp_usd_rate > 0"
                )
            rate = DEFAULT_GBP_USD

        # Aggregate into one native space.
        if mixed_ccy:
            native = "MIXED"
            buy_val_usd_space = buy_val["USD"] + buy_val["GBP"] * rate
            sell_val_usd_space = sell_val["USD"] + sell_val["GBP"] * rate
            buy_native = buy_val_usd_space
            sell_native = sell_val_usd_space
        else:
            native = next(iter(ccys)) if ccys else "GBP"
            buy_native = buy_val[native]
            sell_native = sell_val[native]
        entry = buy_native / buy_shares if buy_shares else 0.0

        remaining = buy_shares - sell_shares
        realized_cost = sell_shares * entry
        realized_pnl_native = sell_native - realized_cost
        status = "CLOSED" if remaining <= 0 else "OPEN"

        # MIXED positions were unified into USD space above.
        pnl_space = "USD" if native == "MIXED" else native
        if pnl_space == "GBP":
            buy_gbp = realized_cost
            sell_gbp = sell_native
            pnl_gbp = realized_pnl_native
            buy_usd = buy_gbp * gbp_usd_rate
            sell_usd = sell_gbp * gbp_usd_rate
            pnl_usd = pnl_gbp * gbp_usd_rate
        else:
            buy_usd = realized_cost
            sell_usd = sell_native
            pnl_usd = realized_pnl_native
            buy_gbp = buy_usd / gbp_usd_rate if gbp_usd_rate else 0.0
            sell_gbp = sell_usd / gbp_usd_rate if gbp_usd_rate else 0.0
            pnl_gbp = pnl_usd / gbp_usd_rate if gbp_usd_rate else 0.0

        pnl_pct = (pnl_usd / buy_usd * 100) if buy_usd else 0.0

        pnl_by_ticker[ticker] = {
            "ticker": ticker,
            "buy_shares": int(round(buy_shares)),
            "sell_shares": int(round(sell_shares)),
            "remaining_shares": int(round(remaining)) if remaining > 0 else 0,
            "realized_shares": int(round(sell_shares)),
            "native_ccy": native,
            "mixed_ccy": mixed_ccy,
            "unresolved_rows": unresolved_rows,
            "buy_usd": round(buy_usd, 2),
            "sell_usd": round(sell_usd, 2),
            "pnl_usd": round(pnl_usd, 2),
            "buy_gbp": round(buy_gbp, 2),
            "sell_gbp": round(sell_gbp, 2),
            "pnl_gbp": round(pnl_gbp, 2),
            "pnl_pct": round(pnl_pct, 2),
            "status": status,
            "entry_price": round(entry, 4),
        }

    return pnl_by_ticker


def compute_portfolio_summary(pnl_by_ticker: dict) -> dict:
    """Portfolio-level realized stats. Win rate uses fully CLOSED tickers only."""
    total_invested_usd = sum(v["buy_usd"] for v in pnl_by_ticker.values())
    total_invested_gbp = sum(v["buy_gbp"] for v in pnl_by_ticker.values())
    total_pnl_usd = sum(v["pnl_usd"] for v in pnl_by_ticker.values())
    total_pnl_gbp = sum(v["pnl_gbp"] for v in pnl_by_ticker.values())
    closed_trades = [v for v in pnl_by_ticker.values() if v["status"] == "CLOSED"]
    open_trades = [v for v in pnl_by_ticker.values() if v["status"] == "OPEN"]

    win_count = sum(1 for v in closed_trades if v["pnl_usd"] > 0)
    loss_count = sum(1 for v in closed_trades if v["pnl_usd"] < 0)
    win_rate = round(win_count / len(closed_trades) * 100, 1) if closed_trades else 0

    return {
        "total_invested_usd": round(total_invested_usd, 2),
        "total_invested_gbp": round(total_invested_gbp, 2),
        "total_pnl_usd": round(total_pnl_usd, 2),
        "total_pnl_gbp": round(total_pnl_gbp, 2),
        "total_pnl_pct": round((total_pnl_usd / total_invested_usd * 100) if total_invested_usd else 0, 2),
        "total_closed_trades": len(closed_trades),
        "total_open_trades": len(open_trades),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
    }


def compute_drawdown(pnl_by_ticker: dict) -> float:
    """Peak-to-trough proxy: current realized P&L / invested (negative = drawdown)."""
    total_invested = sum(v["buy_usd"] for v in pnl_by_ticker.values())
    if not total_invested:
        return 0.0
    pnl_pct = sum(v["pnl_usd"] for v in pnl_by_ticker.values()) / total_invested
    return min(pnl_pct, 0.0)


def fetch_spy_benchmark(start_date: str = "2026-06-30") -> dict:
    """Fetch SPY returns for benchmark comparison. Best-effort, no hard dep."""
    try:
        import yfinance as yf
        spy = yf.Ticker("SPY")
        hist = spy.history(start=start_date)
        if hist.empty:
            return {"error": "No SPY data", "spy_return_pct": 0, "spy_start": 0, "spy_end": 0}
        start_price = float(hist["Close"].iloc[0])
        end_price = float(hist["Close"].iloc[-1])
        spy_return = (end_price - start_price) / start_price * 100
        return {
            "spy_start": round(start_price, 2),
            "spy_end": round(end_price, 2),
            "spy_return_pct": round(spy_return, 2),
            "error": None,
        }
    except Exception as exc:
        return {"error": str(exc), "spy_return_pct": 0, "spy_start": 0, "spy_end": 0}


def fetch_live_bracket_distribution() -> dict:
    """Fetch live bracket distribution from Renee's latest weekly indicator data."""
    weekly_dir = os.path.expanduser("~/.hermes/shared/reports/renee/weekly")
    if not os.path.isdir(weekly_dir):
        return {}

    json_files = sorted(
        [f for f in os.listdir(weekly_dir) if f.endswith("-indicator-data.json")],
        reverse=True,
    )
    if not json_files:
        return {}

    latest_path = os.path.join(weekly_dir, json_files[0])
    try:
        with open(latest_path) as f:
            data = json.load(f)
    except Exception:
        return {}

    signals = data.get("signals_by_bracket", {})
    total = data.get("total_scanned", 1) or 1
    return {k: v / total for k, v in signals.items()}


def reconcile_brackets(live_dist: dict, baseline: dict) -> list[str]:
    """Compare live vs backtest bracket distribution. Returns list of alerts."""
    alerts = []
    for bracket, baseline_pct in baseline.items():
        live_pct = live_dist.get(bracket, 0)
        divergence = abs(live_pct - baseline_pct)
        if divergence > DIVERGENCE_THRESHOLD:
            direction = "↑" if live_pct > baseline_pct else "↓"
            alerts.append(
                f"  {bracket}: live={live_pct:.1%} vs backtest={baseline_pct:.1%} "
                f"({direction}{divergence:.1%})"
            )
    return alerts


def build_bracket_divergence_alert(bracket_alerts: list[str]) -> str:
    """Header + stale-baseline label + inline diverging bracket lines."""
    header = (
        f"⚠️ Backtest bracket divergence detected! ({STALE_BASELINE_LABEL})"
    )
    body = "\n".join(line.rstrip() for line in bracket_alerts)
    return f"{header}\n{body}" if body else header


def load_bracket_alert_streak(path: str | None = None) -> int:
    """Return consecutive bracket-divergence fire count from state file."""
    state_path = path or BRACKET_ALERT_STATE_PATH
    try:
        with open(state_path) as f:
            data = json.load(f)
        return max(0, int(data.get("consecutive_fires", 0)))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 0


def save_bracket_alert_streak(streak: int, path: str | None = None) -> None:
    """Persist consecutive bracket-divergence fire count."""
    state_path = path or BRACKET_ALERT_STATE_PATH
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    payload = {
        "consecutive_fires": max(0, int(streak)),
        "updated": date.today().isoformat(),
    }
    with open(state_path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def bracket_telegram_suppressed(
    prior_streak: int,
    suppress_after_n: int = BRACKET_ALERT_SUPPRESS_AFTER_N,
) -> bool:
    """True when last N consecutive fires already alerted (downgrade to INFO)."""
    return prior_streak >= suppress_after_n


def _pair(usd: float, gbp: float, signed: bool = False) -> str:
    if signed:
        return f"${usd:+,.2f} (£{gbp:+,.2f})"
    return f"${usd:,.2f} (£{gbp:,.2f})"


def write_report(
    pnl: dict,
    summary: dict,
    spy: dict | None = None,
    bracket_alerts: list[str] | None = None,
    gbp_usd_rate: float = DEFAULT_GBP_USD,
) -> str:
    """Generate markdown report with USD and GBP together; write CSV + md."""
    spy = spy or {"error": "no data", "spy_return_pct": 0, "spy_start": 0, "spy_end": 0}
    bracket_alerts = bracket_alerts or []
    today = date.today().isoformat()
    os.makedirs(REPORT_DIR, exist_ok=True)
    lines = []

    lines.append(f"# Portfolio P&L Report — {today}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | USD | GBP |")
    lines.append("|:-------|----:|----:|")
    lines.append(
        f"| Realized invested | ${summary['total_invested_usd']:,.2f} | "
        f"£{summary['total_invested_gbp']:,.2f} |"
    )
    lines.append(
        f"| Realized P&L | ${summary['total_pnl_usd']:+,.2f} | "
        f"£{summary['total_pnl_gbp']:+,.2f} |"
    )
    lines.append(f"| Total return | {summary['total_pnl_pct']:+.2f}% | {summary['total_pnl_pct']:+.2f}% |")
    lines.append(f"| Closed trades | {summary['total_closed_trades']} | |")
    lines.append(f"| Open trades | {summary['total_open_trades']} | |")
    lines.append(
        f"| Win rate | {summary['win_rate']:.1f}% "
        f"({summary['win_count']}W / {summary['loss_count']}L) | |"
    )

    if spy.get("error") is None and spy.get("spy_return_pct"):
        alpha = summary["total_pnl_pct"] - spy["spy_return_pct"]
        lines.append(
            f"| SPY benchmark | {spy['spy_return_pct']:+.2f}% "
            f"(${spy['spy_start']:.2f} -> ${spy['spy_end']:.2f}) | |"
        )
        lines.append(f"| Alpha vs SPY | {alpha:+.2f}% | |")
    else:
        lines.append(f"| SPY benchmark | N/A ({spy.get('error', 'no data')}) | |")

    lines.append("")
    lines.append("## Positions (realized)")
    lines.append("")
    lines.append("| Ticker | Status | Realized sh | Buy | Sell | P&L | P&L % |")
    lines.append("|:-------|:-------|------------:|:----|:-----|:----|------:|")
    for ticker, data in sorted(pnl.items()):
        if data["status"] == "OPEN":
            status_txt = f"OPEN {data['remaining_shares']}"
        else:
            status_txt = "CLOSED"
        lines.append(
            f"| {ticker} | {status_txt} | {data['sell_shares']} | "
            f"{_pair(data['buy_usd'], data['buy_gbp'])} | "
            f"{_pair(data['sell_usd'], data['sell_gbp'])} | "
            f"{_pair(data['pnl_usd'], data['pnl_gbp'], signed=True)} | "
            f"{data['pnl_pct']:+.2f}% |"
        )
    lines.append("")

    open_positions = [v for v in pnl.values() if v["status"] == "OPEN" and v["remaining_shares"] > 0]
    if open_positions:
        lines.append("## Open remainder")
        lines.append("")
        lines.append("| Ticker | Shares | Entry | Open cost |")
        lines.append("|:-------|-------:|------:|----------:|")
        for op in open_positions:
            rem = op["remaining_shares"]
            entry = op["entry_price"]
            if op["native_ccy"] == "GBP":
                cost_gbp = rem * entry
                cost_usd = cost_gbp * gbp_usd_rate
                lines.append(
                    f"| {op['ticker']} | {rem} | £{entry:,.2f} | "
                    f"${cost_usd:,.2f} (£{cost_gbp:,.2f}) |"
                )
            else:
                cost_usd = rem * entry
                cost_gbp = cost_usd / gbp_usd_rate if gbp_usd_rate else 0.0
                lines.append(
                    f"| {op['ticker']} | {rem} | ${entry:,.2f} | "
                    f"${cost_usd:,.2f} (£{cost_gbp:,.2f}) |"
                )
        lines.append("")

    data_quality = [
        (t, d) for t, d in sorted(pnl.items())
        if d.get("mixed_ccy") or d.get("unresolved_rows")
    ]
    if data_quality:
        lines.append("## Data-quality warnings")
        lines.append("")
        for t, d in data_quality:
            if d.get("mixed_ccy"):
                lines.append(
                    f"- ⚠️ {t}: mixed GBP/USD fills — GBP legs converted at "
                    f"{gbp_usd_rate:.4f}; entry is an FX-converted average."
                )
            if d.get("unresolved_rows"):
                lines.append(
                    f"- ⚠️ {t}: {d['unresolved_rows']} journal row(s) had no "
                    f"resolvable price and were excluded from P&L."
                )
        lines.append("")

    lines.append("## Backtest vs Live Reconciliation")
    lines.append("")
    lines.append(f"**Backtest baseline:** v2.3 win rate = {BACKTEST_BASELINE_WR:.1%}")
    lines.append(f"**Live win rate:** {summary['win_rate']:.1f}% (closed n={summary['total_closed_trades']})")

    wr_divergence = (
        abs(summary["win_rate"] / 100 - BACKTEST_BASELINE_WR)
        if summary["total_closed_trades"] > 0
        else 0
    )
    if summary["total_closed_trades"] < WR_MIN_CLOSED:
        lines.append(
            f"  ℹ️ Win-rate vs backtest skipped (need ≥{WR_MIN_CLOSED} closed trades)."
        )
    elif wr_divergence > DIVERGENCE_THRESHOLD:
        lines.append(
            f"  ⚠️ Win rate divergence: {wr_divergence:.1%} > {DIVERGENCE_THRESHOLD:.0%} threshold!"
        )
    else:
        lines.append(f"  ✅ Win rate within {DIVERGENCE_THRESHOLD:.0%} tolerance")

    lines.append("")
    if bracket_alerts:
        lines.append("### Bracket Distribution Alerts")
        lines.append("")
        for alert in bracket_alerts:
            lines.append(f"- ⚠️ {alert}")
    else:
        lines.append("### Bracket Distribution")
        lines.append("")
        lines.append("✅ All brackets within 10% tolerance of backtest baseline")
    lines.append("")
    lines.append(
        f"> FX: USD-native P&L converted to GBP (and GBP-native to USD) at "
        f"**{gbp_usd_rate:.4f}**. Cost basis is Shares × native fill price "
        f"(USD rows: `Price USD` / `Total USD`; GBP rows: `Price`); journal "
        f"`GBP Amount` is not used."
    )
    lines.append("")

    csv_path = os.path.join(REPORT_DIR, f"portfolio-pnl-{today}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Ticker", "Status", "Buy Shares", "Sell Shares", "Remaining",
            "Native", "Buy USD", "Buy GBP", "Sell USD", "Sell GBP",
            "P&L USD", "P&L GBP", "P&L %",
        ])
        for ticker, data in sorted(pnl.items()):
            writer.writerow([
                ticker, data["status"], data["buy_shares"], data["sell_shares"],
                data["remaining_shares"], data["native_ccy"],
                data["buy_usd"], data["buy_gbp"], data["sell_usd"], data["sell_gbp"],
                data["pnl_usd"], data["pnl_gbp"], data["pnl_pct"],
            ])
    lines.append(f"CSV saved: `{csv_path}`")

    md_path = os.path.join(REPORT_DIR, f"portfolio-pnl-{today}.md")
    report_text = "\n".join(lines) + "\n"
    with open(md_path, "w") as f:
        f.write(report_text)

    return report_text


def main():
    parser = argparse.ArgumentParser(
        description="Portfolio P&L Tracker + Backtest vs Live Reconciliation"
    )
    parser.add_argument("--journal", default=JOURNAL_PATH, help="Trade journal CSV path")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no alert")
    parser.add_argument(
        "--gbp-usd", type=float, default=DEFAULT_GBP_USD,
        help=f"GBP->USD rate (default: {DEFAULT_GBP_USD})",
    )
    args = parser.parse_args()

    alerts = []

    if not os.path.isfile(args.journal):
        print(f"[❌] Journal not found: {args.journal}", file=sys.stderr)
        return 1

    rows = load_journal(args.journal)
    if not rows:
        print("[⚠] No journal data — nothing to track", file=sys.stderr)
        return 0

    try:
        pnl = compute_pnl(rows, gbp_usd_rate=args.gbp_usd)
    except ValueError as exc:
        # e.g. mixed-currency fills with --gbp-usd 0: a clean CLI error beats
        # a raw traceback (a zero rate stays valid for single-ccy books).
        print(f"[❌] {exc}", file=sys.stderr)
        return 1
    summary = compute_portfolio_summary(pnl)
    spy = fetch_spy_benchmark()

    live_bracket_dist = fetch_live_bracket_distribution()
    bracket_alerts = (
        reconcile_brackets(live_bracket_dist, BACKTEST_BRACKET_DIST)
        if live_bracket_dist else []
    )
    bracket_alert_msg = ""
    suppress_bracket_telegram = False
    if bracket_alerts:
        bracket_alert_msg = build_bracket_divergence_alert(bracket_alerts)
        prior_streak = load_bracket_alert_streak()
        suppress_bracket_telegram = bracket_telegram_suppressed(prior_streak)
        if not suppress_bracket_telegram:
            alerts.append(bracket_alert_msg)
        if not args.dry_run:
            save_bracket_alert_streak(prior_streak + 1)
    elif not args.dry_run:
        save_bracket_alert_streak(0)

    dd = compute_drawdown(pnl)
    if dd < -DRAWDOWN_ALERT_THRESHOLD:
        alerts.append(
            f"🚨 PORTFOLIO DRAWDOWN: {dd:.1%} (threshold: {DRAWDOWN_ALERT_THRESHOLD:.0%})"
        )

    for t, d in sorted(pnl.items()):
        if d.get("mixed_ccy"):
            alerts.append(f"⚠️ {t}: mixed GBP/USD fills — P&L uses FX-converted entries at {args.gbp_usd}")
        if d.get("unresolved_rows"):
            alerts.append(f"⚠️ {t}: {d['unresolved_rows']} journal row(s) without a resolvable price (excluded from P&L)")

    if summary["total_closed_trades"] >= WR_MIN_CLOSED:
        wr_divergence = abs(summary["win_rate"] / 100 - BACKTEST_BASELINE_WR)
        if wr_divergence > DIVERGENCE_THRESHOLD:
            alerts.append(
                f"⚠️ Win rate divergence: live={summary['win_rate']:.1f}% vs "
                f"backtest={BACKTEST_BASELINE_WR:.1%}"
            )

    report = write_report(
        pnl, summary, spy=spy, bracket_alerts=bracket_alerts,
        gbp_usd_rate=args.gbp_usd,
    )
    print(report, file=sys.stderr)

    if suppress_bracket_telegram and bracket_alert_msg:
        print(
            f"[INFO] Bracket divergence suppressed "
            f"({BRACKET_ALERT_SUPPRESS_AFTER_N} consecutive fires already; "
            f"{STALE_BASELINE_LABEL})"
        )
        print(bracket_alert_msg)

    if alerts and not args.dry_run:
        alert_msg = "📊 Portfolio Tracker Alert:\n" + "\n".join(alerts)
        send_telegram_alert(alert_msg)
        print(alert_msg)
        print("[portfolio_tracker] alerts sent; exit 0 (signal, not job failure)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
