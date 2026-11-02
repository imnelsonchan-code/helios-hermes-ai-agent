#!/usr/bin/env python3
"""width_publish_guard.py — Non-blocking check: JSON vs published width revised.md.

Flags the W36 class of silent publish bugs:
  - Prefer *-revised.md over *-report.md as the published artifact
  - 🔴 if JSON has numeric $fv_range / +NNN% verdict but revised.md table cell is `?`
  - 🟡 if ~/.hermes/shared/reports/eliza/inbox/ still has files (wrong relative inbox)

Always exits 0.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WIDTH_DIR = Path.home() / ".hermes" / "shared" / "reports" / "eliza" / "valuation-width"
WRONG_INBOX = Path.home() / ".hermes" / "shared" / "reports" / "eliza" / "inbox"

WEEK_RE = re.compile(r"(\d{4})-W(\d{2})")
DOLLAR_FV_RE = re.compile(r"\$\s*[\d,]+(?:\.\d+)?")
PCT_VERDICT_RE = re.compile(r"\+\d+(?:\.\d+)?%")
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,6}$")


def _week_tuple(name: str) -> tuple[int, int] | None:
    m = WEEK_RE.search(name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _latest_week_files(directory: Path) -> tuple[str | None, list[Path]]:
    best: tuple[int, int] = (0, 0)
    by_week: dict[tuple[int, int], list[Path]] = {}
    if not directory.is_dir():
        return None, []
    for f in directory.iterdir():
        if not f.is_file():
            continue
        if "valuation-width" not in f.name.lower():
            continue
        yw = _week_tuple(f.name)
        if yw is None:
            continue
        by_week.setdefault(yw, []).append(f)
        if yw > best:
            best = yw
    if best == (0, 0):
        return None, []
    label = f"{best[0]}-W{best[1]:02d}"
    return label, by_week[best]


def _pick_published_md(files: list[Path]) -> Path | None:
    mds = [f for f in files if f.suffix == ".md"]
    revised = [
        f for f in mds
        if "revised" in f.name.lower() and "stale" not in f.name.lower()
    ]
    if revised:
        revised.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return revised[0]
    reports = [f for f in mds if f.name.endswith("-report.md")]
    if reports:
        reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return reports[0]
    return None


def _pick_json(files: list[Path], week: str) -> Path | None:
    exact = [f for f in files if f.name == f"{week}-valuation-width.json"]
    if exact:
        return exact[0]
    jsons = [f for f in files if f.suffix == ".json" and "valuation-width" in f.name]
    return jsons[0] if jsons else None


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[width_publish_guard] WARNING: cannot load {path.name}: {e}", file=sys.stderr)
        return {}


def _all_rankings(report: dict) -> list[dict]:
    rows = []
    for track_key in ("A", "B"):
        track = report.get("tracks", {}).get(track_key, {})
        rows.extend(track.get("rankings", []))
    return rows


def _numeric_json_signal(row: dict) -> tuple[str | None, str | None]:
    fv = str(row.get("fv_range") or "")
    verdict = str(row.get("verdict") or "")
    fv_hit = fv if DOLLAR_FV_RE.search(fv) else None
    ver_hit = verdict if PCT_VERDICT_RE.search(verdict) else None
    return fv_hit, ver_hit


def _parse_md_fv_cells(text: str) -> dict[str, str]:
    """Map ticker → FV Range cell from markdown tables that have /Ticker + FV Range."""
    cells: dict[str, str] = {}
    lines = text.splitlines()
    fv_idx = None
    ticker_idx = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            fv_idx = None
            ticker_idx = None
            continue
        parts = [p.strip() for p in stripped.strip("|").split("|")]
        headerish = [p.lower() for p in parts]
        if any("fv range" in h or h in ("fv", "fv_range") for h in headerish) and any(
            h in ("", "ticker") or "ticker" in h for h in headerish
        ):
            for i, h in enumerate(headerish):
                if h in ("", "ticker") or h.endswith("ticker"):
                    ticker_idx = i
                if "fv range" in h or h in ("fv", "fv_range"):
                    fv_idx = i
            continue
        if all(set(p) <= set(":- ") for p in parts if p):
            continue
        if ticker_idx is None or fv_idx is None:
            continue
        if ticker_idx >= len(parts) or fv_idx >= len(parts):
            continue
        ticker = parts[ticker_idx].strip().strip("*").strip()
        if not TICKER_RE.match(ticker):
            continue
        cells[ticker] = parts[fv_idx].strip()
    return cells


def _cell_is_question(cell: str) -> bool:
    s = cell.lstrip()
    return s.startswith("?")


def _inbox_file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def main() -> None:
    week, files = _latest_week_files(WIDTH_DIR)
    if not week:
        print("[width_publish_guard] no valuation-width week files found")
        sys.exit(0)

    published = _pick_published_md(files)
    json_path = _pick_json(files, week)
    kind = "revised" if published and "revised" in published.name.lower() else "report"
    print(f"[width_publish_guard] week={week} published={published.name if published else 'NONE'} ({kind})")

    if published and json_path:
        report = _load_json(json_path)
        md_cells = _parse_md_fv_cells(published.read_text(encoding="utf-8", errors="replace"))
        mismatches = 0
        for row in _all_rankings(report):
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            fv_hit, ver_hit = _numeric_json_signal(row)
            if not fv_hit and not ver_hit:
                continue
            md_cell = md_cells.get(ticker)
            if md_cell is None:
                continue
            if _cell_is_question(md_cell):
                mismatches += 1
                bits = []
                if fv_hit:
                    bits.append(f"fv_range={fv_hit}")
                if ver_hit:
                    bits.append(f"verdict={ver_hit}")
                print(
                    f"🔴 mismatch {ticker}: JSON {' '.join(bits)} "
                    f"but {published.name} FV cell is {md_cell[:60]!r}"
                )
        if mismatches == 0:
            print("[width_publish_guard] JSON vs revised FV cells OK")
    elif not published:
        print("[width_publish_guard] 🟡 no published md for latest week")
    elif not json_path:
        print("[width_publish_guard] 🟡 no JSON for latest week")

    leftover = _inbox_file_count(WRONG_INBOX)
    if leftover:
        print(
            f"🟡 warn: {WRONG_INBOX} still has {leftover} file(s) "
            "(wrong relative inbox path; publish uses workspace/reports/inbox)"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
