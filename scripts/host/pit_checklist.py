#!/usr/bin/env python3
"""Point-in-time audit checklist for scoring packs (data correctness, not score rewrite).

Validators run over a pack/meta JSON describing what the pack claims.
Never mixes T&M and value sleeve scores.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

CheckResult = dict[str, str]


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _section(meta: dict, *keys: str) -> dict:
    cur: Any = meta
    for key in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(key)
    return cur if isinstance(cur, dict) else {}


def check_statement_as_of_present(meta: dict) -> CheckResult:
    """Value sleeve: financial statement as-of must be declared."""
    value = _section(meta, "value")
    as_of = value.get("statement_as_of") or value.get("as_of")
    if as_of and str(as_of).strip():
        return {
            "id": "statement_as_of_present",
            "sleeve": "value",
            "status": "pass",
            "detail": f"statement_as_of={as_of}",
        }
    return {
        "id": "statement_as_of_present",
        "sleeve": "value",
        "status": "fail",
        "detail": "missing value.statement_as_of (or value.as_of)",
    }


def check_news_social_window_trimmed(meta: dict) -> CheckResult:
    """Alice/T&M context: news/social window must not extend past as_of."""
    alice = _section(meta, "alice")
    tm = _section(meta, "tm")
    ctx = alice or tm
    as_of = _parse_date(ctx.get("as_of") or meta.get("as_of"))
    window = ctx.get("news_social_window") or alice.get("news_social_window")
    if not isinstance(window, dict):
        return {
            "id": "news_social_window_trimmed",
            "sleeve": "alice",
            "status": "skip",
            "detail": "no news_social_window declared",
        }
    end = _parse_date(window.get("end"))
    start = _parse_date(window.get("start"))
    if as_of is None:
        return {
            "id": "news_social_window_trimmed",
            "sleeve": "alice",
            "status": "warn",
            "detail": "news_social_window present but as_of missing",
        }
    if end is None:
        return {
            "id": "news_social_window_trimmed",
            "sleeve": "alice",
            "status": "fail",
            "detail": "news_social_window.end missing or unparsable",
        }
    if end > as_of:
        return {
            "id": "news_social_window_trimmed",
            "sleeve": "alice",
            "status": "fail",
            "detail": f"window end {end} > as_of {as_of} (look-ahead risk)",
        }
    if start and start > end:
        return {
            "id": "news_social_window_trimmed",
            "sleeve": "alice",
            "status": "fail",
            "detail": f"window start {start} > end {end}",
        }
    return {
        "id": "news_social_window_trimmed",
        "sleeve": "alice",
        "status": "pass",
        "detail": f"window {start or '?'}..{end} trimmed to as_of {as_of}",
    }


def _is_nan_close(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in {"", "nan", "null", "none", "na", "n/a"}


def check_latest_bar_not_dropped_on_nan_close(meta: dict) -> CheckResult:
    """T&M: latest bar with NaN close must not be silently dropped."""
    tm = _section(meta, "tm")
    bars = tm.get("bars")
    if not isinstance(bars, list) or not bars:
        flag = tm.get("latest_bar_nan_close")
        if flag is True:
            return {
                "id": "latest_bar_not_dropped_on_nan_close",
                "sleeve": "tm",
                "status": "fail",
                "detail": "latest bar had NaN close and was dropped",
            }
        if flag is False:
            return {
                "id": "latest_bar_not_dropped_on_nan_close",
                "sleeve": "tm",
                "status": "pass",
                "detail": "latest bar retained (explicit flag)",
            }
        return {
            "id": "latest_bar_not_dropped_on_nan_close",
            "sleeve": "tm",
            "status": "skip",
            "detail": "no tm.bars or latest_bar_nan_close flag",
        }

    offenders: list[str] = []
    for item in bars:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "?").upper()
        series = item.get("series") or item.get("ohlc") or item.get("bars")
        if not isinstance(series, list) or not series:
            continue
        last = series[-1]
        if not isinstance(last, dict):
            continue
        close = last.get("close", last.get("Close"))
        dropped = last.get("dropped_on_nan_close", item.get("dropped_on_nan_close"))
        if _is_nan_close(close) and dropped is not False:
            offenders.append(ticker)

    if offenders:
        return {
            "id": "latest_bar_not_dropped_on_nan_close",
            "sleeve": "tm",
            "status": "fail",
            "detail": f"NaN close bar dropped or unhandled: {', '.join(offenders)}",
        }
    return {
        "id": "latest_bar_not_dropped_on_nan_close",
        "sleeve": "tm",
        "status": "pass",
        "detail": "latest bars with valid close or explicit NaN handling",
    }


def check_memory_lessons_resolved_by_trade_date(meta: dict) -> CheckResult:
    """Both sleeves: memory lessons must cite trade_date and be resolved by it."""
    lessons = meta.get("memory_lessons")
    if lessons is None:
        lessons = _section(meta, "both").get("memory_lessons")
    if not isinstance(lessons, list):
        return {
            "id": "memory_lessons_resolved_by_trade_date",
            "sleeve": "both",
            "status": "skip",
            "detail": "no memory_lessons list",
        }
    if not lessons:
        return {
            "id": "memory_lessons_resolved_by_trade_date",
            "sleeve": "both",
            "status": "pass",
            "detail": "empty memory_lessons (nothing to resolve)",
        }

    unresolved: list[str] = []
    for i, lesson in enumerate(lessons):
        if not isinstance(lesson, dict):
            unresolved.append(f"#{i}: not a dict")
            continue
        trade_date = _parse_date(lesson.get("trade_date"))
        if trade_date is None:
            unresolved.append(f"#{i}: missing trade_date")
            continue
        resolved = lesson.get("resolved_by_trade_date")
        resolved_date = _parse_date(lesson.get("resolved_date"))
        if resolved is True:
            continue
        if resolved_date is not None and resolved_date <= trade_date:
            continue
        if resolved is False or resolved_date is None:
            unresolved.append(f"#{i}: trade_date={lesson.get('trade_date')} not resolved")
            continue
        if resolved_date > trade_date:
            unresolved.append(f"#{i}: resolved_date {resolved_date} > trade_date {trade_date}")

    if unresolved:
        return {
            "id": "memory_lessons_resolved_by_trade_date",
            "sleeve": "both",
            "status": "fail",
            "detail": "; ".join(unresolved),
        }
    return {
        "id": "memory_lessons_resolved_by_trade_date",
        "sleeve": "both",
        "status": "pass",
        "detail": f"{len(lessons)} lesson(s) resolved by trade_date",
    }


def check_fred_vintage_pinned(meta: dict) -> CheckResult:
    """Alice: FRED vintage should be pinned; warn if missing."""
    alice = _section(meta, "alice")
    pinned = alice.get("fred_vintage_pinned")
    vintage = alice.get("fred_vintage")
    if pinned is True and vintage:
        return {
            "id": "fred_vintage_pinned",
            "sleeve": "alice",
            "status": "pass",
            "detail": f"fred_vintage={vintage}",
        }
    if pinned is True and not vintage:
        return {
            "id": "fred_vintage_pinned",
            "sleeve": "alice",
            "status": "warn",
            "detail": "fred_vintage_pinned=true but fred_vintage empty",
        }
    return {
        "id": "fred_vintage_pinned",
        "sleeve": "alice",
        "status": "warn",
        "detail": "fred_vintage not pinned (macro series may shift on revision)",
    }


VALIDATORS: list[Callable[[dict], CheckResult]] = [
    check_statement_as_of_present,
    check_news_social_window_trimmed,
    check_latest_bar_not_dropped_on_nan_close,
    check_memory_lessons_resolved_by_trade_date,
    check_fred_vintage_pinned,
]


def run_checklist(meta: dict) -> list[CheckResult]:
    return [fn(meta) for fn in VALIDATORS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Point-in-time pack audit checklist")
    parser.add_argument("--meta", required=True, help="Pack meta JSON path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when any check fails (default: always exit 0)",
    )
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args(argv)

    meta_path = Path(args.meta)
    if not meta_path.is_file():
        print(f"[pit_checklist] ERROR: meta not found: {meta_path}", file=sys.stderr)
        return 2 if args.strict else 0

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    results = run_checklist(meta)

    fails = [r for r in results if r["status"] == "fail"]
    warns = [r for r in results if r["status"] == "warn"]

    print("[pit_checklist] Point-in-time audit (data correctness; sleeves never blended):")
    for row in results:
        mark = {"pass": "✅", "fail": "🔴", "warn": "🟡", "skip": "⏭"}.get(row["status"], "?")
        print(f"  {mark} [{row['sleeve']}] {row['id']}: {row['detail']}")

    payload = {"checks": results, "fail_count": len(fails), "warn_count": len(warns)}
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if fails:
        print(f"[pit_checklist] {len(fails)} failure(s)", file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
