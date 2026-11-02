---
name: christina-macro-bridge
description: >-
  emily receive-only helper: cite christina rates/FX session for US↔UK commodity
  leg divergence. Hardcodes SOUL §8 three locks. Not Keep; not in daily/weekly
  8-skill load. Status=Receive/optional. Never invent FX_*/B_*/Rate Δbp/DXY Est;
  never rewrite dual-leg C_*.
status: Receive/optional
---

# Christina macro-bridge — Rates/FX receive (not in Keep)

**Owner:** emily · commodities · **Status:** **Receive/optional** (folder exists; **not in** Keep 8-skill load)  
**Cadence:** Daily/Weekly trunk **Rates/FX receive** section may load; same optional pattern as Eval/Sat helper (like `commodity-obs-backtest`: **not in** mandatory sources→…→trunk chain)  
**Not:** daily/weekly Keep mandatory load · invent FX/rates depth · paid API · broker/SimpleFX/IB/Alpaca/RL  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**; `commodity_regime` ≠ desk Risk-on/off

Label "**Not investment advice · observation only**". **miss > invent.**

---

## Purpose

Align christina “FX → emily” three points; on **emily receive side** hard-code SOUL §8 three locks, produce trunk **Rates/FX receive** handoff stub — **cite only**, no rates/FX depth.

---

## When to use

- Session trunk writes **Rates/FX receive** section (Daily ≥1 cite or `miss`; Weekly one paragraph cite or `miss`)  
- Car/same-day christina rates published (or explicit `miss`)  
- **Not:** insert into Keep-8 load; **Not** as mandatory upstream to `commodity-sources-crawl`/signal

---

## RECEIVE-side three locks (hard-coded · SOUL §8)

1. **emily keeps writing** dual-leg prices/mechanism/`C_*`/`commodity_regime` (do not hand commodity work back out).  
2. **Receive only** christina explanation of how FX/real rates/DXY **drive US vs UK leg divergence**; if missing → whole section **`miss`** + one-sentence reason. Real-rate sentences may only verbatim-cite same-day christina revised DFII5/DFII10 (with as-of). If series is DGS* or level equals DGS10 in same doc → that sentence `miss`.  
3. **Do not** rewrite commodity `C_*` into `B_*`/`FX_*`, nor reverse; ❌ self-fill DXY/`DFII*` Est/Rate Δbp/Fed path.

---

## Cite paths (priority)

Pick one auditable path + as-of. Hard priority:

1. **prefer-1:** same-session `inbox/rates-session/*-revised.md` (Zoe→christina revise)  
2. same-session `shared/reports/christina/*-rates-session.md` — **only if** same day/week **AND** inbox miss  
3. else whole receive section **`miss`** + reason (e.g. Car1 missing / no same-session revised / path unreadable)

❌ T-1 / yesterday / prior-session `shared/reports/christina` as live cite (whole section miss)  
❌ invent `FX_*`/`B_*`/Rate Δbp/DXY Est/FedWatch probabilities.  
❌ rewrite dual-leg `C_*`/Obs levels/ten-column tape.  
❌ `C_*`↔`B_*`↔`FX_*` mapping.

---

## Output — trunk Rates/FX receive handoff stub

Hand to **`commodity-session-report`** (trunk) embed; this skill **does not** finalize Regime/Trade map.

```markdown
## Rates/FX receive (cite christina-macro-bridge)

- **Status:** cite | miss
- **Path:** `inbox/rates-session/…-revised.md` | same-session `shared/reports/christina/…-rates-session.md` (inbox miss only) | miss
- **As-of:** …
- **US↔UK leg divergence (one sentence/paragraph):** … (paraphrase christina only; if missing → miss + reason)
- **Locks OK:** emily owns C_* / regime · no invent FX_*/B_*/Δbp/DXY Est · no C_*↔B_*↔FX_*
```

Daily: ≥1 sentence. Weekly: one paragraph.

---

## Handoff

| → | Note |
|---|------|
| → `commodity-session-report` | Rates/FX receive section stub; do not rewrite Scenario/Trade map/`commodity_regime` |
| ↛ Keep-8 chain | **Not in** sources → world → insight → direction → forecast → signal → puzzle → trunk mandatory order |
| ← christina | rates session/revised only; if missing → miss |

---

## Banned

- ❌ invent `FX_*`/`B_*`/Rate Δbp/DXY/DFII Est  
- ❌ rewrite dual-leg `C_*`/ten-column/Obs  
- ❌ blend `tm_score`/`valuation_score`/`rates_signal`  
- ❌ insert into Keep 8-skill load  
- ❌ invent cron IDs / self-pull FRED as rates depth  

---

## Checklist

- [ ] Three locks satisfied line-by-line (or whole section `miss`)  
- [ ] Path is one of cite priorities above, or explicit miss  
- [ ] ❌ no self-filled FX/Rate Est; ❌ no rewrite of `C_*`  
- [ ] ❌ **not in** Keep load order (Receive/optional only)
