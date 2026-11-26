"""穿過站場的主線、支線依年代改走描出的股道（第 28 輪）。

python3 yardlines.py            # 讀 geo_v13.json，寫回 G['alt']（主線、支線）與 G['xalt']（側線）

選錨點用 yarddiag.py（股道示意圖）與 yardnear.py（最近股道），檢查用 overlap.py。

問題：主線、支線的線形只有一套（多依 1945、1989 年圖），站場股道卻依年代換成 1945、1970、1998 年的描線，
所以在某些年份主線會斜穿股道，或與股道平行錯開幾公尺，看起來像畫了兩次。

做法：對每一組股道（年代），把穿過站場的線在站場內那一段，改成在該組股道上找出的可行駛路徑
（yardroute.py），站場外的部分不動；接點前後各取一段做平滑銜接。
每段路徑由錨點決定（起點、途經點、終點），錨點依 1970 年 1:1200 都市計畫航測地形圖（中研院）
與 1976、1998 年像片基本圖上的股道配置選定，座標為高雄港站 z18 像素（左上角 120.2715, 22.6270）。
"""
import json, math, sys
import numpy as np
from yardroute import Graph, route, to_xy, to_ll

Z, W0, N0 = 18, 120.2715, 22.6270
_n = 2 ** Z * 256
_ox = (W0 + 180) / 360 * _n
_oy = (1 - math.asinh(math.tan(math.radians(N0))) / math.pi) / 2 * _n


def px2ll(x, y):
    lon = (_ox + x) / _n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (_oy + y) / _n))))
    return (lat, lon)


def ll2px(p):
    return ((p[1] + 180) / 360 * _n - _ox, (1 - math.asinh(math.tan(math.radians(p[0]))) / math.pi) / 2 * _n - _oy)


def nearest_idx(L, p):
    x, y = to_xy(p)
    d = [math.hypot(*(np.subtract(to_xy(q), (x, y)))) for q in L]
    i = int(np.argmin(d))
    return i, d[i]


def blend(route_pts, rest, L=30.0):
    """把路徑接到既有線段 rest 上：rest 開頭 L 公尺內的點換成由路徑終點平滑過渡。"""
    a = np.array([to_xy(p) for p in rest])
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(a, axis=0).T))]
    j = int(np.searchsorted(seg, L))
    if j >= len(rest):
        return route_pts + rest[-1:]
    off = np.array(to_xy(route_pts[-1])) - a[0]
    out = list(route_pts)
    for k in range(1, j):
        t = seg[k] / seg[j]
        w = 0.5 * (1 + math.cos(math.pi * t))   # 1 → 0
        out.append(to_ll(*(a[k] + off * w)))
    return out + rest[j:]


def proj(L, p):
    """p 在折線 L 上的投影：回傳 (線段序號 i, 參數 t)，投影點在 L[i]→L[i+1] 之間。"""
    P = np.array([to_xy(q) for q in L])
    x = np.array(to_xy(p))
    best = (1e18, 0, 0.0)
    for i in range(len(P) - 1):
        v = P[i + 1] - P[i]
        n2 = float(v @ v) or 1e-9
        t = float(np.clip((x - P[i]) @ v / n2, 0, 1))
        d = float(np.hypot(*(P[i] + v * t - x)))
        if d < best[0]:
            best = (d, i, t)
    return best[1], best[2]


def splice(L, path, c0, c1, bl=30.0):
    """以 path 取代 L 上對應的一段：c0／c1 為真時，path 起點／終點接回 L（從投影點往外的下一個頂點起，
    以 blend 平滑銜接）；為假時 path 的該端就是線的端點。"""
    i0, t0 = proj(L, path[0])
    i1, t1 = proj(L, path[-1])
    if (i0, t0) > (i1, t1):            # 線的方向與路徑相反
        L = L[::-1]
        i0, t0 = proj(L, path[0])
        i1, t1 = proj(L, path[-1])
    p = list(path)
    if c1:
        p = blend(p, L[i1 + 1:], bl)
    if c0:
        p = blend(p[::-1], L[:i0 + 1][::-1], bl)[::-1]
    return p


# 每一年代、每一條線：('seg' 或 'x', 名稱, 錨點清單, 起點接回原線, 終點接回原線)
# 起點／終點不接回原線，表示該端就是線的端點（例如以高雄港站為端點的西臨港線）。
PLAN = {
    0: [  # 1945 年美軍高雄市街圖（1900–1959）
        # 濱線：原線形在車站以南沿鼓山一路，比 1945 年圖（與 1970 年圖）上的濱線股道偏西 20–40 m；
        # 改走 1945 年圖的股道，北端以 90 m 長的緩和段接回原線（1945 年描線在車站南側有 40 m 以上的缺口）。
        ('seg', 'hm', [(720, 1262), (495, 1450)], True, True, {'blend': 90.0}),
        # 北裏岸壁線東側的弧線在 1970 年圖上仍有股道（行政區界也沿著它），1945 年描線只是沒描到，所以維持原線形。
        ('seg', 'ob', [(1048, 561), (1030, 650), (1005, 760), (999, 850), (999, 950), (1001, 1000), (1030, 1200), (1060, 1290)], True, True),
    ],
    1: [  # 1970 年 1:1200 都市計畫航測地形圖（1960–1986）
        # 站場北端咽喉區股道密集、描線破碎，各線在 y≈760–800 以北維持原線形（與股道同向並行）。
        ('seg', 'west', [(838, 1030), (921, 766)], False, True),
        ('seg', 'hm', [(838, 1030), (560, 1430)], False, True),
        ('seg', 'ob', [(986, 795), (1040, 1300), (1100, 1560), (1108, 1609)], True, True),
        ('seg', 'l1w', [(1018, 800), (1240, 1150)], True, True),
    ],
    2: [  # 1998 年 1:5000 像片基本圖（1987–2007）
        ('seg', 'west', [(838, 1030), (921, 766)], False, True),
        ('seg', 'hm', [(838, 1030), (560, 1430)], False, True),
        ('seg', 'ob', [(1048, 561), (1015, 700), (986, 795), (1100, 1560), (1150, 1625)], True, True),
        ('seg', 'l1w', [(1018, 800), (1250, 1200)], True, True),
    ],
}


def hermite(p0, h0, p1, h1, step=2.0):
    """以三次 Hermite 曲線連接 p0→p1（xy 公尺），h0、h1 為兩端切線方位角。"""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = float(np.hypot(*(p1 - p0)))
    m0 = L * np.array([math.cos(h0), math.sin(h0)])
    m1 = L * np.array([math.cos(h1), math.sin(h1)])
    out = []
    for u in np.linspace(0, 1, max(2, int(L / step)) + 1):
        out.append((2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * m0
                   + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * m1)
    return out


def on_line(L, p):
    """p 在折線 L 上的投影點（xy）與該處沿 L 方向的方位角。"""
    i, t = proj(L, p)
    a, b = np.array(to_xy(L[i])), np.array(to_xy(L[i + 1]))
    return a + (b - a) * t, math.atan2(*(b - a)[::-1]), i


# 濱線商港側（第 28 輪改線）：1962 年高雄港擴建區域地形圖上，這條線自濱線往哈瑪星方向的一段分出，
# 沿南側街廓北緣往東南接到岸壁線；1970 年 1:1200 圖上同一位置只剩一條地界線，股道已拆。
# 原本依 1945 年美軍圖畫成自濱線直直往南穿過街廓，與 1962、1970 年圖都對不上，改依 1962 年圖。
HAMA_J = (540, 1425)                                    # 分岐點附近（取濱線上最近點）
HAMA_PTS = [(760, 1500), (870, 1580), (960, 1625)]     # 1962 年圖與 1970 年地界線上的通過點


def hamasen_link(hm):
    J, h, _ = on_line(hm, px2ll(*HAMA_J))
    # 濱線的走向是車站→哈瑪星（往西南）；分岔出去的線是由哈瑪星往東的列車轉入，切線取反方向
    h = h + math.pi
    P = [np.array(to_xy(px2ll(*q))) for q in HAMA_PTS]
    h1 = math.atan2(*(P[1] - P[0])[::-1])
    pts = hermite(J, h, P[0], h1)
    for q in P[1:]:
        pts.append(q)
    return [to_ll(*p) for p in pts]


def reattach(ex, parent, L=40.0):
    """側線 ex 的起點原本在母線上；母線換了線形後，把起點移到新母線上最近處，前 L 公尺平滑銜接。"""
    P0, h, _ = on_line(parent, ex[0])
    a = np.array([to_xy(p) for p in ex])
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(a, axis=0).T))]
    off = P0 - a[0]
    out = []
    for k in range(len(a)):
        w = 0.5 * (1 + math.cos(math.pi * min(1.0, seg[k] / L)))
        out.append(to_ll(*(a[k] + off * w)))
    return out


# 起點在母線上的側線：母線依年代換線形時，側線起點跟著移
REATTACH = {'裏岸壁線': 'ob', '中岸壁線': 'ob'}


def main():
    G = json.load(open('geo_v13.json'))
    G['alt'], G['xalt'] = {}, {}
    for gi, plan in PLAN.items():
        gr = G['yards'][gi]
        g = Graph(gr['lines'])
        for kind, name, anchors, c0, c1, *opt in plan:
            opt = opt[0] if opt else {}
            pts, full = route(g, [px2ll(*p) for p in anchors], snap=20.0)
            base = G['seg'][name] if kind == 'seg' else G['extra'][name][0]
            new = splice(base, pts, c0, c1, opt.get('blend', 30.0))
            jumps = sum(1 for s, t in zip(full, full[1:]) if s[0] != t[0])
            print(gr['src'], name, '路徑', len(pts), '點', '換股', jumps, '次')
            (G['alt'] if kind == 'seg' else G['xalt']).setdefault(name, []).append([gr['o'], gr['c'], new if kind == 'seg' else [new]])
    # 濱線商港側：預設線形改依 1962 年圖；1960–1964 年濱線走 1970 年股道時，分岐點跟著移
    hn = '濱線（商港側，往海關碼頭）'
    G['extra'][hn] = [hamasen_link(G['seg']['hm'])]
    for o, c, g in G['alt'].get('hm', []):
        G['xalt'].setdefault(hn, []).append([o, c, [hamasen_link(g)]])
    for xn, par in REATTACH.items():
        for o, c, g in G['alt'].get(par, []):
            G['xalt'].setdefault(xn, []).append([o, c, [reattach(G['extra'][xn][0], g)] + G['extra'][xn][1:]])
    json.dump(G, open('geo_v13.json', 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
