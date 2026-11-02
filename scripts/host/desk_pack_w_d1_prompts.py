#!/usr/bin/env python3
"""P3b prompt bodies for hermes cron create (daily session legs).

Historical single-leg templates. Live Mon–Fri Desk Pack is now **one** train
`desk-pack-daily` — see `desk_pack_daily_train_prompts.py` +
`patch_desk_pack_daily_train.py`. These strings remain for unit tests / audit.

Used by ops / docs; also imported by unit tests. Does not touch live cron.
"""
from __future__ import annotations

# Canonical desk-pack portal root (filesystem). Never ~/.hermes/shared/inbox/.
INBOX_ROOT = "$REPORTS_INBOX"

RATES_DAILY = f"""You are Sarah — Hermes desk operator. Desk Pack W-D1 Wave1 — christina daily rates (lite). 
Not investment advice · observation only. Display "christina · rates". 

1) kanban_create(christina). Mode=daily lite. 
2) Load skills: curve-watch -> real-rates -> fedwatch-consume -> bond-etf-tape -> fx-us-uk-bridge -> rates-session-report(trunk). 
3) FedWatch: CONSUME-ONLY cron fedwatch-daily artifact. Cite-or-miss. ❌ hermes cron-run FedWatch · ❌ probability . 
4) Draft: shared/reports/christina/YYYY-MM-DD-rates-session.md. 
5) REQUIRED after Header: ## Session summary(5–8 bullets; rates_regime; Alice pull -> Market insight). rates_regime ≠ desk Risk-on/off. 
5b) REQUIRED: ## Market insight(; ❌ desk Risk-on/off ). 
6) Daily: bond Obs ≤3; FX (low–high miss; Obs ); Obs ≤2( DXY, GBPUSD; FX_LONG/FX_SHORT); Session summary FX bullet; News/Market ≥1; Miss ledger. 
7) Zoe IC -> **christina** revise(owner only). B_*/FX_*. 
8) 3-layer final: workspace + shared + {INBOX_ROOT}/rates-session/YYYY-MM-DD-*-revised.md. 
9) Hard fail miss/attempted , Alice overall miss. 
 task IDs. 
"""

COMMODITIES_DAILY = f"""You are Sarah — Hermes desk operator. Desk Pack W-D1 Wave2 — emily daily commodities (lite). 
Not investment advice · observation only. Display "emily · commodities"(≠ broker Emily). 

1) kanban_create(emily). Mode=daily lite. 
2) Load: commodity-sources-crawl -> world-to-commodity -> commodity-insight -> commodity-direction -> commodity-forecast -> commodity-signal-table -> commodity-puzzle -> commodity-session-report(trunk). 
3) Draft: shared/reports/emily/YYYY-MM-DD-commodity-session.md( commodities-session ). 
4) REQUIRED after Header: ## Session summary(5–8 bullets + commodity_regime; Alice pull -> Market insight). commodity_regime ≠ desk Risk-on/off. 
4b) REQUIRED: ## Market insight(cite commodity-insight; ❌ desk Risk-on/off ). 
5) Cite slots: Insight · Direction(DIR_*)· Forecast( · 1–4w · bull|base|bear ± Est band; miss, ; skip). News/Market check( Scenario/levels ): ≥1 Emily-topic `News: miss`. Lenses(Macro+Micro; Market ; Dominant). 
6) Daily: + Trade map C_*; Obs ≤3 Obs entry/cut/TP, Obs TP cite Est band ; levels -> Basis cite Forecast + Dominant tag(macro-led|micro-led|market-led|mixed); Forecast/Est cite -> Obs levels. levels Basis lean: base|bull|bear|two-way. 3–5; ≥3 . 
7) ❌ C_* Direction · ❌ DIR_* Signal · ❌ bare BUY · ❌ invent inventory/ARIMA Scenario. 
8) FX/rates: prefer cite Wave1/christina rates session miss — ❌ FX Est/B_*/Rate Δbp. 
9) Zoe -> **emily** revise(owner only). ❌ C_*↔B_*↔FX_*. 
10) 3-layer: workspace + shared + {INBOX_ROOT}/commodities-session/YYYY-MM-DD-*-revised.md. 
 task IDs. 
"""

VALUE_DAILY = f"""You are Sarah — Hermes desk operator. Desk Pack W-D1 Wave2 — eliza daily value-session. 
Not investment advice. P-VAL only — ❌ tm_score/T&M brackets. 

1) kanban_create(eliza). Desk pack #4 value-session. 
2) value-sleeve data snapshot + movers vs Sunday lock. Sunday valuation_score; ; reshuffle weekly value-100. Movers : Today spot / %,Sunday lock FV( revised JSON `fv_range` ),Display upside %(= FV / spot − 1). FV spot -> `attempted + miss`. ❌ FV. ❌ upside `valuation_score`/`width_verdict`/. 
3) REQUIRED after Header: ## Session summary(5–8 bullets + valuation stance; Alice pull -> Market insight). 
3b) REQUIRED: ## Market insight + News/Market + Lenses(valuation domain; ❌ desk Risk-on/off/tm_score). 
4) Zoe -> **eliza** revise(owner only)— ❌ do not hand off to Alice value revise. 
5) 3-layer: workspace + shared + {INBOX_ROOT}/value-session/YYYY-MM-DD-*-revised.md. 
6) Eliza . E5: overlap ticker WARN only. 
 task IDs. 
"""

# Legacy split-clock schedules (paused after daily train absorb).
SCHEDULES = {
    "rates": "25 21 * * 1-5",
    "commodities": "45 21 * * 1-5",
    "value": "50 21 * * 1-5",
}

NAMES = {
    "rates": "Sarah: Daily rates session (W-D1 Wave1)",
    "commodities": "Sarah: Daily commodities session (W-D1 Wave2)",
    "value": "Sarah: Daily value session (W-D1 Wave2)",
}
