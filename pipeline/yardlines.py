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
import yardroute
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


# 鍵為站場股道組別的起始年（G['yards'] 裡高雄港站各組的 'o'），值為該年代各線的路徑。
# 每一年代、每一條線：('seg' 或 'x', 名稱, 錨點清單, 起點接回原線, 終點接回原線)
# 起點／終點不接回原線，表示該端就是線的端點（例如以高雄港站為端點的西臨港線）。
PLAN = {
    1908: [  # 1945 年美軍高雄市街圖（1908–1959；第 34 輪前為 1900 起）
        # 濱線：原線形在車站以南沿鼓山一路，比 1945 年圖（與 1970 年圖）上的濱線股道偏西 20–40 m；
        # 改走 1945 年圖的股道，北端以 90 m 長的緩和段接回原線（1945 年描線在車站南側有 40 m 以上的缺口）。
        ('seg', 'hm', [(720, 1262), (495, 1450)], True, True, {'blend': 90.0}),
        # 北裏岸壁線東側的弧線在 1970 年圖上仍有股道（行政區界也沿著它），1945 年描線只是沒描到，所以維持原線形。
        ('seg', 'ob', [(1048, 561), (1030, 650), (1005, 760), (999, 850), (999, 950), (1001, 1000), (1030, 1200), (1060, 1290)], True, True),
    ],
    1960: [  # 1970 年 1:1200 都市計畫航測地形圖（1960–1976）
        # 站場北端咽喉區股道密集、描線破碎，各線在 y≈760–800 以北維持原線形（與股道同向並行）。
        ('seg', 'west', [(838, 1030), (921, 766)], False, True),
        ('seg', 'hm', [(838, 1030), (560, 1430)], False, True),
        ('seg', 'ob', [(986, 795), (1040, 1300), (1100, 1560), (1108, 1609)], True, True),
        ('seg', 'l1w', [(1018, 800), (1240, 1150)], True, True),
    ],
    1977: [  # 1984 年都市計畫航測地形圖（1977–1990）
        ('seg', 'west', [(838, 1030), (921, 766)], False, True),
        ('seg', 'hm', [(838, 1030), (560, 1430)], False, True),
        # 1984 年描線在站場中段股道完整：表岸壁線沿同一股（x≈990–1010）一路向南，錨點吸附半徑縮到 8 m，
        # 避免像 1970 年圖那組錨點一樣在中段斜跨三股（第 29 輪）。
        ('seg', 'ob', [(989, 850), (1007, 1300), (1054, 1543), (1108, 1609)], True, True, {'snap': 8.0}),
        ('seg', 'l1w', [(1018, 800), (1240, 1150)], True, True),
        # 裏岸壁線：原線形的西段在 1984 年圖上穿過建物；圖上的裏岸壁線是站場東側一股往東南彎出、
        # 沿碼頭北側倉庫列向東的股道。這股與表岸壁線所在的股道之間隔兩股，以一段長約 100 m 的
        # 緩和曲線（轉轍器梯線）從表岸壁線分出，不在短距離內斜跨。到 x≈1140 與原線形會合後沿原線形：
        # 再往東，1984 年圖倉庫列南側有一股帶枕木的股道，比原線形（依 1989 年經建版與碼頭輪廓）偏南約 25 m，
        # 哪一條才是裏岸壁線未查明，先不改（第 29 輪）。
        ('x', '裏岸壁線', [(1014, 1045), (1049, 1228), (1138, 1438)], False, True, {'snap': 8.0, 'from': ('ob', (989, 860))}),
    ],
    # 中島（第 36 輪）：中島線本線依各版像片基本圖的描線走。錨點：5.4K 西側擴建路上、擴建路西段、東側線南段、東側線北段、
    # 北段轉彎處、北段倉庫列之間那組的西端。原本的中島線在北段斜穿倉庫、夾在兩組軌道中間（使用者在 1983 年圖上指出）。
    1980: [('seg', 'zd', 'ZD', True, False, {'snap': 50.0, 'R': 120.0, 'jump': 80.0, 'blend': 80.0, 'extend_end': True})],   # 1983 年版；整個 1970–2007 都用這一版（見 main）
    1991: [  # 1998 年 1:5000 像片基本圖（1991–2007）
        ('seg', 'west', [(838, 1030), (921, 766)], False, True),
        ('seg', 'hm', [(838, 1030), (560, 1430)], False, True),
        ('seg', 'ob', [(1048, 561), (1015, 700), (986, 795), (1100, 1560), (1150, 1625)], True, True),
        ('seg', 'l1w', [(1018, 800), (1250, 1200)], True, True),
    ],
}


# 中島線本線的錨點（緯度, 經度），依 1976–1998 年像片基本圖描線上的位置選定（第 36 輪）
ZD_ANCHORS = [(22.59050, 120.30200), (22.58962, 120.29900), (22.59300, 120.29600), (22.59820, 120.29400),
              (22.60000, 120.29335), (22.60565, 120.29118), (22.60872, 120.28483)]


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
    # 站場以外依年代換的線形（apply_reg.py 寫在 G['alt0']，例如 1907–1940 年的鳳山支線舊線），先放進來（第 34 輪）
    for k, v in G.get('alt0', {}).items():
        G['alt'][k] = [list(r) for r in v]
    for k, v in G.get('xalt0', {}).items():          # 側線的同類資料（第 36 輪：台糖中心倉庫線 1962–1976）
        G['xalt'][k] = [list(r) for r in v]
    ZD_ERA = {1980: (1983, 1986)}
    for y0, plan in PLAN.items():
        if y0 in ZD_ERA:                 # 中島：描線只用來吸附，不畫上地圖（第 36 輪）
            ed, c = ZD_ERA[y0]
            gr = {'src': f'{ed} 年 1:5000 像片基本圖（中島，自動描線，只供吸附）', 'o': y0, 'c': c,
                  'lines': json.load(open(f'yard_zd{ed}.json'))}
        else:
            gr = next(g for g in G['yards'] if g.get('o') == y0)
        g = Graph(gr['lines'])
        start = {}     # 同一組裡起點錨點相同的線共用同一個起點（第 36 輪：1984 年組的濱線與西臨港線起點差 3.3 m，連通檢查判為斷開）
        for kind, name, anchors, c0, c1, *opt in plan:
            opt = opt[0] if opt else {}
            if anchors == 'ZD':
                anchors = [ll2px(p) for p in ZD_ANCHORS]
            # 中島東側線北端到北段西行那組之間的彎道，各版描線都斷開 60–110 m（彎道、文字），跳躍距離放寬到 120 m，
            # 斷開處由 yardroute 以 Hermite 曲線銜接（第 36 輪）
            yardroute.R, yardroute.JUMP_COST = opt.get('R', 40.0), opt.get('jump', 20.0)
            pts, full = route(g, [px2ll(*p) for p in anchors], snap=opt.get('snap', 20.0))
            yardroute.R, yardroute.JUMP_COST = 40.0, 20.0
            if opt.get('extend_end'):
                # 描線在線的盡頭常常斷掉（文字、圖幅邊），終點錨點是人工依圖定的：路徑沒到時，順著路徑末端方向延伸到錨點（第 36 輪）
                end = px2ll(*anchors[-1])
                a, b = np.array(to_xy(pts[-2])), np.array(to_xy(pts[-1]))
                e = np.array(to_xy(end))
                gap = float(np.hypot(*(e - b)))
                if gap > 5:
                    u = (b - a) / (float(np.hypot(*(b - a))) or 1e-9)
                    if float((e - b) @ u) / gap > math.cos(math.radians(20)):
                        pts = list(pts) + [to_ll(*e)]
            if not c0 and 'from' not in opt:
                pts = list(pts)
                if anchors[0] in start:
                    pts[0] = start[anchors[0]]
                else:
                    start[anchors[0]] = pts[0]
            if 'from' in opt:                  # 自母線（本年代的線形）上的指定點以緩和曲線分出，接到路徑起點
                par = G['alt'][opt['from'][0]][-1][2]
                P0, h0, _ = on_line(par, px2ll(*opt['from'][1]))
                a, b = np.array(to_xy(pts[0])), np.array(to_xy(pts[1]))
                lead = hermite(P0, h0, a, math.atan2(*(b - a)[::-1]))
                pts = [to_ll(*p) for p in lead[:-1]] + list(pts)
            base = G['seg'][name] if kind == 'seg' else G['extra'][name][0]
            new = splice(base, pts, c0, c1, opt.get('blend', 30.0))
            jumps = sum(1 for s, t in zip(full, full[1:]) if s[0] != t[0])
            print(gr['src'], name, '路徑', len(pts), '點', '換股', jumps, '次')
            (G['alt'] if kind == 'seg' else G['xalt']).setdefault(name, []).append([gr['o'], gr['c'], new if kind == 'seg' else [new]])
    # 中島線本線：四版像片基本圖上是同一股軌道，只用 1983 年版算出的線形，整個 1970–2007 年通用；
    # 中島其他各股由人工定線（manual_lines.ZD_LINES），接在這條本線上（第 36 輪）
    import manual, manual_lines
    zd = G['alt']['zd'][0][2]
    G['alt']['zd'] = [[1970, 2008, zd]]
    G['yards'] = [g for g in G['yards'] if g['src'] not in (manual_lines.ZSRC, manual_lines.ZSRC_E, manual_lines.ZSRC_YL)]
    manual.apply(G, {**G['seg'], 'zd': zd}, G['extra'], manual_lines.ZD_LINES)
    # 濱線商港側：預設線形改依 1962 年圖；1960–1964 年濱線走 1970 年股道時，分岐點跟著移
    hn = '濱線（商港側，往海關碼頭）'
    G['extra'][hn] = [hamasen_link(G['seg']['hm'])]
    for o, c, g in G['alt'].get('hm', []):
        G['xalt'].setdefault(hn, []).append([o, c, [hamasen_link(g)]])
    for xn, par in REATTACH.items():
        own = {o for o, c, g in G['xalt'].get(xn, [])}     # 已在 PLAN 依股道算過的年代不再重接
        for o, c, g in G['alt'].get(par, []):
            if o not in own:
                G['xalt'].setdefault(xn, []).append([o, c, [reattach(G['extra'][xn][0], g)] + G['extra'][xn][1:]])
        G['xalt'].get(xn, []).sort(key=lambda a: a[0])
    # 自動描線把主線本身也描成一股的：高雄機廠組（1975–2018）裡沿東臨港線的那一條。e1 在第 36 輪之十一依像片基本圖移到這條線上之後，
    # 兩者是同一股軌道，描線又是八個頂點的折線，會和主線互相交織（overlap.py 報斜穿）。六成以上頂點離 e1 不到 2.5 m 的股道移除。
    def _dseg(p, L):
        best = 1e9
        for a_, b_ in zip(L, L[1:]):
            ax, ay = (a_[1] - p[1]) * 102700, (a_[0] - p[0]) * 110800; bx, by = (b_[1] - p[1]) * 102700, (b_[0] - p[0]) * 110800
            dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, -(ax * dx + ay * dy) / l2)); best = min(best, math.hypot(ax + t * dx, ay + t * dy))
        return best
    for g in G['yards']:
        if g.get('o') == 1975 and g.get('c') == 2018:
            keep = [l for l in g['lines'] if sum(_dseg(p, G['seg']['e1']) < 2.5 for p in l) < 0.6 * len(l)]
            if len(keep) != len(g['lines']): print('機廠組移除與 e1 重複的描線', len(g['lines']) - len(keep), '條')
            g['lines'] = keep
    json.dump(G, open('geo_v13.json', 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
