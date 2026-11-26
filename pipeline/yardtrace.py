"""從 1:5000 像片基本圖描出站場股道。

python3 yardtrace.py IMG Z W N POLY OUT.json [OVERLAY.png]

IMG   nlsc.py 拼出的圖（縮放層級 Z，左上角經緯度 W、N）
POLY  站場範圍：JSON 的像素多邊形 [[x,y],...]，只在範圍內找股道
OUT   描出的股道，[[lat,lon],...] 的清單

做法：
1. 用 Sato 脊線濾波找出細的暗線（鐵路符號是帶橫刻的細黑線）；
2. 限定在站場範圍、排除粉紅色道路與藍色水域；
3. 細化成一像素寬的骨架，建成圖；
4. 反覆剪掉短的末端分支（鐵路符號的橫刻、文字筆畫）；
5. 剪掉兩條平行股道之間被橫刻連起來的短橋；
6. 把度數 2 的點串成線段，保留夠長的，用 RDP 簡化後轉成經緯度。
"""
import json
import math
import sys

import cv2
import networkx as nx
import numpy as np
from PIL import Image, ImageDraw
from skimage.draw import polygon as poly_fill
from skimage.feature import structure_tensor
from skimage.filters import sato
from skimage.morphology import remove_small_objects, skeletonize

SEL = 17      # 方向性斷開用的線段結構元素長度（px），比橫刻長、比股道短
SPUR = 14      # 末端分支短於此（px）就剪掉
BRIDGE = 16    # 兩個分岔點之間短於此、且與兩側走向近乎垂直的邊視為橫刻橋
KEEP = 45      # 最後保留的線段最短長度（px）


def rdp(P, eps):
    if len(P) < 3:
        return P
    a, b = np.array(P[0], float), np.array(P[-1], float)
    ab = b - a
    n = np.hypot(*ab) or 1.0
    d = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / n for p in P]
    i = int(np.argmax(d))
    if d[i] > eps:
        return rdp(P[:i + 1], eps)[:-1] + rdp(P[i:], eps)
    return [P[0], P[-1]]


def build_graph(sk):
    G = nx.Graph()
    ys, xs = np.nonzero(sk)
    S = set(zip(ys.tolist(), xs.tolist()))
    for y, x in S:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (y + dy, x + dx) in S:
                    G.add_edge((y, x), (y + dy, x + dx), w=math.hypot(dy, dx))
    # 8 連通在對角處會多出三角形，去掉對角邊讓骨架回到樹狀
    for y, x in list(G.nodes):
        for dy, dx in ((1, 1), (1, -1)):
            q = (y + dy, x + dx)
            if G.has_edge((y, x), q) and ((y + dy, x) in G and (y, x + dx) in G):
                G.remove_edge((y, x), q)
    return G


def prune_spurs(G, L):
    changed = True
    while changed:
        changed = False
        for n in [n for n in G.nodes if G.degree(n) == 1]:
            if n not in G or G.degree(n) != 1:
                continue
            path = [n]
            cur, prev = n, None
            while True:
                nb = [m for m in G.neighbors(cur) if m != prev]
                if len(nb) != 1 or G.degree(cur) > 2 and cur != n:
                    break
                prev, cur = cur, nb[0]
                path.append(cur)
                if G.degree(cur) != 2:
                    break
            if len(path) - 1 < L and G.degree(path[-1]) >= 3:
                G.remove_nodes_from(path[:-1])
                changed = True
    G.remove_nodes_from([n for n in list(G.nodes) if G.degree(n) == 0])


def chains(G):
    """把度數 2 的點串起來，回傳端點或分岔點之間的線段。"""
    key = [n for n in G.nodes if G.degree(n) != 2]
    seen = set()
    out = []
    for s in key:
        for nb in G.neighbors(s):
            e = frozenset((s, nb))
            if e in seen:
                continue
            path = [s, nb]
            seen.add(e)
            prev, cur = s, nb
            while G.degree(cur) == 2:
                nxt = [m for m in G.neighbors(cur) if m != prev][0]
                seen.add(frozenset((cur, nxt)))
                prev, cur = cur, nxt
                path.append(cur)
            out.append(path)
    # 純環
    for comp in nx.connected_components(G):
        if all(G.degree(n) == 2 for n in comp):
            c = list(nx.cycle_basis(G.subgraph(comp)))
            if c:
                out.append(c[0] + [c[0][0]])
    return out


def direction(path, k=8):
    a, b = np.array(path[0], float), np.array(path[min(k, len(path) - 1)], float)
    v = b - a
    return v / (np.hypot(*v) or 1)


def drop_bridges(G):
    """刪掉兩個分岔點之間、短而且與兩端其他邊近乎垂直的邊（橫刻把相鄰股道連起來）。"""
    removed = 0
    for path in chains(G):
        if len(path) > BRIDGE:
            continue
        a, b = path[0], path[-1]
        if G.degree(a) < 3 or G.degree(b) < 3:
            continue
        v = direction(path, len(path) - 1)
        others = []
        for end in (a, b):
            for nb in G.neighbors(end):
                if nb in path:
                    continue
                w = np.array(nb, float) - np.array(end, float)
                others.append(w / (np.hypot(*w) or 1))
        if others and max(abs(float(np.dot(v, w))) for w in others) < 0.6:
            G.remove_nodes_from(path[1:-1])
            if len(path) == 2 and G.has_edge(a, b):
                G.remove_edge(a, b)
            removed += 1
    return removed


def main():
    img, Z, W, N, poly, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]
    ov = sys.argv[7] if len(sys.argv) > 7 else None
    im = Image.open(img).convert('RGB')
    a = np.asarray(im).astype(float)
    R, Gc, B = a[..., 0], a[..., 1], a[..., 2]
    gray = a.mean(-1)
    pink = (R - Gc > 25) & (R > 170)
    water = (B - R > 25)
    mask = np.zeros(gray.shape, bool)
    P = json.load(open(poly))
    rr, cc = poly_fill([p[1] for p in P], [p[0] for p in P], gray.shape)
    mask[rr, cc] = True
    ridge = sato(gray / 255.0, sigmas=[0.8, 1.0], black_ridges=True)
    thr = np.percentile(ridge[mask], 80)
    line = (ridge > thr) & mask & ~pink & ~water
    # 鐵路符號的橫刻很長，會橫跨整束股道，所以不能只靠長度去掉。
    # 先用大尺度的結構張量求出每個位置股道的主方向，再用各方向的線段 opening
    # 判斷每個像素屬於哪個方向的線，只留下與主方向夾角 30° 以內的像素。
    m8 = line.astype(np.uint8)
    Arr, Arc, Acc = structure_tensor(line.astype(float), sigma=14, order='rc')
    # 梯度主方向的垂直方向就是線的走向（以 x 向右、y 向下的角度表示）
    theta_g = 0.5 * np.arctan2(2 * Arc, Acc - Arr)          # 梯度方向（相對 x 軸）
    dom = (np.degrees(theta_g) + 90) % 180                   # 線的走向
    keep = np.zeros(m8.shape, bool)
    for ang in np.arange(0, 180, 6):
        k = np.zeros((SEL, SEL), np.uint8)
        c = SEL // 2
        dx, dy = math.cos(math.radians(ang)) * c, math.sin(math.radians(ang)) * c
        cv2.line(k, (int(round(c - dx)), int(round(c - dy))), (int(round(c + dx)), int(round(c + dy))), 1, 1)
        o = cv2.morphologyEx(m8, cv2.MORPH_OPEN, k).astype(bool)
        diff = np.abs(((dom - ang) + 90) % 180 - 90)
        keep |= o & (diff < 30)
    line = remove_small_objects(keep, max_size=40)
    sk = skeletonize(line)
    G = build_graph(sk)
    prune_spurs(G, SPUR)
    for _ in range(3):
        if not drop_bridges(G):
            break
        prune_spurs(G, SPUR)
    def gridline(p):  # 圖幅的方格線與接邊線：完全正南北或正東西的直線
        ys = [q[0] for q in p]
        xs = [q[1] for q in p]
        return len(p) > 60 and (max(xs) - min(xs) <= 3 or max(ys) - min(ys) <= 3)
    segs = [p for p in chains(G) if len(p) >= KEEP and not gridline(p)]
    # 道路邊線：粉紅色道路的邊緣也是一條暗線，沿著道路邊的線段去掉
    near_pink = cv2.dilate(pink.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    segs = [p for p in segs if np.mean([near_pink[y, x] for y, x in p]) < 0.5]
    # 走向與周圍股道明顯不同的短線段（建物邊、橫刻殘段）去掉
    def angle(p):
        (y0, x0), (y1, x1) = p[0], p[-1]
        return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180
    info = [(p, angle(p), np.mean(p, axis=0), len(p)) for p in segs]
    kept = []
    for p, a, c, L in info:
        ws, ds = [], []
        for q, b, d, M in info:
            if q is p or np.hypot(*(c - d)) > 90:
                continue
            ws.append(M)
            ds.append(abs(((a - b) + 90) % 180 - 90))
        if L < 150 and ws and np.average(ds, weights=ws) > 35:
            continue
        kept.append(p)
    segs = kept
    n = 2 ** Z * 256
    ox = (W + 180) / 360 * n
    oy = (1 - math.asinh(math.tan(math.radians(N))) / math.pi) / 2 * n

    def ll(y, x):
        lon = (ox + x) / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (oy + y) / n))))
        return [round(lat, 7), round(lon, 7)]

    def smooth(p, k=3):  # 骨架有一像素的鋸齒，先做移動平均再簡化
        a = np.array(p, float)
        if len(a) <= 2 * k:
            return [tuple(q) for q in a]
        b = a.copy()
        for i in range(k, len(a) - k):
            b[i] = a[i - k:i + k + 1].mean(0)
        return [tuple(q) for q in b]
    res = [[ll(y, x) for y, x in rdp(smooth(p), 1.5)] for p in segs]
    json.dump(res, open(out, 'w'))
    print('segments', len(res), 'px total', sum(len(p) for p in segs))
    if ov:
        o = im.copy()
        d = ImageDraw.Draw(o)
        d.line([tuple(p) for p in P] + [tuple(P[0])], fill=(0, 120, 255), width=2)
        for p in segs:
            d.line([(x, y) for y, x in rdp(smooth(p), 1.5)], fill=(0, 200, 60), width=2)
        if len(sys.argv) > 8:   # 另疊現有幾何（紅色），檢查套合
            g = json.load(open(sys.argv[8]))
            def px(la, lo):
                return ((lo + 180) / 360 * n - ox, (1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * n - oy)
            for v in g['seg'].values():
                d.line([px(*q) for q in v], fill=(230, 0, 0), width=1)
        o.save(ov)


if __name__ == '__main__':
    main()
