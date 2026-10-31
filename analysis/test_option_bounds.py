"""Check vertical spread valuation bounds across volatility regimes."""
import importlib.util
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datamodel import OrderDepth
spec=importlib.util.spec_from_file_location('trader','Team23_Trader.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);t=m.Trader()
for v in [.03,.07,.12]:
    books={'LYCHEE':OrderDepth({7499:20},{7501:-20})}
    for k in m.VOUCHER_STRIKES:
        c=round(t._call_price(7500,k,v))
        books[f'VOUCHER_{k}']=OrderDepth({max(0,c-2):10},{c+2:-10})
    fairs=t._option_fair_values(books)
    assert fairs
    for s,f in fairs.items():
        k=t._option_strike(s)
        assert max(0,7500-k)<=f<=7500
        for q,b in books.items():
            j=t._option_strike(q)
            if j and j!=k:
                assert f>=max(b.buy_orders)-max(0,k-j)-1e-9
                assert f<=min(b.sell_orders)+max(0,j-k)+1e-9
    # Grossly inconsistent adjacent prices must not enter the fitted model.
    books['VOUCHER_8100']=OrderDepth({3000:10},{3002:-10})
    assert not t._option_fair_values(books)
print('PASS: peer-strike bounds, intrinsic limits and inconsistent-chain fallback')
