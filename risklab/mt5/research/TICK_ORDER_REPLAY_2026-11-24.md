# ZALAH — actual timestamp-ordered tick study, 2026-11-24

## Executed and verified, not merely planned

GitHub Actions [run 45299980158](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45299980158) successfully downloaded a PINNED independent historical BID/ASK sample from the public Dukascopy-derived repository, ran chronological quote-path analysis and a conservative research-only SMA10/30 tick replay, and published **only aggregate JSON**, not third-party raw quotes.

Source ref: `Touhid-HZ/xauusd-tick-data-2026` at `019f74d942545196adab8e481338fde7c4df67c4`. Source file `data/tick/XAUUSD_2026_w01.csv.gz`, SHA-256 `a4fb1fb4c8877d6ea6b04494c5e85cdeca114d5e6ef958e6d22a358d29c13247`, 11,426,399 bytes downloaded. Contains **1,542,732 BID/ASK quote updates** in 1,116 M5 bars, from `2026-01-01 23:00:00.596` to `2026-01-07 23:59:59.958` UTC.

### Intrabar stop/target ordering evidence
Hypothetical fixed first-bar-tick long/short orders: 2.0 gold-price-unit SL, 3.0 gold-price-unit TP, no trading P/L assumptions. In bars whose extrema contained BOTH levels:
- Long: **78** ambiguous OHLC bars; **14** first touched TP, so a blanket OHLC "stop first" assumption differed from actual chronological BID/ASK in 14 cases.
- Short: **80** ambiguous bars; **19** touched TP first instead.
- This exercise is NOT the EA, not evidence that changing the rule creates profit, and does not reconstruct the broker's order book or fills.

### Separate tick-exact SMA10/30 research replay
With simulated $10,000, 0.5% risk/trade, minimum 0.01 lot, adverse slippage 0.15 USD/oz each side, ASSUMED commission $7/standard lot round trip, broker BID/ASK and chronologically confirmed closed-M5 SMA crosses:
- **37** crossover signals; **35** spread-cap rejections; **2** finished simulated trades.
- Net research-only P/L **+$19.28**, win percentage **50%**, profit factor **1.4703**, maximum quote-marked equity drawdown approximately **0.607%**.
- **Only two trades**: uninformative sample. No evidence of reliable profitability or daily income. Most earlier long historical research resulted in losses.
- For **$50 simulated deposit**, **zero trades** under the same protection rules. Never lift min-lot, leverage or risk thresholds to force a trade.
- This quote-marked drawdown is a time-ordered, tick-quote approximation, *not* Exness account equity or verifiable fills. Broker-specific margin, spreads, swaps, commissions, liquidity, outages, latency, retcodes and real-world gaps are unvalidated.

### Reproducibility / safety
- Code: `risklab/mt5/research/tick_bar_path_audit.py`, `tick_exact_sma_replay.py`, `public_xauusd_ingest.py`. Research pipeline: `.github/workflows/zalah-tick-path-audit.yml`.
- Later refactoring replaced quadratic ATR history recomputation with **O(1)** Wilder closed-bar streaming updates. [CI 45300309939](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45300309939): **53 JS tests + 69 Python tests passed** on commit `bf7cd151710646990e050d3c0d6a4968ded0b8a4`. The already finished tick replay run above predates that optimization; economic equivalence should be checked by rerunning on the same pinned source.
- The separate full-year research run [45299310847](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45299310847) was ongoing at initial report verification. It does not certify profitable alpha or live financial returns.
- `ZALAH_RiskHeartbeat_Research_v107.mq5` remains uncompiled/unverified in MetaEditor and DEMO only; the tick simulator is a distinct Python research application, NOT a deployable EA.
- **No real-money release authorized**; no deposits, subscriptions or account actions. This data does not support claims of 99-100% winning trades, zero losses, permanent income, predicting surprise geopolitics or beating every competitor.
