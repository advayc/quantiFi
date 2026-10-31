# V13 official UTEFA comparison

All performance results below come from uploads to https://www.utefa.com/quantifi and the downloaded raw .log files. Local tools verify math and summarize those logs; they do not generate backtest PnL.

| Version | Total PnL | Historical mean daily increment | Day -2 | Day -1 | Day 0 | Max drawdown | Products with own fills | Nonempty sandbox/lambda logs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Team23_Trader_V12 | 123,447.0 | 41,149.0 | 43,865.0 | 43,429.5 | 36,152.5 | 4,421.0 | 26/26 | 0 |
| V13A_PortfolioHedge | 123,640.5 | 41,213.5 | 44,521.5 | 42,591.5 | 36,527.5 | 4,128.5 | 26/26 | 0 |
| V13B_ConvexBounds | 121,736.0 | 40,578.7 | 42,792.0 | 42,897.5 | 36,046.5 | 4,500.5 | 26/26 | 0 |

## Selection

Selected: V13A_PortfolioHedge. Relative to V12, total historical PnL changes by +193.5 (+0.157%) and maximum drawdown falls by 292.5 (6.62%).

Select the portfolio-aware passive hedge. It increases historical PnL slightly and lowers drawdown while preserving all 26 markets. Convexity candidate B loses 1,711 versus V12 and has higher drawdown, so it is rejected. The proposed combined candidate is not run because the isolated convexity experiment did not support inclusion. The active code retains V12 vertical-spread checks and does not add the rejected convexity logic.

## Improvements against the rubric

| Criterion | What changed | Limits on the claim |
|---|---|---|
| Breadth | Preserves all 26 traded markets; LYCHEE has a portfolio-hedge role within the call family | Coverage was already complete; this does not create 26 independent alpha sources |
| Depth | Uses held portfolio delta to price and size underlying quotes; retains distinct core models, per-product capacities and independent pending-side risk budgets. The convexity alternative is documented and rejected after its controlled test | Passive hedge fills are uncertain; LYCHEE cap can bind; current-delta budgets cannot prevent future gamma/volatility effects. Per-target bounds are not a globally projected arbitrage-free surface |
| PnL | Controlled UTEFA experiments compare total, daily attribution, coverage, drawdown and runtime logs | Historical selection is repeated on the same three days; no independent OOS average or judge rank is available |
| Communication | Updated strategy explanation, failed-hypothesis diagnostic, raw logs, source hashes and reproducible summaries | A code/documentation update does not finish the graded abstract. The older PDF and missing member names remain outstanding |

## Mathematical and execution details

The zero-rate call payoff is convex in strike. For L<K<U, C(K) is at most the linear chord through C(L), C(U); using peer asks gives a conservative upper bound. Two peer prices on one side imply a lower extrapolation bound, using bids for positive coefficients and asks for negative coefficients. Intersect these with the previous intrinsic and vertical-spread intervals. Deduplicate equal-strike aliases to avoid zero denominators. Contradictory bounds disable the cross-strike model fair, leaving small book-based quoting.

LYCHEE uses its current mid as fair rather than a competing outright trend/imbalance forecast. Its quote/size skew uses held LYCHEE units plus held call delta. A short underlying position offsetting long calls is not automatically unwound just for being short. The underlying target limit remains 24 and the estimated portfolio delta limit remains 35. Unfilled option or hedge orders are never credited as risk offsets.

## Validation and selection limits

Checks include randomized product/portfolio fill subsets, stateless restarts, malformed memory, passive exit size caps, hedge direction/offset behavior, synthetic convex call chains over 200 spot/volatility regimes, and duplicate-strike aliases. See candidate_tests.txt and final_tests.txt.

The fruit-factor diagnostic is exploratory signal analysis, not a local backtest. Its correlations were too small/inconsistent to justify the proposed simple basket lead/lag signal. The basket signal stays disabled. This is evidence of rejecting an unsupported model, not evidence that all basket strategies fail.

All configurations and failed alternatives are retained. No numerical rubric weights were supplied, so no numerical projected grade is invented. The small PnL difference is not established as statistically significant, and the final reproducibility rerun is not another independent experiment.

## Selected product attribution

| Product | Final PnL | Own execution records |
|---|---:|---:|
| AMETHYST | 975.5 | 225 |
| BLACK_PEARLS | 189.0 | 84 |
| BLUE_PEARLS | 33.5 | 102 |
| DRAGONFRUIT | 1,320.5 | 29 |
| FRUIT_BASKET | -370.0 | 23 |
| GOLDEN_PEARLS | 1,752.0 | 101 |
| GRANADILLA | -245.5 | 33 |
| JELLY | -396.0 | 106 |
| LYCHEE | -151.0 | 93 |
| MANGOSTEEN | -553.0 | 31 |
| PAPER_LANTERNS | 33,627.5 | 236 |
| PEANUT_BUTTER | 113.5 | 94 |
| PINK_PEARLS | 553.0 | 101 |
| TELLURIUM | 5,492.0 | 848 |
| TOFFEE_CAKE | 26,290.0 | 538 |
| VOUCHER_6800 | 497.0 | 245 |
| VOUCHER_7000 | 6,075.0 | 945 |
| VOUCHER_7200 | 1,787.0 | 2014 |
| VOUCHER_7300 | 9,706.0 | 3319 |
| VOUCHER_7400 | 9,325.0 | 3618 |
| VOUCHER_7500 | 9,211.0 | 3812 |
| VOUCHER_7600 | 8,708.0 | 3681 |
| VOUCHER_7750 | 4,596.0 | 2283 |
| VOUCHER_7900 | 3,349.5 | 1690 |
| VOUCHER_8100 | 71.5 | 217 |
| WHITE_PEARLS | 1,683.5 | 108 |

## Final upload verification

The single active Team23_Trader.py was uploaded and rerun on UTEFA. Team23_Trader_V13.log reproduces the selected candidate on total/per-product PnL, daily increments, maximum drawdown, fill counts by product and runtime messages.
