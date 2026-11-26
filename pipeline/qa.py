"""Geometry QA: (1) offset from 1989 rail symbol, (2) overlaps/duplicates, (3) kinks & tight radii, (4) dangling ends."""
import json, math, sys, numpy as np
from scipy.ndimage import distance_transform_edt
from corr import ll2px
LAT0 = 22.62; KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
def M(p): return np.array([p[1] * KX, p[0] * KY])
MASK = np.load('dark2.npy'); DT = distance_transform_edt(~MASK) * 2.21   # metres
H, W = MASK.shape

def resample(L, step=2.0):
    P = np.array([M(p) for p in L]); seg = np.hypot(*np.diff(P, axis=0).T); c = np.concatenate([[0], np.cumsum(seg)])
    if c[-1] == 0: return P[:1], np.array([0.0])
    s = np.arange(0, c[-1], step); s = np.append(s, c[-1])
    return np.stack([np.interp(s, c, P[:, 0]), np.interp(s, c, P[:, 1])], 1), s

def toll(v): return (v[1] / KY, v[0] / KX)

def offset_check(name, L, thr=12, minlen=30):
    R, s = resample(L); d = []
    for v in R:
        x, y = ll2px(*toll(v)); xi, yi = int(round(x)), int(round(y))
        d.append(DT[yi, xi] if 0 <= xi < W and 0 <= yi < H else 0)
    d = np.array(d); k = 7; dm = np.array([np.median(d[max(0, i-k):i+k+1]) for i in range(len(d))])
    bad = dm > thr; out = []; i = 0
    while i < len(bad):
        if bad[i]:
            j = i
            while j < len(bad) and bad[j]: j += 1
            if s[j-1] - s[i] >= minlen: out.append((round(s[i]), round(s[j-1]), round(float(dm[i:j].max()), 1), toll(R[(i+j)//2])))
            i = j
        else: i += 1
    return out

def overlap_check(lines, thr=3.5, minlen=40, excl=60):
    res = []
    names = list(lines)
    samp = {n: resample(lines[n], 3)[0] for n in names}
    ends = {n: [M(lines[n][0]), M(lines[n][-1])] for n in names}
    for a in names:
        A = samp[a]
        for b in names:
            if a >= b: continue
            B = samp[b]
            # quick bbox reject
            if (A[:, 0].min() > B[:, 0].max() + thr or B[:, 0].min() > A[:, 0].max() + thr or
                A[:, 1].min() > B[:, 1].max() + thr or B[:, 1].min() > A[:, 1].max() + thr): continue
            from scipy.spatial import cKDTree
            t = cKDTree(B); dd, _ = t.query(A)
            close = dd < thr
            # exclude junction zones around shared endpoints
            for e in ends[a] + ends[b]:
                close &= np.hypot(*(A - e).T) > excl
            run = 0; best = 0; where = None
            for i, c in enumerate(close):
                run = run + 3 if c else 0
                if run > best: best = run; where = A[i]
            if best >= minlen: res.append((a, b, best, toll(where)))
    return res

def kink_check(name, L, win=8, maxturn=25, rmin=None):
    R, s = resample(L, 2.0); out = []
    if len(R) < 2 * win + 1: return out
    for i in range(win, len(R) - win):
        d1 = R[i] - R[i - win]; d2 = R[i + win] - R[i]
        n1, n2 = np.hypot(*d1), np.hypot(*d2)
        if not n1 or not n2: continue
        ang = math.degrees(math.acos(np.clip(d1 @ d2 / n1 / n2, -1, 1)))
        if ang > maxturn: out.append((round(s[i]), round(ang), toll(R[i])))
        elif rmin and ang > 0.5:
            r = (win * 2.0) / math.radians(ang)
            if r < rmin: out.append((round(s[i]), f'R≈{round(r)}m', toll(R[i])))
    # collapse neighbours
    col = []
    for o in out:
        if not col or o[0] - col[-1][0] > 20: col.append(o)
    return col

def dangling(lines, tol=1.0):
    res = []
    allp = {n: [M(p) for p in L] for n, L in lines.items()}
    def near_any(p, me):
        for n, P in allp.items():
            if n == me: continue
            A = np.array(P)
            # distance to polyline
            for i in range(len(A) - 1):
                a, b = A[i], A[i + 1]; d = b - a; l2 = d @ d or 1e-9
                t = np.clip((p - a) @ d / l2, 0, 1)
                if np.hypot(*(p - (a + d * t))) < tol: return n
        return None
    for n, L in lines.items():
        for end, p in (('start', L[0]), ('end', L[-1])):
            if near_any(M(p), n) is None: res.append((n, end, p))
    return res

if __name__ == '__main__':
    G = json.load(open(sys.argv[1])); S = G['seg']; X = G['extra']
    FROM89 = ['l1w', 'w0', 'w1', 'w2', 'w3', 'k4', 'e1', 'zd', 'ob', 'west',
              '205 兵工廠外側線（廠區北緣—凱得街）', '臺糖倉庫側線（臺鐵）', '成功路側線（臺鋁南側油槽區）', '臺肥三廠側線']
    print('== 與 1989 年圖鐵路符號的偏離（連續 >30 m、偏離 >12 m）')
    for n in FROM89:
        L = S.get(n) or X.get(n, [None])[0]
        for r in offset_check(n, L): print(' ', n, r)
    lines = {k: v for k, v in S.items() if not k.startswith('lr')}
    lines.update({k: v[0] for k, v in X.items()})
    print('== 重疊／重複（兩線相距 <3.5 m 連續 >40 m，排除接點 60 m 內）')
    for r in overlap_check(lines): print(' ', r)
    print('== 折角（16 m 弦內轉角 >25°）與小半徑（主線 R<80 m）')
    MAIN = {'west', 'l1w', 'w0', 'w1', 'w2', 'w3', 'k4', 'e1', 's2', 's2b', 'zd'}
    for n, L in lines.items():
        for r in kink_check(n, L, rmin=80 if n in MAIN else None): print(' ', n, r)
    print('== 懸空端點（未接到任何線）')
    for r in dangling(lines): print(' ', r)
