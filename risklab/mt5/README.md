# ZALAH MT5 Demo Guard (XAUUSD)
Research-only **demo account** Expert Advisor. It will refuse initialization on a real account. Orders are **OFF by default**. No claimed profitability, no live-account support.

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
