# renee · T&M signal funnel — BAD fixture（after_G=0 · after_vol>0）

**Purpose:** Intentionally violate `after_G=0 ⇒ after_vol=0` so the audit's negative control can FAIL this file.  
**Do not use as a template for real revise.**

---

## § T&M signal funnel（eval overlay — T sleeve only）

| Field | Value |
|-------|-------|
| Theoretical BUY (`buys_theoretical`) | 4 |
| After Option G (`buys_after_option_g`) | 0 |
| After volume gate (`buys_after_volume_gate`) | 2 |

<!-- BAD: after_G=0 but after_vol>0 (and non-empty demotions would also be wrong) -->

| Label | Count |
|-------|-------|
| Theoretical BUY | 4 |
| After Option G | 0 |
| After volume gate | 2 |
