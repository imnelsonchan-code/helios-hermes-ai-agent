# Glossary (desk / scripts)

English terms used in public docs and host scripts. Tickers and JSON field keys stay ASCII in data artifacts.

| Term | Meaning |
|------|---------|
| **E5** | Firewall between T&M sleeve (`tm_score`) and value sleeve (`valuation_score`). Overlap tickers → WARN only; never blend ranks or scores. |
| **P-TM** | Trend & momentum sleeve; publishes `tm_score` / `daily_score`. |
| **P-VAL** | Value / width sleeve; publishes `valuation_score`. |
| **Desk Pack** | Fixed train of session reports: rates, T&M, commodities, value, then macro overall. |
| **Draft → Zoe → revise** | Kanban chain: specialist draft, IC challenge, owner `*-revised.md` portal file. |
| **Portal / inbox** | User-facing report root (`$REPORTS_INBOX/<category>/`). Not agent workspace paths alone. |
| **Session summary** | Required `## Session summary` block (5–8 bullets) on session drafts. |
| **Market insight** | Required specialist domain insight section; not desk-wide macro view. |
| **Macro view** | Alice-only desk-wide synthesis from four specialist insights + desk risk-on/off. |
| **Option G** | Daily-only T&M gate: suppress effective BUY when benchmark trend strength (e.g. SPY ADX) is below threshold; score unchanged. |
| **Fail-closed** | Missing data → N/A / miss / pending; do not invent numbers. |
| **Shadow / overlay** | Eval layer that may change effective bracket or caps without rewriting live engine weights. |
| **Risk plan / sidecar** | Immutable plan store keyed by journal `RowID`; journal remains execution ledger. |
| **PLAN vs JOURNAL_ONLY** | Adopted plan levels drive official breach alerts; journal-only SL/TP are file-only. |
| **Mercury Decide** | Post–Zoe-challenge enforce layer; escalate-only vs IC verdict; separate from chat models. |
| **Synthetic fixture** | Test tickers (`TST1.L`, `ACME`, `BETA`) and notes `Synthetic buy` — not live holdings. |
