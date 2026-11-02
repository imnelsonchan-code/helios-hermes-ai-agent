#!/usr/bin/env python3
"""MOA publish gate — score an existing MOA report via Mercury Decide.

v1 does **not** invoke Hermes MOA chat. It scores ``--report`` with
``mercury_decide.py --scope moa_publish`` (threshold 90) and writes a rework
brief when decision is REWORK.

Exit codes:
  0  ACCEPT (or FAIL-OPEN / mode=off)
  1  REWORK
  2  refuse (bad args / missing report)

Kill switch: ``MERCURY_DECIDE_MODE=off`` (via mercury_decide).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_mercury():
    here = Path(__file__).resolve().parent
    path = here / "mercury_decide.py"
    spec = importlib.util.spec_from_file_location("mercury_decide", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MOA Mercury publish gate (score only)")
    ap.add_argument("--report", required=True, help="Existing MOA report .md path")
    ap.add_argument("--mode", choices=("off", "enforce"), default=None)
    ap.add_argument("--attempt", type=int, default=0)
    ap.add_argument("--out", default="", help="Decide ledger path")
    ap.add_argument("--rework-brief-out", default="", help="Rework brief JSON path")
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args(argv)

    md = _load_mercury()
    report = md.resolve_path(args.report)
    if not report.is_file():
        print(f"refuse: report missing: {report}", file=sys.stderr)
        return 2
    text = report.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        print(f"refuse: report empty: {report}", file=sys.stderr)
        return 2

    mode = md.resolve_mode(args.mode)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stem = report.stem
    out = (
        md.resolve_path(args.out)
        if args.out
        else md.ledger_root() / "moa" / f"{day}-{stem}.decide.json"
    )
    ledger = md.decide_moa_publish(
        text,
        mode=mode,
        artifact_path=str(report),
        attempt=args.attempt,
    )
    md.write_ledger(out, ledger)
    msg = md.format_telegram(ledger)
    print(msg)
    if not args.no_telegram:
        md.send_telegram(msg)

    decision = str(ledger.get("decision") or "ACCEPT")
    status = str(ledger.get("status") or "OK")
    brief = {
        "report": str(report),
        "ledger": str(out),
        "decision": decision,
        "publish_score": ledger.get("publish_score"),
        "threshold": ledger.get("threshold", md.MOA_PUBLISH_THRESHOLD),
        "defects": ledger.get("defects") or [],
        "dims": ledger.get("dims") or {},
        "attempt": args.attempt,
        "status": status,
        "rework_instructions": (
            "Fix only listed defects; do not invent numbers; keep E5 no-blend; "
            "cite sources; then re-run moa_rework_gate on the revised file."
            if decision == "REWORK"
            else None
        ),
    }
    brief_path = (
        md.resolve_path(args.rework_brief_out)
        if args.rework_brief_out
        else md.ledger_root() / "moa" / f"{day}-{stem}-rework.json"
    )
    if decision == "REWORK" and status not in ("DECIDE_UNAVAILABLE", "OFF"):
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(
            json.dumps(brief, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        brief["rework_brief"] = str(brief_path)

    print(json.dumps({"ok": True, **{k: brief[k] for k in brief if k != "rework_instructions"}}, ensure_ascii=False))
    if status in ("DECIDE_UNAVAILABLE", "OFF"):
        return 0
    return 0 if decision == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
