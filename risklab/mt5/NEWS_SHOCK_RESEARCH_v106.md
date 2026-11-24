# ZALAH v1.06 — Economic News and Shock Research Protocol

**Status: exploratory DEMO-only source. Not compiled in MetaEditor as of 2026-11-24; do not use on real funds. No proof of positive alpha, let alone near-zero losses.**

## What was actually coded

- `ZALAH_NewsShock_SafeResearch_v105.mq5` retains the v1.04 demo-account guard, default OFF order switch, capital risk and broker-side SL/TP; adds a **volatility shock cooldown** when a completed M5 range exceeds 3 times the *preceding closed-bar ATR*, when the bid/ask price spread exceeds the existing 0.50 gold-price-unit threshold, or when the observed M5 timestamp gap exceeds 30 minutes. The default cooldown is 60 minutes. This halts **new entries** only; positions already open remain subject to broker execution and original exits.
- State persistence via the MT5 terminal's global variables `Z104_<login>_<symbol>_<magic>_SHOCK`, reusing the previous v1.04 guard prefix. This helps survive restart; terminal global variables are not permanent tamper-proof records and require supervised restart testing.
- Optional **manual known-event blackout**: `InpUseManualNewsBlackout=true`, `InpHighImpactServerTimes` is semicolon-separated event release dates/times e.g. `YYYY.MM.DD HH:MM;YYYY.MM.DD HH:MM`, and `InpNewsScheduleExpiresServer` must be a future timestamp, all **in the broker server time zone**. Default 45 minutes before/after release. Missing, invalid or expired manual schedule means NO NEW ENTRIES. This is NOT an automatically refreshed news service.
- `ZALAH_LiveCalendar_SafeResearch_v106.mq5` adds native MT5 **live USD macroeconomic events**: `CalendarValueHistory(...,"","USD")`, `CalendarEventById` and `CALENDAR_IMPORTANCE_HIGH`. Defaults: enabled for supervised connected DEMO, 48-hour lookahead, refresh every 15 minutes, 45-minute pre/post blackout. If live calendar call, event metadata or time specificity is unavailable the EA **blocks new entries**. An empty valid calendar result is not proof all global events are covered.
- Native calendar times follow MT5 **trade server time**, not automatically UTC or Riyadh time. Compare the terminal's server clock and event release source before validation.
- The native MT5 USD economic calendar **does not monitor unstructured geopolitical news or know unexpected events before they become public**. The price/spread/gap guard is a REACTIVE proxy for unexpected dislocation, not an AI forecast. A live geopolitical-risk news feed with recorded publication/receipt timestamps is NOT implemented or independently tested.

## Mandatory safe verification

1. Preserve existing v1.02–v1.05; create `ZALAH_LiveCalendar_SafeResearch_v106.mq5` as a *separate* Expert Advisor in MetaEditor; press Compile. It must show **zero errors**. **This has not yet been verified**. Static GitHub tests are not MQL5 compiler tests.
2. In MT5 connect only an explicitly labeled **DEMO** account. Attach only to `XAUUSDm` **M5**. Keep `InpAllowDemoOrders=false` during initial inspection of Journal: `ZALAH_CALENDAR`, `ZALAH_SHOCK`, `SAFETY LOCK` and `ZALAH_DIAG`. If calendar is unreachable, order entry must stay disabled. Do not disable the filter to force a profitable-looking test.
3. For MT5 Strategy Tester, set `InpUseLiveUsdEconomicCalendar=false` because economic calendar APIs are not usable there; to claim news-aware historical testing you must ALSO set `InpUseManualNewsBlackout=true` with original-source-verified, historically **pre-announced** release dates mapped to broker server time and a valid schedule expiry. If no such data is available, explicitly mark test **NO NEWS FILTER**. A future revised calendar is NOT reliable evidence of what was known at each historical decision time.
4. On supervised DEMO, check that artificially widened spread, high-range M5 closed bar, or delayed-feed condition blocks an entry. Ensure test involves only synthetic/instrumented conditions and NEVER a funded account. Verify restart persistence and no repeated entries. Test no-data calendar, error retcodes, old tick, invalid/high-latency feed, and the loss lock.
5. **Do not increase risk, leverage, or force broker min 0.01 lot** to enable trades on a $50 account. Historical zero trades with that capital reflects a genuine risk/lot-size conflict. No live or unattended deployment approval was granted.
6. Before choosing v1.06, execute independent broker-equivalent real-tick A/B testing and supervised live DEMO forward trading with measured fills and costs; establish after-cost alpha, realistic intrabar equity drawdowns and capacity. News guards can reduce trading opportunities *and can worsen profits*; they are protective hypotheses to test, not proven performance upgrades.

## Point-in-time economic/geopolitical event research

Optional archival interface `research/news_event_gate.py` enforces no hindsight. CSV columns MUST be exactly:

`id,kind,event_at_utc,known_at_utc,importance,source_url`

- `kind` is `scheduled_economic`, `unscheduled_geopolitical`, or `exchange_disruption`; severity is `high` or `critical`. Times must use ISO UTC with final `Z`. `known_at_utc` is the first supportable source timestamp at which the information became public. A scheduled release must have been announced before it happened; a surprise must NOT be assumed known ahead of its first timestamp.
- Require a provenance URL to original archived source and independently verify that source is timestamped. The code validates file structure and timestamps but cannot verify that a URL's publication claim is truthful or its content was unchanged. No actual historical geopolitical event dataset was loaded or authenticated for this research.
- Research replay, only with verified records: `python risklab/mt5/research/walkforward_bidask.py --m5 path/to/aggregated.csv --news-events-csv path/to/verified_events.csv --output /tmp/zalah_news_benchmark.json`. Without the optional file, the report explicitly says the news embargo was NOT enabled. The code refuses an empty required feed.
- Tests include pre-known scheduled releases, sudden events known only after their publication, impossible hindsight, stale feed and unsupported time zones. See `research/test_news_event_gate.py`.
- Events imported for replay are NOT converted automatically into broker-server-time MQL5 manual settings; source UTC offset/DST mapping is a separate audited step.

## Evidence and release gate

2026 independent public tick feed yielded **negative net P/L** for all prior SMA/regime/Donchian strategies. See `research/FULL_YEAR_RESULTS_2026-11-24.md` for documented source run, 84,371,369 BID/ASK quote records and negative holdout P/L. The updated v1.06 has **NO measured independent profitability and no completed MQL5 compilation**, and CANNOT claim to beat Sonic or other competitor EAs without independently verified cost-comparable results.

Official background:
- https://www.mql5.com/en/docs/calendar/calendarvaluehistory — API, USD filter, trade-server time
- https://www.mql5.com/en/docs/calendar/calendareventbyid — event metadata
- https://www.mql5.com/en/book/advanced/calendar — calendar tester limitations
- https://www.mql5.com/en/docs/marketinformation/symbolinfotick — current bid/ask/timestamps
