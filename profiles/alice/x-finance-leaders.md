# X/Twitter finance leaders roster (20)

> Alice **Social snapshot (Mon–Sat)** scan roster. Free public pages only (no X API).
> Daily cron: **tier-1 required**; **rotate** when crawl/time budget allows. Full depth on all 20 reserved for Sunday/adhoc.

**Impact level (narrative influence, not a trade signal):** 🔴 high · 🟡 medium · ⚪ low / not material  
**Social-alone** defaults to `weak_signal`; upgrade to `persistent_signal` only with cross-source confirmation.

---

## Tier-1 — scan daily (~6–8)

| # | Tier | Handle | Name | Role | Primary impact | Influence type |
|---|------|--------|------|------|----------------|----------------|
| 1 | tier-1 | @elonmusk | Elon Musk | Tesla/SpaceX CEO | TSLA, BTC, DOGE, broad market | Immediate price shock, policy signal |
| 2 | tier-1 | @CathieDWood | Cathie Wood | ARK Invest CEO | ARK holdings, innovation sector | Holdings disclosure, sector views |
| 3 | tier-1 | @BillAckman | Bill Ackman | Pershing Square | SPY, Treasuries, activist targets | Macro, activist investing |
| 4 | tier-1 | @michaeljburry | Michael Burry | Scion | Value/short targets | 13F, tail risk |
| 5 | tier-1 | @jimcramer | Jim Cramer | CNBC Mad Money | Single names, sentiment | Media impact (often contrarian controversy) |
| 6 | tier-1 | @zerohedge | Zero Hedge | Finance aggregator | Broad-market breaking | High-frequency commentary; drifts into macro essays — only record material ticker posts |
| 7 | tier-1 | @KobeissiLetter | Kobeissi Letter | Market commentary | Names, tape, volatility | Fast takes; do not turn macro posts into close wrap |

---

## Rotate — when budget allows (remainder of list)

| # | Tier | Handle | Name | Role | Primary impact | Influence type |
|---|------|--------|------|------|----------------|----------------|
| 8 | rotate | @jack | Jack Dorsey | Block founder | SQ, BTC, payments | Corporate strategy, policy |
| 9 | rotate | @cdixon | Chris Dixon | a16z GP | Crypto, Web3 | Sector/VC trends |
| 10 | rotate | @chamath | Chamath Palihapitiya | Social Capital | SPAC, tech, crypto | Catalyst; note conflicts of interest |
| 11 | rotate | @Carl_C_Icahn | Carl Icahn | Icahn Enterprises | IEP, activist targets | Open letters, holdings |
| 12 | rotate | @RayDalio | Ray Dalio | Bridgewater | Macro, Treasuries, gold | Debt cycle; default demote pure macro long-form |
| 13 | rotate | @ianbremmer | Ian Bremmer | Eurasia Group | Geopolitics → broad market | Geopolitical events |
| 14 | rotate | @LynAldenContact | Lyn Alden | Macro research | BTC, energy, Treasuries, gold | Deep macro |
| 15 | rotate | @Schuldensuehner | Holger Zschaepitz | Welt/macro | US/EU macro, Treasuries | Europe session signal |
| 16 | rotate | @DavidSacks | David Sacks | Craft Ventures | AI/tech, policy | Policy, startups |
| 17 | rotate | @SahilBloom | Sahil Bloom | Content/investing | Retail sentiment | Education-oriented; weak direct signal |
| 18 | rotate | @APompliano | Anthony Pompliano | Pomp | BTC, fintech | Daily views |
| 19 | rotate | @GameofTrades_ | Game of Trades | Technical analysis | Single-name TA | Short squeeze/charts |
| 20 | rotate | @TheStalwart | Joe Weisenthal | Bloomberg | Macro, bonds, central banks | Policy interpretation |

---

## Daily monitoring method (lean)

1. **Priority:** tier-1 material posts → Reddit heat (ApeWisdom top-N + at most WSB/r/stocks; on failure must write `ApeWisdom: miss`) → StockTwits trending+M7 → rotate/other subs (only when already flagged; do not scan everything to fill the form)
2. **Search:** `site:twitter.com <handle>`, last 1–2 days; free search may miss — record `attempted + miss`, do not claim “fully scanned”
3. **Materiality:** need concrete ticker/trade/catalyst to enter table; skip teasers/education/pure promo
4. **Impact notes (🔴 only):** may cite one free price or media follow-up; do not write mini market-close
5. **Anti-wrap:** leader pure FOMC/yield/oil essays → at most one line `regime_chatter` (±2 trading-day event window only), otherwise demote. Snapshot **forbidden** standalone **Macro/policy Notes** section (macro belongs in market-close).

---

## Impact guide (by type)

| Type | Typical impact | Timing |
|------|----------------|--------|
| CEO/founder | Immediate gap, options IV, sector ETF | minutes–days |
| Fund manager | 13F follow, activist target, media amplification | hours–days |
| Macro research | Treasury/gold/USD sentiment | hours–days; restraint — easy to drift |
| Media/KOL | retail/meme; often weak signal | hours |

---

## Change log

- 2026-06-04: initial 20 (host)
- 2026-09-16: vendored into refine; added tier-1/rotate; anti-wrap/lean priority (Option A)
