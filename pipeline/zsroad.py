"""中山四路（前鎮—草衙）的道路中心線與東側平行線（第 31 輪）。

糖鐵籬仔內線沿中山四路的一段走在道路東側，第二臨港線走西側（使用者提供的臉書社團留言與前鎮區行政區域圖；
1984 年都市計畫航測地形圖、1989 與 1993 年經建版都在兩側各畫一條鐵路）。道路位置取 OSM 的中山四路
（雙向分隔，兩向車道中線的平均即道路中心），糖鐵以「道路中心往東 D 公尺」表示，D 依 1989、1993 年圖量得。

    python3 zsroad.py          # 重新向 Overpass 下載中山四路，寫入 zs4road.json
"""
import json, math, sys
import numpy as np
from regularize import toM, toLL

QUERY = '[out:json][timeout:25];way["name"~"中山四路"](22.55,120.30,22.60,120.35);out geom;'
URL = 'https://maps.mail.ru/osm/tools/overpass/api/interpreter'
FILE = 'zs4road.json'


def _load(path=FILE):
    d = json.load(open(path))
    seg = {1: [], -1: []}                      # 1 = 往南車道，-1 = 往北車道
    for e in d['elements']:
        if e['type'] != 'way':
            continue
        w = [np.array(toM((q['lat'], q['lon']))) for q in e['geometry']]
        g = 1 if (w[-1] - w[0])[1] < 0 else -1
        seg[g] += list(zip(w, w[1:]))
    return seg


_SEG = None


def _proj(p, segs):
    best = None
    for a, b in segs:
        d = b - a
        L = d @ d
        if L == 0:
            continue
        t = max(0.0, min(1.0, (p - a) @ d / L))
        q = a + d * t
        dist = float(np.hypot(*(p - q)))
        if best is None or dist < best[0]:
            best = (dist, q, d / math.sqrt(L))
    return best


def centre(p):
    """p（xy 公尺）附近的道路中心點、往南的單位方向、東向法線。"""
    global _SEG
    if _SEG is None:
        _SEG = _load()
    a, b = _proj(p, _SEG[1]), _proj(p, _SEG[-1])
    q = (a[1] + b[1]) / 2
    u = a[2] if a[2][1] < 0 else -a[2]
    e = np.array([-u[1], u[0]])
    if e[0] < 0:
        e = -e
    return q, u, e


def offset(p):
    """點到道路中心的有號距離（東正西負，公尺）。"""
    P = np.array(toM(p))
    q, u, e = centre(P)
    return float((P - q) @ e)


def centreline(lat0, lat1, dlat=0.0001):
    """lat0 往南到 lat1，每 dlat 度取兩向車道與該緯線的交點，平均為道路中心（xy 公尺）。"""
    global _SEG
    if _SEG is None:
        _SEG = _load()
    out, prev = [], None
    for lat in np.arange(lat0, lat1, -dlat):
        y = toM((lat, 120.33))[1]
        xs = {}
        for g in (1, -1):
            c = []
            for a, b in _SEG[g]:
                if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
                    c.append(a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]))
            if c:
                ref = prev if prev is not None else np.mean(c)
                xs[g] = min(c, key=lambda x: abs(x - ref))
        if len(xs) == 2 and abs(xs[1] - xs[-1]) < 60:
            prev = (xs[1] + xs[-1]) / 2
            out.append(np.array([prev, y]))
    return out


def east_line(lat0, lat1, D, smooth=9):
    """沿道路中心從 lat0 往南到 lat1，取往東 D(lat) 公尺的平行線，回傳 [lat, lon] 串列。"""
    C = centreline(lat0, lat1)
    C = np.array(C)
    k = np.ones(smooth) / smooth
    Cs = np.stack([np.convolve(np.pad(C[:, i], smooth // 2, mode='edge'), k, mode='valid') for i in range(2)], 1)
    T = np.gradient(Cs, axis=0)
    T = T / np.hypot(T[:, 0], T[:, 1])[:, None]
    E = np.stack([-T[:, 1], T[:, 0]], 1)
    E[E[:, 0] < 0] *= -1
    out = []
    for c, e in zip(Cs, E):
        d = D(toLL(c)[0])
        p = c + e * d
        for _ in range(3):                       # 以 offset() 的道路中心定義校正，使與量測時一致
            p = p + e * (d - offset(toLL(p)))
        out.append(p)
    P = np.array(out)                            # 校正後再平滑一次
    P = np.stack([np.convolve(np.pad(P[:, i], smooth // 2, mode='edge'), k, mode='valid') for i in range(2)], 1)
    return [list(toLL(p)) for p in P]


if __name__ == '__main__':
    import urllib.parse, urllib.request
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    open(FILE, 'wb').write(urllib.request.urlopen(URL, data, timeout=60).read())
    print('wrote', FILE)
