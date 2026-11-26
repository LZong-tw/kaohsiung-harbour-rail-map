import json, math, numpy as np
from regularize import *

G = json.load(open('geo_v12b.json')); S = G['seg']; X = G['extra']
ORIG = json.loads(json.dumps(G))
LR = S['lr2'] + S['lr1']

def walk_back(T, i, q, dist, u_branch):
    # move from q along parent T by dist, in the direction opposite to the branch heading
    dvec = toM(T[i+1]) - toM(T[i]); fwd = (unit(dvec) @ u_branch) > 0
    pts = T[:i+1][::-1] if fwd else T[i+1:]
    prev = q; acc = 0.0
    for p in pts:
        pm = toM(p); d = np.hypot(*(pm - prev))
        if acc + d >= dist: return prev + unit(pm - prev) * (dist - acc)
        acc += d; prev = pm
    return prev
def make_turnout(L, T, end=0, maxang=35, back=45):
    # if the branch leaves its parent too steeply, move the junction back along the parent
    p0, p1 = (L[0], L[1]) if end == 0 else (L[-1], L[-2])
    d, i, q, t, u = nearest_on(p0, T)
    k = min(len(L) - 1, 4) if end == 0 else max(0, len(L) - 5)
    ub = unit(toM(L[k]) - q)
    ang = math.degrees(math.acos(np.clip(abs(u @ ub), -1, 1)))
    if ang <= maxang: return L
    J = toLL(walk_back(T, i, q, back, ub))
    if end == 0:
        k = 1
        while k < len(L) - 2 and np.hypot(*(toM(L[k]) - q)) < back * 0.8: k += 1
        return [J] + L[k:]
    k = len(L) - 2
    while k > 1 and np.hypot(*(toM(L[k]) - q)) < back * 0.8: k -= 1
    return L[:k+1] + [J]

def mid_far_from_lr(V, i, d=20):
    m = (V[i] + V[i+1]) / 2; return nearest_on(toLL(m), LR)[0] > d

def mask_all(V): return lambda i: True

# 1) west line: 鼓山 end merges into 縱貫線 (coming from the north)
zg = S['zg_n']
S['west'] = regularize(S['west'], 4, 400, tail_parent=zg, Tlead=60)

# 1b) re-trace 1989-sourced lines along the rail symbol (used only as the trace for RDP/refit/fillet)
ROUTE2 = {'l1w': 30, 'w0': 20, 'w1': 35, 'w2': 25, 'w3': 20, 'e1': 14, 'ob': 30}
for k, b in ROUTE2.items():
    S[k] = route2(S[k], b)
# 國際商專一帶：1989 年圖上為一直線，描線會被校舍輪廓吸走 -> 以兩端錨點的直線取代
from corr import px2ll as _p2l
_A, _B = toM(list(_p2l(2860, 2770))), toM(list(_p2l(2990, 3080)))
_u = unit(_B - _A)
def _proj_straight(L, A, B, u):
    out = []
    for p in L:
        v = toM(p); t = (v - A) @ u
        if 0 < t < np.hypot(*(B - A)): v = A + u * t
        out.append(toLL(v))
    return out
S['e1'] = _proj_straight(S['e1'], _A, _B, _u)
# 2) main loop as two chains meeting the 中島線 at 5.4K
S['zd'] = regularize(S['zd'], 6, 400, Tlead=30)
def run_chain(CH, REF, lead=None, tail=None):
    joins = [ORIG['seg'][k][-1] for k in CH[:-1]]
    V, owner, TR = [], [], []
    for k in CH:
        tol = 3 if k == 'k4' else 6
        vk = drop_collinear(rdp([toM(p) for p in S[k]], tol))
        if V: vk = vk[1:]
        V += vk; owner += [k] * len(vk); TR += [toM(p) for p in S[k]]
    def mask(i):
        k = owner[min(i + 1, len(owner) - 1)]
        if k not in REF: return False
        if k == 'e1': return mid_far_from_lr(V, i)
        return True
    V = refit_poly(V, (True, True), mask)
    V = simplify_pi(drop_collinear(V), minlen=60)
    lu = tu = None
    if lead: V, lu = seat_turnout(V, lead[0], 0, force=lead[1], Rmin=lead[2], maxback=lead[3])
    if tail: V, t_ = seat_turnout(V, tail[0], -1, force=tail[1], Rmin=tail[2], maxback=tail[3]); tu = -t_
    out = fillet(V, 500, lu, tu, Tlead=90, trace=TR, Rmin=50)
    chain = [toLL(p) for p in out]
    if lead: chain[0] = insert_on(lead[0], out[0])
    if tail: chain[-1] = insert_on(tail[0], out[-1])
    cuts = []
    for j in joins:
        dd, i, q, t, u = nearest_on(j, chain); ll = toLL(q)
        if 0 < t < 1: chain.insert(i + 1, ll); cuts.append(i + 1)
        else: cuts.append(i if t == 0 else i + 1)
    cuts = sorted(cuts); prev = 0
    for k, c in zip(CH, cuts + [len(chain) - 1]):
        S[k] = chain[prev:c + 1]; prev = c
J54 = S['zd'][0]
run_chain(['l1w', 'w0', 'w1', 'qzb', 'w2'], {'l1w', 'w0', 'w1', 'qzb', 'w2'},
          lead=(S['west'], None, 100, 140), tail=(S['zd'], -1, 60, 60))
S['w3'][0] = J54
run_chain(['w3', 'k4', 'e1'], {'w3', 'e1'}, lead=None, tail=(S['pt'], None, 80, 24))
S['w3'][0] = J54

# 3) branches from west
S['ob'] = regularize(S['ob'], 8, 300, refit_mask=lambda i: True, lead_parent=S['west'], Tlead=50)
S['hm'] = regularize(S['hm'], 3, 200, lead_parent=S['west'], Tlead=40)

# 4) 中島線 from the Y at 5.4K (parent = 成功路 line arriving from north)
# 第二臨港線 + 中鋼 chain from 6.8K
V2 = simplify_pi(drop_collinear(rdp([toM(p) for p in S['s2']], 4)) + drop_collinear(rdp([toM(p) for p in S['s2b']], 4))[1:], minlen=50)
j2 = S['s2'][-1]
_par2 = S['k4'] if nearest_on(S['s2'][0], S['k4'])[0] < nearest_on(S['s2'][0], S['w3'])[0] else S['w3']
V2, lead_u = seat_turnout(V2, _par2, 0)
o2 = fillet(V2, 500, lead_u, None, Tlead=90, trace=[toM(p) for p in S['s2']+S['s2b']], Rmin=100)
c2 = [toLL(p) for p in o2]; c2[0] = insert_on(_par2, o2[0])
dd, i, q, t, u = nearest_on(j2, c2); c2.insert(i + 1, toLL(q))
S['s2'] = c2[:i + 2]; S['s2b'] = c2[i + 1:]
for k in ('c2', 'c3'):
    par = S['s2'] if nearest_on(S[k][0], S['s2'])[0] < nearest_on(S[k][0], S['s2b'])[0] else S['s2b']
    S[k] = regularize(S[k], 4, 300, lead_parent=par, Tlead=50)

# 5) extras: find parents on the ORIGINAL geometry, then process in dependency order
def find_parent(pt, self_name):
    best = None
    for k, v in ORIG['seg'].items():
        if k.startswith('lr') or k == self_name: continue
        d = nearest_on(pt, v)[0]
        if d < 1.0 and (best is None or d < best[0]): best = (d, 'seg', k)
    for k, parts in ORIG['extra'].items():
        if k == self_name: continue
        d = nearest_on(pt, parts[0])[0]
        if d < 1.0 and (best is None or d < best[0]): best = (d, 'extra', k)
    return best
def cur(kind, k): return S[k] if kind == 'seg' else X[k][0]

SUGAR = lambda n: n.startswith('糖鐵')

REFIT_X = {'205 兵工廠外側線（廠區北緣—凱得街）', '臺糖倉庫側線（臺鐵）', '成功路側線（臺鋁南側油槽區）', '臺肥三廠側線'}
SKIP = set()
todo = [k for k in X if k not in SKIP]; done = set()
info = {}
for k in todo:
    L = ORIG['extra'][k][0]
    info[k] = (find_parent(L[0], k), find_parent(L[-1], k))
K205 = '205 兵工廠外側線（廠區北緣—凱得街）'
info['淺野線（臺泥側線）'] = (None, None)
for _k in ('船渠北岸造船所線 A（1945 年美軍圖）', '船渠北岸造船所線 B（1945 年美軍圖）', '苓雅寮東側線（1945 年美軍圖，三股）'):
    _L = X[_k][0]
    _par = min(('w1', 'qzb'), key=lambda s: nearest_on(_L[0], S[s])[0])
    info[_k] = ((0, 'seg', _par), None)
info['前鎮車場股道 1'] = ((0, 'seg', 'k4'), (0, 'seg', 'e1'))
info['前鎮車場股道 2'] = ((0, 'seg', 'k4'), (0, 'seg', 'e1'))
SKIP.update(k for k in X if SUGAR(k))
info['臺糖倉庫側線（臺鐵）'] = ((0, 'seg', 's2'), None)
todo = [k for k in todo if k not in SKIP]
from corr import px2ll as _p2l
_m = nearest_on(list(_p2l(2681, 4080)), S['k4'])[2]
X[K205] = [X[K205][0][:-1] + [toLL(_m)]]; info[K205] = (info[K205][0], (0, 'seg', 'k4'))
for _ in range(6):
    for k in todo:
        if k in done: continue
        hp, tp = info[k]
        deps = [p for p in (hp, tp) if p and p[1] == 'extra']
        if any(p[2] not in done and p[2] in todo for p in deps): continue
        L = X[k][0]
        lp = cur(hp[1], hp[2]) if hp else None
        tpar = cur(tp[1], tp[2]) if tp else None
        if SUGAR(k) and k == '糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）': lp = None   # starts at 鳳山 station, separate gauge
        tol = 4; R = 250 if SUGAR(k) else 300
        if k == '中岸壁線':
            Xs, Us = parent_samples(lp); j0 = int(np.argmin(np.hypot(*(Xs - toM(L[0])).T)))
            j1 = min(len(Xs) - 1, j0 + 15); L = [toLL(Xs[j1])] + [p for p in L[1:] if (toM(p) - Xs[j1]) @ Us[j1] > 10]
        mask = (lambda i: True) if k in REFIT_X else None
        X[k] = [regularize(L, tol, R, refit_mask=mask, lead_parent=lp, tail_parent=tpar, Tlead=45)]
        done.add(k)
print('extras not done:', [k for k in todo if k not in done])

# 淺野線：依 1989 年地形圖（z17，與 OSM 對位良好）逐點重描；直線段從西端一路到鼓山站北側，再右彎併入縱貫線
def _an89(x, y):
    Z = 17; n = 2 ** Z * 256
    ox = (120.270 + 180) / 360 * n; oy = (1 - math.asinh(math.tan(math.radians(22.6485))) / math.pi) / 2 * n
    X_, Y_ = ox + x, oy + y
    return [math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * Y_ / n)))), X_ / n * 360 - 180]
_L = [_an89(*p) for p in [(502, 342), (580, 381), (655, 419), (720, 452), (790, 487), (850, 515), (895, 532),
                          (930, 541), (960, 552), (985, 570), (1000, 598), (1012, 630), (1022, 665), (1030, 695)]]
_L = regularize(_L, 3, 300)
_d, _i, _q, _t, _u = nearest_on(_an89(1036, 735), S['zg_n'])
_J = insert_on(S['zg_n'], _q)
X['淺野線（臺泥側線）'] = [_L + [_J]]
# pull quay/shipyard lines back onto land (OSM water) and trim ends that still run into water
import math as _m
_W = np.load('water.npy')
def _ozpx(la, lo):
    n = 2 ** 15
    x = (lo + 180) / 360 * n * 256; y = (1 - _m.asinh(_m.tan(_m.radians(la))) / _m.pi) / 2 * n * 256
    x0 = (120.262 + 180) / 360 * n * 256; y0 = (1 - _m.asinh(_m.tan(_m.radians(22.680))) / _m.pi) / 2 * n * 256
    return int(x - x0), int(y - y0)
def wet(p):
    x, y = _ozpx(*p); return 0 <= y < _W.shape[0] and 0 <= x < _W.shape[1] and _W[y, x]
def to_land(L, maxd=40, margin=5, skip=25):
    """parallel-offset the whole line by the smallest distance that takes it out of the water"""
    P0 = np.array([toM(p) for p in L]); sg = np.hypot(*np.diff(P0, axis=0).T); cc = np.concatenate([[0], np.cumsum(sg)])
    ss = np.append(np.arange(0, cc[-1], 3.0), cc[-1])
    P = list(np.stack([np.interp(ss, cc, P0[:, 0]), np.interp(ss, cc, P0[:, 1])], 1))
    N_ = []
    for i in range(len(P)):
        u = unit(P[min(len(P)-1, i+1)] - P[max(0, i-1)]); N_.append(np.array([-u[1], u[0]]))
    cum = np.concatenate([[0], np.cumsum([np.hypot(*(P[i+1]-P[i])) for i in range(len(P)-1)])])
    def wetfrac(off):
        w = [wet(toLL(P[i] + N_[i] * off)) for i in range(len(P)) if cum[i] > skip]
        return sum(w) / max(1, len(w))
    if wetfrac(0) < 0.05: return L
    best = None
    for d in np.arange(2, maxd, 2):
        for s in (1, -1):
            f = wetfrac(s * d)
            if f < 0.05: best = s * (d + margin); break
        if best is not None: break
    if best is None: return L
    out = []
    for i in range(len(P)):
        w_ = min(1.0, cum[i] / skip)       # keep the junction end fixed, ramp the offset in
        out.append(toLL(P[i] + N_[i] * best * w_))
    return out
def trim_wet_end(L):
    while len(L) > 3 and wet(L[-1]): L = L[:-1]
    return L
for _k in ('中岸壁線', '船渠北岸造船所線 A（1945 年美軍圖）', '船渠北岸造船所線 B（1945 年美軍圖）', '苓雅寮東側線（1945 年美軍圖，三股）'):
    X[_k] = [regularize(trim_wet_end(to_land(X[_k][0])), 1.5, 300)]
# 蓬萊碼頭：依 1989 年圖（與 2024 正射影像對位良好）
_PZ = json.load(open('pier89.json'))
def _straight_tail(L, a, b, frac=1.0, left=0.0, back=80.0):
    d = [math.dist(p, a) for p in L]; i = int(np.argmin(d))
    if left:
        dn, de = (b[0] - a[0]) * 111000, (b[1] - a[1]) * 102700; n0 = math.hypot(dn, de)
        sh = np.array([de / n0 * left / 111000, -dn / n0 * left / 102700])
        a, b = list(np.array(a) + sh), list(np.array(b) + sh)
        acc = 0.0                                   # 往回退 back 公尺，讓平移在這段距離內完成
        while i > 1 and acc < back:
            acc += float(np.hypot(*((np.array(L[i]) - np.array(L[i - 1])) * [111000, 102700]))); i -= 1
    A, B = np.array(a), np.array(a) + (np.array(b) - np.array(a)) * frac
    n = max(2, int(np.hypot(*((B - A) * [111000, 102700])) // 15))
    return L[:i + 1] + [list(A + (B - A) * t) for t in np.linspace(0, 1, n + 1)]
S['ob'] = regularize(_straight_tail(S['ob'], *_PZ['front'], frac=0.96, left=16), 1.5, 300)
X['裏岸壁線'] = [[p for p in X['裏岸壁線'][0] if p[1] < 120.2836]]  # 船渠在人行橋以東變寬，裏岸壁線止於橋西
X['中岸壁線'] = [regularize(_straight_tail(X['中岸壁線'][0], *_PZ['mid']), 1.5, 300)]
S['qy1'] = X.pop('前鎮車場股道 1')[0]; S['qy2'] = X.pop('前鎮車場股道 2')[0]

# e1 接屏東線前的第一個彎：原本 R≈50 m，在圖上看起來像折角；改成與 2024 正射影像上舊路廊（綠帶）一致的 R=200 m 圓曲線
def _smooth_bend(L, lat_lo, lat_hi, R=200.0):
    idx = [i for i, p in enumerate(L) if lat_lo < p[0] < lat_hi]
    i0, i1 = idx[0], idx[-1]
    a0, a1 = toM(L[i0 - 10]), toM(L[i0]); b0, b1 = toM(L[i1]), toM(L[i1 + 1])
    u, w = unit(a1 - a0), unit(b1 - b0)
    I = intersect(a1, u, b0, w); th = math.acos(np.clip(u @ w, -1, 1)); T = R * math.tan(th / 2)
    A = I - u * T; B = I + w * T
    keep0 = [p for p in L[:i0 + 1] if (toM(p) - A) @ u < 0]
    keep1 = [p for p in L[i1 + 1:] if (toM(p) - B) @ w > 0]
    return keep0 + [toLL(v) for v in arc_pts(A, u, w, T, th)] + keep1
S['e1'] = _smooth_bend(S['e1'], 22.63640, 22.63700)
# 7) 專用側線考證（第 21 輪）：依 1955／1966／1989 年圖與廠址比對改名，並補台塑線
# 台塑線：1966 年圖上 205 外側線西端有鐵路符號沿支渠北岸往西南延伸到中山路，對面標「塑膠廠」；1955 年圖無此段
_k205 = '205 兵工廠外側線（廠區北緣—凱得街）'
_w = X[_k205][0][0]
_TS = [_w, [22.60490, 120.31236], [22.60435, 120.31149], [22.60356, 120.31055]]
X['台灣塑膠公司線（推定）'] = [regularize(_TS, 3, 300)]
_RN = {
    '成功路側線（臺鋁南側油槽區）': '台電南部火力發電所線（推定）',
    '臺肥三廠側線': '台灣肥料公司線（臺肥三廠）',
    '前鎮運河支渠側線': '台灣鹼業公司線（推定）',
    '經貿變電所側線（2009 年街景可見路面下軌道）': '經貿變電所側線（推定台機鋼品廠線）',
    _k205: '205 兵工廠外側線（推定兼硫酸錏廠線）',
    '臺糖倉庫側線（臺鐵）': '台糖中心倉庫線（推定）',
}
X = G['extra'] = {_RN.get(k, k): v for k, v in X.items()}
# 每條側線的顯示年份 [啟用年, 停用年)：與主線相同，停用年當年起不再顯示；None 表示不設限。
# 有文獻日期的用文獻；沒有的依地圖證據（最早出現的年圖）與母線停用年推定，依據寫在 METHODS.md。
G['xy'] = {
    # 文獻日期（維基百科〈高雄臨港線〉專用側線表）
    '台電南部火力發電所線（推定）': [1955, 1992],
    '台灣肥料公司線（臺肥三廠）': [1952, 2008],      # 廢止日不詳，上限取第一臨港線西段停用
    '台灣鹼業公司線（推定）': [1954, 1993],
    '台灣塑膠公司線（推定）': [1965, 1990],
    '205 兵工廠外側線（推定兼硫酸錏廠線）': [1959, 2018],   # 廢止日不詳，上限取凱旋四路段停用
    '205 兵工廠大門側線（凱旋四路側）': [1959, 2018],
    '台糖中心倉庫線（推定）': [1962, 2011],          # 廢止日不詳，上限取第二臨港線廢止
    # 地圖證據
    '中岸壁線': [1945, 2008],                         # 1945、1955、1966、1989、2001 年圖皆有
    '裏岸壁線': [1945, 2008],                         # 1945、1955、1989 年圖有
    '淺野線（臺泥側線）': [1945, 2018],               # 1945～2001 年圖皆有；上限取縱貫線地下化
    '濱線（商港側，往海關碼頭）': [1908, 1965],       # 開辦推定與濱線漁港側同期；1962 年圖仍有、1970 年 1:1200 圖只剩地界線 → 停用推定 1965（第 28 輪）
    '苓雅寮東側線（1945 年美軍圖，三股）': [1944, 1955],  # 只見於 1945 年圖
    '船渠北岸造船所線 A（1945 年美軍圖）': [1941, 1955],
    '船渠北岸造船所線 B（1945 年美軍圖）': [1941, 1955],
    '經貿變電所側線（推定台機鋼品廠線）': [1955, 2008],  # 1955 年圖已有；2009 年街景仍見路面下軌道
    '獅子公園三角線東側（原主線弧線）': [1941, 2008],     # 原主線，與第一臨港線同期
    # 糖鐵：本身年份未查到，以臺鐵「台糖籬仔內線」1955-03-01～1993-12-28 為準
    '糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）': [1955, 1994],
    '糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）': [1955, 1994],
    '糖鐵牛寮三角線（往籬仔內）': [1955, 1994],
    '糖鐵籬子內線後期段（沿中山四路接臺糖倉庫）': [1962, 1994],  # 接臺糖中心倉庫（1962）
}
missing = [k for k in X if k not in G['xy']]
assert not missing, missing
# 8) 站場股道（第 27 輪）：高雄港站、前鎮車場、高雄機廠改用 1:5000 像片基本圖描出的股道（yards.py），
#    依年代分組；其餘站場維持原樣，年份由網頁依最近車站決定。
import math as _m
def _poly_ll(f, Z, W, N):
    n = 2 ** Z * 256; ox = (W + 180) / 360 * n; oy = (1 - _m.asinh(_m.tan(_m.radians(N))) / _m.pi) / 2 * n
    def ll(x, y):
        return (_m.degrees(_m.atan(_m.sinh(_m.pi * (1 - 2 * (oy + y) / n)))), (ox + x) / n * 360 - 180)
    return [ll(x, y) for x, y in json.load(open(f))]
def _inside(pt, poly):
    la, lo = pt; c = False
    for i in range(len(poly)):
        (a1, o1), (a2, o2) = poly[i], poly[i - 1]
        if (a1 > la) != (a2 > la) and lo < (o2 - o1) * (la - a1) / (a2 - a1) + o1:
            c = not c
    return c
_PKS = _poly_ll('yard_poly_ks.json', 18, 120.2715, 22.6270)
_PQZ = _poly_ll('yard_poly_qz.json', 18, 120.3150, 22.6200)
_mid = lambda g: g[len(g) // 2]
_old_ks = [g for g in G['yard'] if _inside(_mid(g), _PKS)]
_others = [g for g in G['yard'] if not _inside(_mid(g), _PKS) and not _inside(_mid(g), _PQZ)]
_qz = json.load(open('yard_qz1998.json'))
_jc = [g for g in _qz if sum(p[0] for p in g) / len(g) > 22.6115]   # 機廠
_qc = [g for g in _qz if sum(p[0] for p in g) / len(g) <= 22.6115]  # 前鎮車場
G['yards'] = [
    {'src': '1945 年美軍高雄市街圖', 'o': 1900, 'c': 1960, 'lines': _old_ks},
    # 1960–1986 改用 1970 年 1:1200 都市計畫航測地形圖（中研院高雄百年歷史地圖）描出的股道（第 28 輪，yardtrace_line.py）：
    # 線劃圖的股道連續、轉轍器清楚，比 1976 年像片基本圖的描線（yard_ks1976.json，片段多）適合讓主線沿股道走。
    {'src': '1970 年 1:1200 都市計畫航測地形圖', 'o': 1960, 'c': 1987, 'lines': json.load(open('yard_ks1970.json'))},
    {'src': '1998 年 1:5000 像片基本圖', 'o': 1987, 'c': 2008, 'lines': json.load(open('yard_ks1998.json'))},
    {'src': '1998 年 1:5000 像片基本圖', 'o': 1967, 'c': 2018, 'lines': _qc},
    {'src': '1998 年 1:5000 像片基本圖', 'o': 1975, 'c': 2018, 'lines': _jc},
    {'src': '既有', 'o': None, 'c': None, 'lines': _others},
]
del G['yard']
print('yards', [(g['o'], g['c'], len(g['lines'])) for g in G['yards']])
# 9) 交叉與疊線修正（第 28 輪，overlap.py 檢查）：
#    側線與母線在接點附近交叉而過、或先疊在母線上走一段才分出，改成從接點起就在同一側以平滑曲線分出／併入。
def _arc(M):
    P = [toM(p) for p in M]
    s = [0.0]
    for a, b in zip(P, P[1:]):
        s.append(s[-1] + float(np.hypot(*(b - a))))
    return P, s
def _at(P, s, x):
    i = max(0, min(len(s) - 2, int(np.searchsorted(s, x)) - 1))
    t = (x - s[i]) / ((s[i + 1] - s[i]) or 1e-9)
    d = P[i + 1] - P[i]
    u = d / (np.hypot(*d) or 1)
    return P[i] + d * t, np.array([-u[1], u[0]])
def _pos(P, s, p):
    best = None
    for i in range(len(P) - 1):
        d = P[i + 1] - P[i]; l2 = float(d @ d) or 1e-9
        t = float(np.clip((p - P[i]) @ d / l2, 0, 1)); q = P[i] + d * t
        dist = float(np.hypot(*(p - q)))
        if best is None or dist < best[0]:
            u = d / np.sqrt(l2)
            best = (dist, s[i] + t * np.sqrt(l2), float(u[0] * (p - q)[1] - u[1] * (p - q)[0]))
    return best   # (距離, 沿線位置, 帶號側距：左正右負)
def clean_junction(S, M, at_start, far=8.0, shared=1.5, step=3.0):
    """側線 S 與母線 M 的接點整理：去掉疊在母線上的部分，從離母線 far 公尺處起沿母線以餘弦漸減的側距併入接點，
    整段都在原本那一側，不會交叉。at_start：接點在 S 的起點。"""
    S = list(S[::-1]) if at_start else list(S)
    # 先加密（原本的頂點可能很疏，一段長直線就跨到母線另一側）
    D = []
    for a, b in zip(S, S[1:]):
        A, B = toM(a), toM(b)
        n = max(1, int(np.hypot(*(B - A)) / step))
        D += [toLL(A + (B - A) * t) for t in np.linspace(0, 1, n, endpoint=False)]
    S = D + [S[-1]]
    P, s = _arc(M)
    d = [_pos(P, s, toM(p)) for p in S]
    j = len(S) - 1
    while j > 0 and d[j - 1][0] < shared:
        j -= 1
    # 側線原本從哪一側來：取接點前 200 m 內離母線 far 以上的點，多數在哪一側就是哪一側
    sa = np.r_[0, np.cumsum([np.hypot(*(toM(b) - toM(a))) for a, b in zip(S, S[1:])])]
    win = [i for i in range(j) if sa[j] - sa[i] < 200 and d[i][0] >= far]
    sgn = np.sign(sum(np.sign(d[i][2]) for i in win)) if win else 0
    cand = [i for i in win if np.sign(d[i][2]) == sgn] or [i for i in range(j) if d[i][0] >= far] or [0]
    k = max(cand)
    s0, side = d[k][1], d[k][2]
    s1 = d[j][1]
    n = max(2, int(abs(s1 - s0) / step))
    ramp = []
    for x in np.linspace(s0, s1, n + 1)[1:]:
        t = (x - s0) / ((s1 - s0) or 1e-9)
        q, nv = _at(P, s, x)
        ramp.append(toLL(q + nv * side * 0.5 * (1 + math.cos(math.pi * t))))
    out = S[:k + 1] + ramp
    return out[::-1] if at_start else out
# 淺野線：從西側接近縱貫線，原本在最後 80 m 斜穿到東側再接回
X['淺野線（臺泥側線）'][0] = clean_junction(X['淺野線（臺泥側線）'][0], S['zg_n'], at_start=False)
# 台電線：起點在前鎮橋北端，原本先往南折出一個尖角，再以小角度斜穿第一臨港線到西側
X['台電南部火力發電所線（推定）'][0] = clean_junction(X['台電南部火力發電所線（推定）'][0], S['w1'], at_start=True)
# 205 大門側線：原本先疊在凱旋四路線上走約 40 m 才分出，分出處又略為交叉
X['205 兵工廠大門側線（凱旋四路側）'][0] = clean_junction(X['205 兵工廠大門側線（凱旋四路側）'][0], S['k4'], at_start=True)
# 第二貨櫃線：起點處略為跨到第二臨港線另一側
S['c2'] = clean_junction(S['c2'], S['s2'], at_start=True)
# 鼓山：西臨港線與鼓山—三塊厝線在鼓山站南側共用路廊，原本兩線在 250 m 內交叉兩次。
# 往高雄港站的西臨港線應在西側、往三塊厝東彎的線在東側：鼓山站以南改為沿 zg_s 西側 6 m 並行，
# 到 zg_s 開始東彎後再接回原線形。
def _fix_gushan():
    W, Z = S['west'], S['zg_s']
    PZ, sZ = _arc(Z)
    # zg_s 從鼓山站往南的直線段（開始東彎前），向西平移 6 m
    stn = toM(G['st']['鼓山'])
    off = []
    for x in np.arange(0, 150, 6.0):
        q, nv = _at(PZ, sZ, x)
        if nv[0] > 0: nv = -nv            # 西側
        off.append(q + nv * 6.0)
    PW = [toM(p) for p in W]
    # W 的北端接縱貫線；找出 W 上最接近 off[-1]、off[0] 的頂點，中間改成 off
    i_s = int(np.argmin([np.hypot(*(p - off[-1])) for p in PW]))
    i_n = int(np.argmin([np.hypot(*(p - off[0])) for p in PW]))
    assert i_s < i_n, (i_s, i_n)
    mid = [toLL(p) for p in off[::-1]]
    # 平移段北端直接接到縱貫線上的接點（W 的最後一點），不再接回原本那段往東的弧線
    return W[:i_s] + mid + W[-1:]
S['west'] = _fix_gushan()
# 草衙：糖鐵籬仔內線與第二臨港線延伸（中鋼線）在 1989 年圖上是同一條軌道（圖上只有一條鐵路），
# 原本兩線各自依不同圖描，在 400 m 內交叉三次。15 m 以內的段落改為與中鋼線同線（以中鋼線的線形為準），
# 前後 70 m 平滑銜接。
def snap_shared(A, B, tol=15.0, step=3.0, L=70.0):
    PA = [toM(p) for p in A]
    D = []
    for a, b in zip(PA, PA[1:]):
        n = max(1, int(np.hypot(*(b - a)) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            D.append(a + (b - a) * t)
    D.append(PA[-1])
    PB, sB = _arc(B)
    pos = [_pos(PB, sB, p) for p in D]
    on = np.array([r[0] < tol for r in pos], float)
    # 與 B 共線的權重：在共線段內為 1，進出共線段時在 L 公尺內以餘弦漸變
    sA = np.r_[0, np.cumsum([np.hypot(*(b - a)) for a, b in zip(D, D[1:])])]
    w = np.zeros(len(D))
    idx = np.nonzero(on)[0]
    for i in range(len(D)):
        if not len(idx):
            break
        dmin = np.min(np.abs(sA[idx] - sA[i]))
        w[i] = 1.0 if on[i] else (0.5 * (1 + math.cos(math.pi * dmin / L)) if dmin < L else 0.0)
    out = []
    for p, r, wi in zip(D, pos, w):
        q, _ = _at(PB, sB, r[1])
        out.append(toLL(p * (1 - wi) + q * wi))
    return rdp_ll(out)
def rdp_ll(L, eps=0.5):
    P = [toM(p) for p in L]
    def _r(a, b):
        if b - a < 2:
            return [a, b]
        A, B = P[a], P[b]; v = B - A; n = np.hypot(*v) or 1
        d = [abs(v[0] * (P[i] - A)[1] - v[1] * (P[i] - A)[0]) / n for i in range(a + 1, b)]
        i = int(np.argmax(d))
        if d[i] > eps:
            m = a + 1 + i
            return _r(a, m)[:-1] + _r(m, b)
        return [a, b]
    return [L[i] for i in _r(0, len(L) - 1)]
X['糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）'][0] = snap_shared(X['糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）'][0], S['s2b'])
# 6) stations & branch markers re-projected
lines = [v for k, v in S.items() if not k.startswith('lr')] + [p[0] for p in X.values()]
for n, p in list(G['st'].items()):
    best = min((nearest_on(p, L) for L in lines), key=lambda r: r[0])
    if best[0] < 40: G['st'][n] = toLL(best[2])
G['br'] = {'5.4K 中島線分歧': S['zd'][0], '6.8K 第二臨港線分歧': S['s2'][0],
           '前鎮橋（1955）': S['qzb'][1]}
json.dump(G, open('geo_v13.json', 'w'), separators=(',', ':'))
print({k: len(v) for k, v in S.items() if not k.startswith('lr')})
