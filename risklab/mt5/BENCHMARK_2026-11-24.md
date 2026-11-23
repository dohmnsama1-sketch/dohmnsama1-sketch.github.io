# ZALAH MT5 research log — 2026-11-24

Source: user-provided MT5 Strategy Tester screenshots (not signed or exported machine-readable reports). No claim of independently audited P&L. **Do not use for live deployment.**

## Latest Research v1.03 screenshot
- Exness-MT5Trial15 DEMO, symbol XAUUSDm, M5, simulated initial deposit 10,000 USD.
- History Quality **0%**; bars 15,965; ticks 17,170,897. Approximate test period Sep 1–Nov 19, 2026 as seen in the journal. Prior run indicated real ticks starting Nov 20, 2026, so these simulated tick counts do NOT establish broker real-tick coverage for this backtest.
- Net profit **-63.21 USD** (-0.6321% of starting balance), gross profit +1,178.20, gross loss -1,241.41; profit factor 0.95, expected payoff -1.47 per closed trade.
- 43 closed trades (86 deals); 18 winning (41.86%) and 25 losing (58.14%). 33 short trades (45.45% win) and 10 long trades (30.00% win).
- Max equity drawdown **491.52 USD / 4.73%**; max balance drawdown **409.68 USD / 3.96%**.
- Journal diagnostics: 17,170,897 ticks, 3,496 eligible bars, 149 crossovers, 85 trend/regime filters, 17 ADX filtered, 0 cost filters, 0 regime missing data. Remaining fields cropped in provided screenshot; don't invent them.

## Earlier v1.02 user-screenshot baseline
- 25 closed trades, 8 wins (32%), profit factor 0.70, net -219.96 USD on 10,000 USD demo starting balance, max equity drawdown 3.67%.
- Settings, tick coverage and exact start/end timestamps must be matched before treating changes as causal improvements. A v1.03 outcome of -63.21 instead of -219.96 is **not evidence of robust outperformance** with History Quality=0%; v1.03 also shows *more* max equity drawdown.

## Next actions / release gate
1. Download and export XAUUSDm **Ticks** via MT5 Market Watch > Symbols > Ticks > Request, and Bars likewise. Document available real-tick start/end dates, server time zone, bid/ask spread, interruptions and CSV export; preserve contract specifications.
2. Use a **real-tick-only eligible period** for both v1.02 and v1.03, without changing parameter values. Confirm report History Quality and log statements. A short first test merely checks data/operation, it is NOT a reliable profitability estimate.
3. Move to train/validation/OOS periods with chronological embargo and enough independent trades. Preserve untouched OOS until the very end. Report costs, equity DD, risk and negative controls.
4. Keep actual USD 50 deposits and all real orders disabled; current Exness Standard 0.01 lot can exceed 0.5% USD 50 risk budget by a large multiple. No leverage or risk-limit increases just to permit trading.
5. MQL5 compile result for Research v1.03 is supported by screenshot of successful Strategy Tester execution, but source-level GitHub Actions tests are not full compiler validation. Automated daemon, persistent kill switch and live demo order measurement are not yet verified.

This log is descriptive research tracking, not a trading recommendation or guarantee.
