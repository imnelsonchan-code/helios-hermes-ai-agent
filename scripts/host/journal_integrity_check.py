#!/usr/bin/env python3
"""
Weekly Trade Journal Integrity Check (L3 prevention layer).

Flags structural problems in trade_journal.csv:
  1. OPEN BUY remaining after a CLOSED SELL that was meant to close the full position
  2. SELL rows with empty Shares/Price (poison phantom rows)
  3. BUY/SELL share mismatch where a CLOSED SELL leaves residual shares

Hardening (matches position_watch / risk_plan / exit_signal_checker semantics):
  * VOID-class rows (VOID/VOIDED/CANCELLED/CANCEL/PENDING/REVERSED) are
    excluded from every share total — they used to inflate `total BUY` in
    both directions (spurious POSITION MISMATCH, or masking an ORPHAN).
  * PARTIAL_EXIT_ACK is honored per ROW: only the specific OPEN BUY row
    carrying the un-sold residual is acknowledged. The whole-ticker skip
    (and an ACK mentioned anywhere in Notes, e.g. quoted from a report)
    used to silence check #3 for every lot of that ticker.
  * Only OPEN lots that actually absorbed sells are assessed (matching
    position_watch, which consumes sells against open lots only); an
    untouched OPEN BUY lot is an open position, not a partial-exit residual.
  * Shares accept thousands separators ("1,000"); unparsable non-empty
    shares on an eligible row are flagged instead of silently becoming 0.

Does not modify the journal.
"""
import csv
import os
import sys
from collections import defaultdict

JOURNAL = os.path.expanduser("~/.hermes/trade_journal.csv")
ACK = "PARTIAL_EXIT_ACK"
SKIP_STATUS = ("VOID", "VOIDED", "CANCELLED", "CANCEL", "PENDING", "REVERSED")
EPS = 1e-9


def _to_float(val) -> float | None:
    """Parse journal Shares with thousands separators; None when unclear."""
    text = str(val or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def main():
    if not os.path.exists(JOURNAL):
        print("[OK] Journal does not exist — nothing to check")
        return 0

    with open(JOURNAL, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))

    issues = []
    closed_sell_shares = defaultdict(float)
    buy_total = defaultdict(float)      # all eligible (non-skip) BUY shares
    buy_lots = defaultdict(list)        # ticker -> [[shares, ack, open_status, row_idx], ...]

    for i, r in enumerate(rows, start=2):
        t = r.get("Ticker", "").strip().upper()
        a = r.get("Action", "").strip().upper()
        s = r.get("Status", "").strip().upper()
        notes = r.get("Notes", "") or ""
        if not t:
            continue
        shares_raw = (r.get("Shares") or "").strip()
        if a == "SELL" and (not shares_raw or not (r.get("Price") or "").strip()):
            issues.append(
                f"PHANTOM SELL (row {i}): {t} SELL has empty Shares/Price"
            )
        sh = _to_float(shares_raw)
        if sh is None:
            if shares_raw and s not in SKIP_STATUS and a in ("BUY", "SELL"):
                issues.append(
                    f"UNPARSED SHARES (row {i}): {t} {a} {s} shares='{shares_raw}' — excluded from totals"
                )
            continue  # skip-status or unreadable → excluded everywhere
        if s in SKIP_STATUS:
            continue
        if a == "BUY":
            buy_total[t] += sh
            buy_lots[t].append([sh, ACK in notes and s == "OPEN", s == "OPEN", i])
        elif a == "SELL":
            if s == "CLOSED":
                closed_sell_shares[t] += sh

    # Check #1 — orphan OPEN BUY: closed sells cover all eligible buys while
    # an OPEN BUY lot still claims remaining shares (contamination signature).
    # Gated on open shares > 0: a fully-closed ticker (BUY rows whose Status
    # flipped to CLOSED, sells == buys) is a *normal closed trade*, not drift.
    for t in buy_total:
        open_open = sum(lot[0] for lot in buy_lots[t] if lot[2])
        if (
            closed_sell_shares[t] > 0
            and open_open > 0
            and closed_sell_shares[t] >= buy_total[t]
        ):
            issues.append(
                f"ORPHAN OPEN BUY: {t} has {int(open_open)} OPEN BUY shares but "
                f"CLOSED SELLs ({int(closed_sell_shares[t])}) >= total BUY "
                f"({int(buy_total[t])}) — position should be CLOSED "
                f"(contamination signature)"
            )

    # Check #3 — residual OPEN shares after closed sells consume open lots.
    # Matches position_watch: sells are attributed to OPEN (unclosed) BUY lots
    # only — a CLOSED BUY lot never absorbs sells, so file order cannot change
    # the reported residual. Only lots that actually absorbed sells are
    # assessed; an OPEN lot never touched by any sell is simply an open
    # position, not a "partial exit" residual. An OPEN BUY lot whose Notes
    # contain PARTIAL_EXIT_ACK (that exact row) is owner-verified.
    for t in sorted(buy_lots):
        lots = buy_lots[t]
        if t not in closed_sell_shares or closed_sell_shares[t] <= 0:
            continue
        qty_left = closed_sell_shares[t]
        for lot in lots:
            if not lot[2]:
                continue  # CLOSED lots are never sell targets upstream
            take = min(lot[0], qty_left)
            lot[0] -= take
            lot.append(take)  # lot[4] = shares this lot absorbed
            qty_left -= take
            if qty_left <= EPS:
                break
        unacked_net = sum(
            lot[0]
            for lot in lots
            if lot[2] and not lot[1] and len(lot) > 4 and lot[4] > EPS
        )
        ack_residual = sum(
            lot[0]
            for lot in lots
            if lot[2] and lot[1] and len(lot) > 4 and lot[4] > EPS
        )
        if ack_residual > EPS:
            print(
                f"[OK] {t}: {int(ack_residual)} open shares acknowledged "
                f"(PARTIAL_EXIT_ACK on OPEN BUY row(s) — owner-verified partial)"
            )
        if unacked_net > EPS:
            issues.append(
                f"POSITION MISMATCH: {t} has {int(unacked_net)} un-acked open shares "
                f"left over after CLOSED SELLs of {int(closed_sell_shares[t])} "
                f"(total BUY: {int(buy_total[t])}) — if this is an intentional "
                f"partial exit, stamp PARTIAL_EXIT_ACK on that exact OPEN BUY row; "
                f"if not, check for a voided/phantom sell"
            )

    if not issues:
        print("[OK] Journal integrity OK — no orphan OPEN positions, no phantom rows")
        return 0

    print(f"[WARN] Journal integrity found {len(issues)} issue(s):")
    for x in issues:
        print("  -", x)
    return 1


if __name__ == "__main__":
    sys.exit(main())
