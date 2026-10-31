# V11 against the official rubric

No numerical scoring weights or judge cutoffs were supplied. A precise projected grade would be invented.

| Criterion | Evidence | Remaining weakness | Improvement pursued |
|---|---|---|---|
| Breadth | Own fills in all 26 products; fixed-value, trend, reversion, peer-relative, spread-capture and option models | Several products share generic quoting; participation is not a distinct strategy per symbol | Preserve coverage while testing execution rules suitable for smaller markets |
| Depth | Leave-one-out option smile, vertical-spread valuation bounds, live-vol delta, separate pending-fill budgets, persistent state and tests | Basket cross-model disabled; five products lose; call checks do not enforce full convexity; no fill-conditioned adverse-selection model | Separate passive entry and inventory-exit incentives; isolate execution-size and inventory-capacity effects |
| PnL | UTEFA website: 119,985 total, 39,995 mean daily increment, all three days positive, 4,491.5 maximum drawdown | All development reuses the same history; no independent OOS run; 47.4% of PnL is the two core products and 44.2% calls | Compare total/daily PnL, downside, coverage and errors; retain exact website logs |
| Communication | Reproducible comparison and accurate strategy guide | Older PDF describes an earlier version; member names unavailable | Document the final selected code and failed experiments before preparing the final abstract |

Five loss-making products are FRUIT_BASKET (-370), GRANADILLA (-245.5), JELLY (-396), LYCHEE (-270), MANGOSTEEN (-553). Their combined loss is 1,834.5; eliminating it alone would add only 1.53% of V11 PnL. Large gains must come from improving the main sources of profit, rather than claiming a tiny loss removal transforms the strategy.

V12 design uses controlled candidates, not a large parameter grid. A changes core order size (4 to 6), keeping risk limits fixed. B changes passive exits on non-core spot products, retaining V11 order sizes. C uses A's execution size with a reduced core inventory target (49 to 45). Their PnL comparisons come from the official UTEFA website. Local tests check correctness only.

A better abstract cannot be scored until it is written and synchronized. Full breadth is already reached; it can be preserved but cannot exceed 26/26. No candidate can be guaranteed better on OOS PnL or every judge's qualitative criteria.
