#!/usr/bin/env python3
"""Fail if markdown tables use DIR_* or bare BUY in Signal column cells."""
from __future__ import annotations

import re
import sys


def main() -> int:
    path = sys.argv[1]
    text = open(path, encoding="utf-8").read()
    chunks = re.split(r"```(?:markdown)?\n?", text)
    violations: list[str] = []
    dir_cell = re.compile(r"^DIR_[A-Z_]+$")
    bare_buy = re.compile(r"^BUY$")

    def scan_tables(blob: str, where: str) -> None:
        lines = blob.splitlines()
        i = 0
        while i < len(lines):
            if not lines[i].strip().startswith("|"):
                i += 1
                continue
            rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            if len(rows) < 2:
                continue
            headers = [c.strip() for c in rows[0].strip("|").split("|")]
            data_start = 1
            if data_start < len(rows) and re.match(r"^\|?\s*[-:]+", rows[data_start]):
                data_start = 2
            if "Signal" not in headers:
                continue
            sig_i = headers.index("Signal")
            for r in rows[data_start:]:
                cells = [c.strip() for c in r.strip("|").split("|")]
                if sig_i >= len(cells):
                    continue
                cell = cells[sig_i]
                for part in re.split(r"\s*/\s*|\s*\|\s*", cell):
                    part = part.strip().strip("`")
                    if dir_cell.match(part):
                        violations.append(
                            f"{where}: Signal cell has DIR_* value '{part}' in row: {r.strip()}"
                        )
                    if bare_buy.match(part):
                        violations.append(
                            f"{where}: Signal cell has bare BUY in row: {r.strip()}"
                        )

    scan_tables(text, "body")
    for n, ch in enumerate(chunks):
        scan_tables(ch, f"fence#{n}")

    if violations:
        print("VIOLATIONS:")
        for v in violations:
            print(" -", v)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
