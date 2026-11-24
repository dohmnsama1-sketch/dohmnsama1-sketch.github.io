# ZALAH weekly-block profitability uncertainty audit — 2026-11-24

## Verified completed work
- Research engine `risklab/mt5/research/walkforward_bidask.py` now computes deterministic **whole-calendar-week P/L resampling** from actual exited simulated trades, including weeks with **no trade**, at 2,000 replicates and a fixed seed.
- Summary contains `bootstrap_week_count`, `bootstrap_weeks_with_trades`, `bootstrap_net_pnl_p2p5`, `bootstrap_net_pnl_p97p5`, `bootstrap_positive_fraction` and the fixed seed. Less than 26 weeks gives `INSUFFICIENT_WEEKS`, not a made-up confidence level. Weeks are exit-attributed and preserve within-week realized clusters. Data remains from independent third-party BID/ASK M5 aggregation, not Exness fills.
- `readiness_gate.py` now requires **positive lower weekly P/L resampling boundary**, at least 95% positive block-resampled totals, and 26+ weeks, in addition to established positive base-case holdout, positive **adverse-cost holdout**, closed and adverse intrabar drawdown ceilings and other risk/data criteria.
- These rules are research heuristics; weeks are not generally independent or exchangeable across geopolitical/monetary regimes. A 2.5/97.5 empirical percentile band is **not a calibrated 95% predictive interval, nor proof of 95% profitable trading**. It does not model uncertainty from comparing many strategies or from broker-specific fills.
- Verified after these code changes: [RiskLab regression 45297530998](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45297530998) passed **53 JavaScript and 52 Python tests**; standalone [research tests 45297531226](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45297531226) passed all 52 Python tests.
- A full 47-week source-data replay was launched separately under [GitHub Actions 45297331643](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45297331643). That run pins an earlier code SHA and will **not include the two later checks requiring positive stressed-cost holdout/intrabar risk**; they have nevertheless passed dedicated tests. A run cannot be called economically successful until actual report JSON is inspected.

## Historical ground truth
The prior full 84.37m BID/ASK quote replay on simulated $10k showed all three strategy families **negative net P/L** after research costs: SMA -$937.59, EMA/ADX -$145.45, Donchian -$860.87. All had negative chronological holdout P/L. The latest scientific task is evidence quality and safe candidate screening; *no strategy currently qualifies for funded deployment.*

## Capital and broker constraints
- Real $50 gold contract minimum 0.01 lot on the previously observed Exness demo specs frequently forces risk above a 0.5% ($0.25) cap; do not override with leverage or higher risk simply to force entry.
- The newest MQL5 EA risk-heartbeat source v1.07 is **not yet compiled/forward tested** in the user's MT5 terminal; no broker-side receipt, position close retcode or price-event replay has been validated.
- Cannot guarantee daily profit, 99% wins, 100% returns, zero drawdown or future geopolitical prediction. Surprise events can only be guarded **after** evidence becomes available, while known scheduled releases require genuine point-in-time records.
- The repo does not activate real-money trading or request additional deposits.
