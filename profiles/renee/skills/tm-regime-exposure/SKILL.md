---
name: tm-regime-exposure
description: >-
  Narrate T&M regime then size or conviction, then the sentence. Daily Option G
  stays the live generator's ADX < 25 gate. Do not rewrite tm_score, do not
  invent a new ADX cutoff, and do not apply Option G on the weekly report.
---

# Regime exposure — market state and sizing (narrative only)

**Owner:** Renee · **Process:** **P-TM** · **When:** daily + weekly T&M narrative  
**Load with:** `skills/tm-e5-firewall` · `skills/tm-session-report`  
**Not:** a new ADX threshold · a live verdict change · a weekly Option G banner · blending Book V

Mark "Not investment advice". This skill only explains regime / SPY ADX / verdict already written in the daily pack. It does not change `tm_score` or Option 6 weights.

---

## Gate order

1. **Regime** — cite the pack: `trending` / `ranging` / `choppy` / `volatile`, plus SPY ADX and VIX when the pack has them.
2. **Size / threshold** — say what that regime means for exposure:
   - trending → full scoring language
   - ranging / choppy → higher conviction, smaller size (narrative)
   - volatile → smaller size
3. **Narrate** — then the session prose. Do not invent a second cutoff.

Daily live trades still follow the generator: SPY ADX < 25 (`choppy`) rewrites the verdict to `NO SIGNAL (choppy market)`. This skill reports that fact. It does not reopen those names.

Weekly: **no Option G**. Do not suppress weekly BUY counts for ADX < 25.

---

## What to say when choppy

First line of the exposure note, from the pack only:

- SPY ADX value
- `ADX < 25`
- today is no-trade under Option G
- the held-back list is every non-BUY with published score ≥ 60 (not only ≥ 90)

If the pack has no SPY ADX, say **N/A — ADX missing**. Do not treat a missing ADX as trending.

---

## Hard no

- Do not change 25.
- Do not replace the hard suppress with a size-only rule unless a new backtest has already changed the generator.
- Do not copy `valuation_score` or Book V into this note.
