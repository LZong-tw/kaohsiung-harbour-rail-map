"""選路徑錨點用：列出某組站場股道上離給定像素點最近的股道片段與距離。

python3 yardnear.py GROUP X,Y [X,Y ...]
  GROUP：G['yards'] 的組別序號；座標為高雄港站 z18 像素（左上角 120.2715, 22.6270），與 yardlines.py、yarddiag.py 相同
"""
import json,sys
sys.path.insert(0,'.')
from yardroute import Graph
from yardlines import px2ll,ll2px
import numpy as np, yardroute as yr
gi=int(sys.argv[1]);G=json.load(open('geo_v13.json'));g=Graph(G['yards'][gi]['lines'])
for a in sys.argv[2:]:
    x,y=map(float,a.split(','));p=yr.to_xy(px2ll(x,y))
    d,k=g.tree.query(p,k=6)
    out=[]
    for dd,kk in zip(d,k):
        c,i=g.idx[kk];q=g.ch[c][i];ll=(q[1]/yr.KY+yr.LAT0,q[0]/yr.KX+yr.LON0);px=ll2px(ll)
        out.append(f'ch{c}@({px[0]:.0f},{px[1]:.0f}) {dd:.1f}m')
    print(a,' | '.join(dict.fromkeys(out)))
