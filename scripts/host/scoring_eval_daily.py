#!/usr/bin/env python3
"""Daily scoring-eval overlays (no-agent cron entrypoint).

After Daily T&M pack exists:
  1. stamp pack meta (spy_adx, volume_ratio, tm_score aliases)
  2. apply volume BUY gate (report only — does not rewrite live pack)
  3. emit T&M prediction JSONL
  4. write eval summary under shared/reports/renee/scoring-eval/

Silent (exit 0, empty-ish stdout) when no pack for session date.
Never blends value sleeve. Never edits Option 6 weights.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPTS = Path.home() / ".hermes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pack_meta_stamp import stamp_tm_pack  # noqa: E402
from prediction_emit import append_jsonl, emit_tm_predictions  # noqa: E402
from tm_volume_gate import apply_volume_gate  # noqa: E402
from tm_variant import (  # noqa: E402
    OPTION_G_SPY_ADX_THRESHOLD,
    apply_variant_to_pack,
)

# Pack search order (first hit wins for YYYY-MM-DD-data.json):
# 1. renee workspace (desk pack prompts: profiles/renee/workspace/daily-trend-momentum/)
# 2. shared mirror (shared/reports/renee/daily-trend-momentum/)
# 3. legacy workspace/reports/ path
TM_DIRS = [
    Path.home() / ".hermes" / "profiles" / "renee" / "workspace" / "daily-trend-momentum",
    Path.home() / ".hermes" / "shared" / "reports" / "renee" / "daily-trend-momentum",
    Path.home() / ".hermes" / "profiles" / "renee" / "workspace" / "reports" / "daily-trend-momentum",
]
OUT_DIR = Path.home() / ".hermes" / "shared" / "reports" / "renee" / "scoring-eval"
INBOX_DIR = Path.home() / "workspace" / "reports" / "inbox" / "scoring-eval"
PRED_PATH = OUT_DIR / "predictions-tm.jsonl"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _publish(path: Path, payload: dict) -> None:
    _write_json(path, payload)
    # Mirror into inbox so sync_reports_www publishes to Jobs portal
    _write_json(INBOX_DIR / path.name, payload)


def _session() -> date:
    return datetime.now(timezone.utc).date()


def _find_pack(session: date) -> Path | None:
    """Require same-session daily pack — never silently reuse a stale date."""
    name = f"{session.isoformat()}-data.json"
    for d in TM_DIRS:
        p = d / name
        if p.is_file():
            return p
    return None


def compute_funnel_counts(variant_rows: list) -> dict:
    """Nested funnel: theoretical -> Option G -> volume (monotonic counts).

    Only theoretical BUY rows enter the funnel. Option G / volume are demotions
    inside that set — so DMI promotions (WATCH->effective BUY without score≥60)
    never inflate after_G above theo. Volume gate runs only when both
    theoretical and effective_bracket are BUY. Mutates rows in place with
    volume_gated_bracket / volume_gate_reason when gated. Never touches
    valuation or live packs.
    """
    buys_theoretical = 0
    buys_after_option_g = 0
    buys_after_volume = 0
    demotions: list[dict] = []

    for row in variant_rows:
        if not isinstance(row, dict):
            continue
        if not is_theoretical_buy(row):
            continue
        buys_theoretical += 1

        after_g = str(row.get("effective_bracket") or "").upper()
        if after_g != "BUY":
            continue
        buys_after_option_g += 1

        # Volume gate only after Option G survival (effective BUY ⊂ theo BUY)
        gated, reason = apply_volume_gate(row)
        row["volume_gated_bracket"] = gated
        if reason:
            row["volume_gate_reason"] = reason
            demotions.append(
                {
                    "ticker": row.get("ticker"),
                    "reason": reason,
                    "volume_ratio": row.get("volume_ratio"),
                    "tm_score": row.get("tm_score") or row.get("daily_score"),
                }
            )
        elif gated == "BUY":
            buys_after_volume += 1

    return {
        "buys_theoretical": buys_theoretical,
        "buys_after_option_g": buys_after_option_g,
        "buys_after_volume_gate": buys_after_volume,
        "volume_demotions": demotions,
    }


def assert_funnel_monotonic(funnel: dict) -> None:
    """Raise ValueError if funnel counts are corrupt / non-monotonic.

    Expects keys from ``compute_funnel_counts``. When after_G is 0, volume
    demotions must be empty and after_vol must be 0.
    """
    theo = int(funnel.get("buys_theoretical") or 0)
    after_g = int(funnel.get("buys_after_option_g") or 0)
    after_vol = int(funnel.get("buys_after_volume_gate") or 0)
    demotions = funnel.get("volume_demotions") or []

    if not (theo >= after_g >= after_vol):
        raise ValueError(
            f"non-monotonic funnel: theo={theo} after_g={after_g} after_vol={after_vol}"
        )
    if after_g == 0:
        if demotions:
            raise ValueError(
                f"after_g=0 but volume_demotions non-empty ({len(demotions)})"
            )
        if after_vol != 0:
            raise ValueError(f"after_g=0 but after_vol={after_vol}")


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_theoretical_buy(row: dict) -> bool:
    """Score-ladder Theoretical BUY (independent of live DMI daily_bracket).

    Prefer stamped ``theoretical_bracket``; else score≥60; else legacy
    ``bracket==BUY`` only when no score is present (unit-test helpers).
    """
    theo = str(row.get("theoretical_bracket") or "").strip().upper()
    if theo:
        return theo == "BUY"
    score = _to_float(row.get("tm_score"))
    if score is None:
        score = _to_float(row.get("daily_score"))
    if score is not None:
        return score >= 60
    return str(row.get("bracket") or "").strip().upper() == "BUY"


def build_summary(
    *,
    session: date,
    pack_path: Path | str,
    spy_f: float | None,
    theo_buys: list,
    funnel: dict,
    preds_count: int,
    predictions_path: Path | str = PRED_PATH,
) -> dict:
    """Build daily-eval summary dict (no I/O).

    When ``spy_f`` is None, ``option_g_active`` is JSON null and
    ``option_g_skipped`` is set — do not report false as if market were trending.
    """
    if spy_f is None:
        option_g_active = None
        option_g_skipped = "missing_spy_adx"
    else:
        option_g_active = spy_f < OPTION_G_SPY_ADX_THRESHOLD
        option_g_skipped = None

    note = (
        "funnel: theoretical BUY -> Option G -> volume gate; "
        "counts monotonic theo ≥ after_G ≥ after_vol; "
        "volume gate only on effective BUY (post Option G); "
        f"Option G threshold={OPTION_G_SPY_ADX_THRESHOLD} "
        "(missing spy_adx -> option_g_active null, no demote)"
    )

    summary: dict = {
        "job": "scoring_eval_daily",
        "session": session.isoformat() if hasattr(session, "isoformat") else str(session),
        "pack": str(pack_path),
        "spy_adx": spy_f,
        "option_g_active": option_g_active,
        "theoretical_buys": theo_buys,
        "buys_theoretical": len(theo_buys),
        "buys_after_option_g": funnel["buys_after_option_g"],
        "buys_after_volume_gate": funnel["buys_after_volume_gate"],
        "volume_demotions": funnel["volume_demotions"],
        "predictions_emitted": preds_count,
        "predictions_path": str(predictions_path),
        "e5_note": "T&M sleeve only — never blends valuation_score",
        "note": note,
    }
    if option_g_skipped is not None:
        summary["option_g_skipped"] = option_g_skipped
    return summary


def main() -> int:
    session = _session()
    pack_path = _find_pack(session)
    if pack_path is None:
        print(f"[scoring_eval_daily] no T&M pack for {session} — skip")
        return 0

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    stamped = stamp_tm_pack(pack)
    spy_adx = stamped.get("spy_adx")
    try:
        spy_f = float(spy_adx) if spy_adx is not None else None
    except (TypeError, ValueError):
        spy_f = None

    # Theoretical BUYs from score ladder (pre Option G) — not live daily_bracket
    theo_buys = []
    for row in stamped.get("results") or stamped.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if is_theoretical_buy(row):
            theo_buys.append(row.get("ticker"))

    # Missing spy_adx: still run variant (no demote); skip is explicit in summary
    variant = apply_variant_to_pack(
        stamped, "control", spy_adx=spy_f, timeframe="daily"
    )
    rows = variant.get("results") or variant.get("rows") or []
    funnel = compute_funnel_counts(rows)
    try:
        assert_funnel_monotonic(funnel)
    except ValueError as exc:
        print(f"[scoring_eval_daily] corrupt funnel — refuse publish: {exc}", file=sys.stderr)
        return 2

    buys_after_option_g = funnel["buys_after_option_g"]
    buys_after_volume = funnel["buys_after_volume_gate"]
    demotions = funnel["volume_demotions"]

    preds = emit_tm_predictions(stamped, horizon_days=7)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    append_jsonl(PRED_PATH, preds)

    summary = build_summary(
        session=session,
        pack_path=pack_path,
        spy_f=spy_f,
        theo_buys=theo_buys,
        funnel=funnel,
        preds_count=len(preds),
        predictions_path=PRED_PATH,
    )
    out_path = OUT_DIR / f"{session.isoformat()}-daily-eval.json"
    _publish(out_path, summary)

    print(
        f"[scoring_eval_daily] {session} pack={pack_path.name} "
        f"spy_adx={spy_f} theoretical_BUY={len(theo_buys)} "
        f"after_OptionG={buys_after_option_g} after_vol={buys_after_volume} "
        f"vol_demote={len(demotions)} preds={len(preds)}"
        + (f" option_g_skipped={summary.get('option_g_skipped')}" if spy_f is None else "")
    )
    if demotions:
        for d in demotions[:12]:
            print(f"  demote {d['ticker']} score={d['tm_score']} vol={d['volume_ratio']}")
    print(f"wrote {out_path}")
    print(f"inbox {INBOX_DIR / out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
