# Structure TP proposal — rejected

Operational note. Non-investment advice.

## Status

**Not adoptable.** Two rounds of independent multi-agent audit rejected
`atr-structure-v1` (structure-banded TP1 + higher-low trail) as written.

Adopt path for trailing exits is the existing **`atr-chandelier-v1`** policy
documented in [`TP-PROPOSAL.md`](TP-PROPOSAL.md) and
[`SL-TP-AUDIT.md`](SL-TP-AUDIT.md):

- TP1 frozen at `F + 2R`, ~1/3 tranche, no fixed TP2
- Close-based Chandelier trail at `k = 4.0` via propose / owner `TRAIL_SL`
- Live default remains `atr-r-v2` until explicit `--policy atr-chandelier-v1 --adopt`

## Why structure was rejected

Cross-model consensus (8 lenses):

- Measured-move as a TP1 candidate: **drop** (8/8)
- Band `[1.0R, 2.5R]` for structure TP1: **unsupported** (prefer frozen 2R)
- Higher-low trail is non-monotone vs `highest_close`, lags ~3 sessions behind
  a pivot, and often cannot engage inside the ~10-session time-stop window on
  T&M breakouts (`NO_STRUCTURE` is the modal case when fill is at range highs)
- Variable TP1 harms the owner ritual; swing identification invites override

See the plan audit notes in-repo and agent transcripts for full ballots.

## Do not implement

- Pivot / measured-move TP1 scanners as live plan inputs
- Nightly recomputed targets (Type C)
- Auto-breakeven or `(SL0, F]` “protection” raises without an MFE gate
