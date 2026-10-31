# QuantiFi Competition Team 23

The active algorithm is **Team23_Trader.py (V11)**. Earlier versions are archived under logs; only this root trader file should be used for the next backtest.

V11 combines fixed-value AMETHYST pricing, PAPER_LANTERNS momentum, TOFFEE_CAKE mean reversion, bounded trend/imbalance quotes, peer-relative PINK_PEARLS pricing, and call valuation from neighboring implied total volatilities. Basket cross-signals are disabled. Persistent memory travels in traderData.

Risk controls include product inventory targets, separate reservations for potential buy and sell fills, an estimated aggregate delta budget, and JELLY entry filters that still allow inventory reductions. These controls cannot guarantee future profitability.

The selected capacity candidate returned **119,985 PnL**, traded **26/26 products**, and had **4,491.5 maximum drawdown** on the three supplied days. These are development results on reused training data.

See [V10 comparison and limitations](logs/v10/RESULTS.md), [machine-readable comparison](logs/v10/comparison.csv), and the official logs in [logs/v10](logs/v10).

Reproduce the summaries with `python3 analysis/analyze_v10.py logs/v10/V10D_Capacity.log`; run risk checks with `python3 analysis/test_v10.py Team23_Trader.py`.

V11 adds executable peer-strike valuation bounds to the call model. It reproduces the V10 training result exactly. See [V11 validation](logs/v11/RESULTS.md) and [strategy/rubric guide](STRATEGY.md). The older abstract requires updating before submission.
