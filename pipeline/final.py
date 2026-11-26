import json,math
from tr import trace,crop2ll
G=json.load(open('geo_ll.json'));R=json.load(open('retrace.json'))
B=(22.600,120.305,22.642,120.332);s=1.06
c=lambda x,y:crop2ll(B,x*s,y*s)
R['p205']=trace(c(745,1890),c(640,1800),c(480,1700),c(380,1730))
HB=(22.612,120.272,22.624,120.292)
hm=trace(crop2ll(HB,232,58),crop2ll(HB,165,150),crop2ll(HB,115,215))
R['hm']=hm+[[22.61948,120.2735],[22.61945,120.2720],[22.61950,120.2710],[22.61970,120.27005]]
def m(a,b):return math.hypot((a[0]-b[0])*111000,(a[1]-b[1])*111000*math.cos(math.radians(22.6)))
def proj(p,a,b):
    k=math.cos(math.radians(22.6));ax,ay=a[1]*k,a[0];bx,by=b[1]*k,b[0];px,py=p[1]*k,p[0]
    dx,dy=bx-ax,by-ay;L=dx*dx+dy*dy or 1e-12;t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L))
    q=[round(ay+t*dy,6),round((ax+t*dx)/k,6)];return q,t
def snap(line,targets,which=(0,-1),tol=180):
    for idx in which:
        p=line[idx];best=None
        for tk in targets:
            T=G['seg'][tk] if tk in G['seg'] else None
            if T is None:continue
            for i in range(len(T)-1):
                q,t=proj(p,T[i],T[i+1]);d=m(p,q)
                if best is None or d<best[0]:best=(d,tk,i,q,t)
        if best and best[0]<tol:
            d,tk,i,q,t=best;T=G['seg'][tk]
            if 0<t<1:T.insert(i+1,q)
            else:q=T[i] if t==0 else T[i+1]
            line[idx]=q
    return line
S=G['seg']
def despike(L,ang=120):
    k=math.cos(math.radians(22.6));ch=True
    while ch and len(L)>2:
        ch=False
        for i in range(1,len(L)-1):
            a,b,c2=L[i-1],L[i],L[i+1]
            v1=((b[1]-a[1])*k,b[0]-a[0]);v2=((c2[1]-b[1])*k,c2[0]-b[0])
            n=math.hypot(*v1)*math.hypot(*v2)
            if n and math.degrees(math.acos(max(-1,min(1,(v1[0]*v2[0]+v1[1]*v2[1])/n))))>ang:
                del L[i];ch=True;break
    return L
e1=R['e1']
# trim e1 where it first comes within 12 m of the Pingtung line
cut=None
for i,p in enumerate(e1):
    for j in range(len(S['pt'])-1):
        q,t=proj(p,S['pt'][j],S['pt'][j+1])
        if m(p,q)<12:cut=i;break
    if cut is not None:break
S['e1']=despike(e1[:cut+1] if cut else e1)
S['hm']=despike(R['hm'][2:])
# 草衙->中鋼: follow 1989 track to corner, then OSM 中鋼側線
cs_osm=S['s2b'][2:] if len(S['s2b'])>2 else S['s2b']
S['s2b']=R['cy_corner']+cs_osm
# order matters: snap branches onto parents
snap(S['e1'],['pt'],which=(-1,));S['e1'][0]=S['br'][-1]
snap(S['west'],['zg_n','zg_s'],which=(-1,))
snap(S['hm'],['west'],which=(0,),tol=250);despike(S['hm'],90)
def rdpm(L,eps=8):
    k=math.cos(math.radians(22.6))*111000
    P=[(p[1]*k,p[0]*111000) for p in L]
    def r(i,j):
        a,b=P[i],P[j];dx,dy=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dy) or 1
        best,bi=0,None
        for t in range(i+1,j):
            d=abs(dx*(P[t][1]-a[1])-dy*(P[t][0]-a[0]))/n
            if d>best:best,bi=d,t
        return (r(i,bi)[:-1]+r(bi,j)) if best>eps else [i,j]
    return [L[i] for i in r(0,len(L)-1)]
S['e1']=rdpm(despike(S['e1'],100),7)
snap(S['w0'],['west'],which=(0,))
snap(S['zd'],['w1'],which=(0,))
snap(S['s2'],['br','w1'],which=(0,))
snap(S['s2b'],['s2'],which=(0,))
snap(S['c2'],['s2'],which=(0,))
snap(S['c3'],['s2','s2b'],which=(0,))
snap(S['br'],['w1'],which=(0,))
# extras
X={}
X['205兵工廠側線']=[snap(despike(R['p205']),['e1','br'],which=(0,))]
X['臺糖倉庫側線']=[snap(R['tw'],['s2','br','w1'],which=(0,))]
X['高港支線（蓬萊碼頭）']=[snap(despike(R['hg']),['west','w0'],which=(0,),tol=250)]
X['小港糖廠線']=[snap(R['xg'],['s2b'],which=(0,))]
for k in ('淺野線（臺泥側線）','裏岸壁線','糖鐵小港線（鳳山—小港糖廠）','糖鐵籬子內線','高雄港站機迴線'):
    if k in G['extra']:X[k]=G['extra'][k]
X['淺野線（臺泥側線）']=[snap(X['淺野線（臺泥側線）'][0],['zg_n','zg_s','west'],which=(0,-1),tol=120)]
X['裏岸壁線']=[snap(X['裏岸壁線'][0],['w0'],which=(0,-1),tol=120)]
X['糖鐵籬子內線']=[snap(X['糖鐵籬子內線'][0],['s2','br','w1'],which=(0,-1),tol=250)]
G['extra']=X
# light rail lr1/lr2 start/end consistency not needed
G['br']={'5.4K 中島線分歧':S['zd'][0],'6.8K 第二臨港線分歧':S['s2'][0]}
G['st']['前鎮車場']=S['br'][-1]
json.dump(G,open('geo_final.json','w'),separators=(',',':'))
print('ok',S['e1'][-1],S['s2'][0])
