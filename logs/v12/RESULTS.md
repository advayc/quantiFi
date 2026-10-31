# Team 23 V12: official UTEFA comparison

Selected: V12E_FamilyRisk, consolidated into the sole active root file Team23_Trader.py. Every PnL result below was obtained through the UTEFA website and downloaded with its Download logs control. Local tests check correctness; they do not simulate performance.

| Candidate | Total PnL | Mean daily increment | Day -2 | Day -1 | Day 0 | Maximum drawdown | Own fills | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Team23_Trader_V11 | 119,985.0 | 39,995.0 | 41,488.0 | 40,977.5 | 37,519.5 | 4,491.5 | 24553 | 26/26 |
| V12A_Execution | 124,983.5 | 41,661.2 | 44,343.0 | 43,150.0 | 37,490.5 | 4,816.5 | 24475 | 26/26 |
| V12B_InventoryExit | 120,395.5 | 40,131.8 | 41,545.0 | 41,384.0 | 37,466.5 | 4,385.0 | 24599 | 26/26 |
| V12C_EfficientCapacity | 120,641.5 | 40,213.8 | 42,784.0 | 42,159.0 | 35,698.5 | 4,520.5 | 24458 | 26/26 |
| V12D_Combined | 121,052.0 | 40,350.7 | 42,841.0 | 42,565.5 | 35,645.5 | 4,421.0 | 24504 | 26/26 |
| V12E_FamilyRisk | 123,447.0 | 41,149.0 | 43,865.0 | 43,429.5 | 36,152.5 | 4,421.0 | 24511 | 26/26 |

## Selection

V12E increases total development PnL by 3,462 (+2.89%) and lowers maximum observed drawdown by 70.5 (-1.57%) versus V11, preserving full coverage and zero sandbox/lambda messages. Mean daily increment is 41,149. A earns more but has a worse drawdown; E is selected for the joint profit/risk objective. This choice is an explicit tradeoff, not a proof that E will win on unseen data.

Day 0 declines from 37,519.5 to 36,152.5 (-1,367, or -3.64%). All three days remain positive; days -2 and -1 improve. There is no claim that every historical statistic improved, and breadth is already at its maximum 26/26.

## Controlled experiments

- A: core order size from four to six; limits unchanged. Higher PnL and higher drawdown.
- B: V11 plus passive inventory-exit concessions on all non-core spot markets. Higher PnL and lower drawdown.
- C: A with both core inventory targets reduced from 49 to 45. Much of the PnL gain is lost.
- D: C plus B exits. Higher PnL and lower drawdown than V11.
- E: D with PAPER_LANTERNS restored to 49, TOFFEE_CAKE retained at 45. Highest PnL among the tested candidates whose drawdown does not exceed V11.

The sequence is adaptive development on the same three days. Five tested configurations were retained, including failures and alternatives. It is not independent OOS validation. Do not represent the final verification rerun as an additional unseen test.

## Depth and execution change

Entry prices keep at least a small estimated edge. A non-core reducing quote may concede up to the lesser of half the spread and its inventory skew. Its quantity is capped to the held inventory remaining after any earlier reducing taker orders; maker quotes stay behind the opposite best price. This separates willingness to enter a position from willingness to exit it. It does not guarantee liquidation or eliminate adverse selection.

Core models, option smile, peer-strike checks and the independent buy/sell delta reservations remain. Product limits stay unchanged. Core order sizes become six; PAPER_LANTERNS soft limit remains 49, TOFFEE_CAKE becomes 45. Selected interior-call soft limits remain 20. Portfolio estimated delta limit remains 35.

## Rubric assessment

| Criterion | V12 evidence | Honest remaining limit |
|---|---|---|
| Breadth | All 26 markets trade, preserving the different strategy families | Some products share generic quoting; no claim of 26 unrelated models |
| Depth | Distinct momentum/reversion inventory budgets, explicit entry/exit economics, option valuation checks and tested fill-risk limits | Basket cross-signal disabled; no active hedge; some markets still lose |
| PnL | Higher total/mean daily historical PnL with lower drawdown than V11; official logs retained | OOS average PnL is unknown; one supplied day worsens; repeated selection risks overfit |
| Communication | Updated STRATEGY.md, full candidate comparison and reproducible raw logs | This is supporting material, not the final graded abstract; the older PDF must be rewritten and member names added |

The official rubric supplies no numerical weights, so no projected numerical grade is given. A stronger historical result cannot guarantee a better judge score.

## Reproduce the audit

Run python3 analysis/analyze_v10.py against any saved official .log. Metrics are based on the activity PnL series; daily gains are increments, not averages of cumulative endpoints. Products traded counts own trade records tagged SUBMISSION. Local tests cover one-sided fill risk, product limits, memory persistence, invalid memory, restarts, option price bounds and bounded passive inventory exits.

## Final file verification

Team23_Trader.py was uploaded and rerun through UTEFA. Its downloaded Team23_Trader_V12.log reproduces the selected E candidate on total and per-product PnL, daily increments, maximum drawdown, own executions by product and zero logged messages.
