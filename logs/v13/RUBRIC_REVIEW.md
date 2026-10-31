# V12 review and V13 experiment design

The official rubric supplies qualitative breadth, depth, communication and average OOS PnL criteria, without point weights. No projected numerical grade is assigned.

| Criterion | V12 evidence | Gap addressed in V13 |
|---|---|---|
| Breadth | Actual own fills in all 26 products; several strategy families | Preserve coverage; improve the purpose of LYCHEE trading within the option family |
| Depth | Product-dependent directional signals, option smile with vertical-spread bounds, inventory exit economics and separate pending-fill delta reservations | Underlying quotes ignore held option delta; call-value checks do not yet use payoff convexity |
| PnL | UTEFA: 123,447 cumulative; 41,149 mean daily increment; 4,421 maximum drawdown; all three days profitable | Unknown OOS behavior; repeated selection uses the same three days; five spot markets lose in aggregate |
| Communication | STRATEGY.md and complete candidate comparisons | Final graded abstract is still outdated and missing member names; documentation alone does not complete this criterion |

## Candidates

- A: delta-aware passive LYCHEE quoting. Set its fair to book mid and use held portfolio delta, rather than standalone LYCHEE position, for reservation-price and size skew. Remove its competing outright trend/imbalance forecast. Keep the underlying soft position limit 24 and the estimated portfolio delta limit 35. Pending opposite orders still provide no offset credit.
- B: convex-call payoff bounds. A call between neighboring strikes must lie below their price chord; outside a peer pair it must lie above the extrapolation. Use asks for positive upper-bound coefficients and bids for positive lower-bound coefficients, reversing quote side for negative coefficients. Intersect with V12's existing vertical-spread bounds; fall back to book-based quoting when intervals are inconsistent. Deduplicate strike aliases before dividing by a strike gap.
- C: combine A and B if isolated tests support their inclusion.

The core signal strengths, order sizes, soft inventory targets and delta limit are frozen. These are economic model/execution experiments, not another capacity sweep.

## Diagnostics and rejected hypothesis

A simple common fruit-return factor had correlations with future basket changes near zero and inconsistent signs across the supplied days/horizons (see market_diagnostics.json). This does not disprove every basket model. It is insufficient support for adding this particular lead/lag forecast. The old basket cross-signal remains disabled.

## Limits

A passive hedge can remain unfilled and can reach the LYCHEE inventory cap. Delta is model-estimated, and spot/volatility changes can move it after submission. No realized delta-risk reduction is claimed merely from a quote rule. Per-target convex inequalities do not establish a globally coherent arbitrage-free fitted surface. No atomic option/underlying execution or exercise is assumed.

All performance results must come from UTEFA's website and its downloaded .log files. Local tests verify math, code and order constraints only. Retain failed candidates and final source hashes. A repeat on identical data is a reproducibility check, not a fresh OOS run.
