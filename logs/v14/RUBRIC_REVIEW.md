# V13 review and V14 execution experiments

The rubric grades breadth, depth, communication and average OOS PnL. It does not supply numerical point weights. The observations below are evidence and remaining gaps, not a projected judge score.

| Criterion | V13 benchmark | V14 focus |
|---|---|---|
| Breadth | Own fills in all 26 products, across fixed-value quoting, continuation, reversion, relative option valuation, passive hedge quotes and cautious spread capture | Preserve actual participation and distinct economic models; additional turnover alone does not improve breadth |
| Depth | Leave-one-strike-out option interpolation, executable peer bounds, portfolio-aware LYCHEE hedging, persistent memory and separate worst-case buy/sell reservations | Test liquidity depth, inventory cost in aggressive entries, and separation of PAPER's trend horizon from its execution horizon |
| PnL | 123,640.5 historical total; 41,213.5 mean daily increment; 4,128.5 observed maximum drawdown | Use official UTEFA runs to compare daily outcomes and risk, without another position-limit increase |
| Communication | Strategy explanation and complete earlier experiment logs | Document hypotheses, rejected variants, exact selected source and raw evidence; final abstract remains deferred and missing team member names |

## Remaining weaknesses

- The same three historical days have been used repeatedly. No experiment here can prove improvement in the organizers' unseen average PnL. Higher model complexity can make that problem worse.
- Historical profits are concentrated in the two core directional products and related calls. Full product participation does not imply independent return sources.
- Some small markets lose money. Tiny positions limit their contribution but do not demonstrate a profitable model for each product.
- Delta is a model estimate. Passive hedge orders may not fill, product capacity can bind, and price/volatility changes can move delta after submission. Opposing pending orders receive no risk credit.
- Option peer bounds provide per-contract valuation checks, not a fully fitted arbitrage-free surface or an executable atomic arbitrage package.

The selected result and precise metric changes belong in RESULTS.md after the official runs finish. No breadth gain is claimed when coverage stays at 26/26, and no communication grade is claimed while the abstract remains outdated.

## Completed outcome

Retain V13 unchanged. A loses 19 with unchanged drawdown. B loses 18,419.5 despite lower drawdown. C loses 10,150 with only 81 less drawdown. All retain 26-market coverage and have zero nonempty runtime logs. Neither B nor C improves any daily PnL increment. No tested combination is justified. V14 is an experiment archive, not a promoted strategy version; the single active root file remains V13. No fresh final-source rerun is needed because its bytes are unchanged from the archived baseline and previously verified V13 upload.

This round improves the audit trail and understanding of execution tradeoffs. It does not establish higher breadth, strategy depth, OOS PnL or an abstract grade for the active bot.
