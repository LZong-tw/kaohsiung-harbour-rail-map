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
    # 造船所線 A、B 接在成功路北段（w1，1944 年隨苓雅寮大橋通車）。原本寫 1941（誤取運河南岸 w2 的年份），
    # 1941–1943 年地圖上成了不與任何線相連的側線（第 36 輪使用者指出，connect_check.py 也查得到）。
    '船渠北岸造船所線 A（1945 年美軍圖）': [1944, 1955],
    '船渠北岸造船所線 B（1945 年美軍圖）': [1944, 1955],
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
# 描線雜訊過濾（第 29 輪，yardclean.py）：去掉圍牆、建物輪廓的鋸齒線，以及兩頭都不接任何股道、也不在股道束裡的短線
from yardclean import clean as _yclean
_mains = [v for k, v in S.items() if not k.startswith('lr')] + [p for ps in X.values() for p in ps]
def _yc(lines, name):
    k, d = _yclean(lines, _mains)
    print('yardclean', name, 'kept', len(k), 'dropped', len(d), {r: [x for _, x in d].count(r) for r in set(x for _, x in d)})
    return k
_qc, _jc = _yc(_qc, 'qz'), _yc(_jc, 'jc')
G['yards'] = [
    # 1908 年起（第 34 輪由 1900 改）：哈瑪星新生地上的打狗驛 1908 年才啟用，1900–1907 年終點在北方約 600 m 的打狗停車場。
    {'src': '1945 年美軍高雄市街圖', 'o': 1908, 'c': 1960, 'lines': _old_ks},
    # 1960–1976 改用 1970 年 1:1200 都市計畫航測地形圖（中研院高雄百年歷史地圖）描出的股道（第 28 輪，yardtrace_line.py）：
    # 線劃圖的股道連續、轉轍器清楚，比 1976 年像片基本圖的描線（yard_ks1976.json，片段多）適合讓主線沿股道走。
    {'src': '1970 年 1:1200 都市計畫航測地形圖', 'o': 1960, 'c': 1977, 'lines': _yc(json.load(open('yard_ks1970.json')), 'ks1970')},
    # 1977–1990：1984 年都市計畫航測地形圖（第 29 輪，yardtrace.py，以 1970 年描線當方向場）。分界取相鄰兩版的中間年份。
    {'src': '1984 年都市計畫航測地形圖', 'o': 1977, 'c': 1991, 'lines': _yc(json.load(open('yard_ks1984.json')), 'ks1984')},
    {'src': '1998 年 1:5000 像片基本圖', 'o': 1991, 'c': 2008, 'lines': _yc(json.load(open('yard_ks1998.json')), 'ks1998')},
    {'src': '1998 年 1:5000 像片基本圖', 'o': 1967, 'c': 2018, 'lines': _qc},
    {'src': '1998 年 1:5000 像片基本圖', 'o': 1975, 'c': 2018, 'lines': _jc},
    {'src': '既有', 'o': None, 'c': None, 'lines': _others},
]
del G['yard']
# 轉車台（第 29 輪，turntable.py）：圓與放射股道依 1970 年 1:1200 圖；1984 年圖上配置相同，1998 年像片基本圖上已不見。
# 1945、1956 年舊航照上已有轉車台（1945 年另見扇形車庫），放射股道的配置不明，1945–1959 只畫圓。
_tt = json.load(open('tt_ks1970.json'))
G['tt'] = [
    {'src': '1945、1956 年舊航照（位置依 1970 年圖）', 'o': 1945, 'c': 1960, 'center': _tt['center'], 'r': _tt['r_m'], 'spokes': []},
    {'src': '1970 年 1:1200 都市計畫航測地形圖（1984 年圖相同）', 'o': 1960, 'c': 1991, 'center': _tt['center'], 'r': _tt['r_m'], 'spokes': _tt['spokes']},
]
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
# 中山四路（第 31 輪）：糖鐵籬仔內線走道路東側，第二臨港線走西側。
# 依據：使用者提供的臉書社團討論（留言確認第二臨港線在中山路西側、糖鐵在東側）與留言所附前鎮區行政區域圖；
# 1984 年都市計畫航測地形圖在道路東側畫有帶枕木的鐵路，往牛寮的支線由此分出；1989、1993 年經建版在道路兩側
# 各有一條鐵路（西側那條與 OSM 第二臨港線軌跡重合）。東側那條距道路中心約 34 m（22.585 以北）、30 m（22.580 以南），
# 以兩張經建版量得，並以各圖西側線與第二臨港線的差校正圖幅偏移（zsroad.py）。22.584 以北，東側線走在道路與前鎮運河之間的
# 狹長地帶（運河在道路中心以東約 44–82 m）；自籬仔內站南下的線斜跨運河後併入。
# 第 29 輪依「1984 與經建版都只有一條鐵路」把糖鐵併到第二臨港線上，是誤讀：兩側各有一條。
import zsroad
from shapely.geometry import LineString as _LS, Point as _Pt
_SMK = '糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）'
_LTK = '糖鐵籬子內線後期段（沿中山四路接臺糖倉庫）'
def hermite(p0, h0, p1, h1, step=2.0):      # 與 yardlines.py 相同
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = float(np.hypot(*(p1 - p0)))
    m0 = L * np.array([math.cos(h0), math.sin(h0)]); m1 = L * np.array([math.cos(h1), math.sin(h1)])
    return [(2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * m0 + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * m1
            for u in np.linspace(0, 1, max(2, int(L / step)) + 1)]
def _near_ll(L, q):
    return int(np.argmin([math.hypot((p[0] - q[0]) * 110540, (p[1] - q[1]) * 102800) for p in L]))
def _hd(a, b):
    a, b = toM(a), toM(b); return math.atan2(b[1] - a[1], b[0] - a[0])
_ZD = lambda lat: 34.0 if lat >= 22.585 else (30.0 if lat <= 22.580 else 30.0 + 4.0 * (lat - 22.580) / 0.005)
_E = zsroad.east_line(22.5950, 22.5715, _ZD)
_S0 = X[_SMK][0]
_i7 = _near_ll(_S0, (22.591111, 120.321524))          # 自籬仔內站南下、斜向接近中山四路的最後一點
_mi = min(range(len(_E)), key=lambda i: abs(_E[i][0] - 22.5880))   # 併入東側線的位置：斜跨前鎮運河後併入（R≈115 m）
_s = _near_ll(_E, (22.5719, 120.3364))                 # 離開東側線、轉向東往小港糖廠的位置
_i38 = _near_ll(_S0, (22.5694967, 120.3390374))         # 併入草衙以東、沿機場北側往東那段（在中鋼線併入點以東，兩線不交叉）
# 斜跨運河的曲線：原用 hermite，會越過東側線約 7 m 再折回（與後期段交叉 12°，第 31 輪 overlap.py 查出）；
# 改為與舊線（自籬仔內站南下的方向）及東側線兩直線相切的 R 115 m 圓曲線，切點落在東側線的節點上。
_v0 = unit(toM(_S0[_i7]) - toM(_S0[_i7 - 1]))
_k0 = min(range(len(_E)), key=lambda i: abs(_E[i][0] - 22.5885))
_ve = unit(toM(_E[_k0 + 5]) - toM(_E[_k0 - 5]))
_ab = np.linalg.solve(np.array([_v0, -_ve]).T, toM(_E[_k0]) - toM(_S0[_i7]))
_Xm = toM(_S0[_i7]) + _ab[0] * _v0; _th = math.acos(float(np.clip(_v0 @ _ve, -1, 1)))
_Tf = 115.0 * math.tan(_th / 2)
_T1 = _Xm - _Tf * _v0
_mi = min(range(len(_E)), key=lambda i: float(np.hypot(*(toM(_E[i]) - (_Xm + _Tf * _ve)))))
assert _ab[0] > _Tf, ('切點在 _i7 之前', _ab[0], _Tf)
_Of = _T1 + 115.0 * unit(np.array([-_v0[1], _v0[0]]) if np.array([-_v0[1], _v0[0]]) @ _ve > 0 else np.array([_v0[1], -_v0[0]]))
_ang = lambda p: math.atan2(p[1] - _Of[1], p[0] - _Of[0])
_a0, _a1 = _ang(_T1), _ang(toM(_E[_mi])); _da = (_a1 - _a0 + math.pi) % (2 * math.pi) - math.pi
_c1 = [toLL(_Of + 115.0 * np.array([math.cos(_a0 + _da * i / 40), math.sin(_a0 + _da * i / 40)])) for i in range(40)] + [list(_E[_mi])]
_c1 = [list(_S0[_i7])] + _c1
print('運河曲線：交角', round(math.degrees(_th), 1), '切線長', round(_Tf), '併入點', [round(v, 6) for v in _E[_mi]])
_c2 = [toLL(p) for p in hermite(toM(_E[_s]), _hd(_E[_s - 1], _E[_s]), toM(_S0[_i38]), _hd(_S0[_i38], _S0[_i38 + 1]))]
X[_SMK][0] = _S0[:_i7] + _c1[:-1] + _E[_mi:_s] + _c2[:-1] + _S0[_i38:]
# 後期段北端原本就沿東側（約 +33 m），往南改沿同一條東側線到併入點
_LT = X[_LTK][0]
X[_LTK][0] = _LT[:5] + _E[_near_ll(_E, _LT[5]):_mi + 1]
# 五甲鳳山線、牛寮三角線：原本越過道路接到西側；改為在東側線上截斷，端點落在主線上
def _trim(L, M, at_start):
    P = L[::-1] if at_start else L
    m = _LS([(q[1], q[0]) for q in M])
    for k in range(len(P) - 1):
        seg = _LS([(P[k][1], P[k][0]), (P[k + 1][1], P[k + 1][0])])
        x = seg.intersection(m)
        if not x.is_empty:
            x = x if x.geom_type == 'Point' else list(x.geoms)[0]
            out = P[:k + 1] + [[x.y, x.x]]
            return out[::-1] if at_start else out
    return L
_SM = X[_SMK][0]
X['糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）'][0] = _trim(X['糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）'][0], _SM, False)
X['糖鐵牛寮三角線（往籬仔內）'][0] = _trim(X['糖鐵牛寮三角線（往籬仔內）'][0], _SM, True)
# 鳳山線（臺灣製糖，鳳山—西門—二苓—工場，7.8 km，1909-10-05 開業；第 30 輪）。
# 1942 年二萬五千分一地形圖標「臺灣製糖鐵道」，自鳳山向南直行經牛寮、二苓（いれに）入後壁林工場；
# 1950、1955 年圖同線仍在（1955 年 AMS 圖標 Sugar Refinery Plant Railroad），1966 年圖上這段已被小港機場跑道切斷。
# 北段（鳳山—牛寮）就是現行五甲鳳山線的線形（OSM 廢線軌跡，與 1942、1955 年圖重合）；
# 南段（牛寮以南）現為機場用地，沒有現存路廊，依 1942、1950、1955 三張圖上同一條線的位置取點（三張圖彼此相差 ≤ 20 m）；
# 末段（二苓以南進工場）與籬仔內線末段同線。
_FS = X['糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）'][0]
_SM = X['糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）'][0]
def _near_i(L, q):
    return int(np.argmin([math.hypot((p[0] - q[0]) * 110540, (p[1] - q[1]) * 102800) for p in L]))
_j1 = _near_i(_FS, (22.58403, 120.34644))      # 五甲鳳山線在此往西南彎離南北向的舊線
_j2 = _near_i(_SM, (22.56552, 120.34558))      # 舊線在二苓南側併入籬仔內線末段
_FS_SOUTH = [(22.5800, 120.3464), (22.5760, 120.3463), (22.5720, 120.3463), (22.5700, 120.3463), (22.5680, 120.3460)]
X['糖鐵鳳山線（鳳山—二苓—小港糖廠）'] = [_FS[:_j1 + 1] + [list(p) for p in _FS_SOUTH] + _SM[_j2:]]
G['xy']['糖鐵鳳山線（鳳山—二苓—小港糖廠）'] = [1909, 1966]   # 1909-10-05 開業；1955 年圖仍有、1966 年圖已被跑道切斷
# 改用 1977 年臺糖小港糖廠鐵道路線圖（民國 66 年 6 月，1:100,000）的正式線名（第 31 輪）。
# 該圖：林園線 K0（工場）→ 三角線分岐 K3+046.50（A）→ 籬子內線分岐 K3+290.70（B）→ 佛公旗站 K3+431 → 牛寮旗站 → 鳳山 K10+911.10；
# 籬子內線自 B 起，K0+294（C）接三角線；三角線 A—C 長 326 m。
# 原圖上這三個點就是本圖原有的三角形：A→工場 2,871 m、A→B 171 m、B→C 339 m、A—C 324 m（對照 3,046／244／294／326 m），
# 所以「佛公三角線」不是漏畫，而是原本名為「牛寮三角線」的那一邊；舊的分段方式（籬仔內線含三角線一邊、五甲鳳山線含林園線一段）
# 與正式線名對不上，這裡依 1977 年圖重新分段：
#   林園線（小港糖廠—佛公—鳳山）= 工場→A→B→鳳山；籬子內線（籬仔內站—佛公）= 籬仔內→C→B；三角線（佛公）= C→A。
# 年份沿用原三線的 1955–1993（臺鐵「台糖籬仔內線」代用年份）。
def _len(L): return sum(math.hypot((L[i][0] - L[i + 1][0]) * 110540, (L[i][1] - L[i + 1][1]) * 102800) for i in range(len(L) - 1))
_SM = X.pop('糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）')[0]
_FS = X.pop('糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）')[0]
_NL = X.pop('糖鐵牛寮三角線（往籬仔內）')[0]
for _k in ('糖鐵籬仔內線（籬仔內站—前鎮河—小港糖廠）', '糖鐵五甲鳳山線（鳳山—五甲—籬仔內線分岐）', '糖鐵牛寮三角線（往籬仔內）'):
    G['xy'].pop(_k)
# 三角形本身依 1984 年都市計畫航測地形圖與 1989 年經建版重描：兩張圖上，自東而來的林園線過 B 後直行往西北，
# 到中山四路東側（C）併入沿路北上往籬仔內的線（＝籬子內線 B—C）；在 B 另以約 R 90 m 的弧線向南分出，
# 在 A 併入沿中山四路東側南下往工場的線（＝林園線 A—B）；C—A 沿中山四路東側的直線就是三角線。
# 舊線形的 B 是折角、A 是 27° 斜接、C 比兩張圖偏西北約 90 m（OSM 的 532707459／532707461 都不是兩張圖上的位置）。
# 重描：B 不動（與 1989 年圖相差約 18 m）；C 取兩張圖上的交會點投影到中山四路東側線上；
# A—B 為與 C—B、C—A 兩直線相切的圓弧（兩切線等長，切點即 B 與 A）；籬子內線在 C 以 R 100 m 曲線轉進中山四路側。
# 中山四路東側線在 22.579–22.584 一段改為直線（原為道路中心線平移後平滑，偏離直線 < 1 m），三條線在 A、C 共用同一節點。
def _arc(O, P, Q, step=4.0):
    a0, a1 = math.atan2(*(P - O)[::-1]), math.atan2(*(Q - O)[::-1])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi; r = np.hypot(*(P - O))
    n = max(2, int(abs(da) * r / step) + 1)
    return [O + r * np.array([math.cos(a0 + da * i / (n - 1)), math.sin(a0 + da * i / (n - 1))]) for i in range(n)]
_iB = _near_i(_FS, _NL[-1]); _Bm = toM(_FS[_iB])
_inb = [22.5790 <= p[0] <= 22.5840 for p in _SM]; _b0 = _inb.index(True); _b1 = len(_inb) - _inb[::-1].index(True)
assert all(_inb[_b0:_b1])
_band = np.array([toM(p) for p in _SM[_b0:_b1]])                     # 中山四路東側線，C—A 一段
_c0 = _band.mean(axis=0); _u1 = np.linalg.svd(_band - _c0)[2][0]
if _u1 @ (_band[-1] - _band[0]) < 0: _u1 = -_u1                     # 指向南（工場）
_dev = max(abs((v - _c0) @ np.array([-_u1[1], _u1[0]])) for v in _band)
_Cq = toM((22.5822, 120.3280))                                     # 1984 年圖 (22.58233, 120.32797)、1989 年圖 (22.58208, 120.32810) 的平均
_Cm = _c0 + ((_Cq - _c0) @ _u1) * _u1                               # 投影到中山四路東側線上
_t = float(np.hypot(*(_Bm - _Cm))); _dB = (_Bm - _Cm) / _t
_al = math.acos(float(np.clip(_u1 @ _dB, -1, 1)))                   # C 點兩邊夾角
_Am = _Cm + _t * _u1; _R = _t * math.tan(_al / 2)
_O = _Cm + _t / math.cos(_al / 2) * unit(_u1 + _dB)
_Rc = 100.0; _tc = _Rc * math.tan(_al / 2)                          # 籬子內線在 C 的曲線
_C1, _C2 = _Cm - _tc * _u1, _Cm + _tc * _dB
_Oc = _Cm + _Rc / math.cos(_al / 2) * unit(-_u1 + _dB)
_sl = lambda v: float((v - _c0) @ _u1)
_onl = lambda v: _c0 + _sl(v) * _u1
_bl = [_onl(v) for v in _band]
_N = [list(p) for p in _SM[:_b0]]; _Sx = [list(p) for p in _SM[_b1:]]
_pC, _pA = toLL(_C1), toLL(_Am)
_Nb = [toLL(v) for v in _bl if _sl(v) < _sl(_C1) - 1]
_Mb = [toLL(v) for v in _bl if _sl(_C1) + 1 < _sl(v) < _sl(_Am) - 1]
_Sb = [toLL(v) for v in _bl if _sl(v) > _sl(_Am) + 1]
_LYarc = [toLL(p) for p in _arc(_O, _Am, _Bm)]
_LZarc = [toLL(p) for p in _arc(_Oc, _C1, _C2)]
X['糖鐵林園線（小港糖廠—佛公—鳳山）'] = [(_Sb + _Sx)[::-1] + [_pA] + _LYarc[1:-1] + [list(p) for p in _FS[_iB::-1]]]
X['糖鐵籬子內線（籬仔內站—佛公）'] = [_N + _Nb + [_pC] + _LZarc[1:] + [list(_FS[_iB])]]
X['糖鐵三角線（佛公）'] = [[_pC] + _Mb + [_pA]]
print('佛公三角形：C', [round(float(v), 6) for v in toLL(_Cm)], 'A', [round(float(v), 6) for v in _pA], f'夾角 {math.degrees(_al):.1f}° R {_R:.0f} m 直線化偏移 {_dev:.2f} m',
      'A—B 弧', round(_len(_LYarc)), 'B—C(籬子內線至三角線接點)', round(_len([_pC] + _LZarc[1:] + [list(_FS[_iB])])),
      '三角線', round(_len(X['糖鐵三角線（佛公）'][0])), '（1977：244／294／326）')
for _k in ('糖鐵林園線（小港糖廠—佛公—鳳山）', '糖鐵籬子內線（籬仔內站—佛公）', '糖鐵三角線（佛公）'):
    G['xy'][_k] = [1955, 1994]   # 糖鐵本身年份未查到，以臺鐵「台糖籬仔內線」1955-03-01～1993-12-28 為準
print('1977 名稱分段 m:', {k[2:6]: round(_len(X[k][0])) for k in ('糖鐵林園線（小港糖廠—佛公—鳳山）', '糖鐵籬子內線（籬仔內站—佛公）', '糖鐵三角線（佛公）')})
# 林園線 鳳山—大寮、淡水線岔點、大寮三角線（第 31 輪；圖幅東界擴到 120.420）。
# 原為新興製糖「林仔邊線」（鳳山—林仔邊，18.24 km），1909-06-05 運輸營業（臺灣總督府府報第 2722 號，據中研院 GIS 中心
# 「地圖與遙測影像數位典藏計畫」〈高雄新興製糖株式會社之糖鐵路線〉；維基百科〈臺灣製糖〉林子邊線表同）；
# 1941 年新興製糖併入臺灣製糖，戰後為小港糖廠林園線（1977 年圖）。線形取 OSM 廢線軌跡（lyrail.json），
# 與 1942、1955、1966、1989 年圖逐段對過：鳳山—大寮四張圖都有；1993、2001 年經建版已無（1993 年圖同一路廊改為台 25 線）。
# 停用年份未查到 → 推定 1991 年底（1989 年圖有、1993 年圖無；另有鐵道愛好者部落格記「一直使用到 1990 年代才拆除」）。
# 鳳山站往東約 260 m 與鳥松線共線（1977 年圖鳥松線自林園線 K11+170.20 分出），這段取 OSM 鳥松線軌跡；鳥松線本身不畫。
# 淡水線：1977 年圖自林園線 K17+633.55 分出；大寮三角線連林園線 K17+946.10 與淡水線 K0+327.39（長 318.96 m）。
# 兩者在 1955、1966 年圖上都沒有、1977 年圖與 1989 年圖上有 → 啟用推定 1971（兩圖中間），停用與林園線同。
# 使用者只要求畫到大寮（含淡水線岔點），所以淡水線只畫到三角線接點以北一小段，林園線畫到圖幅東界附近（往南續行至林園，未畫）。
_LY = {e['id']: [[p['lat'], p['lon']] for p in e['geometry']] for e in json.load(open('lyrail.json'))['elements']}
_w = _LY[777724460][::-1]                      # 鳳山站 → 東
_k = _near_i(_w, _LY[532707462][0]); assert math.hypot(*np.subtract(toM(_w[_k]), toM(_LY[532707462][0]))) < 1
_e = _LY[532707464][:[p[1] > 120.4191 for p in _LY[532707464]].index(True)]   # 到轉向南行、貼近圖幅東界處為止
X['糖鐵林園線（鳳山—大寮）'] = [[list(_FS[0])] + _w[1:_k] + _LY[532707462] + _e[1:]]
_d = _LY[532707463]; _cum = 0.0; _ds = [_d[0]]
for _p, _q in zip(_d, _d[1:]):           # 取到 450 m（三角線接點在 K0+327）
    _s = math.hypot(*np.subtract(toM(_q), toM(_p)))
    if _cum + _s >= 450:
        _t = (450 - _cum) / _s; _ds.append([_p[0] + _t * (_q[0] - _p[0]), _p[1] + _t * (_q[1] - _p[1])]); break
    _cum += _s; _ds.append(_q)
X['糖鐵淡水線（大寮岔點段）'] = [_ds]
# 大寮三角線：OSM 軌跡（532707465）在 A′ 附近有 27° 折角，改以兩端分別與林園線（往東）、淡水線（往南）相切的曲線重描，端點不動。
_t3 = _LY[532707465]; _P3, _A3 = _t3[-1], _t3[0]
_jP = [i for i, p in enumerate(_ds) if p == _P3]; _jA = [i for i, p in enumerate(X['糖鐵林園線（鳳山—大寮）'][0]) if p == _A3]
assert _jP and _jA, (_jP, _jA)
_LYD = X['糖鐵林園線（鳳山—大寮）'][0]
_h3 = hermite(toM(_P3), _hd(_ds[_jP[0] + 1], _P3), toM(_A3), _hd(_A3, _LYD[_jA[0] + 1]))
X['糖鐵大寮三角線'] = [[list(_A3)] + [toLL(p) for p in _h3[::-1]][1:-1] + [list(_P3)]]
G['xy']['糖鐵林園線（鳳山—大寮）'] = [1909, 1992]   # 1909-06-05 開業；停用推定（1989 有、1993 無）
G['xy']['糖鐵淡水線（大寮岔點段）'] = [1971, 1992]  # 推定（1966 無、1977 有）
G['xy']['糖鐵大寮三角線'] = [1971, 1992]           # 同上
print('林園線鳳山—大寮 m:', round(_len(X['糖鐵林園線（鳳山—大寮）'][0])), '淡水線段:', round(_len(_ds)), '大寮三角線:', round(_len(_LY[532707465])))
# 圖幅（第 31 輪）：東界由 120.372 擴到 120.420（底圖、水域遮罩見 tiles.py、extend_base.py）。
G['bounds'] = [[22.548, 120.262], [22.68, 120.420]]
# 一般鐵路依年代（第 34 輪）——使用者：「我發現一般鐵路的路線沒有照時序顯示」。第 33 輪只依年份改了線名，線形沒動。
# (a) 1900–1907 的終點：打狗停車場（臨時停車場）在今鼓山一路 87 巷一帶，1908 年才遷到哈瑪星新生地（今高雄港站）。
#     位置取 1904 年臺灣堡圖（中研院 JM20K_1904）上的車站符號；堡圖上鐵路過站後再往西南約 450 m 到海邊的棧堤，
#     與今高雄港站一帶的路廊相合，所以 1900–1907 年西段線形不改，只換站位（tpl.html 的 STN），站場股道自 1908 年起才顯示。
G['st']['打狗停車場'] = [22.6265, 120.2786]
# (b) 1907–1940 的鳳山支線（往三塊厝）：1924 年五萬分一圖（JM50K_1924）、1942 年二萬五千分一圖上，
#     支線在打狗（高雄）驛北方約 1.3 km 處自縱貫線分出，直線往東北東到三塊厝；今日自鼓山站南側彎出、
#     以「高雄川橋」跨愛河到三塊厝的線，是 1941 年配合高雄新驛啟用新建的（英文維基 Gushan station：1941 年在田町站南側新設分岐；
#     自由時報 2026-06-04：1941 年配合縱貫線改道新建高雄川橋）。1942 年圖上新舊兩線並存，舊線在 1945 年美軍圖、1955 年 AMS 圖、
#     1956 年舊航照、1970 年 1:1200 圖、1976 年像片基本圖、1984／1986 年都市計畫圖、1989／1993 年經建版都還在
#     （第 34 輪誤判為 1970 年只剩虛線、1984 年已是道路，第 35 輪更正）；1998 年像片基本圖、2000 年 1:1000 圖已無。
#     網路討論（PTT Railway 板 2013-04-17）稱這段「高雄港=高雄」路廊 1995 年拆除，與地圖相符。舊線形依 1942 年圖取點：
_FSO_PTS = [(22.6342, 120.2843), (22.6351, 120.2857), (22.6357, 120.2870), (22.6361, 120.2882), (22.6370, 120.2900)]
_W, _Z = S['west'], S['zg_s']
_j = nearest_on((22.6335, 120.2826), _W)            # 分岐點：西段（往北為索引遞增）上
_J0 = _j[2]; _hJ = math.atan2(*_j[4][::-1])
_bm = [toM(p) for p in _FSO_PTS]
_ub = unit(_bm[-1] - _bm[1]); _hb = math.atan2(*_ub[::-1])
_m = nearest_on((22.6381, 120.2935), _Z)            # 併入點：1941 年新線上、三塊厝站西側
_iM = _m[1] + 1; _M = toM(_Z[_iM]); _hM = math.atan2(*unit(toM(_Z[_iM + 1]) - _M)[::-1])
_c1 = hermite(_J0, _hJ, _bm[1], _hb)
_c2 = hermite(_bm[-1], _hb, _M, _hM)
_W[:] = _W[:_j[1] + 1] + [toLL(_J0)] + _W[_j[1] + 1:]   # 分岐點插入西段，成為共用節點
S['fso'] = [toLL(_J0)] + [toLL(p) for p in _c1[1:]] + [toLL(p) for p in _bm[2:-1]] + [toLL(p) for p in _c2[:-1]] + [list(_Z[_iM])]
# 1907–1940：三塊厝以東沿用今線（1924、1942 年圖相同）。第 34 輪用 G['alt0'] 讓 zg_s 在 1941 年前只畫併入點以東，
# 但路段代碼仍是同一個、啟用年寫 1907，清單與提示框把 1941 年才有的彎線也標成 1907（第 36 輪使用者指出）。
# 改成在併入點拆成兩段：zgc＝鼓山分岐—高雄川橋—併入點（1941 起），zg_s＝併入點—三塊厝—高雄（1907 起）。
S['zgc'] = [list(p) for p in _Z[:_iM + 1]]
S['zg_s'] = [list(p) for p in _Z[_iM:]]
G['alt0'] = {}
# 台糖中心倉庫線（1962-12-01 開辦）的起點在第二臨港線（1977 年通車）上、6.8K 以南約 310 m。1962–1976 年第二臨港線還沒通，
# 這條側線不可能憑空存在：當時應自 6.8K（凱旋四路線）沿後來第二臨港線的路廊南下再分出，第二臨港線開通時沿用了這一段。
# 1962–1976 年改畫成由 6.8K 起、沿第二臨港線路廊到原分岐點再接側線（推定；第 36 輪 connect_check.py 查出 1962–1976 年孤立）。
_tk = '台糖中心倉庫線（推定）'
_s2 = S['s2']; _jt = nearest_on(X[_tk][0][0], _s2)
G['xalt0'] = {_tk: [[1962, 1977, [[list(p) for p in _s2[:_jt[1] + 1]] + [list(p) for p in X[_tk][0]]] + [list(P) for P in X[_tk][1:]]]]}
print('台糖中心倉庫線 1962–1976 自 6.8K 起的共用段 m:', round(_len(_s2[:_jt[1] + 1])), '分岐點距第二臨港線 m:', round(_jt[0], 2))
print('舊鳳山支線 m:', round(_len(S['fso'])), '分岐角', round(math.degrees(abs((_hb - _hJ + math.pi) % (2 * math.pi) - math.pi))), '°',
      '併入角', round(math.degrees(abs((_hM - _hb + math.pi) % (2 * math.pi) - math.pi))), '°')
# 6) stations & branch markers re-projected
lines =[v for k, v in S.items() if not k.startswith('lr')] + [p[0] for p in X.values()]
for n, p in list(G['st'].items()):
    best = min((nearest_on(p, L) for L in lines), key=lambda r: r[0])
    if best[0] < 40: G['st'][n] = toLL(best[2])
G['br'] = {'5.4K 中島線分歧': S['zd'][0], '6.8K 第二臨港線分歧': S['s2'][0],
           '前鎮橋（1955）': S['qzb'][1]}
json.dump(G, open('geo_v13.json', 'w'), separators=(',', ':'))
print({k: len(v) for k, v in S.items() if not k.startswith('lr')})
