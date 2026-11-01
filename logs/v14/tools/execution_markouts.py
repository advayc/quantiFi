"""Descriptive markouts of actual V13 fills, not a new fill/PnL simulation."""
import csv,io,json
from collections import defaultdict
from pathlib import Path
raw=Path('logs/v13/Team23_Trader_V13.log').read_text()
a,t=raw.split('Activities log:',1)[1].split('Trade History:',1)
books={int(r['timestamp']):r for r in csv.DictReader(io.StringIO(a.strip()),delimiter=';') if r['product']=='PAPER_LANTERNS'}
out=defaultdict(lambda:defaultdict(float))
for trade in json.loads(t):
 if trade['symbol']!='PAPER_LANTERNS' or 'SUBMISSION' not in (trade['buyer'],trade['seller']):continue
 time=trade['timestamp']; row=books[time]; direction=1 if trade['buyer']=='SUBMISSION' else -1
 if time-100 not in books:continue
 price=trade['price']; qty=trade['quantity']
 takes=price>=float(row['ask_price_1']) if direction>0 else price<=float(row['bid_price_1'])
 if not takes:continue
 move=float(row['mid_price'])-float(books[time-100]['mid_price'])
 label='chasing_last_move' if move*direction>0 else 'flat_or_against_last_move'
 for h in [1,10,25]:
  future=books.get(time+100*h)
  if not future or future['day']!=row['day']:continue
  d=out[(int(row['day']),label,h)]
  d['quantity']+=qty; d['records']+=1
  d['signed_future_mid_minus_fill']+=qty*direction*(float(future['mid_price'])-price)
result=[{'day':day,'condition':label,'horizon_ticks':h,**d,'mean_markout_per_unit':d['signed_future_mid_minus_fill']/d['quantity']} for (day,label,h),d in sorted(out.items())]
Path('logs/v14/paper_fill_markouts.json').write_text(json.dumps(result,indent=2))
for d in result:
 if d['horizon_ticks'] in (1,25):print(d['day'],d['condition'],d['horizon_ticks'],round(d['mean_markout_per_unit'],3),int(d['quantity']))
