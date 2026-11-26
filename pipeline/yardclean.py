"""站場股道描線的雜訊過濾（第 29 輪）。

自動描線會留下一些不是股道的短線：建物或圍牆的轉角（鋸齒狀）、道路邊線、文字筆畫。
它們的共同點是「孤立」：股道一定接在別的股道上（轉轍器），或與鄰股平行成束；雜訊多半兩頭都不接任何東西。

clean(lines, mains=()) -> (kept, dropped)
  lines：一組股道 [[lat, lon], ...]
  mains：同一範圍內的主線、支線、側線（股道接在它們上面也算有接）
  dropped：[(線, 原因), ...]

步驟：
  1. 鋸齒：整條的轉角總和每 10 m 超過 40°（圍牆、建物輪廓）→ 整條去掉。
  2. 其餘在急轉（> 45°）處切開：描線常在端點勾出一小段，切掉後保留主體；短於 12 m 的碎段去掉。
  3. 確定是股道：長於 ISO_LEN，或任一端接上走向相近（夾角 < 30°）的股道或主線：端點貼著另一股（≤ 3 m，轉轍器），
     或與另一股之間 ENDR 內的空隙順著行進方向（斷開處）。
  4. 與「已確定是股道」的線在 BUNDLE 內平行（夾角 < 15°）的短段也留下（一束股道中被切斷的一段）；反覆到不再增加。
     只拿已確定的線當依據，所以兩條互相平行的道路邊線不會互相保住。
  5. 其餘（孤立的短線）去掉。
"""
import math
import numpy as np
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

LAT0, LON0 = 22.61, 120.30
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
ISO_LEN = 70.0     # m
ENDR = 10.0        # m
BUNDLE = 13.0      # m（站場內相鄰股道中心距約 5–8 m，描線常隔一股才有）
MIN_PIECE = 12.0   # m
TURN_PER_10M = 40.0
KINK = 45.0


def _xy(g):
    return [((p[1] - LON0) * KX, (p[0] - LAT0) * KY) for p in g]


def _head(ls, d):
    a = ls.interpolate(max(0, d - 3))
    b = ls.interpolate(min(ls.length, d + 3))
    return math.atan2(b.y - a.y, b.x - a.x)


def _ang(a, b):
    d = abs(a - b) % math.pi
    return min(d, math.pi - d)


def split_kinks(g):
    """在急轉處切開，回傳各段。"""
    P = _xy(g)
    if len(P) < 3:
        return [g]
    cut = [0]
    for i in range(1, len(P) - 1):
        a = math.atan2(P[i][1] - P[i - 1][1], P[i][0] - P[i - 1][0])
        b = math.atan2(P[i + 1][1] - P[i][1], P[i + 1][0] - P[i][0])
        if math.degrees(abs((b - a + math.pi) % (2 * math.pi) - math.pi)) > KINK:
            cut.append(i)
    cut.append(len(P) - 1)
    return [g[a:b + 1] for a, b in zip(cut, cut[1:]) if b > a]


def zigzag(ls):
    pts = np.array(ls.coords)
    if len(pts) < 3 or ls.length < 1:
        return False
    v = np.diff(pts, axis=0)
    h = np.arctan2(v[:, 1], v[:, 0])
    t = np.abs((np.diff(h) + np.pi) % (2 * np.pi) - np.pi)
    return np.degrees(t.sum()) / ls.length * 10 > TURN_PER_10M


def _connected(i, ls, allg, tree):
    for end, d in ((Point(ls.coords[0]), 0.0), (Point(ls.coords[-1]), ls.length)):
        h = _head(ls, d)
        for j in tree.query(end.buffer(ENDR)):
            if j == i:
                continue
            o = allg[j]
            dist = o.distance(end)
            if dist > ENDR or _ang(h, _head(o, o.project(end))) >= math.radians(30):
                continue
            # 接上：端點貼著另一股（轉轍器，橫距 ≤ 3 m），或兩段之間的空隙順著行進方向（斷開處）。
            # 兩條平行、相隔幾公尺的線（例如道路兩側的邊線）不算接上。
            if dist <= 3:
                return True
            q = o.interpolate(o.project(end))
            if _ang(h, math.atan2(q.y - end.y, q.x - end.x)) < math.radians(25):
                return True
    return False


def clean(lines, mains=()):
    pieces, dropped = [], []
    for g in lines:
        if zigzag(LineString(_xy(g))):        # 整條就是鋸齒（圍牆、建物輪廓）：整條去掉，不切開
            dropped.append((g, '鋸齒'))
            continue
        for q in split_kinks(g):
            if LineString(_xy(q)).length >= MIN_PIECE:
                pieces.append(q)
            else:
                dropped.append((q, '碎段'))
    L = [LineString(_xy(g)) for g in pieces]
    allg = L + [LineString(_xy(g)) for g in mains]
    tree = STRtree(allg)
    status = [None] * len(L)
    for i, ls in enumerate(L):
        if zigzag(ls):
            status[i] = '鋸齒'
        elif ls.length >= ISO_LEN or _connected(i, ls, allg, tree):
            status[i] = 'ok'
    changed = True
    while changed:
        changed = False
        for i, ls in enumerate(L):
            if status[i] is not None:
                continue
            mid = ls.interpolate(0.5, normalized=True)
            h = _head(ls, ls.length / 2)
            for j in tree.query(mid.buffer(BUNDLE)):
                if j == i or j >= len(L) or status[j] != 'ok':
                    continue
                o = allg[j]
                if o.distance(mid) <= BUNDLE and _ang(h, _head(o, o.project(mid))) < math.radians(15):
                    status[i] = 'ok'
                    changed = True
                    break
    kept = [pieces[i] for i, st in enumerate(status) if st == 'ok']
    dropped += [(pieces[i], st or '孤立') for i, st in enumerate(status) if st != 'ok']
    return kept, dropped
