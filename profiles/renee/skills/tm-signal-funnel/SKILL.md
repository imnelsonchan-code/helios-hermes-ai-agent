---
name: tm-signal-funnel
description: >-
  Renee § T&M signal funnel cite from scoring-eval daily-eval fields. N/A if
  missing; null ADX → N/A not trending; monotonic theo≥after_G≥after_vol;
  three labels; demotions do not change tm_score; Saturday Mon–Fri roll-up;
  never invent counts; never cite value_hit_rate / Book V.
---

# T&M signal funnel — signal funnel(eval overlay · T sleeve only)

**Owner:** Renee · **Process:** **P-TM** · **When:** daily T&M revise（and Saturday roll-up）  
**Load with:** `skills/tm-session-report`（place section after `## Lenses` / before ranking）；shared `trading/technical-analysis` as needed  
**Not:** invent funnel counts · rewrite `tm_score` from demotions · cite Book V / `value_hit_rate` · Alice-owned funnel

Mark "Not investment advice".Eval overlays are **narrative gates** — they do **not** change Option 6 weights。

---

## When to use

- **Daily T&M revise** when `scoring-eval/*-daily-eval.json` exists → cite § T&M signal funnel
- **3-layer eval lookup：** prefer `shared/reports/renee/scoring-eval/`，then workspace sibling；cite basename `scoring-eval/*-daily-eval.json`
- Missing at revise time → **N/A + pending**；do **not** invent
- **Saturday self-review** — roll-up = aggregate **Mon–Fri** daily-eval JSON（not weekly-eval alone for funnel counts）
- **Not** for value-sleeve / Paper Book V narratives

---

## Cite fields（daily-eval）

When the file exists, after `## Lenses` / before ranking, add:

**§ T&M signal funnel（eval overlay — T sleeve only）**

Cite（names as present in JSON）:

| Field | Role |
|-------|------|
| `spy_adx` | SPY ADX as-of |
| `option_g_active` | Option G flag |
| `buys_theoretical` / `theoretical_buys` | Theoretical BUY count |
| `buys_after_option_g` | After Option G |
| `buys_after_volume_gate` | After volume gate |
| `volume_demotions[]` | Informational demotions |

### Null / missing ADX

If `option_g_active` is JSON `null` **or** `option_g_skipped` present（missing SPY ADX）→ say **N/A — ADX missing**.  
Do **not** treat as trending（`false`）.

### Monotonicity

Eval counts must be **monotonic**:

```text
theo ≥ after_G ≥ after_vol
```

If `after_G = 0` ⇒ `after_vol = 0` and empty demotions. Flag inconsistency；do not invent fixes.

---

## Three distinct labels

| Label | Meaning |
|-------|---------|
| **Theoretical BUY** | `tm_score` / `daily_score` ≥60（score ladder） |
| **After Option G** | daily only；SPY ADX &lt;25 may suppress effective BUY |
| **After volume gate** | survives Option G **then** volume confirmation；fail → demote WATCH；**`tm_score` unchanged** |

Ranking stays **live pack**. Demotions are **informational** — demotions **do not** change `tm_score`.

(Book V empty/zero Candidates → Eliza/P-VAL concern, not owned by T-sleeve funnel。）

---

## Saturday roll-up

- Funnel roll-up = aggregate **Mon–Fri** `scoring-eval/*-daily-eval.json`（`buys_theoretical` → `buys_after_option_g` → `buys_after_volume_gate`, `volume_demotions`）
- **Never** invent funnel counts from `weekly-eval.json` alone
- Cite `book_t` + `settlement.tm_hit_rate` from **prior-week / latest available** `*-weekly-eval.json` when present；**N/A** if missing
- ❌ **Never** cite `value_hit_rate` or Book V here

---

## Hard rules

- **Never invent** funnel counts, demotion lists, or hit rates
- Missing JSON → **N/A**（+ pending on daily revise）
- Null ADX → **N/A — ADX missing**；not “trending”
- Demotions do **not** rewrite `tm_score` or live ranking brackets
- ❌ `value_hit_rate` · Book V · Eliza width funnel language
- ❌ Fold volume-gate / Option G into a new blended score

---

## Banned

- Invented counts from narrative memory  
- Treating weekly-eval as Mon–Fri funnel source  
- Citing value-sleeve settlement fields  
- Changing brackets because of demotion footnotes  
