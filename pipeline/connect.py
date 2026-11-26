import json,math
E=json.load(open('rail.json'))['elements'];G=json.load(open('geo_ll.json'))
def dist(a,b):return math.hypot((a[0]-b[0])*111000,(a[1]-b[1])*111000*math.cos(math.radians(22.6)))
def nearest(pt,segs):
    best=None
    for s in segs:
        for p in G['seg'][s]:
            d=dist(p,pt)
            if best is None or d<best[0]:best=(d,p)
    return best
def way(**kw):
    out=[]
    for e in E:
        if e['type']!='way':continue
        t=e.get('tags',{})
        if all((t.get(k)==v) if k!='id' else str(e['id']).endswith(v) for k,v in kw.items()):
            out.append([[round(p['lat'],5),round(p['lon'],5)] for p in e['geometry']])
    return out
def attach(line,segs,both=False):
    # connect nearer end (or both ends) to nearest point on given segs
    d0=nearest(line[0],segs);d1=nearest(line[-1],segs)
    if both:return [d0[1]]+line+[d1[1]]
    return ([d0[1]]+line) if d0[0]<=d1[0] else (line+[d1[1]])
def chain(parts):
    parts=[p[:] for p in parts];out=parts.pop(0)
    while parts:
        best=None
        for i,p in enumerate(parts):
            for rev in (False,True):
                q=p[::-1] if rev else p
                for front in (False,True):
                    d=dist(out[0],q[-1]) if front else dist(out[-1],q[0])
                    if best is None or d<best[0]:best=(d,i,rev,front)
        d,i,rev,front=best;q=parts.pop(i);q=q[::-1] if rev else q
        out=(q+out) if front else (out+q)
    return out
ex={}
# 淺野線 (臺泥士敏廠側線) -> 縱貫線 at 鼓山 (田町驛)
ex['淺野線（臺泥側線）']=[attach(way(name='臺泥士敏廠側線')[0],['zg_n','zg_s'])]
# 裏岸壁線 -> 第一臨港線 (北裏岸壁線, 駁二)
ex['裏岸壁線']=[attach(way(name='裏岸壁線')[0],['w0'])]
# unnamed private sidings near 前鎮 (OSM abandoned, no name)
sd=[]
for sid in ('44425','44444','01716'):
    w=way(id=sid)[0];sd.append(attach(w,['br','s2','e1']))
ex['專用側線（名稱未確認）']=sd
# 糖鐵小港線 鳳山—後壁林(小港糖廠): chain 林園線 pieces inside bbox + 籬子內線
lin=[w for w in way(name='小港糖廠林園線') if w[0][1]<120.37 and w[-1][1]<120.37]
main=chain(lin)
# ensure north end at 鳳山 station
fs=G['st']['鳳山']
if dist(main[-1],fs)<dist(main[0],fs):main=main[::-1]
main=[fs]+main
ex['糖鐵小港線（鳳山—小港糖廠）']=[main]
liz=chain(way(name='小港糖廠籬子內線')+way(id='07461'))
ex['糖鐵籬子內線']=[attach(liz,['br','s2'])]
ex['高雄港站機迴線']=way(name='高雄港站機迴線')
G['extra']=ex
# 濱線（漁港線）traced along 鼓山一路, between 濱海一路 and 捷興一街, to 鼓山渡船場 fish market
G['seg']['hm']=[G['seg']['west'][0] if dist(G['seg']['west'][0],(22.6216,120.2775))<300 else [22.6216,120.2775],
 [22.6220,120.2754],[22.6213,120.2750],[22.62005,120.27414],[22.61948,120.2735],[22.61945,120.2720],[22.61950,120.2710],[22.61970,120.27005]]
json.dump(G,open('geo_ll.json','w'),separators=(',',':'))
print({k:[len(x) for x in v] for k,v in ex.items()},G['seg']['hm'][0])
