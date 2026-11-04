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


def _exit_receipt_ok(path: Path | None) -> str | None:
    """Receipt acceptance: None (no receipt) / 'ok' / 'failed-overlay'.

    The tm-exits receipt records its own outcome (`status: checker_rc=N`).
    A nonzero N means the exit overlay crashed — acceptance until now only
    checked file existence, so a failed overlay counted as success-grade
    completion evidence for the whole pack. Undefeated evidence is required.
    """
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("status: checker_rc=") and not stripped.endswith("=0"):
            return "failed-overlay"
    return "ok"


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
    evidence_state = _exit_receipt_ok(exit_ev)

    status = {
        "date": date,
        "market_close": "ok" if market_close else "miss",
        "daily_social": "ok" if daily_social else "miss",
        # 'ok' | 'failed-overlay' (receipt recorded a nonzero checker rc) | 'miss'
        "exit_evidence": evidence_state if evidence_state is not None else "miss",
        "market_close_path": str(market_close) if market_close else None,
        "daily_social_path": str(daily_social) if daily_social else None,
        "exit_evidence_path": str(exit_ev) if exit_ev else None,
    }
    if (
        market_close
        and daily_social
        and evidence_state == "ok"
    ):
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
