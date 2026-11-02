# Scoring enhancements (P0 / P1)

Host scripts under `scripts/host/` implement **evaluation overlays** — gates,
shadow packs, and sizing clamps that sit **beside** live scoring engines. They
do **not** replace Option 6 T&M weights or Eliza five-factor valuation weights.

## E5 — never blend sleeves

- **T&M** (`tm_score`, `score_breakdown`) and **value** (`valuation_score`,
  `valuation_score_breakdown`) stay separate.
- Overlap tickers get **two labels**, never a blended score or unified rank.
- Overlays may WARN or demote within a sleeve; they must not copy one sleeve’s
  number into the other.

## What changes scores vs gates

| Layer | Changes numeric score? | Changes bracket / verdict? | Examples |
|-------|------------------------|----------------------------|----------|
| Live engine | Yes | Yes | Option 6 T&M; Eliza 33/28/19/15/5 width |
| Shadow variant | No (`shadow_tm_score` only for `equal_weights`) | Yes (effective bracket) | `tm_variant.py` |
| Volume gate | No | Yes (BUY→WATCH) | `tm_volume_gate.py` |
| Value vetoes | No | Yes (block Candidate) | `value_veto.py` |
| FCF FV bands | No | Informational / optional second FV | `fcf_fv_bands.py` |
| Vol×corr size | No | Position cap only | `vol_corr_size.py` |

**CLIP+RAW (published T&M total):** Hard clip of the Option 6 **weighted** sum to published 0–100 (`tm_score` / `daily_score`) plus optional uncapped `weighted_total_raw` is a **live-engine** concern (`compute_all` SSOT). Repo helper: `scripts/host/tm_score_publish.py`; `pack_meta_stamp` may defensively clip already-emitted packs. **Overlays still do not change Option 6 weights** (no rescale ×100/136).

## P0 (eval / audit)

| Script | Sleeve | Role |
|--------|--------|------|
| `sleeve_paper_book` | T / V | Independent paper books (MTM); never blended `final_score` |
| `prediction_settler` | T / V | Settle predictions; separate `tm_hit_rate` / `value_hit_rate` |
| `value_ic_tracker` | V | Spearman IC vs forward returns; optional separate quality series |
| `pit_checklist` | both / Alice | Point-in-time audit (`statement_as_of`, news window, NaN bar, memory, FRED) |
| `tm_snapshot_verify` | T | Narrative claims vs engine pack; rejects value-sleeve fields |

## P1 (this batch)

### T&M — `tm_variant.py`

- **`variant_key`**: `control` \| `no_option_g` \| `dmi_off` \| `equal_weights`
- Stamps `meta.variant_key`; `control` also sets `meta.scoring_contract=option6_v4.4`.
- **`apply_shadow_gates`**: effective BUY/WATCH/NO_SIGNAL without rewriting
  `tm_score` (except `equal_weights` writes **`shadow_tm_score`** only).
- **Option G** (**daily only**): `control` demotes BUY→WATCH when
  `spy_adx < OPTION_G_SPY_ADX_THRESHOLD` (25; overridable via `--adx-threshold`);
  `no_option_g` ignores SPY ADX; **weekly** packs never apply Option G
  (`--timeframe weekly`). Missing `spy_adx` skips demote; daily-eval sets
  `option_g_active: null` + `option_g_skipped: "missing_spy_adx"` (not `false`).
  Publish refuses non-monotonic funnel (`theo ≥ after_G ≥ after_vol`) with exit 2.

### T&M — `tm_volume_gate.py`

- After an effective **BUY**, require volume confirmation:
  `volume_ratio > 1.0` **or** `score_breakdown.volume >= 12` (of 20).
- Failure **demotes to WATCH**; `tm_score` unchanged.
- Daily-eval funnel (`scoring_eval_daily`): volume gate is applied **only**
  after effective BUY (post Option G) for nested metrics
  (`theo ≥ after_G ≥ after_vol`).

### Value — `value_veto.py`

- Extra vetoes (solvency, dilution, ROE, F-Score, accounting 🚨) return
  `{vetoes, allowed_candidate}` — never writes `valuation_score`.

### Value — `fcf_fv_bands.py`

- Second-width engine: **`fv_engine: fcf_band_10_15_20`**
- FV per share = normalized FCF × {10, 15, 20} / shares.
- Candidate floor unchanged: **≥+15% upside** vs chosen band.

### Both sleeves — `vol_corr_size.py`

- **`position_cap_pct(ann_vol, avg_corr)`** — max name weight after vol and
  correlation overlays; does not edit scores or brackets.

## Contract summary

- **E5:** Never blend sleeve scores; overlap is WARN only.
- **P1 scripts** change gates / shadow / size only — not live formula weights.
- T&M: `tm_variant` shadow pack; `tm_volume_gate` volume confirmation; `vol_corr_size` position cap.
- Value: `value_veto` extra vetoes; `fcf_fv_bands` optional second FV band.

## Production wiring (2026-09-15)

Live Hermes host now has:

| Job | Id | Schedule | Script |
|-----|-----|----------|--------|
| Scoring eval daily | `<scoring-eval-daily-job-id>` | Mon–Fri 23:59 | `scoring_eval_daily.py` |
| Scoring IC → eval weekly | `<scoring-ic-weekly-job-id>` | Sun 19:00 | `scoring_ic_eval_train.sh` (IC then `scoring_eval_weekly.py`) |

Apply pool: sync `scripts/host/` onto the Hermes host with your private apply path.

- After Option G ADX P0 hardening (`tm_variant.py` + `scoring_eval_daily.py`), sync the host script pool and re-apply Renee SOUL funnel cite rules via that private path before the next `<scoring-eval-daily-job-id>` run.

Pack meta contract (promoted by `pack_meta_stamp.py`, not invented):

- T&M: `spy_adx`, `volume_ratio` (from `raw_indicators`), `tm_score`←`daily_score`, **`theoretical_bracket` always from score≥60 ladder** (live `daily_bracket` words stay on `bracket` only; score bands like `60-69` are not BUY labels)
- Value: `meta.value.statement_as_of` from week/`as_of`

Predictions: `prediction_emit.py` appends JSONL; weekly job settles due rows into separate `tm_hit_rate` / `value_hit_rate`.

**Still eval-only:** overlays do not change live Option 6 weights, width factors, or published BUY/Candidate tables.

Daily and weekly scoring-eval crons are measurement-only; they do not change live selection tables.
