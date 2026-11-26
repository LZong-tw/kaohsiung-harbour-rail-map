import json,math
exec(open('rb2.py').read().split('# ---------- main west line')[0])
G=json.load(open('geo_v11.json'));S=G['seg'];X=G['extra']
W=S['west']  # GK -> 鼓山
# keep part north of the throat
k0=next(i for i,p in enumerate(W) if p[0]>=22.6250)
north=W[k0:]
print('north start',north[0])
STN=[22.62182,120.27574]
main=[[22.6247,120.27745],[22.6242,120.27712],[22.62383,120.27673],[22.62351,120.27656],[22.62291,120.27627],[22.62214,120.27593],STN]
west=gs(main[::-1]+[north[0]],4)[:-1]+north   # station -> 鼓山
west[0]=STN
S['west']=west
G['st']['高雄港站']=STN
def onW(p):
    d,i,q,t=near(p,west);west.insert(i+1,q);return q
J1=onW([22.6243,120.2771])
J2=onW([22.6239,120.2767])
# 北裏岸壁線
l1=S['l1w'];j=next(i for i,p in enumerate(l1) if p[1]>=120.2789)
nb=gs([J1,[22.6236,120.27695],[22.6229,120.2770],[22.6224,120.27725],[22.6220,120.2777],[22.6217,120.27825]]+l1[j:j+3],7)
S['l1w']=nb[:-1]+l1[j+2:]
S['l1w'][0]=J1
# 表岸壁線 through yard centre
ob=S['ob'];j=next(i for i,p in enumerate(ob) if p[0]<=22.6196)
newob=gs([J2,[22.6232,120.2766],[22.6224,120.27655],[22.6215,120.2766],[22.6206,120.2767],[22.6200,120.2770]]+ob[j:j+3],7)
S['ob']=newob[:-1]+ob[j+2:];S['ob'][0]=J2
# 濱線 from station south end
hm=S['hm']
S['hm']=[STN]+gs([STN,[22.6214,120.27535],[22.6209,120.2750],hm[1]],5)[1:]+hm[2:]
cust=X['濱線（商港側，往海關碼頭）'][0];cust[0]=hm[1]
# re-attach dependants
for n,T in (('中岸壁線',S['ob']),('三號船渠北岸碼頭線（名稱待查）',S['ob'])):
    L=X[n][0]
    if n=='三號船渠北岸碼頭線（名稱待查）':
        L=[p for p in L if p[1]>120.2775];X[n][0]=L
    attach(L,T,0,250)
attach(X['裏岸壁線'][0],X['中岸壁線'][0],0,80)
A=X.pop('三號船渠北岸碼頭線（名稱待查）');X.pop('裏岸壁線')
new={}
for k,v in X.items():
    new[k]=v
    if k=='中岸壁線':new['裏岸壁線']=A
G['extra']=new
json.dump(G,open('geo_v12.json','w'),separators=(',',':'));print('ok',S['l1w'][:4],S['ob'][:3])
