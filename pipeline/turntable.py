"""轉車台與放射股道（第 29 輪）。

python3 turntable.py IMG Z W N X Y OUT.json [OVERLAY.png|-] [TRACKS.json] [CAPS.json]
  IMG：拼接圖（左上角 W, N，縮放層級 Z）；X, Y：轉車台的大約像素位置
  TRACKS：同一張圖描出的股道；放射股道碰到斜交的股道就截斷（不會穿過旁邊的股道束）
  CAPS：{"角度": 最遠半徑 px}，依原圖目視量取的長度上限（自動偵測在建物、股道束處會越界）

1. 在 (X, Y) 周圍 ±20 px、半徑 12–26 px 內窮舉，取「圓周暗度 − 圈內暗度」最大的圓（Hough 會被放射股道的匯聚處騙走）；
2. 從圓心往外每 0.5° 取一條射線，量圓外 4～28 px 的平均暗度。放射股道（扇形股道）的符號在射線上
   連續偏暗，取暗度的局部極大（相鄰至少 5°）當股道方向，再在 ±3° 內依圓外 10～70 px 的暗度微調（股道不一定精確指向圓心）；
3. 每條股道沿射線往外延伸，到連續 10 px「不像單獨一條股道」為止：中心不比白底暗，或（離圓 25 px 後）兩側也一樣暗
   （走進斜線填滿的建物或整束股道）。最長 110 px（約 60 m），碰到斜交的描線股道也停；
4. 輸出圓心經緯度、半徑（公尺）與各放射股道（圓周上一點到外端）。
"""
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString

MAXLEN = 110  # 放射股道最長（px，z18 約 60 m）
STOP = 10


def main():
    a = sys.argv[1:]
    img, Z, W, N, X, Y, out = a[0], int(a[1]), float(a[2]), float(a[3]), float(a[4]), float(a[5]), a[6]
    ov = a[7] if len(a) > 7 and a[7] != '-' else None
    trk = json.load(open(a[8])) if len(a) > 8 else []
    caps = {float(k): v for k, v in json.load(open(a[9])).items()} if len(a) > 9 else {}
    im = Image.open(img).convert('RGB')
    g = np.asarray(im.convert('L'))
    x0, y0 = int(X) - 90, int(Y) - 90
    D = np.clip((235 - g.astype(float)) / 200, 0, 1)
    # 轉車台的符號是細圓圈、圈內留白：在猜測位置 ±20 px、半徑 12–26 px 內窮舉，
    # 取「圓周暗度 − 圈內暗度」最大者（Hough 會被放射股道匯聚處騙走）
    best = None
    ang = np.linspace(0, 2 * np.pi, 120, endpoint=False)
    for cy_ in range(int(Y) - 20, int(Y) + 21):
        for cx_ in range(int(X) - 20, int(X) + 21):
            for r_ in range(12, 27):
                ring = D[np.round(cy_ + np.sin(ang) * r_).astype(int), np.round(cx_ + np.cos(ang) * r_).astype(int)]
                inner = D[np.round(cy_ + np.sin(ang) * r_ * .6).astype(int), np.round(cx_ + np.cos(ang) * r_ * .6).astype(int)]
                sc = ring.mean() - inner.mean() - ring.std() * .5
                if best is None or sc > best[0]:
                    best = (sc, cx_, cy_, r_)
    _, cx, cy, r = best
    cx, cy, r = float(cx), float(cy), float(r)

    def ray(deg, r0, r1):
        t = math.radians(deg)
        vals = []
        for s in np.arange(r0, r1, 1.0):
            px, py = cx + math.cos(t) * s, cy + math.sin(t) * s
            # 垂直方向取 3 px 平均，對準股道符號的寬度
            nx, ny = -math.sin(t), math.cos(t)
            v = [D[int(round(py + ny * o)), int(round(px + nx * o))] for o in (-1, 0, 1)]
            vals.append(np.mean(v))
        return np.array(vals)

    # 只看圓外 4～28 px：這一圈內放射股道彼此分得開，也還沒碰到旁邊的股道
    step = 0.5
    degs = np.arange(0, 360, step)
    prof = np.array([ray(d, r + 4, r + 28).mean() for d in degs])
    base = np.median(prof)
    bg = float(np.median(D[int(cy) - 120:int(cy) + 120, int(cx) - 120:int(cx) + 120]))
    peaks = []
    for i, d in enumerate(degs):
        v = prof[i]
        if v < base + 0.1:
            continue
        w = [prof[(i + k) % len(degs)] for k in range(-6, 7)]
        if v < max(w):
            continue
        if peaks and min(abs(d - peaks[-1][0]), 360 - abs(d - peaks[-1][0])) < 5:
            if v > peaks[-1][1]:
                peaks[-1] = (d, v)
            continue
        peaks.append((d, v))
    if len(peaks) > 1 and 360 - (peaks[-1][0] - peaks[0][0]) < 5:
        peaks.pop() if peaks[-1][1] < peaks[0][1] else peaks.pop(0)
    peaks = [d for d, _ in peaks]
    n = 2 ** Z * 256
    ox = (W + 180) / 360 * n
    oy = (1 - math.asinh(math.tan(math.radians(N))) / math.pi) / 2 * n

    def ll(x, y):
        return [round(math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (oy + y) / n)))), 7),
                round((ox + x) / n * 360 - 180, 7)]
    def px(p):
        return ((p[1] + 180) / 360 * n - ox, (1 - math.asinh(math.tan(math.radians(p[0]))) / math.pi) / 2 * n - oy)
    trkpx = [LineString([px(p) for p in g]) for g in trk if len(g) > 1]
    mpp = 156543.03392 * math.cos(math.radians(ll(cx, cy)[0])) / 2 ** Z
    spokes = []
    for d in peaks:
        d0 = d
        # 放射股道不一定精確指向圓心：在 ±3° 內找圓外 10～70 px 平均暗度最大的方向
        d = max(np.arange(d - 3, d + 3.01, 0.25), key=lambda a_: ray(a_, r + 10, r + 70).mean())
        thr = bg + 0.08     # 以圖面白底為準（圓周附近股道密集，不能用射線的中位數）
        # 往外走：中心要暗於白底，而且離圓 25 px 以後，中心要比兩側（垂直 ±5 px）明顯暗——
        # 走進斜線填滿的建物或整束股道時兩側也暗，就停。連續 STOP px 不符合就停。
        t = math.radians(d)
        nx, ny = -math.sin(t), math.cos(t)
        L, low = 0, 0
        for i, s_ in enumerate(np.arange(r + 2, r + 2 + MAXLEN, 1.0)):
            px_, py_ = cx + math.cos(t) * s_, cy + math.sin(t) * s_
            c_ = np.mean([D[int(round(py_ + ny * o)), int(round(px_ + nx * o))] for o in (-1, 0, 1)])
            side = max(np.mean([D[int(round(py_ + ny * o)), int(round(px_ + nx * o))] for o in (k, k + sg)])
                       for k, sg in ((5, 1), (-5, -1)))
            bad = c_ < thr or (s_ > r + 25 and c_ - side < 0.05 and side > thr)
            low = low + 1 if bad else 0
            if low >= STOP:
                break
            L = i
        L = max(0, L - STOP + 1)
        if L < 10:
            continue
        t = math.radians(d)
        p0 = (cx + math.cos(t) * r, cy + math.sin(t) * r)
        p1 = (cx + math.cos(t) * (r + 2 + L), cy + math.sin(t) * (r + 2 + L))
        # 碰到斜交（> 20°）的股道就截斷
        sp = LineString([(cx + math.cos(t) * (r + 6), cy + math.sin(t) * (r + 6)), p1])
        cut = r + 2 + L
        for g in trkpx:
            if not sp.intersects(g):
                continue
            x = sp.intersection(g)
            for q in getattr(x, 'geoms', [x]):
                if q.geom_type != 'Point':
                    continue
                dd = g.project(q)
                a1, a2 = g.interpolate(max(0, dd - 3)), g.interpolate(min(g.length, dd + 3))
                ga = math.atan2(a2.y - a1.y, a2.x - a1.x)
                if abs((ga - t + math.pi / 2) % math.pi - math.pi / 2) > math.radians(20):
                    cut = min(cut, math.hypot(q.x - cx, q.y - cy) - 2)
        cap = [v for k, v in caps.items() if min(abs(k - d0), 360 - abs(k - d0)) <= 2.5]
        if cap:
            cut = min(cut, cap[0])
        if cut - r < 10:
            continue
        p1 = (cx + math.cos(t) * cut, cy + math.sin(t) * cut)
        spokes.append([ll(*p0), ll(*p1)])
    res = {'center': ll(cx, cy), 'r_m': round(r * mpp, 1), 'spokes': spokes, 'px': [round(cx, 1), round(cy, 1), round(r, 1)]}
    json.dump(res, open(out, 'w'))
    print('circle', res['px'], 'r', res['r_m'], 'm, spokes', len(spokes), 'at', peaks)
    if ov:
        o = im.crop((x0 - 40, y0 - 40, x0 + 220, y0 + 220)).resize((780, 780))
        dr = ImageDraw.Draw(o)
        s = 3
        P = lambda x, y: ((x - x0 + 40) * s, (y - y0 + 40) * s)
        dr.ellipse([*P(cx - r, cy - r), *P(cx + r, cy + r)], outline=(255, 0, 0), width=3)
        for sp in spokes:
            pts = []
            for la, lo in sp:
                x = (lo + 180) / 360 * n - ox
                y = (1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * n - oy
                pts.append(P(x, y))
            dr.line(pts, fill=(0, 180, 0), width=3)
        o.save(ov)


if __name__ == '__main__':
    main()
