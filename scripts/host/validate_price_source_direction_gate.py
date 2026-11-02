#!/usr/bin/env python3
"""Price-source direction gate for commodity session markdown.

Same-line / same-row checks as the kanban validator:

* Precious 1D rows must cite GLD, SLV, GC=F, SI=F, or prev close.
* A BZ=F line must disclose futures / financial distortion / ICE Brent.
* A CL–BZ spread sentence requires a file-level ``same-source`` note.

CLI: python3 validate_price_source_direction_gate.py <markdown files...>
Exit 0 when clean, 1 when any violation is printed, 2 when no files are given.
"""
from __future__ import annotations

import re
import sys
from collections import namedtuple
from pathlib import Path

Violation = namedtuple("Violation", "code source detail")

_PRECIOUS_ROW = re.compile(r"\|\s*(?:Gold|Silver)\s*\|")
# A 1D% claim, not a trade-map "lean: base" row. Bare words like lean/up/down
# appear on rows that are not a previous-close print.
_DIRECTION_OR_PCT = re.compile(r"%|\bDIR_", re.IGNORECASE)
# Ticker required. "previous close" alone does not prove GLD/GC=F or SLV/SI=F.
_CANONICAL_SRC = re.compile(r"GLD|SLV|GC=F|SI=F", re.IGNORECASE)
_MISS_CELL = re.compile(r"\bmiss\b", re.IGNORECASE)
_BZ_DISCLOSURE = re.compile(
    r"futures|financial|distort|disclosure|ICE Brent",
    re.IGNORECASE,
)
# CL and BZ inside one sentence, at most 40 characters apart (kanban window).
_SPREAD_SENTENCE = re.compile(
    r"CL[^.\n]{0,40}BZ|BZ[^.\n]{0,40}CL",
    re.IGNORECASE,
)

_PRECIOUS_DETAIL = (
    "Gold/Silver direction row lacks GLD/SLV/GC=F/SI=F prev close cite"
)
_BZ_DETAIL = (
    "BZ=F used without ICE Brent / financial-contract distortion disclosure"
)
_SPREAD_DETAIL = "CL-BZ spread sentence without same-source check"


def check_text(text: str, source: str = "<text>") -> list[Violation]:
    """Return same-row / same-line violations in ``text``. Import-safe."""
    if not isinstance(text, str):
        return [
            Violation(
                "FILE_READ_ERROR",
                source,
                "price-source gate expected markdown text",
            )
        ]

    found: list[Violation] = []
    for line in text.splitlines():
        if not _PRECIOUS_ROW.search(line):
            continue
        if not _DIRECTION_OR_PCT.search(line):
            continue
        if _CANONICAL_SRC.search(line):
            continue
        found.append(
            Violation("PRECIOUS_1D_MISSING_CANONICAL_SRC", source, _PRECIOUS_DETAIL)
        )

    for line in text.splitlines():
        if "BZ=F" not in line or _MISS_CELL.search(line):
            continue
        if _BZ_DISCLOSURE.search(line):
            continue
        found.append(
            Violation(
                "OIL_BZ_F_DISTORTION_DISCLOSURE_MISSING",
                source,
                _BZ_DETAIL,
            )
        )

    if "same-source" not in text.lower():
        for sentence in re.split(r"[.\n]", text):
            if _MISS_CELL.search(sentence):
                continue
            if _SPREAD_SENTENCE.search(sentence):
                found.append(
                    Violation("OIL_SPREAD_SAME_SOURCE", source, _SPREAD_DETAIL)
                )
                break
    return found


def check_file(path: str | Path) -> list[Violation]:
    """Read one markdown file and return its violations."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Violation("FILE_READ_ERROR", file_path.name, str(exc))]
    return check_text(text, file_path.name)


def main(argv: list[str] | None = None) -> int:
    """Validate markdown files. 0 clean, 1 violations, 2 if no files given."""
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print(
            "usage: validate_price_source_direction_gate.py <markdown files...>",
            file=sys.stderr,
        )
        return 2

    violations: list[Violation] = []
    for raw in argv:
        violations.extend(check_file(raw))
    for item in violations:
        print(f"[{item.code}] {item.source}: {item.detail}")
    if violations:
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
