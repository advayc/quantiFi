# QuantiFi Competition Team 23

The single active algorithm is **Team23_Trader.py (V12)**. Earlier sources and official UTEFA backtest logs are archived under logs/v1 through logs/v12. Use this root file for the next backtest.

V12 combines fixed-value AMETHYST pricing, PAPER_LANTERNS momentum, TOFFEE_CAKE mean reversion, bounded trend/imbalance quoting, peer-relative PINK_PEARLS pricing, and call valuation from neighboring implied total volatilities. Option values respect executable peer-strike bounds. Basket cross-signals remain disabled.

Execution uses separate pending buy/sell delta reservations, serialized traderData, six-unit core orders, different momentum/reversion inventory targets, and passive inventory-reducing concessions on non-core products. Entry filters do not block bounded JELLY exits.

The selected candidate returned **123,447 PnL**, traded **26/26 products**, and had **4,421 maximum drawdown** on UTEFA's three supplied days. Versus V11 this is **2.89% more profit and 1.57% less drawdown**. Day 0 worsened; these are reused training-data results, not independent OOS validation.

See [V12 experiments and rubric assessment](logs/v12/RESULTS.md), [strategy guide](STRATEGY.md), [V11 rubric review](logs/v11/RUBRIC_REVIEW.md), and [comparison CSV](logs/v12/comparison.csv). Raw .log files are committed alongside the metrics for every version.

Reproduce a log summary with `python3 analysis/analyze_v10.py logs/v12/Team23_Trader_V12.log`. Correctness checks: `python3 analysis/test_v10.py Team23_Trader.py`, `python3 analysis/test_option_bounds.py`, and `python3 analysis/test_inventory_exits.py Team23_Trader.py`.

The older PDF abstract is not synchronized with V12. Before the competition form submission, write an abstract describing this final model, add Team 23 and member names at the top of page one, and keep it within five pages. Names have not yet been supplied.
