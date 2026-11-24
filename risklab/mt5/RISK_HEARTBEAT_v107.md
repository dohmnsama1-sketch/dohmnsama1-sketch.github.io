# ZALAH Risk Heartbeat Research v1.07 — DEMO / research only

**This version is a safety-engineering candidate, not a profitable trading model. It is not compiled in MetaEditor and has not traded an Exness demo account yet.**

## Files and provenance
- New candidate: `ZALAH_RiskHeartbeat_Research_v107.mq5`. Prior `ZALAH_LiveCalendar_SafeResearch_v106.mq5`, `ZALAH_NewsShock_SafeResearch_v105.mq5`, `ZALAH_SafeResearch_v104.mq5` remain preserved for A/B review.
- The native calendar is MetaTrader's own `CalendarValueHistory` USD query; event timestamps are in **broker trade-server time**, not Riyadh or UTC.
- News cannot reliably be accessed through the MT5 Strategy Tester; online native calendar remains enabled for connected DEMO by default, so `OnInit()` now **returns INIT_PARAMETERS_INCORRECT in Strategy Tester unless `InpUseLiveUsdEconomicCalendar=false` is explicitly chosen.** In the offline tester, disabling the live feed is not proof of a correctly backtested economic news embargo. Optional manual data must be historically available point-in-time, in server time.
- The live calendar may be absent, lagged or inaccurate during provider/API incidents. On errors, stale refresh, or ambiguous high-impact release times, no new entries should be allowed. There is no predictive geopolitics feature. Sudden shocks can damage an existing position before a filter recognizes them.

## New risk engineering in v1.07
1. **Timer heartbeat:** `EventSetTimer(InpSafetyTimerSeconds)` for non-tester DEMO monitors equity and active risk when the market is not generating ticks. If timer initialization fails, `OnInit()` returns failure. `OnDeinit()` kills the timer. Timer events require MT5 terminal running and do not work while device or terminal is offline.
2. **Stale quote defense:** if an **EA-owned** gold demo position is open and quote age exceeds `InpOpenPositionMaxQuoteAgeSeconds`, latch a persistent entry lock and attempt to close that EA-owned position. It cannot force a close when market is closed, disconnected, or rejecting orders. Other/manual magic IDs are not treated as belonging to this EA.
3. **Broker account restriction:** still DEMO-only; only USD-denominated demo accounts accepted for explicit USD fee assumptions, and symbol/timeframe must match the chart/tester.
4. **Position size loss stress:** estimate worst-case one-lot loss at the stop price **plus `InpAdverseStopSlippagePrice`** via `OrderCalcProfit`, add a conservative additional spread buffer and explicit `InpAssumedCommissionUSDPerLotRoundTurn`, and round lots **down** to the broker's step. Minimum contract larger than the 0.5% budget => **reject all orders**. Estimates are scenario assumptions, not guaranteed worst-case losses: gap-through-stop can exceed the allowance.
5. **Existing protections remain:** persistent equity/daily loss latch, one-position-per-symbol entry guard, spread and ATR shock cooldown, higher timeframe closed-bar EMA, ADX, stale tick entry rejection, high impact calendar guard and manual news embargo.
6. **Disaster case:** when terminal closes/crashes while an EA-owned position remains open, neither watchdog nor script can monitor or close it. A broker-side stop is required, yet market gaps, leverage and outages still pose loss risks.

## Current trading research evidence — all failures
- Independently evaluated public Dukascopy-derived 2026 gold quotes: **84,371,369 tick updates converted to 63,275 M5 bars** in GitHub run [45291504940](https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45291504940).
- Historical P/L on simulated USD 10,000 (0.15 USD/oz adverse slippage per side, assumed USD 7/lot fee): SMA baseline **-$937.59** (224 trades); EMA/ADX filter **-$145.45** (47 trades); Donchian breakout **-$860.87** (197 trades). All lose in the last independent segment; all fail strategy gate.
- **USD 50 real account:** simulated **zero eligible trades** under 0.5% risk and 0.01 minimum gold lot; no safe path to make this a daily high-margin profit machine via risk increases alone.
- v1.07 improves defensiveness but neither creates new predictive alpha nor proves returns; benchmark data above are from prior research engine and not v1.07 forward fills.

## Minimal validation needed
1. Download separate v1.07, compile in MetaEditor; capture exact compiler output: **0 errors** required before it is run even on DEMO.
2. For an offline tester explicitly disable the online USD economic calendar, record that the historical test then **does not** cover live calendar operation, and use a point-in-time manual schedule if verified.
3. Test on matching **XAUUSDm / M5** (or exact broker symbol) USD **DEMO**, with `InpAllowDemoOrders=false` until supervised risk tests. Do not attach to a real account.
4. On the connected DEMO, validate: calendar feed outage fails closed; a forced volatile bar and spread shock defer entries; restart preserves the latch; broker stop placement, fill receipts and margin; timer detects a simulated open-EA-position stale quote (on a controlled DEMO only). Record log timestamps, expected behavior and results.
5. Only if subsequent genuinely untouched historical data and actual forward demo evidence support positive expectancy after realistic costs should the hypothesis be reconsidered. **No live funded orders without explicit user approval and safe broker min-lot feasibility.**

## References
- MQL5 official EventSetTimer: https://www.mql5.com/en/docs/eventfunctions/eventsettimer
- MQL5 official OnTimer: https://www.mql5.com/en/docs/event_handlers/ontimer
- MQL5 official economic calendar timestamps: https://www.mql5.com/en/docs/calendar/calendarvaluehistory
- MQL5 official background on calendar/tester data export: https://www.mql5.com/en/book/advanced/calendar/calendar_cache_tester
