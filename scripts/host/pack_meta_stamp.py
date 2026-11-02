#!/usr/bin/env python3
"""Stamp pack meta fields needed by P0/P1 overlays (fail-closed).

Promotes fields already present in live packs into a stable contract:
  - meta.spy_adx / row.spy_adx context (from pack spy_adx)
  - row.volume_ratio (from raw_indicators.volume_ratio)
  - row.tm_score alias of daily_score when missing
  - row.theoretical_bracket always from score ladder (≥60 BUY / ≥50 WATCH)
  - row.bracket = live daily_bracket words when present; else score ladder
  - value.statement_as_of / meta.statement_as_of from pack date/week/as_of
  - meta.pack_meta_stamped = true
  - Defensive CLIP+RAW: if tm_score/daily_score >100, clip published fields
    and preserve original into weighted_total_raw when missing
    (belt-and-suspenders — live engine compute_all remains SSOT)

Never changes Option 6 weights or valuation_score arithmetic.
Theoretical BUY (eval funnel) must use theoretical_bracket / score≥60 —
never live DMI daily_bracket alone. Brackets use published (clipped) score.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tm_score_publish import clip_published  # noqa: E402


def _as_of(pack: dict) -> str | None:
    for key in ("data_as_of", "as_of", "date", "expected_as_of", "week"):
        val = pack.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            return text[:10] if key != "week" else text
    return None


def _iter_tm_rows(pack: dict) -> list[dict]:
    rows: list[dict] = []
    for key in ("results", "rows", "signals", "rankings"):
        block = pack.get(key)
        if isinstance(block, list):
            rows.extend(r for r in block if isinstance(r, dict))
    return rows


def _iter_value_rows(pack: dict) -> list[dict]:
    rows: list[dict] = []
    rankings = pack.get("rankings")
    if isinstance(rankings, list):
        rows.extend(r for r in rankings if isinstance(r, dict))
    tracks = pack.get("tracks")
    if isinstance(tracks, dict):
        for track in tracks.values():
            if isinstance(track, dict):
                block = track.get("rankings")
                if isinstance(block, list):
                    rows.extend(r for r in block if isinstance(r, dict))
    return rows


_BRACKET_WORDS = frozenset({"BUY", "WATCH", "SELL", "NO_SIGNAL", "AVOID"})


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_ladder_bracket(score: float | None) -> str | None:
    """Theoretical / score-ladder bracket. Independent of live DMI labels."""
    if score is None:
        return None
    if score >= 60:
        return "BUY"
    if score >= 50:
        return "WATCH"
    return "NO_SIGNAL"


def stamp_tm_pack(pack: dict) -> dict:
    out = copy.deepcopy(pack)
    meta = dict(out.get("meta") or {})
    spy = out.get("spy_adx")
    if spy is not None:
        meta["spy_adx"] = spy
    as_of = _as_of(out)
    if as_of:
        meta["as_of"] = as_of
    for row in _iter_tm_rows(out):
        score = row.get("tm_score")
        if score is None and row.get("daily_score") is not None:
            row["tm_score"] = row["daily_score"]
            score = row["daily_score"]
        s = _to_float(score)
        ds = _to_float(row.get("daily_score"))
        # Defensive CLIP+RAW (not engine SSOT — belt-and-suspenders)
        over = None
        if s is not None and s > 100:
            over = s
        elif ds is not None and ds > 100:
            over = ds
        if over is not None:
            if row.get("weighted_total_raw") is None:
                row["weighted_total_raw"] = round(over, 1)
            published = clip_published(over)
            row["tm_score"] = published
            if row.get("daily_score") is not None:
                row["daily_score"] = published
            s = published
        ladder = _score_ladder_bracket(s)
        # Always stamp theoretical from score ladder (funnel / Alice-Zoe contract)
        if ladder is not None:
            row["theoretical_bracket"] = ladder
        # Live narrative bracket: prefer explicit daily_bracket words; else ladder.
        # Score bands like "60-69" are not BUY labels — fall through to ladder.
        explicit = str(row.get("bracket") or "").strip().upper()
        daily_b = str(row.get("daily_bracket") or "").strip().upper()
        if daily_b in _BRACKET_WORDS:
            row["bracket"] = daily_b
        elif explicit in _BRACKET_WORDS:
            pass
        elif ladder is not None:
            row["bracket"] = ladder
        if row.get("daily_verdict"):
            row["option_g_verdict"] = row["daily_verdict"]
        if row.get("volume_ratio") is None:
            raw = row.get("raw_indicators")
            if isinstance(raw, dict) and raw.get("volume_ratio") is not None:
                row["volume_ratio"] = raw["volume_ratio"]
        raw = row.get("raw_indicators") if isinstance(row.get("raw_indicators"), dict) else {}
        if row.get("dmi_plus") is None and raw.get("plus_di") is not None:
            row["dmi_plus"] = raw["plus_di"]
        if row.get("dmi_minus") is None and raw.get("minus_di") is not None:
            row["dmi_minus"] = raw["minus_di"]
        if row.get("last") is None and row.get("price") is not None:
            row["last"] = row["price"]
    meta["pack_meta_stamped"] = True
    meta["sleeve"] = "tm"
    out["meta"] = meta
    return out


def stamp_value_pack(pack: dict) -> dict:
    out = copy.deepcopy(pack)
    meta = dict(out.get("meta") or {})
    as_of = _as_of(out)
    value_meta = dict(meta.get("value") or {}) if isinstance(meta.get("value"), dict) else {}
    if as_of:
        meta["as_of"] = as_of
        value_meta["statement_as_of"] = as_of
        value_meta["as_of"] = as_of
        out["statement_as_of"] = as_of
    for row in _iter_value_rows(out):
        if row.get("close") is None and row.get("price") is not None:
            row["close"] = row["price"]
        # Normalize emoji verdicts already present as width_verdict
        verdict = str(row.get("width_verdict") or "").strip()
        if verdict == "🟢" and not row.get("status"):
            row["status"] = "Candidate"
        elif verdict in ("🟡", "🔴") and not row.get("status"):
            row["status"] = "Watch" if verdict == "🟡" else "Avoid"
    meta["value"] = value_meta
    meta["pack_meta_stamped"] = True
    meta["sleeve"] = "value"
    out["meta"] = meta
    return out


def stamp_pack(pack: dict, *, sleeve: str | None = None) -> dict:
    kind = (sleeve or "").strip().lower()
    if not kind:
        if "results" in pack or pack.get("spy_adx") is not None:
            kind = "tm"
        elif "tracks" in pack or "valuation-width" in str(pack.get("report_type", "")):
            kind = "value"
        else:
            kind = "tm"
    if kind in ("tm", "t&m", "trend"):
        return stamp_tm_pack(pack)
    if kind in ("value", "val", "width"):
        return stamp_value_pack(pack)
    raise ValueError(f"unknown sleeve: {sleeve}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stamp P0/P1 pack meta fields")
    parser.add_argument("--pack", required=True, help="Input pack JSON")
    parser.add_argument("--sleeve", choices=("tm", "value", "auto"), default="auto")
    parser.add_argument("--out", required=True, help="Output stamped JSON")
    args = parser.parse_args(argv)

    try:
        pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[pack_meta_stamp] read failed: {exc}", file=sys.stderr)
        return 2
    if not isinstance(pack, dict):
        print("[pack_meta_stamp] pack must be object", file=sys.stderr)
        return 2

    sleeve = None if args.sleeve == "auto" else args.sleeve
    try:
        out = stamp_pack(pack, sleeve=sleeve)
    except ValueError as exc:
        print(f"[pack_meta_stamp] {exc}", file=sys.stderr)
        return 2

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"[pack_meta_stamp] wrote {args.out} sleeve={out.get('meta', {}).get('sleeve')} "
        f"as_of={out.get('meta', {}).get('as_of')} spy_adx={out.get('meta', {}).get('spy_adx')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
