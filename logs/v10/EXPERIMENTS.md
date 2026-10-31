# V10 experiment protocol

Baseline: V8 Growth original downloaded log, 112,385.5 PnL. V9: 111,850.
Their only product-level PnL difference is JELLY (-535.5).

All candidates preserve the core directional parameters and order sizes.
All use independent buy/sell delta reservations, live model-consistent
volatility where available, corrected configuration inheritance, malformed
memory recovery, and JELLY entry gates that permit position reductions.

- A: JELLY entries off; original conservative quotes on inactive markets.
- B: A plus V9 JELLY entries, with exits allowed when its entry filter closes.
- C: B plus at-spread passive quoting for cautious products and option wings;
  reduced cautious/wing position limits (4% of hard limit), no directional
  JELLY tilt, and JELLY half-width one half-spread rather than 0.85 half-spreads.

Selection considers daily profit consistency, total PnL, drawdown, breadth,
and correctness. Same-data comparisons are development experiments, not OOS
validation. There are no official numerical rubric weights available here.

Risk bounds apply to current estimated deltas and arbitrary subsets of
submitted fills. They cannot prevent delta changes when prices/volatility move.
An existing breach blocks new exposure in the breached direction, while
permitting reducing orders; it does not force immediate liquidation.

- D: C with core soft inventory limits raised from 45 to 49 and selected
  call limits from 18 to 20. Selected after improving all three days;
  higher observed drawdown is disclosed in RESULTS.md.
