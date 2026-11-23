# ZALAH SafeResearch v1.04 — demo only

**Not a profitable or production-certified bot.** This branch is a *risk engineering experiment* created after v1.02 and v1.03 lost money in the user's MT5 screenshots. Do **not** fund it or enable unattended execution. Static GitHub tests do not compile MQL5.

## Changes vs research v1.03
1. Validate that `InpSymbol` starts with XAUUSD and matches the attached chart/tester `_Symbol`; validate `InpTimeframe==_Period`. Default is `XAUUSDm` / M5. Prevents the previous BCHUSDm vs XAUUSD mismatch.
2. Keep no-real-account guard; `InpAllowDemoOrders=false` by default. Never put passwords, account numbers, or broker tokens in GitHub.
3. Persist demo **entry lock**, daily start equity and high-water-mark equity in MT5 terminal global variables across application restarts when **not in Strategy Tester**. Tester runs are isolated for reproducible results. Reattaching the EA does not intentionally reset the lock. The terminal can expire globals after 4 weeks without access; this is **not** a permanent audited record.
4. On loss gate, block all new entries and **attempt** to close only positions matching the configured gold symbol and EA magic. MT5/broker can reject close requests, and losses can exceed the nominal budget due to price gaps, outages, slippage and account interference. Do not call it a guaranteed stop.
5. Reject stale quotes outside the Strategy Tester using `InpMaxTickAgeSeconds`. The additional safeguard does not guarantee feed quality; it uses the broker/server timestamp.
6. Round stop-loss and take-profit to the actual `SYMBOL_TRADE_TICK_SIZE` rather than arbitrary digits, then calculate position size with the rounded SL. 0.5% risk and lot minimum rejection remain in place.

## How to run A/B checks safely
1. In MetaEditor compile `ZALAH_SafeResearch_v104.mq5`, verify **0 errors**. The prior research control `ZALAH_Regime_Research_v103.mq5` must remain separately installed.
2. Use the Exness **DEMO** account. Attach the EA only to an XAUUSDm **M5** chart, matching its inputs; when using a different broker gold suffix, change `InpSymbol` to that exact symbol.
3. Initially keep `InpAllowDemoOrders=false`. In Strategy Tester only, set it to `true` to test trade fills with a simulated **10,000 USD**, not a real deposit.
4. Record the date range, actual real-tick coverage and `History Quality`. Previous screenshots showed **0%**, so do not use those results to infer profitability. Run v1.03 and v1.04 on identical valid price data and fees. Do not optimize on untouched out-of-sample periods.
5. For the live **demo-only** risk test, validate a kill-switch triggering, restart the MT5 terminal and verify the EA remains locked without placing new orders. Review the `Journal` for `SAFETY LOCK` and `SAFETY_CLOSE` retcodes. This requires deliberate supervised testing, never real deposits.
6. MT5 terminal global variable names begin with `Z104_<login>_<symbol>_<magic>_`. MT5 Tools > Global Variables (F3) can inspect these. **Do not remove a lock variable to resume trading automatically**; investigate the loss trigger and require manual review first. Equity peaks can be distorted by manual deposits/withdrawals or changes to account balance; reconcile account cash flows before relying on the saved peak.
7. No continuous operation guarantee: MT5 must remain online with functioning market data, correct demo permissions and broker access, and a separate watchdog would be needed for unattended execution.

## Release gate
Not suitable for real money until: independent real-tick history & forward validation, positive risk-adjusted OOS P&L after pessimistic costs, supervised demo fills and slippage measurement, account reconciliation, restart/kill tests, and verification that **$50** can support broker's **minimum 0.01 lot** without violating a **0.5% ($0.25)** loss budget. The historical screenshots already show examples where it cannot. There is no reliable way to engineer a 100% win rate or no loss in speculative leveraged markets.
