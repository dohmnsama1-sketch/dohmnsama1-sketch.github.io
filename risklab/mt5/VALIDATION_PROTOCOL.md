# ZALAH research gate — not live-trade authorization

## Current evidence
- Baseline `ZALAH_Demo_Guard.mq5` v1.02: user MT5 screenshot, **Sep–Nov 2026** research sample, 25 trades, net -219.96 USD on 10,000 USD simulated initial balance, profit factor ~0.70, win rate 32%. Screenshot showed `History Quality: 0%`; treat result as *diagnostic*, not independently validated real-tick alpha.
- `ZALAH_Regime_Research_v103.mq5` is a **separate hypothesis**, not a profitable upgrade. Filters: last closed H1 bar vs 100 EMA; last closed M5 ADX >=20 and matching directional movement; spread/ATR <=0.20. Each filter is a fixed initial hypothesis and **not optimized** on the user screenshot.
- Neither EA can initialize on a real account. Order sending is off by default. CI source checks **do not compile MQL5**.

## Research design: A/B, no cherry-picking
1. Compile both files in MetaEditor. Confirm 0 errors. Keep separate names in Navigator.
2. On a licensed, provenance-documented Exness or independent gold data sample, confirm time range and real tick coverage; the MT5 model option alone is insufficient. Check Journal's actual first real tick timestamp and test report History Quality.
3. Run baseline v1.02 and candidate v1.03 with the SAME `XAUUSDm` symbol, M5, 10,000 USD **simulated** deposit, broker commissions, point size, leverage, swaps, tick coverage, 0.5% risk, identical spread cap and delays. Opt into demo/tester orders ONLY inside Strategy Tester. This 10k deposit is for research, not a recommended live deposit.
4. PRE-COMMIT chronological periods before inspecting candidate returns: training/analysis, validation, then later, untouched out-of-sample period; apply a time embargo around partitions. Do not adjust candidate parameters based on OOS results.
5. Report trades, percent profitable, gross profit, gross loss, **net** after fees, profit factor, expectancy per trade, max intraday and peak-to-trough equity drawdown, trading exposure, return volatility, payoff distribution, and test quality. Count distinct closed trades, not deal records or order attempts.
6. Simulate a spread/commission/slippage shock (e.g. 1x, 1.5x, 2x plausible costs) and execution interruptions. Stop-loss gaps and server rejection may lead to losses beyond nominal budget. Use a separate high-volatility/news segment.
7. Prefer candidate only with multiple independent profitable periods, credible sample size, and acceptable risk under cost stress. Discard candidate if results are worse or uncertain. No single strategy is guaranteed to outperform other bots.
8. On a **real 50 USD** account, re-check the *actual instrument* minimum lot, margin, and minimum risk per trade. 10k simulator performance is not automatically achievable on 50 USD. No deposits or real trades until explicitly approved and suitable broker trade constraints are met.

## Data provenance and macro events
- MetaTrader 5 supports broker tick-history access and externally imported data on *custom instruments*; document timestamps/time zones, source/licensing, bid/ask, missing data, spreads, dividends/swaps as relevant, and symbol contract specs. **Do not replace Exness CFD specs with unrelated data-provider specs** without calibration.
- Dukascopy Historical Data Export is a potential independent tick history source, subject to availability, license and format checks. It is **not** currently downloaded or validated for this project.
- Economic calendar/geopolitical news analysis requires timestamped point-in-time records and publication-time controls. MQL5 built-in economic calendar is **not generally available from Strategy Tester**; use historically stored event files/resources before testing news rules. The v1.03 candidate does not claim a working news filter.

## Current unresolved release blockers
- User's screenshot reports History Quality 0%.
- Candidate v1.03 compilation in MetaEditor unverified.
- Candidate independent real tick OOS performance unmeasured.
- Trade execution latency, spreads, fills and slippage on continuous Exness demo unmeasured.
- Restart-safe account-level kill switch and unattended system monitoring unimplemented. Do not run unattended or fund the bot as a production system.
