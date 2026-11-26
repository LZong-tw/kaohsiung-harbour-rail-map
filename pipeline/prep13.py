import json, math
from corr import px2ll, ll2px
from pxconv import mk
G = json.load(open('geo_v12.json')); S = G['seg']; X = G['extra']
OSM = {str(e['id'])[-5:]: [[round(p['lat'], 6), round(p['lon'], 6)] for p in e['geometry']] for e in json.load(open('rail.json'))['elements'] if e['type'] == 'way'}
# --- 1) remove duplicate: '小港糖廠線' traced on 1989 map is the sugar railway already drawn from OSM
X.pop('小港糖廠線', None)
# --- 2) sugar railway topology at 牛寮: through route uses the 07461 chord; 07459 + head of 07460 form a wye
li = X['糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）'][0]
def near_i(L, p): return min(range(len(L)), key=lambda i: (L[i][0]-p[0])**2 + (L[i][1]-p[1])**2)
A = OSM['07458'][-1] if False else OSM['07461'][1]          # (2990,4878) node
Bn = OSM['07461'][0]                                          # (3165,5102) node
ia = near_i(li, A); ib = near_i(li, Bn)
X['糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）'] = [li[:ia] + OSM['07461'][::-1] + li[ib+1:]]
fs = X['糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）'][0]
# drop the 鳳山 station prefix (transfer station, 762 mm gauge — not physically joined to the TRA line)
k0 = near_i(fs, OSM['07457'][0]); fs = fs[k0:]
v = OSM['07460']; j = near_i(v, Bn)
X['糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）'] = [OSM['07457'] + v[1:j+1]]
X['糖鐵牛寮三角線（往籬仔內）'] = [OSM['07459'][::-1]]
# --- 2b) 第二臨港線 rebuilt strictly from the OSM ways tagged 高雄港第二臨港線 (the earlier graph route
#          had taken a shortcut along the sugar railway beside 中山四路)
import math as _m
def _d(a,b): return _m.hypot((a[0]-b[0])*110574,(a[1]-b[1])*102762)
s2 = OSM['91376'][::-1] + OSM['24902'][::-1][1:] + OSM['40735'][::-1][1:]
if _d(S['s2b'][0], s2[-1]) > 3: s2 = s2 + [S['s2b'][0]]
S['s2'] = s2
print('s2 rebuilt', len(s2), round(_d(S['s2'][0], s2[1])), round(_d(s2[-2], s2[-1])))
# --- 2c) 5.4K junction per 1989 map (z16 px): 凱旋四路 line runs straight on into 中島線; 成功路 line curves SW and merges
from corr import px2ll as _p
def _cut_after(L, px_y=None, px_x=None, keep='after'):
    out = []
    for q in L:
        x, y = ll2px(*q)
        out.append((x, y, q))
    return out
J = list(_p(1990, 4472))
w2 = S['w2']; i2 = max(i for i, q in enumerate(w2) if ll2px(*q)[1] < 4398)
S['w2'] = w2[:i2+1] + [list(_p(*q)) for q in [(2040, 4405), (2040, 4430), (2034, 4447), (2020, 4459), (2005, 4466)]] + [J]
w3 = S['w3']; i3 = min(i for i, q in enumerate(w3) if ll2px(*q)[0] > 2135)
S['w3'] = [J] + [list(_p(*q)) for q in [(2040, 4450), (2080, 4432), (2130, 4410)]] + w3[i3:]
zd = S['zd']; iz = min(i for i, q in enumerate(zd) if ll2px(*q)[0] < 1940)
S['zd'] = [J, list(_p(1945, 4492))] + zd[iz:]
# --- 3) 淺野／臺泥側線: full length from 1989 map, plant end per 1945 map
ll89, _ = mk(16, 120.270, 22.648, 0)
c89 = [(255, 148), (320, 175), (390, 203), (440, 222), (480, 238), (500, 258), (510, 280), (514, 300)]
X['淺野線（臺泥側線）'] = [[ll89(*p) for p in c89]]
# --- 3b) 淺野線 per 1989 map: joins the line south of the 縱貫線/鼓山 yard heading south (trailing into 鼓山)
X['淺野線（臺泥側線）'] = [[[22.64512,120.27545],[22.64465,120.27679],[22.64421,120.27790],[22.64404,120.27821],
    [22.64389,120.27885],[22.64366,120.27964],[22.64348,120.28011],[22.64322,120.28046],[22.64282,120.28066],[22.64246,120.28077]]]
# --- 3c) 1945-plan sidings near 成功路: better local registration of the 1945 plan (canal/shoreline matched to OSM)
def _shift(L, dla, dlo): return [[round(a+dla,6), round(b+dlo,6)] for a,b in L]
for k,(dla,dlo) in {'船渠北岸造船所線 A（1945 年美軍圖）':(-0.0003,0.0005),'船渠北岸造船所線 B（1945 年美軍圖）':(-0.0003,0.0005),
                    '苓雅寮東側線（1945 年美軍圖，三股）':(-0.0005,0.0002)}.items():
    X[k] = [_shift(X[k][0], dla, dlo)]
# --- 3d) the "職訓中心側線" was 凱旋四路 itself (road symbol on the 1955/1966 maps; matches the road on the 2024 orthophoto)
X.pop('職訓中心側線（原第一臨港線舊線，今高屏澎東分署）', None)
# --- 4) yard: 機迴線 goes to the yard layer
G['yard'].append(X.pop('高雄港站機迴線')[0])
# --- 5) 前鎮車場 yard tracks traced from the 1989 map (two tracks west of the main line)
def P(L): return [list(px2ll(*p)) for p in L]
X['前鎮車場股道 1'] = [P([(2941, 3742), (2947, 3700), (2958, 3600), (2984, 3522), (3010, 3482), (3028, 3463)])]
X['前鎮車場股道 2'] = [P([(2942, 3738), (2955, 3700), (2970, 3600), (2995, 3522), (3016, 3482), (3029, 3465)])]
print(list(X))

# 裏岸壁線：沿蓬萊碼頭北側（內港池南岸）岸線向陸側內縮 12 m，岸線取自 2024 正射影像
import math as _m
_P=json.load(open('pier.json'))['north']
def _off(L,d):
    c=_m.cos(_m.radians(22.62));R=6371000
    M=[((lo-120.28)*_m.radians(1)*R*c,(la-22.62)*_m.radians(1)*R) for la,lo in L];O=[]
    for i,(x,y) in enumerate(M):
        a=M[max(i-1,0)];b=M[min(i+1,len(M)-1)];tx,ty=b[0]-a[0],b[1]-a[1];n=_m.hypot(tx,ty);nx,ny=ty/n,-tx/n
        O.append((x+nx*d,y+ny*d))
    return [[22.62+y/(_m.radians(1)*R),120.28+x/(_m.radians(1)*R*c)] for x,y in O]
_Q=_off(_P,12)
_old=X['裏岸壁線'][0]
_head=[p for p in _old if p[1]<_Q[0][1]-0.0004]
X['裏岸壁線']=[_head+_Q]
print('裏岸壁線 rebuilt',len(_head),len(_Q))

# 獅子公園三角線東側：1945/1955/1966 年圖上的原主線弧線（今凱旋四路弧段、輕軌路廊），
# 東端經今經貿變電所南半部往東北，與今直線段平行約 450 m 後併入（位置依 1966 年圖與使用者街景比對）
def _bl66(x, y):
    Z = 19; n = 2 ** Z * 256
    ox = (120.3040 + 180) / 360 * n; oy = (1 - _m.asinh(_m.tan(_m.radians(22.5965))) / _m.pi) / 2 * n
    X_, Y_ = ox + 2 * x, oy + 2 * y
    return [_m.degrees(_m.atan(_m.sinh(_m.pi * (1 - 2 * Y_ / n)))), X_ / n * 360 - 180]
def _snap(p, L):
    import numpy as _np
    best = None
    for i in range(len(L) - 1):
        a_, b_ = _np.array(L[i]), _np.array(L[i + 1]); d_ = b_ - a_
        t = max(0, min(1, float((_np.array(p) - a_) @ d_ / (d_ @ d_ or 1e-12)))); q = a_ + d_ * t
        dd = float(_np.hypot(*(q - p) * [111000, 102700]))
        if best is None or dd < best[0]: best = (dd, list(q))
    return best[1]
_E = [_bl66(*p) for p in [(330, 668), (400, 716), (500, 752), (600, 768), (700, 752), (800, 700), (920, 618), (1050, 570), (1200, 540), (1350, 512)]]
X['獅子公園三角線東側（原主線弧線，經今經貿變電所）'] = [[_snap(_bl66(285, 610), S['w2'])] + _E + [_snap(_bl66(1480, 494), S['w3'])]]

json.dump(G, open('geo_v12b.json', 'w'), separators=(',', ':'))
