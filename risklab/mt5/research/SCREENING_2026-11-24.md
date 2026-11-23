# ZALAH independent historical screening — 24 November 2026

**Status: no strategy approved. Do not fund or live-trade.**

## Pinned independent BID/ASK source
- Public Dukascopy-derived external quotes (not broker fills); pinned data repository Touhid-HZ/xauusd-tick-data-2026 commit `019f74d942545196adab8e481338fde7c4df67c4`.
- Prior full source run GitHub Actions https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45288503401: 47 weekly files; **84,371,369 tick rows**, **63,275 M5 bars** Jan-Nov 2026. **Earlier simulator version** before stricter favorable-gap and fee accounting fixes:
  - baseline SMA 10/30, 224 closed trades, 0.15 adverse slippage each side, net **-$916.26**, PF 0.8446, holdout **-$227.83**.
  - regime-filtered baseline, 47 closed trades, net **-$136.17**, PF 0.8958, holdout **-$248.86**.
  - Both negative. Future data snooping concern: multiple hypotheses are already inspected on parts of the 2026 history; positive later 2026 results are *exploratory*, not untouched independent prospective proof.

## Updated benchmark: fee model and conservative target-gap fill
- Independent GitHub Actions https://github.com/dohmnsama1-sketch/dohmnsama1-sketch.github.io/actions/runs/45291111217
- Weeks 1–3, **5,234,182 ticks / 3,846 M5 bars**, fixed research contract 100 oz/lot, minimum .01 lot, $10k test balance (not actual deposit), 0.5% per-trade capital risk, 0.50 USD/oz spread cap, hypothetical **$7 per whole lot round-trip commission** (not an Exness confirmed fee). Net includes bid/ask, assumed commission and configured adverse slippage per side.
- Cost shocks and results:

| Strategy | Closed trades | 0 USD/oz slippage | 0.15 USD/oz slippage | 0.50 USD/oz slippage |
|---|---:|---:|---:|---:|
| baseline SMA crossover | 7 | -$204.10 | **-$208.90** | -$286.33 |
| regime H1 EMA + ADX | 0 | $0 | **$0** | $0 |
| prespecified Donchian36 breakout + H1 EMA | 4 | +$49.97 | **-$71.25** | -$77.90 |

- Profit in the *zero-slippage* breakout variant is **NOT** robust; a small adverse fill assumption turns it negative. Four trades cannot show a reliable edge. Current independent release gate rejected ALL THREE strategies as `INSUFFICIENT_EVIDENCE`.
- 50 USD simulated account: zero trades under 0.5% risk with min 0.01 gold lot. A zero-trade account cannot claim "no-loss profitable" performance.
- Python tests: 27 passed for data quality, closed-bar signals, fee modeling, pessimistic fills, chronological split and fail-closed research gate. CI tests check **software invariants**, not profitability.

## Engineering and business rules
1. Keep Exness MT5 real account disabled. v1.04 EA remains a DEMO-only separate build; no direct broker connection or successful source compilation of latest EA in this run.
2. Large backtests must use the *corrected* simulator and be repeated only when engineering QA passes, without unnecessary data download costs.
3. Future evaluation needs tick-exact fill path, broker contract execution/cost validation, new independently timestamped prospective holdout and forward DEMO records.
4. Target **positive robust risk-adjusted returns after realistic costs**, not high win-rate marketing, 99-100% returns or a guarantee of zero loss.
