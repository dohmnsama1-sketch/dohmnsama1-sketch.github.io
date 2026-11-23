# ZALAH preregistered research comparison — 24 November 2026

**Research only. No financial performance guarantee. Real-money execution disabled.**

Three competing fixed entry rules are now encoded in `walkforward_bidask.py` before the new 3-week comparative run:

1. `baseline`: SMA(10) / SMA(30) crossover on **closed M5 candles**.
2. `regime`: same crossover subject to previous completed H1 candle vs EMA(100), M5 ADX(14) >=20 and directional DI confirmation, plus spread/ATR cap.
3. `breakout`: previous *closed* M5 candle clearing the previous 36 M5-bar Donchian high/low by 0.10 x ATR(14), then previous completed H1 candle vs EMA(100), with spread/ATR cap. This is a new, unproven hypothesis.

The same execution assumptions apply: next-bar bid/ask entry, 0.5% equity risk, ATR(14) x 2 stop, 1.5 R target, bid/ask spread cap 0.50 USD per ounce, adverse slippage of 0, 0.15 or 0.50 USD/ounce *per side*, 100 oz/lot, minimum 0.01 lot, and research-only assumed commission 7 USD per whole lot round trip. The commission is a conservative independent assumption; **not** a verified Exness contract fee. M5-candle stop/target ordering always assumes stop first, target fills at its limit rather than unsupported favorable gap price. No swap or margin enforcement; not tick-exact Exness fills.

The existing January-November 2026 dataset has already been examined for two strategies, so subsequent results on that dataset are **exploratory rather than pristine unseen holdout evidence**, especially if used to choose the best of multiple hypotheses. The 60/20/20 partition is descriptive and trades crossing boundaries are excluded from split-specific statistics. No parameter tuning on the final partition is allowed. Full forward validation will require future previously unseen data and supervised broker-demo order records.

Decision rules:
- Reject zero-trade/high-win-rate marketing claims.
- Do not approve a strategy based on a 3-week sample, 10 profitable trades, or in-sample profit alone.
- Require positive net P/L after modeled spread, slippage and commission, positive independent chronological out-of-sample, adequate number of separate closed trades, and reasonable peak-to-trough drawdown; test higher costs and gap assumptions.
- Every candidate goes through the same `readiness_gate.py`, which never grants authority for a real deposit or trading.
- A USD 50 account with 0.01 minimum Exness gold lot may not meet even 0.5% ($0.25) trade risk. No software tweak can change the broker contract specification.
