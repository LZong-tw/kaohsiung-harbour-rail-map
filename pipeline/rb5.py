import json,math
exec(open('rb2.py').read().split('# ---------- main west line')[0])
G=json.load(open('geo_v10.json'));S=G['seg'];X=G['extra']
OSM={str(e['id'])[-5:]:[[round(p['lat'],6),round(p['lon'],6)] for p in e['geometry']] for e in json.load(open('rail.json'))['elements'] if e['type']=='way'}
A=json.load(open('s45.json'))
# 1 戲獅甲 removed (1945 map shows a double-line road)
X.pop('戲獅甲線（往十字船渠北端；1955 年圖實線，是否為鐵道待確認）',None)
# 2 rename quay-edge track
q=X.pop('北裏岸壁線（三號船渠北岸）');X['三號船渠北岸碼頭線（名稱待查）']=q
# 3 1945 sidings along 成功路 corridor
ly=gs(A['lyA'],8)
d0=near(ly[0],S['w1']);d1=near(ly[0],S['w0'])
attach(ly,S['w1'] if d0[0]<=d1[0] else S['w0'],0,200)
X['苓雅寮東側線（1945 年美軍圖，三股）']=[ly]
for key,nm in (('cnA','船渠北岸造船所線 A（1945 年美軍圖）'),('cnB','船渠北岸造船所線 B（1945 年美軍圖）')):
    L=gs(A[key],8);T=S['w1'] if near(L[0],S['w1'])[0]<near(L[0],S['qzb'])[0] else S['qzb'];attach(L,T,0,200);X[nm]=[L]
# 4 sugar railways
tt=X.pop('臺糖倉庫／副產品加工廠側線')[0]
ci=min(range(len(tt)),key=lambda i:m(tt[i],px2ll(2805,4207)))
X['臺糖倉庫側線（臺鐵）']=[tt[:ci+1]]
osm58=OSM['07458'][::-1]   # NW(2586,4218) -> SE(2990,4878)
yard=[px2ll(*p) for p in [(2825,4020),(2820,4120),(2814,4220),(2810,4320),(2800,4420),(2780,4480)]]
d,i,qq,t=near(px2ll(2745,4530),osm58)
li=gs(yard+[qq],10)+osm58[i+1:]
li=li+OSM['07459'][1:]+OSM['07460'][1:]+OSM['40737'][1:]
li=gs(li,10)
X.pop('糖鐵（籬仔內線）',None)
X['糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）']=[li]
link=gs(osm58[:i+1]+[qq],8);attach(link,li,-1,60)
X['糖鐵籬子內線後期段（沿中山四路接臺糖倉庫）']=[link]
fs=[G['st']['鳳山']]+OSM['07457']
fs=gs(fs,14);fs[-1]=OSM['07457'][-1]
attach(fs,li,-1,80)
X.pop('糖鐵小港線（鳳山—小港糖廠）',None)
X['糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）']=[fs]
# 5 北裏岸壁線 = l1w
json.dump(G,open('geo_v11.json','w'),separators=(',',':'))
print(list(X))
