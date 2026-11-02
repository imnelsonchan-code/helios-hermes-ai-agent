# renee · T&M signal funnel — BAD fixture（negative control）

**Purpose:** Intentionally violate funnel monotonicity so the audit's negative control can FAIL this file.  
**Do not use as a template for real revise.**

---

## § T&M signal funnel（eval overlay — T sleeve only）

| Field | Value |
|-------|-------|
| Theoretical BUY (`buys_theoretical`) | 2 |
| After Option G (`buys_after_option_g`) | 5 |
| After volume gate (`buys_after_volume_gate`) | 4 |

<!-- BAD: invented non-monotonic theo < after_G (2 < 5) -->

| Label | Count |
|-------|-------|
| Theoretical BUY | 2 |
| After Option G | 5 |
| After volume gate | 4 |
