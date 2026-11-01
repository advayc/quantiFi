"""Signal diagnostics only: no execution/fill simulation or strategy PnL."""
import csv,json,math
from pathlib import Path
products=['PAPER_LANTERNS','TOFFEE_CAKE','TELLURIUM','JELLY','PEANUT_BUTTER','FRUIT_BASKET','DRAGONFRUIT','GRANADILLA','MANGOSTEEN']
out={}
for path in sorted(Path('Data').glob('prices*.csv')):
 data={s:[] for s in products}
 for r in csv.DictReader(path.open(),delimiter=';'):
  if r['product'] in data:data[r['product']].append(r)
 day={}
 for s,rs in data.items():
  mids=[float(r['mid_price']) for r in rs];ema=mids[0];dev=[]
  for mid in mids:ema=(2/101)*mid+(99/101)*ema;dev.append(mid-ema)
  def corr(a,b):
   n=len(a);ma=sum(a)/n;mb=sum(b)/n;va=sum((v-ma)**2 for v in a);vb=sum((v-mb)**2 for v in b)
   return sum((v-ma)*(w-mb) for v,w in zip(a,b))/math.sqrt(va*vb) if va*vb else 0
  d={'mean_spread':sum(float(r['ask_price_1'])-float(r['bid_price_1']) for r in rs)/len(rs),'ask_volume_below_six':sum(float(r['ask_volume_1'])<6 for r in rs)/len(rs),'bid_volume_below_six':sum(float(r['bid_volume_1'])<6 for r in rs)/len(rs),'ema_deviation_forward_correlation':{}}
  for h in [1,10,25]:
   d['ema_deviation_forward_correlation'][h]=corr(dev[100:-h],[mids[i+h]-mids[i] for i in range(100,len(mids)-h)])
  day[s]=d
 out[path.name]=day
Path('logs/v14/market_diagnostics.json').write_text(json.dumps(out,indent=2))
for day,ss in out.items():
 print(day)
 for s,d in ss.items():print(s,'spread',round(d['mean_spread'],1),'thin top',round(d['ask_volume_below_six'],2),'forward corr', {h:round(c,3) for h,c in d['ema_deviation_forward_correlation'].items()})
# Distinguish return autocorrelation from the EMA-deviation diagnostic above.
timing={}
for path in sorted(Path('Data').glob('prices*.csv')):
 p=[float(r['mid_price']) for r in csv.DictReader(path.open(),delimiter=';') if r['product']=='PAPER_LANTERNS']
 changes=[p[i]-p[i-1] for i in range(1,len(p))]
 x,y=changes[:-1],changes[1:]
 timing[path.name]={'lag1_return_correlation':corr(x,y),'next_return_after_up':sum(b for a,b in zip(x,y) if a>0)/sum(a>0 for a in x),'next_return_after_down':sum(b for a,b in zip(x,y) if a<0)/sum(a<0 for a in x)}
Path('logs/v14/paper_timing_diagnostics.json').write_text(json.dumps(timing,indent=2))
