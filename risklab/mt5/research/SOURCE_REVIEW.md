# ZALAH third-party source review — 2026-11-24

## Verified public dataset
- Dataset: https://github.com/Touhid-HZ/xauusd-tick-data-2026
- Pinned source commit: 019f74d942545196adab8e481338fde7c4df67c4
- Manifest at pin: 47 weekly gzip CSVs, 84,371,369 bid/ask tick records, ~644 MB compressed. Quoted period Jan 1 to Nov 22 2026 UTC.
- Pipeline has already processed week 1: 1,542,732 rows, 1,116 M5 bid/ask bars. Source manifest first/last timestamps matched actual file. Independent GitHub Actions report is preserved.
- The repo displays an MIT software license. Rights to original Dukascopy feed are not automatically guaranteed by a downstream repository; raw third-party quotes are not committed or republished. This is a research source, NOT Exness tradable quotes.
- Importer rejects non-monotonic timestamps, bad price, bid/ask inversion and catalog-count mismatches. Summary reports contain source SHA-256 and commit pin.

## Open-source strategy & engineering comparisons; no imported bot code
1. QuantConnect/Lean — Apache-2.0: https://github.com/QuantConnect/Lean . Mature fee, brokerage and slippage model architecture. We adopt the independent testing principle without copying engine implementation or implying proven profit.
2. Ali-1999/XAUUSD — MIT: https://github.com/Ali-1999/XAUUSD . Public gold backtest and Dukascopy-data research examples. Reported past tests are not third-party verified live profits.
3. RicardoBarato/xauusd-mt5-expert-advisor — GPL-3.0: https://github.com/RicardoBarato/xauusd-mt5-expert-advisor . Research EA risk-model reference. No code imported; GPL propagation obligations must be reviewed before copying.
4. tcolja/TradingXAUUSD — no detected license: https://github.com/tcolja/TradingXAUUSD . Tick-data analysis example only; source is not reused without permission.

## What the new independent research engine measures
- Strictly chronological signal calculation from CLOSED bars, and NEXT M5 bar bid/ask entry.
- BID/ASK-adjusted exit rather than imaginary mid-price fills.
- Pessimistic stop-first resolution when both stop and take profit are within the same candle.
- Slippage sensitivity at 0, 0.15 and 0.50 USD per ounce per side; default 0.50 USD maximum spread, 0.5 percent capital-at-risk and 0.01 min volume.
- Two FROZEN competing hypotheses: SMA crossover baseline, and an H1 EMA100 + M5 ADX14 + spread/ATR regime filtered version.
- A fixed chronological 60/20/20 analysis-validation-holdout report, with no parameter-fitting on holdout.
- Stats: total trades, net P/L, profit factor, loss and gain aggregates, realized drawdown, confidence interval for win rate, number of rejections.
- Limitations: M5 price extrema do not recover true tick order; it is not an MT5 fill engine, ignores broker margin/swaps, and 100 trades is only a minimal sample threshold, not a scientific guarantee.

## Known launch blockers
- The user's previous MT5 report showed History Quality 0 percent and negative P/L in versions 1.02 and 1.03.
- Real demonstration of profitable holdout after stressed costs and true Exness demo fills is missing.
- Tiny equity ($50) does not support 0.01 lot gold with strict 0.5 percent risk for many ATR stops. Never widen risk just to force trade.
- No guaranteed 99 percent win rate or no-loss execution exists.
