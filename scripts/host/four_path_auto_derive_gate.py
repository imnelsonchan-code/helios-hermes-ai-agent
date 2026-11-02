#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
four_path_auto_derive_gate.py — W43 Four-path Auto-Derive Gate()

Desk train default is NO ``--patch`` (check only). ``--patch`` replaces one
existing Header block and must not append a second copy.

Exit codes: 0 = PASS / 1 = BLOCK / 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────
# Regex to locate the four-path block inside `## Header`
# Bold markers optional: `- **Four-path status:**` or `- Four-path status:`
# ──────────────────────────────────────────────────────────────────────
HEADER_RE = re.compile(r"^## Header\s*(.*?)(?=\n## |\Z)", re.DOTALL | re.MULTILINE)
FOUR_PATH_START_RE = re.compile(
    r"(?m)^- (?:\*\*)?Four-path status:(?:\*\*)?\s*$"
)
_FP_ALIAS_RE = (
    r"(?:commodities-session|commodity-session)"
    r"|(?:rates-session)"
    r"|(?:weekly-trend-momentum|trend-momentum|daily-trend-momentum)"
    r"|(?:valuation-width|value-session)"
)
FOUR_PATH_ITEM_RE = re.compile(
    r"(?m)^\s*-\s*(" + _FP_ALIAS_RE + r")\s*\(([^)]+)\):\s*`([^`]+)`\s*→\s*\*\*([^*]+)\*\*(.*)$"
)

_ALIAS_TO_CANONICAL = {
    "commodities-session": "commodities-session",
    "commodity-session": "commodities-session",
    "rates-session": "rates-session",
    "weekly-trend-momentum": "weekly-trend-momentum",
    "trend-momentum": "weekly-trend-momentum",
    "daily-trend-momentum": "weekly-trend-momentum",
    "valuation-width": "valuation-width",
    "value-session": "valuation-width",
}

SESSION_ORDER = [
    "commodities-session",
    "rates-session",
    "weekly-trend-momentum",
    "valuation-width",
]

SESSION_ALIASES: Dict[str, list] = {
    "commodities-session": [
        "commodities-session",
        "commodity-session",
        "commodities-session-revised",
        "commodity-session-revised",
    ],
    "rates-session": [
        "rates-session",
        "rates-session-revised",
    ],
    "weekly-trend-momentum": [
        "weekly-trend-momentum",
        "trend-momentum",
        "daily-trend-momentum",
        "weekly-trend-momentum-report",
        "trend-momentum-report",
        "daily-trend-momentum-report",
    ],
    "valuation-width": [
        "valuation-width",
        "value-session",
        "valuation-width-revised",
        "value-session-revised",
    ],
}

# canonical key -> owner, on-disk dirs, zoe challenge subdir, inbox session dirs
_LAYOUT = {
    "commodities-session": {
        "owner": "emily",
        "dirs": ("commodities-session",),
        "zoe_sub": "commodities-session",
        "inbox_dirs": ("commodities-session",),
    },
    "rates-session": {
        "owner": "christina",
        "dirs": ("rates-session",),
        "zoe_sub": "rates-session",
        "inbox_dirs": ("rates-session",),
    },
    "weekly-trend-momentum": {
        "owner": "renee",
        "dirs": ("weekly-trend-momentum", "daily-trend-momentum"),
        "zoe_sub": "daily-trend-momentum",
        "inbox_dirs": ("weekly-trend-momentum", "daily-trend-momentum"),
    },
    "valuation-width": {
        "owner": "eliza",
        "dirs": ("valuation-width", "value-session"),
        "zoe_sub": "value-session",
        "inbox_dirs": ("valuation-width", "value-session"),
    },
}


def _shared_reports() -> Path:
    """Shared reports root. HERMES_SHARED wins; else $HERMES_HOME/shared/reports."""
    override = os.environ.get("HERMES_SHARED")
    if override:
        return Path(override)
    hermes = os.environ.get("HERMES_HOME")
    if hermes:
        return Path(hermes) / "shared" / "reports"
    return Path.home() / ".hermes" / "shared" / "reports"


def _inbox() -> Path:
    """Portal inbox. REPORTS_INBOX wins; else ~/workspace/reports/inbox.

    Example host layout: ~/workspace/reports/inbox (override with $REPORTS_INBOX).
    """
    override = os.environ.get("REPORTS_INBOX")
    if override:
        return Path(override)
    return Path.home() / "workspace" / "reports" / "inbox"


def _revised_name_candidates(session_key: str, date_str: str) -> list[str]:
    names: list[str] = []
    for alias in SESSION_ALIASES.get(session_key, []):
        if alias.endswith("-revised"):
            names.append(f"{date_str}-{alias}.md")
        else:
            names.append(f"{date_str}-{alias}-revised.md")
    return names


def _unique_dirs(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _challenge_roots(session_key: str) -> list[Path]:
    layout = _LAYOUT[session_key]
    shared = _shared_reports()
    inbox = _inbox()
    roots = [shared / "zoe" / layout["zoe_sub"]]
    for dirname in layout["dirs"]:
        roots.append(shared / layout["owner"] / dirname)
    for dirname in layout["inbox_dirs"]:
        roots.append(inbox / dirname)
    return _unique_dirs(roots)


def _revised_roots(session_key: str) -> list[Path]:
    layout = _LAYOUT[session_key]
    shared = _shared_reports()
    inbox = _inbox()
    roots = [shared / layout["owner"] / dirname for dirname in layout["dirs"]]
    roots.append(shared / layout["owner"])
    for dirname in layout["inbox_dirs"]:
        roots.append(inbox / dirname)
    return _unique_dirs(roots)


def _iter_files(root: Path):
    if not root.is_dir():
        return
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for path in entries:
        if path.is_file():
            yield path


def find_challenge_file(session_key: str, date_str: str) -> Optional[Path]:
    """First same-day file whose name matches ``*challenge*``, or None."""
    hits: list[Path] = []
    for root in _challenge_roots(session_key):
        for path in _iter_files(root):
            name = path.name.lower()
            if "challenge" not in name:
                continue
            if date_str not in path.name:
                continue
            hits.append(path)
    if not hits:
        return None
    hits.sort(key=lambda p: p.name)
    return hits[0]


def find_revised_file(session_key: str, date_str: str) -> Optional[Path]:
    """Same-day ``*-revised.md`` under shared reports or the portal inbox."""
    names = _revised_name_candidates(session_key, date_str)
    for root in _revised_roots(session_key):
        if not root.is_dir():
            continue
        for name in names:
            candidate = root / name
            if candidate.is_file():
                return candidate
        try:
            matches = sorted(p for p in root.glob(f"{date_str}-*-revised.md") if p.is_file())
        except OSError:
            matches = []
        if matches:
            return matches[0]
    return None


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _read_verdict(challenge_path: Path) -> Tuple[str, str]:
    try:
        text = challenge_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "UNKNOWN", "file not readable"
    data = _parse_json_block(text)
    if isinstance(data, dict):
        verdict = str(data.get("verdict", "")).upper()
        if verdict in ("PASS", "CONDITIONAL", "PARTIAL", "REJECT", "BLOCKER", "MAJOR", "UNKNOWN"):
            severity = str(data.get("severity", "")).upper()
            return verdict, f"{verdict} / {severity}"
    keywords = ("PASS", "CONDITIONAL", "PARTIAL", "REJECT", "BLOCKER")
    for line in text.splitlines():
        low = line.lower()
        if "ic vote" in low or ("verdict" in low and ":" in line):
            for kw in keywords:
                if re.search(rf"\b{kw}\b", line, re.IGNORECASE):
                    return kw, kw
    return "UNKNOWN", "no verdict found"


def _derive_status(verdict: str, repr_path: Optional[Path]) -> Tuple[str, str]:
    """ok / pending-rechallenge / miss.

    A revised file with no PASS challenge is pending-rechallenge, never miss.
    Miss is only the absence of the same-day revised file.
    """
    if repr_path is None:
        return "miss", "same-day revised repr not found"
    verdict_norm = (verdict or "").strip().upper()
    if verdict_norm == "PASS":
        return "ok", f"Zoe PASS  {repr_path.name}"
    if verdict_norm in ("", "UNKNOWN"):
        return "pending-rechallenge", f"no challenge file  {repr_path.name}"
    return "pending-rechallenge", f"Zoe {verdict_norm}  {repr_path.name}  (2nd gate pending)"


def derive_four_path(date_str: str) -> Dict[str, Any]:
    """Derive four-path legs for ``date_str``.

    Missing ``*challenge*`` files do not short-circuit the revised lookup.
    """
    legs: Dict[str, Dict[str, Any]] = {}
    all_pass = True
    any_leg_missing = False
    any_pending = False
    for session_key in SESSION_ORDER:
        challenge = find_challenge_file(session_key, date_str)
        revised = find_revised_file(session_key, date_str)
        if challenge is None:
            verdict, verdict_note = "UNKNOWN", "no challenge file"
        else:
            verdict, verdict_note = _read_verdict(challenge)
        status, reason = _derive_status(verdict, revised)
        if status == "miss":
            any_leg_missing = True
        if status == "pending-rechallenge":
            any_pending = True
        if status != "ok":
            all_pass = False
        legs[session_key] = {
            "status": status,
            "verdict": verdict,
            "verdict_note": verdict_note,
            "repr_path": revised,
            "reason": reason,
            "repr_exists": revised is not None,
            "challenge_path": challenge,
        }
    return {
        "date": date_str,
        "all_pass": all_pass,
        "any_pending": any_pending,
        "any_leg_missing": any_leg_missing,
        "legs": legs,
    }


def format_four_path_bullets(result: Dict[str, Any]) -> str:
    """Canonical Header bullets. One block, unbolded status line."""
    verdict_emoji = {
        "PASS": "🟢",
        "CONDITIONAL": "🟠",
        "PARTIAL": "🟡",
        "REJECT": "🔴",
        "BLOCKER": "🔴",
        "MAJOR": "🟠",
        "UNKNOWN": "⚪",
    }
    lines = ["- Four-path status:"]
    for session_key in SESSION_ORDER:
        leg = result["legs"][session_key]
        status = leg["status"]
        verdict = leg.get("verdict", "UNKNOWN")
        repr_path = leg.get("repr_path")
        filename = repr_path.name if repr_path else "—"
        owner = _LAYOUT[session_key]["owner"]
        emoji = verdict_emoji.get(verdict, "⚪")
        if status == "ok":
            note = f"(Zoe {emoji} {verdict}, re-challenge)"
        elif status == "pending-rechallenge":
            note = f"(Zoe {emoji} {verdict},revised exists, re-challenge)"
        elif repr_path is not None:
 # Revised file is on disk — never describe that leg as .
            note = f"(Zoe {emoji} {verdict},revised exists, re-challenge)"
        else:
            note = "(revised repr )"
        lines.append(
            f"  - {session_key} ({owner}): `{filename}` → **{status}**{note}"
        )
    return "\n".join(lines)


def _parse_report_four_path(text: str) -> Optional[Dict[str, Dict[str, str]]]:
    header_m = HEADER_RE.search(text)
    if not header_m:
        return None
    header_text = header_m.group(1)
    start_m = FOUR_PATH_START_RE.search(header_text)
    if not start_m:
        return None
    block_lines = header_text[start_m.end():].splitlines()
    result: Dict[str, Dict[str, str]] = {}
    for line in block_lines:
        if not line.strip():
            continue
        if re.match(r"^-[ \t]", line) and "Four-path" not in line:
            break
        match = FOUR_PATH_ITEM_RE.match(line)
        if not match:
            continue
        alias_session, owner, filename, status, _ = match.groups()
        session = _ALIAS_TO_CANONICAL.get(alias_session, alias_session)
        result[session] = {
            "owner": owner,
            "filename": filename,
            "status": status.strip(),
            "raw_line": line.strip(),
        }
    return result if result else None


def _compare(
    canonical: Dict[str, Any], current: Optional[Dict[str, Dict[str, str]]]
) -> Tuple[bool, list]:
    diffs = []
    if current is None:
        for sk in SESSION_ORDER:
            leg = canonical["legs"][sk]
            diffs.append(
                f"{sk}: canonical={leg['status']}({leg.get('verdict', '?')}) vs report=missing"
            )
        return False, diffs
    for sk in SESSION_ORDER:
        leg = canonical["legs"][sk]
        cur = current.get(sk)
        if cur is None:
            diffs.append(
                f"{sk}: canonical={leg['status']}({leg.get('verdict', '?')}) vs report=missing"
            )
            continue
        if leg["status"] != cur["status"]:
            diffs.append(
                f"{sk}: canonical={leg['status']}({leg.get('verdict', '?')})"
                f" vs report={cur['status']}"
            )
    return len(diffs) == 0, diffs


def _replace_existing_block(header_text: str, bullets: str) -> str:
    """Replace the one four-path block. Insert once only when none exists."""
    raw_lines = header_text.splitlines()
    start_idx = None
    for i, line in enumerate(raw_lines):
        if FOUR_PATH_START_RE.match(line):
            start_idx = i
            break
    if start_idx is None:
        body = header_text
        if body and not body.startswith("\n"):
            body = "\n" + body
        return bullets + body
    end_idx = len(raw_lines)
    for j in range(start_idx + 1, len(raw_lines)):
        line = raw_lines[j]
        if not line.strip():
            continue
        if re.match(r"^-[ \t]", line) and "Four-path" not in line:
            end_idx = j
            break
        if not line.startswith((" ", "\t", "-")):
            end_idx = j
            break
    new_lines = raw_lines[:start_idx] + bullets.splitlines() + raw_lines[end_idx:]
    out = "\n".join(new_lines)
    if header_text.endswith("\n"):
        out += "\n"
    return out


def _patch_report(text: str, canonical: Dict[str, Any]) -> Optional[str]:
    """Return patched text, or None when ``## Header`` is missing.

    Callers must not create a file when this returns None.
    """
    header_m = HEADER_RE.search(text)
    if not header_m:
        return None
    bullets = format_four_path_bullets(canonical)
    new_header = _replace_existing_block(header_m.group(1), bullets)
    return text[: header_m.start()] + "## Header\n" + new_header + text[header_m.end() :]


def _extract_date_from_report(text: str) -> Optional[str]:
    match = re.search(r"as[-\s]?of[:\s]+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def _emit(payload: dict, as_json: bool, human: str) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(human)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Four-path auto-derive gate — abolish manual tagging"
    )
    parser.add_argument("--report", required=True, help="Path to report .md")
    parser.add_argument("--date", required=False, help="Session date YYYY-MM-DD")
    parser.add_argument(
        "--patch",
        action="store_true",
        help="Replace the Header four-path block (default off; desk train does not pass this)",
    )
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    if not report_path.exists():
        # --patch must not create a report that has no ## Header.
        if args.patch:
            print(f"❌ ## Header missing — not creating {report_path}", file=sys.stderr)
            return 1
        print(f"❌ report not found: {report_path}", file=sys.stderr)
        return 2

    text = report_path.read_text(encoding="utf-8", errors="replace")
    date_str = args.date or _extract_date_from_report(text)
    if not date_str:
        print("❌ cannot determine session date (use --date YYYY-MM-DD)", file=sys.stderr)
        return 2

    if args.patch and HEADER_RE.search(text) is None:
        print(f"❌ ## Header missing — not patching {report_path}", file=sys.stderr)
        return 1

    canonical = derive_four_path(date_str)
    current = _parse_report_four_path(text)
    match, diffs = _compare(canonical, current)
    payload = {
        "date": date_str,
        "match": match,
        "diffs": diffs,
        "canonical_summary": format_four_path_bullets(canonical),
        "patched": False,
    }
    if match:
        _emit(payload, args.json, f"✅ Four-path gate PASS — {date_str}\n{payload['canonical_summary']}")
        return 0

    if args.patch:
        new_text = _patch_report(text, canonical)
        if new_text is None or new_text == text:
            detail = "\n".join(f"  ⚠️ {d}" for d in diffs)
            _emit(
                payload,
                args.json,
                f"❌ Four-path gate FAIL(patch ) — {date_str}\n{detail}",
            )
            return 1
        report_path.write_text(new_text, encoding="utf-8")
        payload["patched"] = True
        detail = "\n".join(f"  ⚠️ {d}" for d in diffs)
        _emit(
            payload,
            args.json,
            f"🔧 Four-path gate PATCHED — {date_str}\n{payload['canonical_summary']}\n{detail}",
        )
        return 0

    detail = "\n".join(f"  ⚠️ {d}" for d in diffs)
    _emit(
        payload,
        args.json,
        f"❌ Four-path gate FAIL — {date_str}\n{detail}\n\nCanonical:\n{payload['canonical_summary']}",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
