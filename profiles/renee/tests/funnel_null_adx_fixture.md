# renee · T&M signal funnel — hygiene fixture(GOOD · null ADX / Option G N/A)

**Purpose:** Lightweight template for scoring *null-ADX funnel hygiene* — Option G is **N/A**, not trending/false.  
**Not:** invent counts · treat null ADX as `option_g_active: false` · rewrite `tm_score`.  
**Mode:** observation only · eval overlay · T sleeve only.

---

## Meta
- **as_of:** 2026-09-22
- **Source:** scoring-eval/2026-09-22-daily-eval.json(fixture · `option_g_skipped` / null ADX)
- **Disclaimer:** Not investment advice · hygiene only · demotions informational

---

## Session summary
- SPY ADX missing / null → Option G path **N/A — ADX missing**.
- Do **not** treat as trending;do **not** set `option_g_active` false as if ADX were present.
- Ranking stays live pack elsewhere;funnel counts deferred / N/A when gate skipped.

---

## § T&M signal funnel(eval overlay — T sleeve only)

| Field | Value |
|-------|-------|
| `spy_adx` | null |
| `option_g_active` | null |
| `option_g_skipped` | true(missing SPY ADX) |
| Option G | **N/A — ADX missing** |
| Theoretical BUY (`buys_theoretical`) | N/A |
| After Option G (`buys_after_option_g`) | N/A |
| After volume gate (`buys_after_volume_gate`) | N/A |
| `volume_demotions[]` | N/A |

Null-ADX path: Option G N/A only — ADX absent;gate skipped(not a trending/false call).

---

## Hygiene scorecard(what the harness asserts)

| Rule | Expected |
|------|----------|
| Funnel section present | yes |
| N/A — ADX missing language | yes |
| Not treated as trending / option_g false-as-applied | yes |
