# V11: option valuation consistency

Active code: Team23_Trader.py. V10 baseline archived as V10_baseline.py.

The submitted V11 code adds zero-rate call vertical-spread bounds from peer executable quotes. It intersects the model fair with intrinsic value, the underlying price, monotonicity, and the maximum strike slope of one. An inconsistent peer chain falls back to book-based quoting. It does not enforce full convexity or claim an atomic arbitrage.

Official backtest: 119,985 total PnL; daily increments 41,488 / 40,977.5 / 37,519.5; mean daily increment 39,995; maximum drawdown 4,491.5; fills in 26/26 markets; 24,553 own execution records; 30,000 sandbox timestamps with zero nonempty sandbox/lambda messages. All reported metrics and per-product PnL match V10. No incremental historical PnL gain is claimed. Economic guardrails improve failure handling on inconsistent markets; they do not establish improved OOS performance.

Tests: randomized risk invariants, stateless memory, malformed inputs, synthetic option chains across three total-volatility regimes, peer bounds and inconsistent-chain fallback. Run python3 analysis/test_v10.py Team23_Trader.py and python3 analysis/test_option_bounds.py.

The raw log remains available locally in this folder. GitHub includes metrics and source/log hashes; the compressed V10 log is under logs/v10. The raw V11 log is not duplicated in git. These are development results on reused training data. The official judging has no numerical weights supplied here; no estimated grade is presented.
