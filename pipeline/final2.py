import json,math
G=json.load(open('geo_final.json'));A=json.load(open('am45_shift.json'))
S=G['seg'];X=G['extra']
k=math.cos(math.radians(22.6))
def m(a,b):return math.hypot((a[0]-b[0])*111000,(a[1]-b[1])*111000*k)
def proj(p,a,b):
    ax,ay=a[1]*k,a[0];bx,by=b[1]*k,b[0];px,py=p[1]*k,p[0]
    dx,dy=bx-ax,by-ay;L=dx*dx+dy*dy or 1e-12;t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L))
    return [round(ay+t*dy,6),round((ax+t*dx)/k,6)],t
def nearest_on(p,L):
    best=None
    for i in range(len(L)-1):
        q,t=proj(p,L[i],L[i+1]);d=m(p,q)
        if best is None or d<best[0]:best=(d,i,q,t)
    return best
def rdpm(L,eps):
    P=[(p[1]*k*111000,p[0]*111000) for p in L]
    def r(i,j):
        a,b=P[i],P[j];dx,dy=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dy) or 1;best,bi=0,None
        for t in range(i+1,j):
            d=abs(dx*(P[t][1]-a[1])-dy*(P[t][0]-a[0]))/n
            if d>best:best,bi=d,t
        return (r(i,bi)[:-1]+r(bi,j)) if best>eps else [i,j]
    return [L[i] for i in r(0,len(L)-1)]
def chaikin(L,n=2):
    for _ in range(n):
        if len(L)<3:return L
        out=[L[0]]
        for a,b in zip(L,L[1:]):
            out+=[[a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25],[a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75]]
        out[-1]=L[-1];out=out[:1]+out[2:-1]+[L[-1]] if len(out)>3 else out
        L=[[round(x,6),round(y,6)] for x,y in out]
    return L
def despike(L,ang):
    ch=True
    while ch and len(L)>2:
        ch=False
        for i in range(1,len(L)-1):
            a,b,c=L[i-1],L[i],L[i+1]
            v1=((b[1]-a[1])*k,b[0]-a[0]);v2=((c[1]-b[1])*k,c[0]-b[0]);n=math.hypot(*v1)*math.hypot(*v2)
            if n and math.degrees(math.acos(max(-1,min(1,(v1[0]*v2[0]+v1[1]*v2[1])/n))))>ang:del L[i];ch=True;break
    return L
smooth=lambda L,eps=5:chaikin(rdpm(L,eps),2)
# ---- east line: light rail where it overlaps, smoothed trace beyond
lr=S['lr2'];e1=S['e1']
# lr2 runs ... -> PX -> QZ ; take its tail near QZ
qi=min(range(len(lr)),key=lambda i:m(lr[i],e1[0]))
D=[nearest_on(p,lr)[0] for p in e1];cut=None
for i in range(len(D)-3):
    if D[i]<30 and all(x>90 for x in D[i+1:i+4]):cut=i+1;break
if cut and cut>2:
    d,j,q,t=nearest_on(e1[cut-1],lr)
    seg=lr[j+1:qi+1][::-1] if j<qi else lr[qi:j+1]
    head=[e1[0]]+seg[1:]+[q]
    S['e1']=head+chaikin(despike(rdpm(e1[cut-1:],12),40),3)[1:]
else:S['e1']=smooth(e1,6)
print('e1 lr-part pts',cut,len(S['e1']))
S['hm']=smooth(S['hm'],3)
for n in list(X):
    X[n]=[smooth(v,4) if n in('205兵工廠側線','臺糖倉庫側線','小港糖廠線','高港支線（蓬萊碼頭）') else v for v in X[n]]
# s2b first part traced
S['s2b']=smooth(S['s2b'],4)
# ---- 北裏岸壁線: split w0 at the point nearest the bridge approach
br_pt=A['北裏岸壁線'][-3]
d,i,q,t=nearest_on(br_pt,S['w0'])
S['nb']=S['w0'][:i+1]+[q];S['w0']=[q]+S['w0'][i+1:]
# ---- 表岸壁線 = 1989 traced south quay line ; 中/裏 from 1945 (shifted)
S['ob']=chaikin(rdpm(X.pop('高港支線（蓬萊碼頭）')[0],9),3)
X.pop('裏岸壁線',None)
def snapstart(L,T):
    d,i,q,t=nearest_on(L[0],T)
    if 0<t<1:T.insert(i+1,q)
    L[0]=q;return L
mid=A['中岸壁線'];snapstart(mid,S['ob'])
ura=A['裏岸壁線'];snapstart(ura,mid)
X['中岸壁線']=[mid];X['裏岸壁線']=[ura]
order=['中岸壁線','裏岸壁線']
G['extra']={**{k2:X[k2] for k2 in order},**{k2:v for k2,v in X.items() if k2 not in order}}
json.dump(G,open('geo_final2.json','w'),separators=(',',':'))
print(list(G['extra']))
