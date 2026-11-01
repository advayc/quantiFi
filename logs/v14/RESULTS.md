# V14 official UTEFA results

All PnL results come from uploads to https://www.utefa.com/quantifi and the raw downloaded `.log` files. Local tools summarize logs and check code; they do not backtest trading performance.

| Version | PnL | Mean historical daily increment | Day -2 | Day -1 | Day 0 | Max drawdown | Markets filled | Nonempty runtime logs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Team23_Trader_V13 | 123,640.5 | 41,213.5 | 44,521.5 | 42,591.5 | 36,527.5 | 4,128.5 | 26/26 | 0 |
| V14A_BookDepth | 123,621.5 | 41,207.2 | 44,502.5 | 42,591.5 | 36,527.5 | 4,128.5 | 26/26 | 0 |
| V14B_TakerInventory | 105,221.0 | 35,073.7 | 37,416.0 | 37,304.0 | 30,501.0 | 3,209.0 | 26/26 | 0 |
| V14C_PaperTiming | 113,490.5 | 37,830.2 | 39,787.5 | 39,120.5 | 34,582.5 | 4,047.5 | 26/26 | 0 |

## Selection

Retain V13 unchanged. A loses 19 with unchanged drawdown. B loses 18,419.5 despite lower drawdown. C loses 10,150 with only 81 less drawdown. All retain 26-market coverage and have zero nonempty runtime logs. Neither B nor C improves any daily PnL increment. No tested combination is justified. V14 is an experiment archive, not a promoted strategy version; the single active root file remains V13. No fresh final-source rerun is needed because its bytes are unchanged from the archived baseline and previously verified V13 upload.

Selected V13 retained: PnL changes by +0.0 (+0.000%) versus V13; drawdown changes by +0.0. All configured position limits and base order sizes remain unchanged.

## Evidence and limitations

See [experiment design](EXPERIMENTS.md) for hypotheses and [rubric review](RUBRIC_REVIEW.md) for what this changes in the judging criteria. The short-horizon price correlations and fill markouts are descriptions of the same training data, not independent validation. Markouts measure signed future mid minus fill price; they are not realized strategy PnL and are not incremental causal estimates.

The mean daily increment above is not the organizers' average across unseen OOS runs. Repeated selection on three days creates selection bias. The final rerun verifies reproducibility only. Product count is participation, not 26 independent profit sources. No official numeric rubric weights, OOS score or judge rank are available.

## Per-product attribution

| Product | V13 PnL | Selected PnL | Change | Selected fill records |
|---|---:|---:|---:|---:|
| AMETHYST | 975.5 | 975.5 | +0.0 | 225 |
| BLACK_PEARLS | 189.0 | 189.0 | +0.0 | 84 |
| BLUE_PEARLS | 33.5 | 33.5 | +0.0 | 102 |
| DRAGONFRUIT | 1,320.5 | 1,320.5 | +0.0 | 29 |
| FRUIT_BASKET | -370.0 | -370.0 | +0.0 | 23 |
| GOLDEN_PEARLS | 1,752.0 | 1,752.0 | +0.0 | 101 |
| GRANADILLA | -245.5 | -245.5 | +0.0 | 33 |
| JELLY | -396.0 | -396.0 | +0.0 | 106 |
| LYCHEE | -151.0 | -151.0 | +0.0 | 93 |
| MANGOSTEEN | -553.0 | -553.0 | +0.0 | 31 |
| PAPER_LANTERNS | 33,627.5 | 33,627.5 | +0.0 | 236 |
| PEANUT_BUTTER | 113.5 | 113.5 | +0.0 | 94 |
| PINK_PEARLS | 553.0 | 553.0 | +0.0 | 101 |
| TELLURIUM | 5,492.0 | 5,492.0 | +0.0 | 848 |
| TOFFEE_CAKE | 26,290.0 | 26,290.0 | +0.0 | 538 |
| VOUCHER_6800 | 497.0 | 497.0 | +0.0 | 245 |
| VOUCHER_7000 | 6,075.0 | 6,075.0 | +0.0 | 945 |
| VOUCHER_7200 | 1,787.0 | 1,787.0 | +0.0 | 2014 |
| VOUCHER_7300 | 9,706.0 | 9,706.0 | +0.0 | 3319 |
| VOUCHER_7400 | 9,325.0 | 9,325.0 | +0.0 | 3618 |
| VOUCHER_7500 | 9,211.0 | 9,211.0 | +0.0 | 3812 |
| VOUCHER_7600 | 8,708.0 | 8,708.0 | +0.0 | 3681 |
| VOUCHER_7750 | 4,596.0 | 4,596.0 | +0.0 | 2283 |
| VOUCHER_7900 | 3,349.5 | 3,349.5 | +0.0 | 1690 |
| VOUCHER_8100 | 71.5 | 71.5 | +0.0 | 217 |
| WHITE_PEARLS | 1,683.5 | 1,683.5 | +0.0 | 108 |
