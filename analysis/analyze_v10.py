"""Reproducible official-log summary; activity PnL is authoritative."""
import csv,io,json,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict

def summarize(path):
    p=Path(path); text=p.read_text(); sandbox,rest=text.split('Activities log:',1); activity,trades=rest.split('Trade History:',1)
    messages=[]; dec=json.JSONDecoder(); raw=sandbox.split('Sandbox logs:',1)[1].strip(); i=0; ticks=0
    while i<len(raw):
        obj,n=dec.raw_decode(raw,i); ticks+=1
        if obj.get('sandboxLog') or obj.get('lambdaLog'): messages.append(obj)
        i=n
        while i<len(raw) and raw[i].isspace():i+=1
    curves=defaultdict(float); ends={}; end_times={}
    for r in csv.DictReader(io.StringIO(activity.strip()),delimiter=';'):
        d=int(r['day']); t=int(r['timestamp']); s=r['product']; pnl=float(r['profit_and_loss'])
        curves[(d,t)]+=pnl
        if d not in ends:ends[d]={}
        ends[d][s]=pnl; end_times[d]=t
    peak=0; dd=0; equity=[]
    for k,v in sorted(curves.items()):
        peak=max(peak,v);dd=max(dd,peak-v);equity.append(v)
    previous=0; daily={}
    for d in sorted(ends):
        value=sum(ends[d].values());daily[d]=value-previous;previous=value
    own=Counter(t['symbol'] for t in json.loads(trades) if 'SUBMISSION' in (t['buyer'],t['seller']))
    block=[]; previous=0
    for i in range(999,len(equity),1000):block.append(equity[i]-previous);previous=equity[i]
    return dict(file=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),total=equity[-1],daily=daily,max_drawdown=dd,products_traded=len(own),fills=sum(own.values()),fills_by_product=dict(own),product_pnl=ends[max(ends)],positive_blocks=sum(x>0 for x in block),blocks=len(block),sandbox_ticks=ticks,nonempty_logs=len(messages),log_samples=messages[:3])
if __name__=='__main__':
    for arg in sys.argv[1:]:
        m=summarize(arg);Path(arg).with_suffix('.metrics.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k not in ('product_pnl','fills_by_product','log_samples','sha256')},indent=2))
