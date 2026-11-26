"""從大比例尺線劃地形圖（1970 年 1:1200 都市計畫航測地形圖）描出站場股道。

python3 yardtrace_line.py IMG Z W N POLY OUT.json [OVERLAY.png]

參數可用環境變數覆寫：YT_KW、YT_SIDE、YT_THR、YT_BAND（線條較細的圖，例如 1984 年都市計畫航測地形圖）。
POLY 為像素多邊形 [[x,y],...]，或 {"include": 多邊形, "exclude": [多邊形, ...]}（排除已知的道路邊、圍牆）。

這張圖的鐵路符號是兩條細軌線夾一串黑色枕木塊（全寬約 5 px，z18），相鄰股道中心約 11 px。
與像片基本圖的細線加橫刻不同，所以另寫一支：
1. 方向濾波：對每個方向 θ（每 3°），用 25×3 px 的長條核沿 θ 平均暗度。沿著股道走的長條會把黑塊與空隙
   平均成一條連續的帶；細的單線（道路邊、圍牆）因為只有 1 px 寬，平均後很淡。
2. 側向對比：股道兩側（垂直方向 ±5 px）是股道之間的白底；斜線填滿的建物兩側仍然是暗的。
   取「中心響應 − 兩側響應的較大者」作為股道強度，建物、文字因此被壓掉。
3. 垂直方向非極大值抑制，只留下帶子的中心線，門檻後細化成骨架；去掉圖幅方格線。
4. 沿用 yardtrace.py 的建圖、剪末端分支、串線段；去掉沿範圍邊界（多為道路邊）與走向和周圍明顯不同的短線段；
   去掉沿線 5 px 寬帶平均暗度低的單線（道路邊、圍牆、地界；股道符號有黑色枕木塊，暗度高）；
   平滑後以 RDP 簡化，轉成經緯度。
"""
import json, math, os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.draw import polygon as poly_fill
from skimage.morphology import skeletonize, remove_small_objects
from yardtrace import build_graph, prune_spurs, chains, rdp

KL, KW = 25, int(os.environ.get('YT_KW', 3))      # 方向核長、寬（px）
SIDE = float(os.environ.get('YT_SIDE', 5))   # 側向取樣距離（px）：相鄰股道之間白底的中央
STEP = 3            # 方向間隔（度）
THR = float(os.environ.get('YT_THR', 0.10))   # 股道強度門檻
BAND = float(os.environ.get('YT_BAND', 0.32))  # 沿線 5 px 寬帶的平均暗度下限
SPUR = 12
KEEP = 30


def kernel(theta):
    k = np.zeros((KL + 4, KL + 4), np.float32)
    c = (KL + 4) / 2 - .5
    dx, dy = math.cos(theta), math.sin(theta)
    nx, ny = -dy, dx
    for t in np.linspace(-KL / 2, KL / 2, KL * 3):
        for w in np.linspace(-KW / 2, KW / 2, KW * 3):
            x, y = c + dx * t + nx * w, c + dy * t + ny * w
            xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < k.shape[1] and 0 <= yi < k.shape[0]:
                k[yi, xi] = 1
    return k / k.sum()


def shift(a, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def main():
    img, Z, W, N, poly, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]
    ov = sys.argv[7] if len(sys.argv) > 7 else None
    im = Image.open(img).convert('RGB')
    gray = np.asarray(im).astype(np.float32).mean(-1)
    D = np.clip((235 - gray) / 200, 0, 1).astype(np.float32)
    mask = np.zeros(gray.shape, bool)
    P = json.load(open(poly))
    EX = []
    if isinstance(P, dict):       # {"include": 多邊形, "exclude": [多邊形, ...]}：排除已知的非股道線（道路邊、圍牆）
        P, EX = P['include'], P.get('exclude', [])
    rr, cc = poly_fill([p[1] for p in P], [p[0] for p in P], gray.shape)
    mask[rr, cc] = True
    for X in EX:
        rr, cc = poly_fill([p[1] for p in X], [p[0] for p in X], gray.shape)
        mask[rr, cc] = False
    best = np.full(gray.shape, -1, np.float32)
    bang = np.zeros(gray.shape, np.float32)
    for deg in range(0, 180, STEP):
        th = math.radians(deg)
        R = cv2.filter2D(D, -1, kernel(th))
        nx, ny = -math.sin(th), math.cos(th)
        side = np.maximum(shift(R, nx * SIDE, ny * SIDE), shift(R, -nx * SIDE, -ny * SIDE))
        S = R - side
        upd = S > best
        best[upd] = S[upd]
        bang[upd] = th
    # 垂直方向非極大值抑制
    ys, xs = np.nonzero((best > THR) & mask)
    nx, ny = -np.sin(bang[ys, xs]), np.cos(bang[ys, xs])
    keep = np.ones(len(ys), bool)
    H, Wd = best.shape
    for s in (1, 2):
        for sg in (1, -1):
            yy = np.clip(np.round(ys + sg * s * ny).astype(int), 0, H - 1)
            xx = np.clip(np.round(xs + sg * s * nx).astype(int), 0, Wd - 1)
            keep &= best[ys, xs] >= best[yy, xx]
    ridge = np.zeros(gray.shape, np.uint8)
    ridge[ys[keep], xs[keep]] = 1
    ridge = cv2.dilate(ridge, np.ones((2, 2), np.uint8))
    ridge = remove_small_objects(ridge.astype(bool), max_size=25)
    sk = skeletonize(ridge)
    G = build_graph(sk)
    prune_spurs(G, SPUR)
    def gridline(p):  # 圖幅方格線：完全正南北或正東西的直線
        ys = [q[0] for q in p]
        xs = [q[1] for q in p]
        return max(xs) - min(xs) <= 3 or max(ys) - min(ys) <= 3
    segs = [p for p in chains(G) if len(p) >= KEEP and not gridline(p)]
    # 沿著範圍邊界的線（範圍多沿道路邊畫，邊界附近的長直線多半是道路邊）
    edge = np.zeros(gray.shape, np.uint8)
    cv2.polylines(edge, [np.array(P, np.int32)], True, 1, 1)
    edge = cv2.dilate(edge, np.ones((17, 17), np.uint8)).astype(bool)
    segs = [p for p in segs if np.mean([edge[y, x] for y, x in p]) < 0.6]
    # 走向與周圍股道明顯不同的短線段（建物邊、道路邊、轉車台的放射線）
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
        if L < 150 and ws and np.average(ds, weights=ws) > 30:
            continue
        kept.append(p)
    segs = kept
    # 單線（道路邊、圍牆、地界）：沿線 5 px 寬帶內的平均暗度低；股道符號有黑色枕木塊，暗度高
    def band(p):
        acc = []
        for (y0, x0), (y1, x1) in zip(p, p[1:]):
            L = math.hypot(x1 - x0, y1 - y0) or 1
            nx, ny = -(y1 - y0) / L, (x1 - x0) / L
            for o in (-2, -1, 0, 1, 2):
                yy, xx = int(round(y0 + ny * o)), int(round(x0 + nx * o))
                if 0 <= yy < D.shape[0] and 0 <= xx < D.shape[1]:
                    acc.append(D[yy, xx])
        return float(np.mean(acc)) if acc else 0
    segs = [p for p in segs if band(p) >= BAND]
    n = 2 ** Z * 256
    ox = (W + 180) / 360 * n
    oy = (1 - math.asinh(math.tan(math.radians(N))) / math.pi) / 2 * n

    def ll(y, x):
        lon = (ox + x) / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (oy + y) / n))))
        return [round(lat, 7), round(lon, 7)]

    def smooth(p, k=3):
        a = np.array(p, float)
        if len(a) <= 2 * k:
            return [tuple(q) for q in a]
        b = a.copy()
        for i in range(k, len(a) - k):
            b[i] = a[i - k:i + k + 1].mean(0)
        return [tuple(q) for q in b]
    res = [[ll(y, x) for y, x in rdp(smooth(p), 1.0)] for p in segs]
    json.dump(res, open(out, 'w'))
    print('segments', len(res), 'px total', sum(len(p) for p in segs))
    if ov:
        o = im.copy()
        d = ImageDraw.Draw(o)
        d.line([tuple(p) for p in P] + [tuple(P[0])], fill=(0, 120, 255), width=2)
        for p in segs:
            d.line([(x, y) for y, x in rdp(smooth(p), 1.0)], fill=(0, 200, 60), width=2)
        o.save(ov)
        Image.fromarray((np.clip(best, 0, .4) / .4 * 255).astype(np.uint8)).save(ov.replace('.png', '_s.png'))


if __name__ == '__main__':
    main()
