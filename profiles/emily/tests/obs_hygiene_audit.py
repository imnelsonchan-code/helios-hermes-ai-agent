#!/usr/bin/env python3
"""Observation-only hygiene score for obs backtest fixtures (no PnL)."""
from __future__ import annotations

import re
import sys


def score_fixture(path: str) -> tuple[list[tuple[str, bool, str]], bool]:
    text = open(path, encoding="utf-8").read()
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    def first_table_after(heading_re: str):
        m = re.search(heading_re, text, re.M | re.I)
        if not m:
            return None
        rest = text[m.end() :]
        rows: list[str] = []
        started = False
        for line in rest.splitlines():
            if line.strip().startswith("|"):
                started = True
                rows.append(line)
                continue
            if started:
                break
        return rows or None

    add("has Session summary", bool(re.search(r"^## Session summary", text, re.M)))
    add("has commodity_regime", "commodity_regime" in text)
    add("has Trade map", bool(re.search(r"^## Trade map", text, re.M)))
    add(
        "has next-day prints block",
        bool(re.search(r"(?i)next[- ]day prints|## Next-day", text)),
    )
    add(
        "declares observation only / no PnL",
        bool(re.search(r"(?i)observation only|no PnL|hygiene", text)),
    )

    rows = first_table_after(r"^## Trade map")
    bare_buy = False
    dir_in_signal = False
    full_levels = 0
    basis_without_forecast = False
    if rows and len(rows) >= 2:
        headers = [c.strip() for c in rows[0].strip("|").split("|")]
        data = rows[2:] if re.match(r"^\|?\s*[-:]+", rows[1]) else rows[1:]
        si = headers.index("Signal") if "Signal" in headers else -1
        bi = next((i for i, h in enumerate(headers) if h.startswith("Basis")), -1)
        ei = next((i for i, h in enumerate(headers) if "Obs entry" in h), -1)
        sli = next((i for i, h in enumerate(headers) if "cut" in h.lower()), -1)
        tpi = next(
            (i for i, h in enumerate(headers) if "Obs TP" in h or h.strip() == "Obs TP"),
            -1,
        )
        empty = {"", "—", "-", "n/a", "–"}

        for r in data:
            cells = [c.strip() for c in r.strip("|").split("|")]

            def filled(i: int) -> bool:
                return i >= 0 and i < len(cells) and cells[i] not in empty

            if si >= 0 and si < len(cells):
                sig = cells[si].strip("`")
                if re.fullmatch(r"BUY", sig):
                    bare_buy = True
                if re.fullmatch(r"DIR_[A-Z_]+", sig):
                    dir_in_signal = True
            has_full_levels = filled(ei) and filled(sli) and filled(tpi)
            if has_full_levels:
                full_levels += 1
                if bi >= 0 and bi < len(cells):
                    basis = cells[bi]
                    if not re.search(r"(?i)forecast|scenario|\b[Ee]st\b", basis):
                        basis_without_forecast = True

    add("no bare BUY in Signal", not bare_buy)
    add("no DIR_* in Signal", not dir_in_signal)
    add("Daily ≤3 full Obs levels", full_levels <= 3, f"full_levels={full_levels}")
    add(
        "Basis cites Forecast/Scenario/Est when levels filled",
        not basis_without_forecast,
    )
    pnl_col = bool(
        re.search(r"(?i)\|\s*(PnL|P&L|ROI|Return %|Profit)\s*\|", text)
    ) or bool(re.search(r"(?i)^(PnL|P&L|ROI)\s*:", text, re.M))
    add("no PnL / return columns", not pnl_col)

    failed = [c for c in checks if not c[1]]
    return checks, not failed


def bad_fixture_has_violation(path: str) -> bool:
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^## Trade map", text, re.M)
    if not m:
        return False
    rows: list[str] = []
    started = False
    for line in text[m.end() :].splitlines():
        if line.strip().startswith("|"):
            started = True
            rows.append(line)
            continue
        if started:
            break
    if not rows:
        return False
    headers = [c.strip() for c in rows[0].strip("|").split("|")]
    data = (
        rows[2:]
        if len(rows) > 1 and re.match(r"^\|?\s*[-:]+", rows[1])
        else rows[1:]
    )
    si = headers.index("Signal") if "Signal" in headers else -1
    for r in data:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if si >= 0 and si < len(cells):
            sig = cells[si].strip("`")
            if re.fullmatch(r"BUY", sig) or re.fullmatch(r"DIR_[A-Z_]+", sig):
                return True
    return False


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: obs_hygiene_audit.py good|bad PATH", file=sys.stderr)
        return 2
    mode, path = sys.argv[1], sys.argv[2]
    if mode == "good":
        checks, ok = score_fixture(path)
        print("Obs backtest hygiene score:")
        for name, passed, detail in checks:
            mark = "PASS" if passed else "FAIL"
            extra = f" ({detail})" if detail else ""
            print(f" {mark} {name}{extra}")
        score = sum(1 for _, passed, _ in checks if passed)
        print(f"Score: {score}/{len(checks)} (hygiene only · no PnL)")
        return 0 if ok else 1
    if mode == "bad":
        return 0 if bad_fixture_has_violation(path) else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
