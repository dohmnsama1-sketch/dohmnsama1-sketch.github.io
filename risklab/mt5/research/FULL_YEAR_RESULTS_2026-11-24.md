# ZALAH 2026 full-year-independent-feed report — 2026-11-24

## Provenance and reproducibility

- Successful run: https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45291504940
- Historical source pinned to third-party Dukascopy-derived quote repository commit `019f74d942545196adab8e481338fde7c4df67c4`. **Not Exness quotes or guaranteed fills**.
- 47 weekly compressed quote archives checked: **84,371,369 BID/ASK ticks** (source dates 2026-01-01 through 2026-11-22 UTC); produced **63,275 M5 OHLC bars**.
- Source research commit in run: `0b484760b2f70a7b2f0f20e486d9000b056c9783`. Report below extracted from actual archived `benchmark.json` and `readiness.json`, **not approximated from screenshots**.
- Simulated reference starting equity: **10,000 USD**; adverse slippage **0.15 USD/oz per side** plus an **assumed 7 USD per standard lot round-trip**. Fees are research stress assumptions, not a validated Exness fee schedule. 100 oz per lot, min 0.01 lot and fixed risk gate 0.5%.
- Chronological research partitions defined by M5 bar count: analysis ending 2026-07-16 03:20 UTC, validation ending 2026-09-18 02:25 UTC, later holdout after. These partitions were pre-defined and should remain frozen.

## Profitability — all three hypotheses failed

| Strategy | Trades | Total P/L USD | Win rate | Profit factor | Max closed-equity drawdown | Holdout trades | Holdout P/L USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| SMA crossover baseline | 224 | **-937.59** | 37.95% | 0.8399 | 12.791% | 49 | **-223.62** |
| SMA + H1 EMA + ADX | 47 | **-145.45** | 38.30% | 0.8890 | 4.044% | 25 | **-251.57** |
| Closed-bar Donchian one-shot breakout + H1 trend | 197 | **-860.87** | 37.06% | 0.8324 | 9.820% | 83 | **-399.32** |

Other partitions (analysis / validation / holdout net USD):
- Baseline: **-1,049.49 / +335.53 / -223.62**
- Regime: **-18.94 / +125.05 / -251.57**
- Donchian breakout: **-766.27 / +304.72 / -399.32**

All three hypotheses have negative after-cost P/L, profit factor <1.0, and negative holdout P/L. **Do not fit a new model to this already-inspected holdout and then call the same period independent.** Treat this dataset as exploratory and reserve a NEW future holdout or another legally usable independent historical series for future claims.

## Cost, risk and capital feasibility

- At stress slippage **0.50 USD/oz per side**, net P/L was baseline **-1,232.43 USD** (222 trades), regime **-175.41 USD** (47 trades), breakout **-1,469.95 USD** (180 trades).
- Research P/L at simulated **50 USD** starting balance: **zero executed trades** with 0.5% risk budget and min 0.01 lot. **Zero trades is not zero-risk profitable trading.** This rules out forcing existing gold contract sizes on a 50 USD account by simply raising risk.
- Research result: `readiness.json` for each strategy is **INSUFFICIENT_EVIDENCE**, with `real_money_release_permitted=false`. No real orders, deposits or switches are authorized.
- Replay uses 5-minute Bid/Ask OHLC, not original tick-event ordering for position execution; assumes stops first when both stop and profit touched inside a bar. Open-equity intrabar drawdown is NOT measured by the reported *closed-equity* DD, which can understate risk. Swap, margin, server order rejects, overnight exposure and real broker slips are not verified.
- Subsequent commits strengthened the evidence gate to reject inconsistent gross/net/equity counts and added per-calendar-month stability diagnostics, but these newer safeguards **were not part of this 2026-11-24 full-year run**. Their unit tests passed separately on GitHub Actions run 45293071276, 33 Python tests and 35 JS tests in run 45293071276.

## Next work — do not overfit

1. Correct simulator uncertainties: reconstruct fill chronology using actual tick BID/ASK for a manageable independent sample, check gap and commission profiles against actual broker demo transactions, and measure floating equity DD.
2. Reserve a **new untouched period** and keep a written list of candidate strategies and parameters established *before* accessing it. Do not relabel Sep–Nov 2026 as untouched holdout.
3. If testing new families (e.g., session-aware mean reversion or volatility breakouts), treat this entire 2026 sample as **exploratory** only and compare out of time/market.
4. Only supervised DEMO after MQL5 compilation and valid tick data; no real trading until independently verified after-cost profitability, broker execution receipts and safe lot-minimum affordability, and explicit user trading authorization.
5. No realistic process can guarantee no losing trades or 99–100% profit/win probability.
