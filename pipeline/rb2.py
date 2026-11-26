import json,math,numpy as np
from scipy.ndimage import gaussian_filter1d
from corr import corridor,ll2px,px2ll
G=json.load(open('geo_t.json'));S=G['seg'];X=G['extra']
k=math.cos(math.radians(22.6))
def toM(L):return np.array([[p[1]*k*111000,p[0]*111000] for p in L])
def toLL(A):return [[round(y/111000,6),round(x/(k*111000),6)] for x,y in A]
def m(a,b):return math.hypot((a[0]-b[0])*111000,(a[1]-b[1])*111000*k)
def rdp(A,eps):
    def r(i,j):
        a,b=A[i],A[j];d=b-a;n=np.hypot(*d) or 1
        if j<=i+1:return [i,j]
        t=np.abs(d[0]*(A[i+1:j,1]-a[1])-d[1]*(A[i+1:j,0]-a[0]))/n;q=int(np.argmax(t))
        return (r(i,i+1+q)[:-1]+r(i+1+q,j)) if t[q]>eps else [i,j]
    return A[r(0,len(A)-1)]
def gs(L,sig=10,step=2.5):
    A=toM(L);seg=np.hypot(*np.diff(A,axis=0).T);c=np.concatenate([[0],np.cumsum(seg)])
    if c[-1]<3*step:return L
    s=np.arange(0,c[-1],step);s=np.append(s,c[-1])
    R=np.stack([np.interp(s,c,A[:,0]),np.interp(s,c,A[:,1])],1)
    sg=min(sig/step,len(R)/6)
    B=np.stack([gaussian_filter1d(R[:,0],sg,mode='nearest'),gaussian_filter1d(R[:,1],sg,mode='nearest')],1)
    # blend so endpoints stay exact
    w=np.clip(np.minimum(s,s[-1]-s)/(3*sig),0,1)[:,None];B=w*B+(1-w)*R
    return toLL(rdp(B,0.8))
def cp(pts,buf=12):
    ll=[px2ll(*p) for p in pts];return corridor(ll,buf)
def proj(p,a,b):
    ax,ay=a[1]*k,a[0];bx,by=b[1]*k,b[0];px,py=p[1]*k,p[0]
    dx,dy=bx-ax,by-ay;Lq=dx*dx+dy*dy or 1e-12;t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/Lq))
    return [round(ay+t*dy,6),round((ax+t*dx)/k,6)],t
def near(p,T):
    best=None
    for i in range(len(T)-1):
        q,t=proj(p,T[i],T[i+1]);d=m(p,q)
        if best is None or d<best[0]:best=(d,i,q,t)
    return best
def attach(L,T,idx=0,tol=250):
    d,i,q,t=near(L[idx],T)
    if d>tol:print('far',round(d));return L
    if 0<t<1:T.insert(i+1,q)
    else:q=T[i] if t==0 else T[i+1]
    L[idx]=q;return L
def split(T,p):
    d,i,q,t=near(p,T);return T[:i+1]+[q],[q]+T[i+1:]
# ---------- main west line rebuilt from 1989 map
l1w=cp([(700,2915),(707,2936),(760,2965),(816,2998),(853,3023),(916,3050),(971,3075),(1025,3100),(1080,3127),(1116,3146),(1160,3162),(1190,3160),(1215,3140),(1245,3105),(1271,3082)],10)
w0=cp([(1271,3082),(1310,3058),(1350,3052)],14)
w1=cp([(1350,3052),(1400,3060),(1440,3095),(1455,3150),(1432,3225),(1385,3290),(1365,3350),(1372,3410),(1405,3450),(1460,3480),(1550,3515),(1640,3545),(1700,3570),(1745,3600),(1790,3700),(1830,3800),(1862,3900),(1900,4000),(1922,4040)],14)
qzb=cp([(1922,4040),(1932,4075),(1945,4105)],12)
w2=cp([(1945,4105),(1960,4170),(1963,4240),(2000,4305),(2060,4355),(2120,4385),(2150,4398),(2200,4385),(2300,4350),(2400,4310),(2506,4254)],14)
segs={'l1w':l1w,'w0':w0,'w1':w1,'qzb':qzb,'w2':w2}
for kk,v in segs.items():segs[kk]=gs(v,6 if kk in('qzb','w0') else 22)
# re-chain exact joins
order=['l1w','w0','w1','qzb','w2']
for a,b in zip(order,order[1:]):segs[b][0]=segs[a][-1]
west=gs(S['west'],15)
segs['l1w'][0]=near(segs['l1w'][0],west)[2];attach(segs['l1w'],west,0)
k4=gs(S['br'],22);e1=gs(S['e1'],20)
k4[0]=segs['w2'][-1];e1[0]=k4[-1]
pt=S['pt'];attach(e1,pt,-1,300)
NS={'zg_n':S['zg_n'],'zg_s':S['zg_s'],'pt':pt,'west':west,'hm':S['hm'],'ob':gs(S['ob'],8),**segs,'k4':k4,'e1':e1}
# branches
zd=gs(S['zd'],18);attach(zd,NS['w2'],0)
s2=gs(S['s2'],20);s2[0]=k4[0]
s2b=gs(S['s2b'],8);s2b[0]=s2[-1]
c2=gs(S['c2'],8);attach(c2,s2,0);c3=gs(S['c3'],8);attach(c3,s2,0,300)
attach(NS['ob'],west,0,300);attach(NS['hm'],west,0,300)
NS.update({'zd':zd,'s2':s2,'s2b':s2b,'c2':c2,'c3':c3,'lr1':S['lr1'],'lr2':S['lr2']})
# ---------- sidings
E={}
nbq=gs(cp([(725,3036),(785,3059),(871,3095),(953,3127),(1044,3159),(1110,3180),(1160,3190)],10),16);attach(nbq,west,0,200)
E['北裏岸壁線（三號船渠北岸）']=[nbq]
for n in ('中岸壁線','裏岸壁線'):E[n]=[gs(X[n][0],8)]
attach(E['中岸壁線'][0],NS['ob'],0);attach(E['裏岸壁線'][0],E['中岸壁線'][0],0)
s205=gs(cp([(2785,3975),(2778,3930),(2765,3885),(2730,3842),(2680,3802),(2620,3765),(2560,3737),(2490,3723),(2440,3728),(2405,3760)],12),14);attach(s205,k4,0)
E['205 兵工廠外側線（廠區北緣，兼通中化公司）']=[s205]
tt=gs(cp([(2560,4295),(2580,4245),(2610,4228),(2700,4223),(2780,4220),(2800,4205),(2810,4170),(2818,4100),(2825,4020)],10),12);attach(tt,s2,0)
E['臺糖倉庫／副產品加工廠側線']=[tt]
al=gs(cp([(1890,4030),(1870,3995),(1830,3982),(1780,3985),(1730,4000),(1700,4015)],10),8);attach(al,NS['w1'],0)
E['成功路側線（臺鋁南側油槽區）']=[al]
tf=gs(cp([(1962,4245),(1945,4272),(1910,4288),(1875,4300)],10),6);attach(tf,NS['w2'],0)
E['臺肥三廠側線']=[tf]
sug=gs([p for p in X['糖鐵（籬仔內線）'][0] if ll2px(*p)[1]>4215],10);attach(sug,tt,0,60);E['糖鐵（籬仔內線）']=[sug]
fs=X['糖鐵小港線（鳳山—小港糖廠）'][0];cut=len(fs)
for i in range(1,len(fs)):
    if m(fs[i-1],fs[i])>120:cut=i;break
E['糖鐵小港線（鳳山—小港糖廠）']=[gs(fs[:cut],12)]
xg=gs(X['小港糖廠線'][0],8);attach(xg,s2b,0);E['小港糖廠線']=[xg]
for n in ('淺野線（臺泥側線）','高雄港站機迴線','濱線（商港側，往海關碼頭）'):E[n]=X[n]
attach(E['濱線（商港側，往海關碼頭）'][0],NS['hm'],0)
G['seg']=NS;G['extra']=E
G['br']={'5.4K 中島線分歧':zd[0],'6.8K 第二臨港線分歧':s2[0]}
G['st']['前鎮車場']=k4[-1]
q=segs['qzb'];G['br']['前鎮橋（1955）']=q[len(q)//2]
for n,ref,sg in [('苓雅寮車場',(1443,3217),'w1'),('新光',(1705,3572),'w1'),('中島車場',(1504,4057),'zd'),('高雄機廠',(3056,3343),'e1')]:
    G['st'][n]=near(px2ll(*ref),NS[sg])[2]
json.dump(G,open('geo_v8.json','w'),separators=(',',':'))
print({k:len(v) for k,v in NS.items()})
