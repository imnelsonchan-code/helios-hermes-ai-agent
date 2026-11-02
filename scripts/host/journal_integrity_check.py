#!/usr/bin/env python3
"""
Weekly Trade Journal Integrity Check (L3 prevention layer).

Flags structural problems in trade_journal.csv:
  1. OPEN BUY remaining after a CLOSED SELL that was meant to close the full position
  2. SELL rows with empty Shares/Price (poison phantom rows)
  3. BUY/SELL share mismatch where a CLOSED SELL leaves residual shares

Check #3 is skipped for a ticker when an OPEN BUY Notes field contains
PARTIAL_EXIT_ACK (owner-verified partial). Does not modify the journal.
"""
import csv
import os
import sys
from collections import defaultdict

JOURNAL = os.path.expanduser("~/.hermes/trade_journal.csv")
ACK = "PARTIAL_EXIT_ACK"


def main():
    if not os.path.exists(JOURNAL):
        print("[OK] Journal does not exist — nothing to check")
        return 0

    with open(JOURNAL, newline="") as f:
        rows = list(csv.DictReader(f))

    issues = []
    open_buy_shares = defaultdict(int)
    closed_sell_shares = defaultdict(int)
    is_position_open = defaultdict(bool)
    acked = set()

    for r in rows:
        t = r.get("Ticker", "").strip().upper()
        a = r.get("Action", "").strip().upper()
        s = r.get("Status", "").strip().upper()
        notes = r.get("Notes", "") or ""
        try:
            sh = int(float(r.get("Shares", "") or 0))
        except ValueError:
            sh = 0
        if a == "BUY":
            if s == "OPEN":
                open_buy_shares[t] += sh
                is_position_open[t] = True
                if ACK in notes:
                    acked.add(t)
        elif a == "SELL" and s == "CLOSED":
            closed_sell_shares[t] += sh

    all_buy_shares = defaultdict(int)
    for r in rows:
        t = r.get("Ticker", "").strip().upper()
        if r.get("Action", "").strip().upper() == "BUY":
            try:
                all_buy_shares[t] += int(float(r.get("Shares", "") or 0))
            except ValueError:
                pass

    for t in open_buy_shares:
        total_buy = all_buy_shares.get(t, 0)
        total_closed_sell = closed_sell_shares.get(t, 0)
        if total_closed_sell >= total_buy and total_closed_sell > 0:
            issues.append(
                f"ORPHAN OPEN BUY: {t} has {open_buy_shares[t]} OPEN BUY shares but "
                f"CLOSED SELLs ({total_closed_sell}) >= total BUY ({total_buy}) — "
                f"position should be CLOSED (contamination signature)"
            )

    for i, r in enumerate(rows, start=2):
        if r.get("Action", "").strip().upper() == "SELL":
            if not r.get("Shares", "").strip() or not r.get("Price", "").strip():
                issues.append(
                    f"PHANTOM SELL (row {i}): {r.get('Ticker')} SELL has empty Shares/Price"
                )

    for t in is_position_open:
        if t in acked:
            print(f"[OK] {t} check #3 skipped ({ACK} on OPEN BUY)")
            continue
        net = all_buy_shares.get(t, 0) - closed_sell_shares.get(t, 0)
        if net > 0 and closed_sell_shares.get(t, 0) > 0:
            issues.append(
                f"POSITION MISMATCH: {t} has {net} open shares after "
                f"CLOSED SELLs of {closed_sell_shares[t]} (total BUY: {all_buy_shares[t]}) "
                f" — verify this is an intentional partial exit, not a residual from a "
                f"voided/phantom sell"
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
