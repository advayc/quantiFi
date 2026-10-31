"""Model invariants independent of historical PnL and fill simulation."""
import sys,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from check_risk import load
from datamodel import OrderDepth

def check(path):
 m=load(path);t=m.Trader();rng=random.Random(23)
 if hasattr(t,'ENABLE_PORTFOLIO_HEDGE'):
  book=OrderDepth({98:20},{102:-20})
  def quotes(held,delta):return t._make_orders('LYCHEE',book,held,100,True,delta,1,delta,False,delta)
  neutral=quotes(0,0);long_delta=quotes(0,25);short_delta=quotes(0,-25)
  assert max(o.price for o in long_delta if o.quantity<0)<max(o.price for o in neutral if o.quantity<0)
  assert max(o.price for o in short_delta if o.quantity>0)>max(o.price for o in neutral if o.quantity>0)
  # The same net delta gives the same reservation, even if spot inventory
  # is an offsetting hedge of a call position. Capacities can still differ.
  neutral_hedged=quotes(-20,0)
  assert [(o.price,o.quantity) for o in neutral_hedged]==[(o.price,o.quantity) for o in neutral]
 for _ in range(200):
  spot=rng.uniform(7100,7900);vol=rng.uniform(.04,.14)
  books={'LYCHEE':OrderDepth({int(spot-1):20},{int(spot+1):-20})}
  # Use the actual book-mid spot in the same payoff model.
  spot=(max(books['LYCHEE'].buy_orders)+min(books['LYCHEE'].sell_orders))/2
  for k in m.VOUCHER_STRIKES:
   price=round(t._call_price(spot,k,vol));books[f'VOUCHER_{k}']=OrderDepth({max(0,price-2):10},{price+2:-10})
  fairs=t._option_fair_values(books)
  assert fairs
  for s,f in fairs.items():
   k=t._option_strike(s);peers=sorted((t._option_strike(q),max(b.buy_orders),min(b.sell_orders)) for q,b in books.items() if q!=s and t._option_strike(q))
   assert max(0,spot-k)<=f<=spot
   if 'Convexity supplies' in Path(path).read_text():
    for l,lb,la in peers:
     for u,ub,ua in peers:
      if l<k<u:
       w=(u-k)/(u-l);assert f<=w*la+(1-w)*ua+1e-8
    left=[q for q in peers if q[0]<k];right=[q for q in peers if q[0]>k]
    for pair in (left[-2:],right[:2]):
     if len(pair)!=2:continue
     l,lb,la=pair[0];u,ub,ua=pair[1]
     if k>u:lower=((k-l)*ub-(k-u)*la)/(u-l)
     else:lower=((u-k)*lb-(l-k)*ua)/(u-l)
     assert f>=lower-1e-8
  # Aliased quote names at one strike must not divide by a zero strike gap.
  books['LYCHEE_VOUCHERS_7300']=books['VOUCHER_7300']
  t._option_fair_values(books)
 print(Path(path).name,'PASS: hedge behavior and 200 convex payoff regimes including strike aliases')
if __name__=='__main__':
 for path in sys.argv[1:]:check(path)
