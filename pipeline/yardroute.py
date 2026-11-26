"""在描出的站場股道上找一條可行駛的路徑（給主線、支線穿過站場用）。

股道是 yardtrace.py 描出的片段，在轉轍器、圖幅接邊、文字壓住的地方會斷開。這裡把片段接成有方向的圖：
- 沿著同一片段前進；
- 在片段端點附近「跳」到另一片段（轉轍器分岐、斷開處）：跳躍距離 ≤ R，跳躍方向與前後股道的夾角都要小，
  所以不會走出折返或直角轉彎；每跳一次加罰 JUMP_COST，路徑盡量少換股。
跳躍處以三次 Hermite 曲線銜接（切線取前後股道方向）；找到的路徑用移動平均平滑，再以 RDP 簡化。

route(lines, anchors) -> [(lat, lon), ...]
  lines：股道（每條為 [(lat, lon), ...]）
  anchors：依序要經過的點（起點、途經點……終點），各點吸附到最近的股道上
"""
import heapq, math
import numpy as np
from scipy.spatial import cKDTree

LAT0, LON0 = 22.61, 120.30
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
STEP = 2.0          # 片段重新取樣間距（m）
R = 40.0            # 跳躍最大距離（m）
A_JUMP = math.radians(35)   # 跳躍方向與目前行進方向的最大夾角
A_TRACK = math.radians(45)  # 跳躍前後兩股方向的最大夾角（描線在股道匯集處常斷開，要容許轉向）
A_COST = 0.6       # 每度轉向的加罰（m）
JUMP_COST = 20.0
JUMP_K = 1.5        # 跳躍距離的權重（比沿股道走貴）


def to_xy(p):
    return ((p[1] - LON0) * KX, (p[0] - LAT0) * KY)


def to_ll(x, y):
    return (round(y / KY + LAT0, 7), round(x / KX + LON0, 7))


def resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        if d == 0:
            continue
        t = step - acc
        while t <= d:
            out.append((a[0] + (b[0] - a[0]) * t / d, a[1] + (b[1] - a[1]) * t / d))
            t += step
        acc = (acc + d) % step
    if math.dist(out[-1], pts[-1]) > step * .3:
        out.append(pts[-1])
    return out


def angdiff(a, b):
    d = abs(a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)


class Graph:
    def __init__(self, lines):
        self.ch = []
        for g in lines:
            xy = [to_xy(p) for p in g]
            if len(xy) < 2:
                continue
            xy = resample(xy, STEP)
            if len(xy) >= 2:
                self.ch.append(np.array(xy))
        self.pts, self.idx = [], []
        for c, a in enumerate(self.ch):
            for i in range(len(a)):
                self.pts.append(a[i])
                self.idx.append((c, i))
        self.pts = np.array(self.pts)
        self.tree = cKDTree(self.pts)

    def head(self, c, i, d):
        """片段 c 第 i 點、朝 d（+1/-1）方向的行進方位角。"""
        a = self.ch[c]
        j0, j1 = (max(0, i - 2), min(len(a) - 1, i + 2))
        v = a[j1] - a[j0]
        h = math.atan2(v[1], v[0])
        return h if d > 0 else h + math.pi

    def nbrs(self, s):
        c, i, d = s
        a = self.ch[c]
        j = i + d
        if 0 <= j < len(a):
            yield (c, j, d), STEP
        # 跳躍：從片段端點可跳到任何片段；從片段中間只能跳到另一片段的端點（轉轍器分岐）。
        # 片段之間的空隙最長 R，空隙越長、越偏離行進方向越不可能。
        at_end = (d > 0 and i >= len(a) - 2) or (d < 0 and i <= 1)
        h = self.head(c, i, d)
        p = a[i]
        for k in self.tree.query_ball_point(p, R):
            c2, j2 = self.idx[k]
            if c2 == c:
                continue
            b = self.ch[c2]
            end2 = j2 <= 1 or j2 >= len(b) - 2
            if not (at_end or end2):
                continue
            q = b[j2]
            v = q - p
            dist = float(np.hypot(*v))
            if dist > 0.5 and angdiff(math.atan2(v[1], v[0]), h) > A_JUMP:
                continue
            for d2 in (1, -1):
                da = angdiff(self.head(c2, j2, d2), h)
                if da < A_TRACK:
                    yield (c2, j2, d2), dist * JUMP_K + JUMP_COST + math.degrees(da) * A_COST

    def snap(self, p, rad=18.0):
        x, y = to_xy(p)
        ks = self.tree.query_ball_point((x, y), rad)
        if not ks:
            d, k = self.tree.query((x, y))
            raise ValueError(f'錨點 {p} 離股道 {d:.1f} m，超過 {rad} m')
        return ks, (x, y)

    def path(self, src_states, dst_keys, src_cost=None):
        dst = set(dst_keys)
        dist, prev, pq = {}, {}, []
        for s, c0 in src_states:
            dist[s] = c0
            heapq.heappush(pq, (c0, s))
        while pq:
            c0, s = heapq.heappop(pq)
            if c0 > dist.get(s, 1e18):
                continue
            if (s[0], s[1]) in dst:
                out = [s]
                while out[-1] in prev:
                    out.append(prev[out[-1]])
                return out[::-1], c0
            for t, w in self.nbrs(s):
                nc = c0 + w
                if nc < dist.get(t, 1e18):
                    dist[t] = nc
                    prev[t] = s
                    heapq.heappush(pq, (nc, t))
        raise ValueError('找不到路徑')


def smooth(xy, k=4):
    a = np.array(xy, float)
    if len(a) < 2 * k + 1:
        return a
    out = a.copy()
    for i in range(k, len(a) - k):
        out[i] = a[i - k:i + k + 1].mean(axis=0)
    return out


def rdp(a, eps):
    if len(a) < 3:
        return list(range(len(a)))
    s, e = a[0], a[-1]
    v = e - s
    n = np.hypot(*v) or 1
    w = a - s
    d = np.abs(v[0] * w[:, 1] - v[1] * w[:, 0]) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        l = rdp(a[:i + 1], eps)
        r = rdp(a[i:], eps)
        return l[:-1] + [x + i for x in r]
    return [0, len(a) - 1]


def route(lines, anchors, eps=0.4, snap=10.0):
    """依序經過各錨點的最短可行駛路徑。各段一起求解（狀態含「已經過第幾個錨點」），
    避免前一段停在無法續行的方向上。"""
    g = lines if isinstance(lines, Graph) else Graph(lines)
    keysets, anc = [], []
    for p in anchors:
        ks, xy = g.snap(p, snap)
        keysets.append(set(g.idx[k] for k in ks))
        anc.append(xy)
    last = len(anchors) - 1
    ks0, _ = g.snap(anchors[0], snap)
    dist, prev, pq = {}, {}, []
    for k in ks0:
        for d in (1, -1):
            st = (*g.idx[k], d, 0)
            c0 = 4 * float(np.hypot(*(g.pts[k] - anc[0])))
            dist[st] = c0
            heapq.heappush(pq, (c0, st))
    goal = None
    while pq:
        c0, s = heapq.heappop(pq)
        if c0 > dist.get(s, 1e18):
            continue
        c, i, d, leg = s
        if (c, i) in keysets[leg + 1]:
            if leg + 1 == last:
                goal = s
                break
            t = (c, i, d, leg + 1)
            if c0 < dist.get(t, 1e18):
                dist[t] = c0
                prev[t] = s
                heapq.heappush(pq, (c0, t))
        for (c2, j2, d2), w in g.nbrs((c, i, d)):
            t = (c2, j2, d2, leg)
            nc = c0 + w
            if nc < dist.get(t, 1e18):
                dist[t] = nc
                prev[t] = s
                heapq.heappush(pq, (nc, t))
    if goal is None:
        raise ValueError(f'錨點 {anchors} 之間找不到路徑')
    out = [goal]
    while out[-1] in prev:
        out.append(prev[out[-1]])
    full = []
    for st in out[::-1]:
        if not full or full[-1] != st[:3]:
            full.append(st[:3])
    # 跳躍處以三次 Hermite 曲線銜接（切線取前後股道方向），轉轍器與斷開處才會是圓順的曲線
    xy = [g.ch[full[0][0]][full[0][1]]]
    for s, t in zip(full, full[1:]):
        p1 = g.ch[t[0]][t[1]]
        if s[0] != t[0]:
            p0 = g.ch[s[0]][s[1]]
            L = float(np.hypot(*(p1 - p0)))
            if L > STEP:
                h0, h1 = g.head(*s), g.head(*t)
                m0 = L * np.array([math.cos(h0), math.sin(h0)])
                m1 = L * np.array([math.cos(h1), math.sin(h1)])
                for u in np.linspace(0, 1, max(2, int(L / STEP)) + 1)[1:-1]:
                    a = 2 * u ** 3 - 3 * u ** 2 + 1
                    b = u ** 3 - 2 * u ** 2 + u
                    c = -2 * u ** 3 + 3 * u ** 2
                    d = u ** 3 - u ** 2
                    xy.append(a * p0 + b * m0 + c * p1 + d * m1)
        xy.append(p1)
    sm = smooth(xy)
    keep = rdp(sm, eps)
    return [to_ll(*sm[i]) for i in keep], full
