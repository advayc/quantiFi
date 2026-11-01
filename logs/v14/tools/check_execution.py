"""Multilevel execution must share size/risk budgets and stop at price limits."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'v13'/'tools'))
from check_risk import load
from datamodel import OrderDepth

def check(path):
 t=load(path).Trader()
 for sign in [-1,1]:
  # First eligible level has 1 unit, second 2, third ample, fourth ineligible.
  book=OrderDepth({99:1,98:2,97:20,94:20},{101:-1,102:-2,103:-20,106:-20})
  fair=105 if sign>0 else 95
  os=t._make_orders('PAPER_LANTERNS',book,0,fair,True)
  takes=[o for o in os if (o.price>=101 if sign>0 else o.price<=99) and o.quantity*sign>0]
  assert [(o.price,abs(o.quantity)) for o in takes]==([(101,1),(102,2),(103,3)] if sign>0 else [(99,1),(98,2),(97,3)])
  # Independent model-delta budget also reserves maker orders.
  os=t._make_orders('PAPER_LANTERNS',book,0,fair,True,33*sign,1)
  assert sum(abs(o.quantity) for o in os if o.quantity*sign>0)<=2
  # Near soft cap, at most one further same-direction unit can be posted.
  os=t._make_orders('PAPER_LANTERNS',book,48*sign,fair,True)
  assert sum(abs(o.quantity) for o in os if o.quantity*sign>0)<=1
 print(Path(path).name,'PASS: multilevel taker size, price, delta and inventory reservations')
if __name__=='__main__':
 for path in sys.argv[1:]:check(path)
