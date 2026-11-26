import json,math,numpy as np
exec(open('rb2.py').read().split('# ---------- main west line')[0])
G=json.load(open('geo_v8.json'));S=G['seg'];X=G['extra']
# straighten 前鎮橋
q0=S['qzb'][0];q1=S['qzb'][-1];S['qzb']=[q0,[(q0[0]*2+q1[0])/3,(q0[1]*2+q1[1])/3],[(q0[0]+q1[0]*2)/3,(q0[1]+q1[1]*2)/3],q1]
# ---- 成功路南段 to Y-junction, then 凱旋四路西段 to 6.8K
w2=gs(cp([(1945,4105),(1960,4170),(1975,4240),(1995,4285),(2020,4330),(2035,4370),(2040,4400),(2038,4428),(2028,4450),(2012,4462)],10),20)
w2[0]=S['qzb'][-1]
J=w2[-1]
w3=gs(cp([(2012,4462),(2060,4445),(2100,4426),(2150,4405),(2200,4385),(2250,4364),(2300,4345),(2400,4310),(2506,4254)],10),22)
w3[0]=J;w3[-1]=S['k4'][0]
zd=S['zd'];zi=min(range(len(zd)),key=lambda i:m(zd[i],px2ll(1975,4478)))
zd=[J]+zd[zi:]
S['w2']=w2;S['w3']=w3;S['zd']=zd

def along(T,i,q,dist,fwd):
    # walk from projection q on segment i by dist metres; insert point into T, return it
    pts=T[i+1:] if fwd else T[:i+1][::-1];prev=q;acc=0
    for p in pts:
        d=m(prev,p)
        if acc+d>=dist:
            f=(dist-acc)/d;r=[round(prev[0]+(p[0]-prev[0])*f,6),round(prev[1]+(p[1]-prev[1])*f,6)]
            idx=T.index(p);T.insert(idx if fwd else idx+1,r);return r
        acc+=d;prev=p
    return pts[-1]
# ---- 205 外側線 along 凱得街
KD=[[22.60435,120.32239],[22.60389,120.32215],[22.60377,120.32209],[22.60371,120.322],[22.60353,120.32199],[22.60334,120.32193],[22.60314,120.32197],[22.60302,120.32187],[22.60293,120.32179],[22.60287,120.32175],[22.60274,120.32173],[22.60258,120.32161],[22.60107,120.3207],[22.59996,120.32005]]
old=X.pop('205 兵工廠外側線（廠區北緣，兼通中化公司）')[0]  # starts at k4, ends at west
old=old[::-1]  # west -> east
def dpl(p,L):return min(near(p,L)[0],1e9)
ci=next(i for i,p in enumerate(old) if dpl(p,KD)<35)
ki=min(range(len(KD)),key=lambda i:m(KD[i],old[ci]))
ki=max(ki,3)
k4=S['k4']
# join point on k4 ~110 m SW of 凱得街 south end, trailing
d,i,q,t=near(KD[-1],k4)
jp=along(k4,i,q,110,False)
s205=gs(old[:ci]+KD[ki:]+[jp],18)
s205[-1]=jp
X['205 兵工廠外側線（廠區北緣—凱得街）']=[s205]
# ---- spur to 205 gate on 凱旋四路 side (OSM gate node)
gate=[22.5988,120.3185]
d,i,q,t=near(gate,k4)
st=along(k4,i,q,70,True)
sp=gs([st,[st[0]*.5+q[0]*.5,st[1]*.5+q[1]*.5],[q[0]*.45+gate[0]*.55,q[1]*.45+gate[1]*.55],gate],10);sp[0]=st
X['205 兵工廠大門側線（凱旋四路側）']=[sp]
G['br']={'5.4K 中島線分歧':J,'6.8K 第二臨港線分歧':S['s2'][0],'前鎮橋（1955）':G['br']['前鎮橋（1955）']}
# re-attach 臺肥 siding to new w2
tf=X['臺肥三廠側線'][0];attach(tf,w2,0,120)
order=['中岸壁線','裏岸壁線']
json.dump(G,open('geo_v9.json','w'),separators=(',',':'));print('ok',len(w2),len(w3),len(zd),len(s205))
G=json.load(open('geo_v9.json'));S=G['seg'];X=G['extra']
al=gs([px2ll(*p) for p in [(1905,4030),(1893,4005),(1875,3986),(1845,3978),(1800,3986),(1760,3999),(1720,4013),(1690,4024)]],12)
attach(al,S['w1'] if near(al[0],S['w1'])[0]<near(al[0],S['qzb'])[0] else S['qzb'],0,80)
X['成功路側線（臺鋁南側油槽區）']=[al]
json.dump(G,open('geo_v9.json','w'),separators=(',',':'));print('al ok')
