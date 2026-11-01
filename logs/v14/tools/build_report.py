"""Compare downloaded UTEFA runs; never simulate fills or manufacture results."""
import csv,json,hashlib
from pathlib import Path
root=Path('logs/v14')
baseline=json.loads(Path('logs/v13/Team23_Trader_V13.metrics.json').read_text())
rows=[baseline]+[json.loads(p.read_text()) for p in sorted(root.glob('V14*.metrics.json'))]
selection=json.loads((root/'selection.json').read_text())
selected=json.loads((root/selection['metrics']).read_text())
lines=['# V14 official UTEFA results','','All PnL results come from uploads to https://www.utefa.com/quantifi and the raw downloaded `.log` files. Local tools summarize logs and check code; they do not backtest trading performance.','','| Version | PnL | Mean historical daily increment | Day -2 | Day -1 | Day 0 | Max drawdown | Markets filled | Nonempty runtime logs |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for m in rows:
 d=m['daily'];lines.append(f"| {Path(m['file']).stem} | {m['total']:,.1f} | {m['total']/3:,.1f} | {d['-2']:,.1f} | {d['-1']:,.1f} | {d['0']:,.1f} | {m['max_drawdown']:,.1f} | {m['products_traded']}/26 | {m['nonempty_logs']} |")
lines+=['','## Selection','',selection['reason'],'',f"Selected {selection['candidate']}: PnL changes by {selected['total']-baseline['total']:+,.1f} ({100*(selected['total']/baseline['total']-1):+.3f}%) versus V13; drawdown changes by {selected['max_drawdown']-baseline['max_drawdown']:+,.1f}. All configured position limits and base order sizes remain unchanged.",'','## Evidence and limitations','','See [experiment design](EXPERIMENTS.md) for hypotheses and [rubric review](RUBRIC_REVIEW.md) for what this changes in the judging criteria. The short-horizon price correlations and fill markouts are descriptions of the same training data, not independent validation. Markouts measure signed future mid minus fill price; they are not realized strategy PnL and are not incremental causal estimates.','','The mean daily increment above is not the organizers\' average across unseen OOS runs. Repeated selection on three days creates selection bias. The final rerun verifies reproducibility only. Product count is participation, not 26 independent profit sources. No official numeric rubric weights, OOS score or judge rank are available.','','## Per-product attribution','','| Product | V13 PnL | Selected PnL | Change | Selected fill records |','|---|---:|---:|---:|---:|']
for s,p in selected['product_pnl'].items():
 b=baseline['product_pnl'][s];lines.append(f"| {s} | {b:,.1f} | {p:,.1f} | {p-b:+,.1f} | {selected['fills_by_product'].get(s,0)} |")
final=root/'Team23_Trader_V14.metrics.json'
if final.exists():
 f=json.loads(final.read_text())
 for k in ['total','daily','max_drawdown','products_traded','product_pnl','fills_by_product','nonempty_logs','sandbox_ticks']:
  assert f[k]==selected[k],k
 lines+=['','## Final source verification','','The root `Team23_Trader.py` was uploaded to UTEFA after selection. Its downloaded `Team23_Trader_V14.log` reproduces the chosen candidate on total/daily/product PnL, drawdown, fills by product and runtime logs. Source and raw-log SHA-256 hashes are recorded in `source_log_sha256.json`.','',f"The final run contains {f['sandbox_ticks']:,} sandbox tick records and {f['nonempty_logs']} nonempty runtime logs; {f['positive_blocks']}/{f['blocks']} consecutive 1,000-tick historical blocks were profitable. Blocks share one inventory/memory path and are not independent experiments."]
(root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
with (root/'comparison.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['version','pnl','mean_historical_daily','day_minus2','day_minus1','day0','drawdown','products_filled','fill_records','nonempty_logs'])
 for m in rows:w.writerow([Path(m['file']).stem,m['total'],m['total']/3,*[m['daily'][d] for d in ['-2','-1','0']],m['max_drawdown'],m['products_traded'],m['fills'],m['nonempty_logs']])
paths=[Path('Team23_Trader.py'),root/'V13_baseline.py',*sorted((root/'candidates').glob('*.py')),*sorted(root.glob('*.log'))]
(root/'source_log_sha256.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
