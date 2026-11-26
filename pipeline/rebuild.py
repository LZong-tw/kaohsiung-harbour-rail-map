import json,math
from corr import corridor,ll2px,px2ll
exec(open('final2.py').read().split('# ---- east line')[0])  # helpers: m,proj,nearest_on,rdpm,chaikin,despike
G=json.load(open('geo_final2.json'));S=G['seg'];X=G['extra']
sm=lambda L,e=4:chaikin(rdpm(L,e),2)
# 1) main 臨港線 corridors: retrace each segment along its current approx within a buffer
for key,buf in [('west',45),('nb',90),('w0',60),('w1',70),('br',50),('e1',50),('zd',50),('s2',40),('c2',50),('c3',50)]:
    try:
        S[key]=sm(corridor(S[key],buf),4)
    except Exception as ex:print('fail',key,ex)
# 2) 中化公司／硫酸錏廠側線 (replace '205兵工廠側線')
B=(22.585,120.305,22.612,120.340)
def cp(x,y):  # crop pixel of /tmp/c_qz.png (z16) -> ll
    x0,y0=ll2px(B[2],B[1]);return px2ll(x0+x,y0+y)
X.pop('205兵工廠側線',None)
cz=[cp(780,545),cp(785,470),cp(760,420),cp(700,330),cp(600,295),cp(500,292),cp(400,330)]
X['中化公司／硫酸錏廠側線']=[sm(corridor(cz,25),3)]
tw=[cp(540,795),cp(600,800),cp(700,792),cp(800,790)]
X['臺糖倉庫側線']=[sm(corridor(tw,25),3)]
# 3) 糖鐵 籬仔內: from 臺糖副產品加工廠 south, then SE along 中山四路 (1989 dashed line) to existing OSM line
old=X.pop('糖鐵籬子內線')[0]
south=[p for p in old if p[0]<22.5900]
nb=[cp(826,588),cp(822,700),cp(820,850),cp(818,980)]
north=sm(corridor(nb,20),3)
X['糖鐵（籬仔內線）']=[north+[cp(760,1040),cp(740,1060)]+sorted(south,key=lambda p:-p[0])]
json.dump(G,open('geo_r.json','w'),separators=(',',':'))
print('ok')
