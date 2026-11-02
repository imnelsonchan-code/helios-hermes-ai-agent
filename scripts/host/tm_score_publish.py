#!/usr/bin/env python3
"""CLIP+RAW helpers for T&M published scores (Option 6 post-weight).

After Option 6 weighting, the **published** total (`tm_score` / aliased
`daily_score` / narrative primary) is a hard clip to [0, 100] rounded to
1 decimal — same display precision as brackets. Do **not** rescale
(no ×100/136).

**Raw bypass:** `weighted_total_raw` is the uncapped weighted sum (may be >100).
**Unweighted:** `base_5indicator_total` stays the 5-leg sum (0–100); this
module does not touch it.

Live engine SSOT: `scripts/host/backtest/score_engine.py` -> host
`~/.hermes/scripts/backtest/score_engine.py` (`compute_all` sets published
`total` + `weighted_total_raw`). Apply via `./scripts/apply-host-scripts.sh`.

Overlays (`pack_meta_stamp`, volume gate, etc.) may defensively clip already-
emitted packs; do not change Option 6 weights / E5 / revise rewrite rules.
"""
from __future__ import annotations

from typing import Any


def clip_published(score: Any) -> float:
    """Hard-clip a weighted total into the published 0–100 band.

    Equivalent to ``min(100, max(0, round(x, 1)))`` after coercing to float.
    Brackets / BUY thresholds must use this published value, not the raw sum.
    """
    x = float(score)
    return min(100.0, max(0.0, round(x, 1)))


def publish_pair(weighted_raw: Any) -> dict[str, float]:
    """Return published clip + uncapped raw for one weighted total.

    Keys:
      - ``published`` — clipped 0–100 (1 decimal)
      - ``weighted_total_raw`` — uncapped weighted sum (1 decimal; may be >100)
    """
    raw = round(float(weighted_raw), 1)
    return {
        "published": clip_published(weighted_raw),
        "weighted_total_raw": raw,
    }
