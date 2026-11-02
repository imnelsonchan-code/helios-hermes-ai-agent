---
name: position-plan-dispatch
description: >-
  Alice dispatches a position-watch comment. Anyone assigned must write their
  own role's comment and analysis, even when the name is missing from the
  daily or weekly report.
---

# Position-watch dispatch

**Owner:** Alice · **Not:** writing the trend, value, rates, or commodity comment · **Not:** a new inbox file

Mark "Not investment advice". Sarah posts the card first; Alice only picks assignees. Sarah runs `kanban_create` from this list only — do not change assignees.

If no deadline is stated, ask first — do not dispatch.

Anyone assigned must submit a comment and analysis. Absence from the daily or weekly report is not a reason to stop writing; investigate in `## Position comments` per your role. Do not write only `miss`, and do not write “not in the report, so no view.”

## Equities

Dispatch both specialists; each writes their own piece. Short-term: Renee’s trend block is the decision frame; long-term: Eliza’s value block is the decision frame. The other specialist still writes a full role analysis — do not collapse to one line.

- **Short-term:** `renee` trend analysis. `eliza` value analysis.
- **Long-term:** `eliza` value analysis. `renee` trend analysis.
- If Renee or Eliza says the name is not an equity → retract the equity path and use the claim path.

## Non-equities

Ask `christina` and `emily` together: per SOUL scope answer `mine` or `not_mine` with one-line reason. Do not guess from lookup tables.

- Exactly one `mine`: assign the comment to that owner. They must write full role analysis.
- Both claim, or neither claims: stop and ask the owner — do not guess.

## Where to write

Append to that day’s `position-watch/YYYY-MM-DD-position-watch.md` under `## Position comments`. Write all three layers (workspace, shared, inbox). Do not change the script table or Final audit above. Do not open `*-revised.md`. Do not change `trade_journal.csv`. No orders. Do not mix `tm_score` and `valuation_score`. Do not write back into the daily or weekly formal lists.
