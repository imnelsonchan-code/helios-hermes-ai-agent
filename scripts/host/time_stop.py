#!/usr/bin/env python3
"""Shared time-stop helpers: session count, MFE_close gate, one-shot latch.

Operational risk-control. Non-investment advice. Never writes risk_plans.json.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

TIME_STOP_LATCH_PATH = os.path.expanduser(
    "~/.hermes/shared/audit/time-stop-latch.json"
)


def count_trading_days(from_date: str, to_date: date) -> int | None:
    """Approximate trading days (~5/7). None on empty/unparseable (do not trip)."""
    text = str(from_date or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            start = datetime.strptime(text, fmt).date()
            return max(0, int((to_date - start).days * 5 / 7))
        except ValueError:
            continue
    return None


def latch_key(ticker: str, entry_date: str) -> str:
    return f"{str(ticker).strip().upper()}|{str(entry_date).strip()}"


def load_time_stop_latch(path: str) -> dict | None:
    """Return latch state, or None if missing/unreadable/invalid (fail closed)."""
    target = Path(path)
    if not target.is_file():
        return {"schema_version": "1", "fired": {}}
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if (
        not isinstance(loaded, dict)
        or loaded.get("schema_version") != "1"
        or not isinstance(loaded.get("fired"), dict)
    ):
        return None
    return loaded


def is_time_stop_latched(path: str, key: str) -> bool:
    state = load_time_stop_latch(path)
    if state is None:
        # Unreadable latch -> treat as already fired (fail closed: do not re-emit).
        return True
    return bool(state.get("fired", {}).get(key))


def mark_time_stop_latched(path: str, key: str, *, session: date) -> None:
    state = load_time_stop_latch(path)
    if state is None:
        raise OSError(f"time-stop latch unreadable: {path}")
    fired = dict(state.get("fired") or {})
    fired[key] = session.isoformat()
    state = {"schema_version": "1", "fired": fired}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def mfe_close_r(
    *,
    fill_price: Decimal,
    risk_per_share: Decimal,
    closes: Sequence[Decimal],
) -> Decimal | None:
    """(max close − fill) / R. None if inputs unusable (fail closed)."""
    try:
        fill = Decimal(str(fill_price))
        risk = Decimal(str(risk_per_share))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not fill.is_finite() or not risk.is_finite() or risk <= 0:
        return None
    if not closes:
        return None
    try:
        best = max(Decimal(str(c)) for c in closes)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not best.is_finite():
        return None
    return (best - fill) / risk


def mfe_close_r_from_bars(
    *,
    fill_price: Decimal,
    risk_per_share: Decimal,
    bars: Sequence,
    entry_session: date,
    through_session: date,
) -> Decimal | None:
    closes: list[Decimal] = []
    for bar in bars:
        session = getattr(bar, "session", None)
        close = getattr(bar, "close", None)
        if session is None or close is None:
            continue
        if entry_session <= session <= through_session:
            closes.append(Decimal(str(close)))
    return mfe_close_r(
        fill_price=fill_price,
        risk_per_share=risk_per_share,
        closes=closes,
    )


def time_stop_eligible(
    *,
    entry_date: str,
    session: date,
    mfe_close: Decimal | None,
    latch_path: str | None,
    ticker: str,
) -> tuple[bool, int | None]:
    """Return (should_emit, days). Never emits without MFE<1R and unlatched."""
    days = count_trading_days(entry_date, session)
    if days is None or days < 10:
        return False, days
    if mfe_close is None:
        return False, days
    if mfe_close >= Decimal("1"):
        return False, days
    key = latch_key(ticker, entry_date)
    if latch_path and is_time_stop_latched(latch_path, key):
        return False, days
    return True, days
