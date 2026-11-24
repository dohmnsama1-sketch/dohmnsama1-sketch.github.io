# ZALAH MT5 Demo Guard (XAUUSD)
Research-only **demo account** Expert Advisor. It will refuse initialization on a real account. Orders are **OFF by default**. No claimed profitability, no live-account support.

## Current research variants (2026-11-24) — NOT validated for live funds

The installation guidance and legacy guard list below refer to the original v1.01/v1.02 EA. **Do not mistake its older limitations for the later, separate files.**

| File | Purpose | MQL5 compiled? | Independently proven profitable? |
|---|---|---|---|
| `ZALAH_Demo_Guard.mq5` v1.02 | Original SMA crossover baseline | User-tested earlier with negative P/L | **NO** |
| `ZALAH_Regime_Research_v103.mq5` | EMA H1 + ADX / cost research | User-tested earlier with negative P/L | **NO** |
| `ZALAH_SafeResearch_v104.mq5` | Persistent demo loss lock and own-position safety close | Compiler on current newest source not independently verified | **NO** |
| `ZALAH_NewsShock_SafeResearch_v105.mq5` | Spread/range/discontinuity cooldown and optional manual news embargo | **Not yet compiled in MetaEditor** | **NO** |
| `ZALAH_LiveCalendar_SafeResearch_v106.mq5` | Adds MT5 native USD high-importance economic calendar (DEMO only) | **Not yet compiled in MetaEditor** | **NO** |

For v1.05 and v1.06 refer to [News & Shock research protocol](NEWS_SHOCK_RESEARCH_v106.md). All variants still **refuse REAL accounts** and default to `InpAllowDemoOrders=false`. The v1.06 live USD calendar is enabled by default and blocks new entries if its source is unavailable; **MT5 Strategy Tester cannot call the live economic calendar**, so set `InpUseLiveUsdEconomicCalendar=false` there and only claim news-aware results if a verified point-in-time manual schedule was actually applied. Neither economic calendars nor volatility halts can predict or prevent all geopolitical shocks. For the user's ~$50 account, broker minimum gold lot sizes remain a fundamental risk barrier.

See [84m-quote full-year negative evidence](research/FULL_YEAR_RESULTS_2026-11-24.md). **Do not fund or run these EAs on a real account.**

## Install on macOS MetaTrader 5
1. In MT5 select File > Open Data Folder, then MQL5 > Experts.
2. Copy `ZALAH_Demo_Guard.mq5` into Experts.
3. Open MetaEditor (Tools > MetaQuotes Language Editor), open the file, and press Compile (F7). **Do not proceed if there are compile errors.**
4. Return to MT5; Navigator > Expert Advisors > Refresh.
5. Attach the EA to an XAUUSD M5 chart on the Exness **DEMO** account. Enable algorithmic trading in terminal settings only after checking the EA and the demo status.
6. Initially leave `InpAllowDemoOrders=false`. Inspect Experts and Journal logs for safe initialization. Only switch it to true for explicitly authorized **demo** order tests.

## Guards
- Real accounts rejected at initialization; checked again every tick.
- Broker-side stop-loss and take-profit on demo orders.
- Spread, risk-based lot rounding, minimum lot, margin and drawdown/daily-loss entry gates.
- Refuses a trade if minimum lot exceeds risk budget.
- Stops new entries on detected drawdown breach; **does not forcibly close existing positions**.
- Only one position per symbol, including manual positions.
- No averaging down, martingale or grid.
- No persistent lock across EA restart, no event-driven news filter, no independent execution watchdog, and no verified broker fill/slippage metrics yet.

## Known limitations / required validation
This is a **first implementation, not production ready**. GitHub CI currently runs JavaScript research tests, **not MQL5 compilation or Strategy Tester**. Run MetaEditor compilation and MT5 Strategy Tester with Exness demo tick data before allowing demo orders. Verify EA logs, broker SL/TP acceptance, stop level/freeze level, commissions, variable spread, disconnect/reconnect, partial fills and account equity controls. 50 USD demo equity with 0.01 minimum lot may reject most signals under 0.5% risk.

Never share trading passwords in chat, commit them to GitHub, or send deposits to an intermediary.

## v1.01 zero-trade diagnostics
After recompiling the updated EA in MetaEditor and running a **demo-only Strategy Tester** pass, open Tester > Journal and find `ZALAH_DIAG`. The end-of-run log reports `ticks`, `spread_blocked_ticks`, `eligible_bars`, `crossover_signals`, `risk_lot_rejections`, `margin_rejections`, and `order_attempts`. The initialization line also reports the effective price spread threshold from `InpMaxSpreadPoints * SYMBOL_POINT`. **Do not increase risk limits just to force a trade.** If a 50 USD account cannot trade the broker's minimum gold volume under the specified risk budget, its correct behavior is NO TRADE.

### Data-coverage warning
A run with `History Quality: 0%` is not validated, even if many modeled ticks and bars were processed. Check the Journal line `real ticks begin from ...`: when real ticks begin late in the test interval, most of the earlier test may be based on generated ticks. Seek broker or licensed independent tick history with documented coverage before claiming a real-tick walk-forward result.

## v1.02 Exness XAUUSDm fix
Broker's XAUUSDm quote point may be 0.001. Previously `InpMaxSpreadPoints=100` meant only 0.10 USD/oz, and the tester rejected every tick. The updated input `InpMaxSpreadPrice=0.50` compares raw `Ask-Bid` in USD per ounce regardless of SYMBOL_POINT precision. This is a *research default*, not a universal broker best setting. Review observed spread distribution, including news spikes, and do not loosen the cap to force trades.

If still on v1.01 and diagnosing without reinstalling, **in Strategy Tester only**, set `InpMaxSpreadPoints=500` for XAUUSDm with `SYMBOL_POINT=0.001`; this is the same 0.50 USD/oz threshold. For other symbols or precision values, do not copy 500: use `desired spread price / SYMBOL_POINT`.

After updating to v1.02, compile on your own MetaEditor; CI checks source safety but **does not compile MQ5**. Do not enable demo live orders until compilation and independent test reports pass. With USD 50 equity and 0.5% risk, expect minimum-lot rejections even after the spread is repaired.
