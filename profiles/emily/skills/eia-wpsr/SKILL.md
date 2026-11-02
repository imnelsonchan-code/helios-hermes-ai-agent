---
name: eia-wpsr
description: >-
  emily Later stub: EIA Weekly Petroleum Status Report (WPSR) inventory lens for Oil.
  Consume-or-miss only. Not Keep; not in daily/weekly load. Status=Later until a stable
  host artifact exists. Cite-or-miss; miss>invent; no paid APIs; handoff to insight/
  direction/forecast. Do not invent cron IDs.
status: Later
---

# EIA WPSR — weekly inventory lens (Later stub)

**Owner:** emily · commodities · **Status:** **Later/Stub** (folder exists; **not in** Keep 8-skill load)  
**Not:** daily/weekly mandatory load · invent inventory numbers · paid API · broker/SimpleFX/IB/Alpaca/RL  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "**Not investment advice · observation only**".

---

## When to use

- **Later only** — only when the host already has a **stable, citable** WPSR/EIA weekly inventory artifact (path + as-of)  
- Adhoc/Sat backlog evaluating whether to upgrade to Keep — read this stub  
- **Not:** daily session load; **Not** force-run when no artifact exists

---

## Hard rules

1. **cite-or-miss only** — write only with auditable outlet + date/as-of + URL/path; paywall/missing/stale → `miss`  
2. **miss > invent** — ❌ guess inventory Δ, fake "consensus", fake surprise  
3. **No paid APIs** — ❌ OilPriceAPI/LSEG/Bloomberg/FactSet/ICE Fundamentals paid  
4. **Handoff:** may pass cite sentences to **`commodity-insight`** → **`commodity-direction`** → **`commodity-forecast`**; ❌ this stub writes `C_*`/`DIR_*`/Obs levels/Est  
5. **Status = Later** until stable host artifact exists; upgrading to Keep requires SOUL/checklist/load updates  
6. **Do not invent cron IDs** — do not write/guess EIA cron; consume existing artifact or `miss`

---

## Intended scope (after upgrade)

| Item | Note |
|------|------|
| Source | EIA WPSR — official https://www.eia.gov/petroleum/supply/weekly/ (or eia.gov Open Data; public page / landed mirror) |
| Lens | Oil inventory cadence → Insight Drivers/complex (cite-or-miss) |
| Cadence | weekly (public window) |
| Status | **Later/Stub** — **not** Keep-8/daily/weekly load |

---

## Checklist (stub)

- [ ] Host artifact path documented (not yet → remain Later)  
- [ ] ❌ insert into 8-skill Keep load  
- [ ] ❌ invent cron ID/paid fill
