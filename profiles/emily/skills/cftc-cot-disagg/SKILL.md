---
name: cftc-cot-disagg
description: >-
  emily Later stub: weekly CFTC Disaggregated COT (Managed Money / commercial) lens.
  Consume-or-miss only. Not Keep; not in daily/weekly load. Status=Later until a stable
  host artifact exists. Cite-or-miss; miss>invent; no paid APIs; handoff to insight/
  direction/forecast. Do not invent cron IDs.
status: Later
---

# CFTC Disagg COT — weekly positioning lens (Later stub)

**Owner:** emily · commodities · **Status:** **Later/Stub** (folder exists; **not in** Keep 8-skill load)  
**Not:** daily/weekly mandatory load · invent net positioning/weekly change · paid API · broker/SimpleFX/IB/Alpaca/RL  
**Firewall:** display **"emily · commodities"**; voice never written as broker **Emily**

Label "**Not investment advice · observation only**".

---

## When to use

- **Later only** — only when the host already has a **stable, citable** Disagg COT artifact (path + week/as-of)  
- Adhoc/Sat backlog evaluating upgrade to Keep — read this stub  
- **Not:** daily session load; **Not** COT-only fill for `C_*`/Est; **Not** force-run without artifact

---

## Hard rules

1. **cite-or-miss only** — Disagg Managed Money (or auditable bucket) outlet + week/as-of + URL/path; paywall/missing → `miss`  
2. **miss > invent** — ❌ guess net positioning, fake crowdedness, fake weekly change  
3. **No paid APIs** — ❌ Bloomberg/FactSet/LSEG paid COT feeds  
4. **Handoff:** cite sentences to **`commodity-insight`** → **`commodity-direction`** → **`commodity-forecast`**; ❌ this stub writes Trade map/`C_*`/Obs levels  
5. **Status = Later** until stable host artifact exists  
6. **Do not invent cron IDs** — do not write/guess CFTC/COT cron; consume existing artifact or `miss`

---

## Intended scope (after upgrade)

| Item | Note |
|------|------|
| Source | CFTC Disaggregated Commitments of Traders (public / landed mirror) |
| Lens | crowdedness / weekly change one-liner → Direction filter (not intraday primary signal) |
| Cadence | weekly |

---

## Checklist (stub)

- [ ] Host artifact path documented (not yet → remain Later)  
- [ ] ❌ insert into 8-skill Keep load  
- [ ] ❌ invent cron ID/paid fill; ❌ COT-only → `C_*`/Est
