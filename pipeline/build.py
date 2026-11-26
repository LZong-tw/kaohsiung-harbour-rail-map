import json,math,networkx as nx
from PIL import Image,ImageDraw
E=json.load(open('rail.json'))['elements']
Z=15
def mp(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
W,N,Ee,S=120.262,22.680,120.372,22.548
OX,OY=mp(W,N);X1,Y1=mp(Ee,S)
px=lambda la,lo:(mp(lo,la)[0]-OX,mp(lo,la)[1]-OY)
def dist(a,b):
    return math.hypot((a[0]-b[0])*111000,(a[1]-b[1])*111000*math.cos(math.radians(22.6)))
# graphs per class
def build(filt):
    G=nx.Graph();ends=[]
    for e in E:
        if e['type']!='way':continue
        t=e.get('tags',{})
        if not filt(t):continue
        g=[(p['lat'],p['lon']) for p in e['geometry']]
        for a,b in zip(g,g[1:]):G.add_edge(a,b,w=dist(a,b))
        ends+= [g[0],g[-1]]
    nodes=list(G.nodes)
    for a in ends:  # bridge small gaps
        for b in nodes:
            if a!=b and dist(a,b)<35 and not G.has_edge(a,b):G.add_edge(a,b,w=dist(a,b)+5)
    return G
def near(G,p):return min(G.nodes,key=lambda n:dist(n,p))
def path(G,*wps):
    out=[]
    for a,b in zip(wps,wps[1:]):
        s=nx.shortest_path(G,near(G,a),near(G,b),weight='w');out+= s if not out else s[1:]
    return out
LR=build(lambda t:t.get('railway')=='light_rail' and t.get('service') not in('yard','siding','spur'))
TR=build(lambda t:t.get('railway')=='rail' and t.get('name') in('縱貫線','屏東線','高雄車站'))
AB=build(lambda t:t.get('railway') in('disused','abandoned','rail') or any('railway' in k for k in t if k!='railway'))
L=dict(
 GK=(22.6216,120.2775), GU=(22.6380,120.2822), AI=(22.6200,120.2862), LY=(22.6178,120.2935),
 SG=(22.6108,120.3012), ZB=(22.5931,120.3057), B68=(22.5946,120.3167), QZ=(22.6086,120.3258),
 PX=(22.6330,120.3230), KS=(22.6396,120.3027), NE=(22.6795,120.2989), EE=(22.6323,120.3661),
 CY=(22.5704,120.3369), CS=(22.5594,120.3555))
# light rail loop pieces
pk=lambda G,*k:path(G,*[L[x] for x in k])
SEG={}
gu_tr=near(TR,(22.6395,120.2812))
SEG['zg_n']=path(TR,L['NE'],gu_tr)
SEG['zg_s']=path(TR,gu_tr,L['KS'])
SEG['pt']=path(TR,L['KS'],L['EE'])
SEG['west']=pk(LR,'GK','GU')+[gu_tr]
SEG['w0']=pk(LR,'GK','AI','LY')
SEG['w1']=pk(LR,'LY','SG','ZB','B68')
SEG['br']=pk(LR,'B68','QZ')
SEG['e1']=pk(LR,'QZ','PX')
# east line joins Pingtung line: from PX to nearest TR node
px_tr=near(TR,L['PX']);SEG['e1']+= [px_tr]
SEG['e1b']=path(TR,px_tr,L['KS'])
SEG['zd']=path(AB,(22.5931,120.3057),(22.6085,120.2868))
SEG['s2']=path(AB,L['B68'],(22.5850,120.3247),L['CY'])
SEG['c2']=path(AB,(22.5850,120.3247),(22.5769,120.3157),(22.5761,120.3112))
SEG['c3']=path(AB,L['CY'],(22.5578,120.3220))
SEG['s2b']=[L['CY'],(22.5676,120.3440)]+path(AB,(22.5676,120.3440),(22.5673,120.3511),L['CS'])
# light rail full loop (two phases)
SEG['lr1']=pk(LR,'QZ','B68','ZB','SG','LY','AI','GK')
SEG['lr2']=pk(LR,'GK','GU')+path(LR,L['GU'],(22.6549,120.2880),(22.6600,120.3150),L['PX'],L['QZ'])
# yard tracks (高雄港站, 前鎮/機廠) for texture
yard=[]
for e in E:
    t=e.get('tags',{})
    if e['type']=='way' and t.get('railway')=='disused':
        g=[(p['lat'],p['lon']) for p in e['geometry']]
        c=g[len(g)//2]
        if dist(c,L['GK'])<500 or dist(c,(22.6130,120.3285))<400:yard.append(g)
r=lambda s:[[round(v,1) for v in px(*p)] for p in s]
out={'size':[round(X1-OX),round(Y1-OY)],'seg':{k:r(v) for k,v in SEG.items()},'yard':[r(g) for g in yard],
     'pts':{k:[round(v,1) for v in px(*p)] for k,p in L.items()}}
out['pts']['GUJ']=[round(v,1) for v in px(*gu_tr)]
json.dump(out,open('geo.json','w'),separators=(',',':'))
print({k:len(v) for k,v in SEG.items()},out['size'])
# basemap crop
full=Image.open('base_full.png')
oX,oY=mp(120.258,22.682)
im=full.crop((round(OX-oX),round(OY-oY),round(X1-oX),round(Y1-oY)))
im.save('base.png');print(im.size)
# ---- lat/lng export
SEG.pop('e1b',None)
rr=lambda s:[[round(a,5),round(b,5)] for a,b in s]
def snap(seg,p):return min(SEG[seg],key=lambda n:dist(n,p))
ST={'高雄港站':L['GK'],'高雄站':L['KS'],'苓雅寮車場':snap('w1',L['LY']),'新光':snap('w1',L['SG']),'中島車場':snap('zd',(22.6005,120.2985)),
 '前鎮車場':L['QZ'],'高雄機廠':snap('e1',(22.6135,120.3290)),'草衙車場':L['CY'],'中鋼':L['CS'],'鳳山':snap('pt',(22.6314,120.3577)),
 '三塊厝':snap('zg_s',(22.6385,120.2930)),'鼓山':gu_tr,'往左營':L['NE']}
json.dump({'seg':{k:rr(v) for k,v in SEG.items()},'yard':[rr(g) for g in yard],'st':{k:[round(v[0],5),round(v[1],5)] for k,v in ST.items()},
 'bounds':[[S,W],[N,Ee]]},open('geo_ll.json','w'),separators=(',',':'))
# ---- extra spurs
want={'裏岸壁線':'裏岸壁線','臺泥士敏廠側線':'臺泥士敏廠側線','小港糖廠籬子內線':'糖鐵籬子內線','小港糖廠林園線':'糖鐵林園線','高雄港站機迴線':'高雄港站機迴線'}
ex={}
for e in E:
    if e['type']!='way':continue
    t=e.get('tags',{});n=t.get('name') or t.get('disused:name')
    if n in want:
        g=[(p['lat'],p['lon']) for p in e['geometry']]
        if all(W<lo<Ee and S<la<N for la,lo in g[:1]):ex.setdefault(want[n],[]).append(rr(g))
gl=json.load(open('geo_ll.json'));gl['extra']=ex
gl['br']={'5.4K 中島線分歧':[round(v,5) for v in SEG['zd'][0]],'6.8K 第二臨港線分歧':[round(v,5) for v in SEG['s2'][0]]}
json.dump(gl,open('geo_ll.json','w'),separators=(',',':'))
print({k:len(v) for k,v in ex.items()})
