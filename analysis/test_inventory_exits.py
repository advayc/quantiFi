"""Concessional maker exits must only reduce held inventory."""
import random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.test_v10 import load
from datamodel import OrderDepth
m=load(sys.argv[1] if len(sys.argv)>1 else 'logs/v12/candidates/V12B_InventoryExit.py'); t=m.Trader();rng=random.Random(23)
for _ in range(3000):
    symbol=rng.choice(sorted(t.INVENTORY_EXIT_PRODUCTS)); hard=m.POSITION_LIMITS[symbol]
    p=rng.randint(-hard,hard);f=rng.uniform(92,110);b=OrderDepth({99:20},{103:-20})
    os=t._make_orders(symbol,b,p,f,True)
    cb=[o for o in os if o.quantity>0 and o.price>f-.5]
    cs=[o for o in os if o.quantity<0 and o.price<f+.5]
    assert sum(o.quantity for o in cb)<=max(0,-p)
    assert sum(-o.quantity for o in cs)<=max(0,p)
    assert all(o.price<103 for o in cb) and all(o.price>99 for o in cs)
print('PASS: 3,000 concessional exit cases; held-quantity cap and passive pricing')
