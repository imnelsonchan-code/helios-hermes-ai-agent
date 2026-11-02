# emily · Obs backtest BAD fixture（negative control）

Intentionally violates namespace isolation so the harness can confirm detection.

## Session summary
- Bad fixture for negative control only.
- **commodity_regime：** Neutral — n/a

## Trade map

| Commodity | Signal | Last | Est value | Obs entry | Obs cut loss | Obs TP | Horizon | Invalidation | Basis（+ Dominant） | Conf |
|-----------|--------|------|-----------|-----------|--------------|--------|---------|--------------|---------------------|------|
| Gold | BUY | 2680 | 2700 | 2665 | 2620 | 2740 | 1–4w | break 2620 | macro-led only (no Forecast cite) | M |
| Oil | DIR_BULLISH | 71 | miss | 70 | 68 | 75 | 1–4w | — | — | L |

## Next-day prints
| Commodity | US print |
|-----------|----------|
| Gold | 2695 |

This file must **fail** hygiene (bare BUY + DIR_* as Signal + Basis without Forecast cite).
