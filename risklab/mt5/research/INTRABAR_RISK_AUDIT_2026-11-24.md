# ZALAH intrabar adverse excursion — audit, 24 Nov 2026

## What changed in this commit series
- Research simulator `walkforward_bidask.py`: new `adverse_ohlc_equity_proxy()` stress valuation for each open long at the **lowest BID** and each open short at the **highest ASK** of a five-minute candle, plus one adverse slippage allowance and assumed commission.
- The simulator reports `max_adverse_intrabar_equity_proxy_fraction`, `max_open_position_adverse_loss_proxy_usd` and `bars_with_open_position` separately from `max_closed_equity_drawdown_fraction`.
- A matching rule in `readiness_gate.py` rejects any candidate that has missing, nonfinite, negative or above-8% adverse equity stress proxy. This 8% is a **research screening threshold**, not a guaranteed loss bound. Testcases include buys/sells and previously concealed floating risk.
- On commit `cb25ba008e2d5ab7a21ff3932bed9c40dbb9a406`: independent [ZALAH Python tests run 45296125037](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45296125037) passed 45 tests; [RiskLab regression run 45296124977](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45296124977) passed 53 JavaScript tests plus 45 Python tests. Tests prove code assertions, **not trading profitability or broker fills**.

## Crucial distinction: NOT tick-accurate floating equity
This new value is a conservative M5 OHLC **adverse-price proxy**, not a reconstructable time series of actual open-account equity:
- BID lows / ASK highs can precede a position entry or occur after exit. Price order cannot be recovered from M5 OHLC alone.
- Both stop-loss and take-profit in the same M5 bar still resolve **stop first**.
- Open-equity excursion is measured versus the peak **realized** equity in the model, not a time-ordered floating-equity peak. Thus **do not label it true maximum equity drawdown**, and do not claim that a threshold prevents losses in reality.
- Genuine open-equity drawdown requires timestamped price events in actual chronological order, with real broker contract, margin, swap, commission, liquidity and fills.

## Market strategy remains unproven
On the last independent full-year 2026 Dukascopy-derived gold M5 replay, net P/L after modelled slippage/fee was negative in all strategy families: SMA -937.59 USD; EMA/ADX -145.45 USD; Donchian -860.87 USD on 10,000 USD simulated starting capital. That test ran **before this adverse-excursion metric**, so those results do NOT have its numerical values.

MT5 expert advisor v1.07 was created with timer risk-heartbeat and live calendar guards, but **has not been compiled or forward-tested in the user's MT5 terminal**. Its demo-only and opt-in protections must remain; real trading stays disabled. On the user's 50 USD real account, the documented 0.01 lot XAUUSDm minimum is incompatible with a typical 0.5%/$0.25 per-trade stop-loss budget. High/guaranteed daily P/L and near-zero loss are not established.
