# Team 23 V10 backtest comparison

Selected: V10D_Capacity, consolidated into the sole active root file `Team23_Trader.py`.

| Candidate | Total PnL | Day -2 | Day -1 | Day 0 | Max drawdown | Traded | Errors/log messages |
|---|---:|---:|---:|---:|---:|---:|---:|
| V8Growth | 112,385.5 | 38,254.0 | 38,881.0 | 35,250.5 | 4,066.0 | 21/26 | 0 |
| quantifi-backtest (9) | 111,850.0 | 37,815.5 | 39,145.0 | 34,889.5 | 4,094.0 | 22/26 | 0 |
| V10A_RiskFixed | 111,926.0 | 38,054.5 | 38,604.0 | 35,267.5 | 4,066.0 | 21/26 | 0 |
| V10B_JellyExit | 111,350.0 | 37,718.5 | 38,622.0 | 35,009.5 | 4,094.0 | 22/26 | 0 |
| V10C_Breadth | 112,596.5 | 38,532.0 | 39,056.0 | 35,008.5 | 4,110.0 | 26/26 | 0 |
| V10D_Capacity | 119,985.0 | 41,488.0 | 40,977.5 | 37,519.5 | 4,491.5 | 26/26 | 0 |

## Selection and tradeoff

V10D gains 7,599.5 (+6.76%) versus V8 Growth and 8,135 (+7.27%) versus V9. It trades every supplied market and improves daily PnL on all three days versus both baselines. Maximum drawdown rises by 425.5 (+10.46%) versus V8 Growth. Candidate C is the lower-exposure alternative (112,596.5 PnL; 4,110 drawdown). D is selected for its stronger observed PnL and full breadth, with explicit acceptance of increased exposure.

V10 fixes a real execution-risk bug: pending opposite orders no longer offset each other when reserving portfolio delta. It estimates delta using live model volatility where reliable, permits JELLY inventory reductions when entry gates close, validates persistent numeric memory, and allows configuration overrides to work.

The core paper momentum and toffee reversion models remain. Passive cautious/wing quoting uses smaller inventory limits and competitive prices. D raises core inventory targets from 45 to 49 and selected call targets from 18 to 20; the estimated aggregate delta limit remains 35. The peer-relative PINK signal stays enabled; basket and other pearl cross-signals remain disabled. LYCHEE has an outright signal and risk limits, not an active delta hedge.

## Limits on conclusions

These are repeated development tests on the same three historical days, not independent OOS runs. No official point weights were supplied, so no numerical judge grade is claimed. Full coverage does not prove equally deep modeling of every market. JELLY and some fruit/underlying markets still lose money; the code is not perfect or guaranteed optimal. Risk bounds hold for arbitrary subsets of proposed fills at the current estimated deltas; future spot/volatility moves can change those deltas.

All candidate runs have 30,000 sandbox timestamps and no nonempty sandbox/lambda messages. Local invariant tests cover 2,000 randomized per-product cases and 400 portfolio cases per candidate, one-sided fills, limits, malformed memory, stateless restarts, clock resets, missing books, and subclass configuration. 29/30 positive 1,000-tick blocks are descriptive and dependent, not 30 independent trials.

## Selected product results

| Product | Final PnL | Own execution records |
|---|---:|---:|
| AMETHYST | 975.5 | 225 |
| BLACK_PEARLS | 312.5 | 81 |
| BLUE_PEARLS | 166.0 | 102 |
| DRAGONFRUIT | 915.5 | 29 |
| FRUIT_BASKET | -370.0 | 23 |
| GOLDEN_PEARLS | 1,675.0 | 99 |
| GRANADILLA | -245.5 | 33 |
| JELLY | -396.0 | 106 |
| LYCHEE | -270.0 | 94 |
| MANGOSTEEN | -553.0 | 31 |
| PAPER_LANTERNS | 32,650.5 | 283 |
| PEANUT_BUTTER | 113.5 | 94 |
| PINK_PEARLS | 546.0 | 99 |
| TELLURIUM | 5,492.0 | 848 |
| TOFFEE_CAKE | 24,215.5 | 579 |
| VOUCHER_6800 | 498.0 | 243 |
| VOUCHER_7000 | 6,087.0 | 945 |
| VOUCHER_7200 | 1,815.0 | 2014 |
| VOUCHER_7300 | 9,698.0 | 3315 |
| VOUCHER_7400 | 9,287.0 | 3604 |
| VOUCHER_7500 | 9,116.0 | 3802 |
| VOUCHER_7600 | 8,459.0 | 3634 |
| VOUCHER_7750 | 4,646.0 | 2299 |
| VOUCHER_7900 | 3,328.5 | 1644 |
| VOUCHER_8100 | 74.5 | 219 |
| WHITE_PEARLS | 1,748.5 | 108 |

## Final upload verification

The consolidated Team23_Trader.py was submitted successfully and rerun. Its downloaded log, Team23_Trader_V10.log, reproduces the selected D candidate exactly on total and per-product PnL, daily gains, drawdown, fills by product, and sandbox messages. Final PnL: 119,985; daily average: 39,995.
