#!/usr/bin/env python3
"""Deterministic gate: promote commodities draft -> *-revised.md only when reviewed.

This is NOT a green-light rename of an unreviewed draft. Goal-mode does not
stat the inbox; this script does. Emily must leave a challenge artifact that
is older than the draft (Zoe challenge written, then Emily revised the draft).
Only then is normalized text copied to the three revised outs. Draft is kept.

Does not touch model config / provider settings.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
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


def _normalize(text: str, date: str) -> str:
    portal_from = "portal `inbox/commodities-session/*-revised.md`"
    portal_to = f"portal `inbox/commodities-session/{date}-commodities-session-revised.md`"
    text = text.replace(portal_from, portal_to)
    text = text.replace("this draft did not use shadow", "this revised did not use shadow")
    lines = [
        line
        for line in text.splitlines(keepends=True)
        if not line.strip().startswith("**Train:**")
    ]
    return "".join(lines)


_ASOF_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-commodity-session\.md$")
_PRICE_GATE_MOD = None


def _load_price_gate():
    """Load the price-source validator that sits next to this file.

    A plain import fails when this module is loaded by path (or from a copy
    whose cwd is not scripts/host). Resolve the sibling via importlib.
    """
    global _PRICE_GATE_MOD
    if _PRICE_GATE_MOD is not None:
        return _PRICE_GATE_MOD

    mod_name = "validate_price_source_direction_gate"
    sibling = Path(__file__).resolve().parent / f"{mod_name}.py"
    if sibling.is_file():
        spec = importlib.util.spec_from_file_location(mod_name, sibling)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {sibling}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        _PRICE_GATE_MOD = mod
        return mod

    try:
        import validate_price_source_direction_gate as mod
    except ImportError as exc:
        raise ImportError(
            "validate_price_source_direction_gate.py is not next to "
            "desk_pack_revised_gate.py and is not importable"
        ) from exc
    _PRICE_GATE_MOD = mod
    return mod


def _strip_asof(text: str, asof: str) -> str:
    if asof:
        return text.replace(asof, "")
    return text


def _older_dated_siblings(parent: Path, date: str) -> list[tuple[str, float, Path]]:
    """Dated ``YYYY-MM-DD-commodity-session.md`` files strictly older than ``date``.

    Undated names (including ``template-commodity-session.md``) are ignored.
    """
    if not parent.is_dir():
        return []
    try:
        siblings = list(parent.glob("*-commodity-session.md"))
    except OSError:
        return []

    found: list[tuple[str, float, Path]] = []
    for sibling in siblings:
        match = _ASOF_NAME.match(sibling.name)
        if not match:
            continue
        sib_date = match.group(1)
        if sib_date >= date:
            continue
        try:
            if not sibling.is_file():
                continue
            mtime = sibling.stat().st_mtime
        except OSError:
            continue
        found.append((sib_date, mtime, sibling))
    return found


def _newest_older_sibling(parents: list[Path], date: str) -> Path | None:
    """Newest strictly older dated sibling across ``parents``.

    Greatest ISO date string wins. The same date in two directories uses the
    newer mtime. Only that one file is a clone candidate.
    """
    best_key: tuple[str, float] | None = None
    best: Path | None = None
    seen: set[Path] = set()
    for parent in parents:
        try:
            parent_key = parent.resolve()
        except OSError:
            parent_key = parent
        if parent_key in seen:
            continue
        seen.add(parent_key)
        for sib_date, mtime, path in _older_dated_siblings(parent, date):
            key = (sib_date, mtime)
            if best_key is None or key > best_key:
                best_key = key
                best = path
    return best


def _matches_sibling_after_strip(text: str, date: str, sibling: Path) -> bool:
    """Exact equality after removing each file's own ISO date.

    One extra sentence keeps the texts unequal, so the note is not a clone.
    """
    match = _ASOF_NAME.match(sibling.name)
    if not match:
        return False
    try:
        sib_text = sibling.read_text(encoding="utf-8")
    except OSError:
        return False
    return _strip_asof(sib_text, match.group(1)) == _strip_asof(text, date)


def _is_clone_of_newest_older(text: str, date: str, parents: list[Path]) -> bool:
    sibling = _newest_older_sibling(parents, date)
    if sibling is None:
        return False
    return _matches_sibling_after_strip(text, date, sibling)


def _candidate_parents(candidates: list[Path]) -> list[Path]:
    """Parent directories of every draft candidate, whether today's file exists.

    An older Friday note often sits in a different root from the newest Monday
    draft. The newest strictly older date is chosen across all of them.
    """
    parents: list[Path] = []
    seen: set[Path] = set()
    for cand in candidates:
        parent = cand.parent
        try:
            key = parent.resolve()
        except OSError:
            key = parent
        if key in seen:
            continue
        seen.add(key)
        parents.append(parent)
    return parents


def _pick_newest(candidates: list[Path]) -> Path | None:
    existing = [p for p in candidates if p.is_file()]
    if not existing:
        return None
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return existing[0]


def _process_date(date: str, min_age: float) -> str:
    inbox = _inbox()
    hermes = _hermes_home()

    inbox_revised = (
        inbox / "commodities-session" / f"{date}-commodities-session-revised.md"
    )
    draft_candidates = [
        inbox / "commodities-session" / f"{date}-commodity-session.md",
        # Prompt/skill SSOT is the flat emily path, not only the subfolder.
        hermes / "shared" / "reports" / "emily" / f"{date}-commodity-session.md",
        hermes
        / "shared"
        / "reports"
        / "emily"
        / "commodities-session"
        / f"{date}-commodity-session.md",
        hermes
        / "profiles"
        / "emily"
        / "workspace"
        / "commodities-session"
        / f"{date}-commodity-session.md",
    ]
    challenge = (
        hermes
        / "shared"
        / "reports"
        / "zoe"
        / "commodities-session"
        / f"{date}-challenge.md"
    )
    also_revised = [
        hermes
        / "shared"
        / "reports"
        / "emily"
        / "commodities-session"
        / f"{date}-commodity-session-revised.md",
        hermes
        / "profiles"
        / "emily"
        / "workspace"
        / "commodities-session"
        / f"{date}-commodity-session-revised.md",
    ]
    revised_outs = [inbox_revised, *also_revised]

    if inbox_revised.is_file() and inbox_revised.stat().st_size > 0:
        revised_text = inbox_revised.read_text(encoding="utf-8")
        if _is_clone_of_newest_older(
            revised_text, date, _candidate_parents(draft_candidates)
        ):
            print(f"{date} miss-clone")
            return "miss-clone"
        print(f"{date} already")
        return "already"

    draft = _pick_newest(draft_candidates)
    if draft is None:
        print(f"{date} miss-no-draft")
        return "miss-no-draft"

    if not challenge.is_file():
        print(f"{date} miss-no-challenge")
        return "miss-no-challenge"

    draft_mtime = draft.stat().st_mtime
    challenge_mtime = challenge.stat().st_mtime
    if draft_mtime < challenge_mtime:
        print(f"{date} miss-draft-older")
        return "miss-draft-older"

    if min_age > 0 and draft_mtime > time.time() - min_age:
        print(f"{date} wait")
        return "wait"

    draft_text = draft.read_text(encoding="utf-8")
    if _load_price_gate().check_text(draft_text, draft.name):
        print(f"{date} miss-direction-gate")
        return "miss-direction-gate"
    if _is_clone_of_newest_older(
        draft_text, date, _candidate_parents(draft_candidates)
    ):
        print(f"{date} miss-clone")
        return "miss-clone"

    body = _normalize(draft_text, date)
    for out in revised_outs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")

    print(f"{date} promoted")
    return "promoted"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote commodities-session draft to revised when challenge is present"
    )
    parser.add_argument(
        "--date",
        action="append",
        dest="dates",
        metavar="YYYY-MM-DD",
        help="UTC date to check (repeatable). Default: UTC today and yesterday.",
    )
    parser.add_argument(
        "--min-age",
        type=float,
        default=0,
        metavar="SECONDS",
        help="Skip promote if draft mtime is newer than now-SECONDS (default 0).",
    )
    args = parser.parse_args(argv)

    if args.dates:
        dates = args.dates
    else:
        today = datetime.now(timezone.utc).date()
        dates = [
            today.isoformat(),
            (today - timedelta(days=1)).isoformat(),
        ]

    statuses: list[str] = []
    for date in dates:
        statuses.append(_process_date(date, args.min_age))

    # Only the first date sets the exit code. Default order is UTC today,
    # then yesterday. A leftover draft on the other day must not turn a
    # completed session into a true miss.
    hard_miss = {
        "miss-no-challenge",
        "miss-draft-older",
        "miss-direction-gate",
        "miss-clone",
    }
    if statuses and statuses[0] in hard_miss:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
