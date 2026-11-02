#!/usr/bin/env python3
"""Deterministic Desk Pack daily train completion check.

Exit 0 only when same-day Alice dual portal revised files exist (size>0) and
exit evidence is present. Primary exit evidence:
inbox/desk-pack-exit/{date}-tm-exits.md (or {date}*tm-exits* nonzero in that
dir) — written by daily_tm_with_exits.sh. Fallback: same dir only
{date}*-tm-exits.md. Does NOT accept position-watch (23:00 risk train).

Fan-out-only failure (market-close missing) -> exit 2.
Does not touch model config / provider settings. No network.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _gate_home() -> Path:
    return Path(os.environ.get("GATE_HOME", Path.home()))


def _inbox() -> Path:
    override = os.environ.get("REPORTS_INBOX")
    if override:
        return Path(override)
    return _gate_home() / "workspace" / "reports" / "inbox"


def _hermes_home() -> Path:
    override = os.environ.get("HERMES_HOME")
    if override:
        return Path(override)
    return _gate_home() / ".hermes"


def _first_nonzero(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def _glob_nonzero(directory: Path, pattern: str) -> Path | None:
    if not directory.is_dir():
        return None
    return _first_nonzero(sorted(directory.glob(pattern)))


def _exit_evidence(inbox: Path, date: str) -> Path | None:
    """Primary: desk-pack-exit/{date}-tm-exits.md or {date}*tm-exits*.

    Fallback: same dir only {date}*-tm-exits.md. Never position-watch.
    """
    exit_dir = inbox / "desk-pack-exit"
    found = _first_nonzero([exit_dir / f"{date}-tm-exits.md"])
    if found is not None:
        return found
    found = _glob_nonzero(exit_dir, f"{date}*tm-exits*")
    if found is not None:
        return found
    return _glob_nonzero(exit_dir, f"{date}*-tm-exits.md")


def check(date: str) -> dict:
    inbox = _inbox()

    market_close = _glob_nonzero(
        inbox / "market-close", f"{date}*-summary-revised.md"
    )
    daily_social = _glob_nonzero(
        inbox / "daily-social", f"{date}*-summary-revised.md"
    )
    exit_ev = _exit_evidence(inbox, date)

    status = {
        "date": date,
        "market_close": "ok" if market_close else "miss",
        "daily_social": "ok" if daily_social else "miss",
        "exit_evidence": "ok" if exit_ev else "miss",
        "market_close_path": str(market_close) if market_close else None,
        "daily_social_path": str(daily_social) if daily_social else None,
        "exit_evidence_path": str(exit_ev) if exit_ev else None,
    }
    if market_close and daily_social and exit_ev:
        status["status"] = "complete"
    else:
        status["status"] = "incomplete"
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Desk Pack daily train completion artifacts"
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="UTC date to check (default: UTC today).",
    )
    args = parser.parse_args(argv)

    result = check(args.date)
    print(json.dumps(result, ensure_ascii=False))

    if result["status"] == "complete":
        return 0
    # Exit 2 for incomplete (incl. fan-out-only: market-close missing).
    return 2


if __name__ == "__main__":
    sys.exit(main())
