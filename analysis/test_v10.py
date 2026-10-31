"""Risk invariants across adversarial inventory and one-sided fill scenarios."""
import importlib.util, random, sys, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datamodel import OrderDepth, TradingState

def load(path):
    spec=importlib.util.spec_from_file_location('candidate',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def check(path):
    m=load(path); t=m.Trader(); rng=random.Random(23)
    for _ in range(2000):
        symbol=rng.choice(list(m.POSITION_LIMITS)); hard=m.POSITION_LIMITS[symbol]
        pos=rng.randint(-hard,hard); exposure=rng.uniform(-35,35); d=rng.random()
        orders=t._make_orders(symbol,OrderDepth({99:10},{103:-10}),pos,rng.uniform(90,110),True,exposure,d)
        buy=sum(max(o.quantity,0) for o in orders); sell=sum(min(o.quantity,0) for o in orders)
        assert pos+buy<=hard and pos+sell>=-hard
        assert exposure+buy*d<=35+1e-9 and exposure+sell*d>=-35-1e-9
        assert all(isinstance(o.price,int) and isinstance(o.quantity,int) and o.quantity for o in orders)
    books={'LYCHEE':OrderDepth({7499:50},{7501:-50})}
    for strike in m.VOUCHER_STRIKES:
        price=round(t._call_price(7500,strike,.07))
        books[f'VOUCHER_{strike}']=OrderDepth({price-3:10},{price+3:-10})
    for _ in range(400):
        positions={s:rng.randint(-10,10) for s in books}
        state=TradingState('',0,{},books,{}, {},positions,None)
        orders,_,_=t.run(state)
        fairs=t._option_fair_values(books)
        ds={'LYCHEE':1}
        for s in books:
            k=t._option_strike(s)
            if k:
                b=books[s]; v=t._implied_total_vol(fairs.get(s,(max(b.buy_orders)+min(b.sell_orders))/2),7500,k)
                ds[s]=t._option_delta(7500,k,v)
        current=sum(positions[s]*ds[s] for s in books)
        hi=current+sum(max(0,o.quantity)*ds[s] for s,os in orders.items() for o in os)
        lo=current+sum(min(0,o.quantity)*ds[s] for s,os in orders.items() for o in os)
        assert hi<=max(35,current)+1e-9 and lo>=min(-35,current)-1e-9
    for raw in ['bad','[]','{"version":2,"ema":{"X":"bad"},"count":{}}','{"version":2,"ema":{},"count":{},"last_mids":[]}']:
        t.run(TradingState(raw,0,{}, {}, {},{}, {},None))
    # Entry gates must not lock in an existing inventory.
    for pos in [-2,2]:
        state=TradingState('',0,{}, {'JELLY':OrderDepth({100:10},{102:-10})},{},{},{'JELLY':pos},None)
        os=t.run(state)[0].get('JELLY',[])
        assert os and all(o.quantity*pos<0 for o in os)
        assert sum(abs(o.quantity) for o in os)<=abs(pos)
    # Stateless process restarts must produce identical decisions from traderData.
    state=TradingState('',100,{},books,{},{},{},None)
    first=t.run(state)
    state.traderData=first[2]; state.timestamp=200
    assert t.run(state)==m.Trader().run(state)
    state.timestamp=0
    reset=t.run(state)
    assert all(n==1 for n in json.loads(reset[2])['count'].values())
    # Empty/one-sided books and unknown symbols must not crash or create orders.
    state=TradingState('',0,{}, {'UNKNOWN':OrderDepth({1:1},{3:-1}), 'AMETHYST':OrderDepth({10000:1},{})},{},{},{},None)
    assert not t.run(state)[0]
    class Override(m.Trader):
        CORE_RISK_FRACTION=.2
        VOUCHER_ORDER_SIZE=3
    assert Override._risk_limit('PAPER_LANTERNS',50)==10
    assert Override._order_size('VOUCHER_7300')==3
    print(Path(path).name, 'PASS: 2,000 single-product + 400 portfolio scenarios; gates, memory, overrides')
if __name__=='__main__':
    for p in sys.argv[1:] or sorted(Path('logs/v10/candidates').glob('*.py')): check(p)
