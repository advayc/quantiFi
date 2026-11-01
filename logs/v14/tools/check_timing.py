"""Timing gates use only the previous observed mid and do not suppress makers."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'v13'/'tools'))
from check_risk import load
from datamodel import OrderDepth, TradingState

def check(path):
 t=load(path).Trader(); book=OrderDepth({99:20},{103:-20})
 for side in [-1,1]:
  fair=110 if side>0 else 92
  def takes(move):
   os=t._make_orders('PAPER_LANTERNS',book,0,fair,True,last_move=move)
   return [o for o in os if o.quantity*side>0 and (o.price>=103 if side>0 else o.price<=99)]
  assert takes(-side) and not takes(side) and takes(0) and takes(None)
  os=t._make_orders('PAPER_LANTERNS',book,0,fair,True,last_move=side)
  assert any(o.quantity*side>0 for o in os)
 # Serialize mid and process reset; no instance attribute supplies the signal.
 s=TradingState('',0,{}, {'PAPER_LANTERNS':book},{},{},{},None)
 out=t.run(s); s.traderData=out[2];s.timestamp=100
 assert t.run(s)==load(path).Trader().run(s)
 print(Path(path).name,'PASS: timing gates, maker preservation, serialized memory')
if __name__=='__main__':
 for p in sys.argv[1:]:check(p)
