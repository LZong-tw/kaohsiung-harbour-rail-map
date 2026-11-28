"""沿一條線取多道垂直軌道的剖面，數大比例尺圖上有幾條線、各離現在畫的線多遠，並把剖面轉正成長條圖並排。
底圖是中研院高雄百年歷史地圖（khh.py 的快取 hk/），圖不收進 repo：輸出一律寫到 /tmp/xsec/。

cd pipeline && python3 xsec.py OUTNAME LINE LAT_A LON_A LAT_B LON_B N [HALF_M] [YEAR] [LAYER]
環境變數：PPM（長條圖每公尺像素，預設 8）、LEN（上下各取幾公尺，預設 30）、SC（底圖放大倍數，預設 3）。
LINE 給 - 時，以 A→B 的直線為軸（站場沒有合適的線可沿時用）。

判讀規則（第 36 輪之十校準）：1984 年都市計畫航測地形圖上一條線是一股，橫刻跨過整束、兩端各超出約 1 m；
單線是一條線加橫刻，經尖岔變成兩條線就是分成兩股。輸出的「圖上線」是剖面上所有深色線（含牆、路緣），要對照長條圖只數有橫刻的。
LINE：seg 代碼或 extra 線名（取當年線形）。在 A、B 之間等距取 N 道剖面。
長條圖：軌道方向朝上（A→B），1 m = 8 px，左右各 HALF m，上下各 30 m；紅＝圖上深色線，藍＝現在畫的線。"""
import sys, json, math, subprocess, os
os.makedirs('/tmp/xsec', exist_ok=True)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
out, lname = sys.argv[1], sys.argv[2]
A = (float(sys.argv[3]), float(sys.argv[4])); B = (float(sys.argv[5]), float(sys.argv[6])); NN = int(sys.argv[7])
half = float(sys.argv[8]) if len(sys.argv) > 8 else 22.0
yr = int(sys.argv[9]) if len(sys.argv) > 9 else 1985
layer = sys.argv[10] if len(sys.argv) > 10 else 'Kaohsiung_1984'
import os
KX, KY = 102700.0, 110800.0; SC = float(os.environ.get('SC', 3.0)); PPM = int(os.environ.get('PPM', 8)); LEN = float(os.environ.get('LEN', 30.0)); ALONG = 14.0
G = json.load(open('geo_v13.json'))
lines = []
for k, v in G['seg'].items():
    if k.startswith('lr'): continue
    alt = [a for a in G.get('alt', {}).get(k, []) if a[0] <= yr < a[1]]
    lines.append((k, alt[0][2] if alt else v))
for k, parts in G['extra'].items():
    o, c = G['xy'].get(k, [0, 9999])
    if o <= yr < c:
        for part in parts: lines.append((k, part))
for grp in G['yards']:
    if (grp.get('o') or 0) <= yr < (grp.get('c') or 9999):
        for i, l in enumerate(grp['lines']): lines.append((f"股#{i}", l))
base = [L for k, L in lines if k == lname]
if lname == '-': base = [[[A[0] + (B[0] - A[0]) * i / 200, A[1] + (B[1] - A[1]) * i / 200] for i in range(201)]]
if not base: raise SystemExit('找不到線 ' + lname + '；可用：' + '、'.join(k for k, _ in lines if not k.startswith('股#'))[:1500])
base = max(base, key=len)
def near(L, p): return min(range(len(L)), key=lambda i: ((L[i][0] - p[0]) * KY) ** 2 + ((L[i][1] - p[1]) * KX) ** 2)
ia, ib = near(base, A), near(base, B)
seg = base[ia:ib + 1] if ia <= ib else base[ib:ia + 1][::-1]
cum = [0.0]
for a, b in zip(seg, seg[1:]): cum.append(cum[-1] + math.hypot((b[0] - a[0]) * KY, (b[1] - a[1]) * KX))
def at_len(s):
    for i in range(len(cum) - 1):
        if cum[i] <= s <= cum[i + 1] and cum[i + 1] > cum[i]:
            t = (s - cum[i]) / (cum[i + 1] - cum[i]); a, b = seg[i], seg[i + 1]
            L = cum[i + 1] - cum[i]
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), ((b[1] - a[1]) * KX / L, (b[0] - a[0]) * KY / L)
    return seg[-1], None
n = 2 ** 18 * 256
font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 12)
strips = []
print(f'== {out}：沿「{lname}」{cum[-1]:.0f} m 取 {NN} 道剖面（正值＝行進方向右側）')
for j in range(NN):
    s = cum[-1] * (j + 0.5) / NN
    (lat, lon), u = at_len(s)
    ux, uy = u; nx, ny = uy, -ux
    D = 0.0006; W, E, S, N = lon - D, lon + D, lat - D, lat + D
    tmp = '/tmp/xsec/_tmp.png'
    subprocess.run(['python3', 'khh.py', layer, '18', str(W), str(E), str(S), str(N), tmp], check=True, stdout=subprocess.DEVNULL)
    im0 = Image.open(tmp).convert('RGB'); im0 = im0.resize((int(im0.width * SC), int(im0.height * SC)), Image.LANCZOS)
    g = np.asarray(im0.convert('L')).astype(float)
    x0 = (W + 180) / 360 * n; y0 = (1 - math.asinh(math.tan(math.radians(N))) / math.pi) / 2 * n
    def px(la, lo): return (((lo + 180) / 360 * n - x0) * SC, ((1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * n - y0) * SC)
    def at(s_, d_): return px(lat + (uy * s_ + ny * d_) / KY, lon + (ux * s_ + nx * d_) / KX)
    ds = np.arange(-half, half + 0.05, 0.1); prof = []
    for d in ds:
        v = []
        for s_ in np.arange(-ALONG, ALONG + 0.01, 0.15):
            x, y = at(s_, d); xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < g.shape[1] and 0 <= yi < g.shape[0]: v.append(g[yi, xi])
        prof.append(255 - np.median(v) if v else 0)
    p = np.convolve(np.array(prof), np.ones(3) / 3, mode='same'); thr = 0.5 * np.percentile(p, 99); pk = []
    for i in range(1, len(p) - 1):
        if p[i] > thr and p[i] >= p[i - 1] and p[i] > p[i + 1]:
            if pk and ds[i] - pk[-1][0] < 0.9:
                if p[i] > pk[-1][1]: pk[-1] = (ds[i], p[i])
            else: pk.append((ds[i], p[i]))
    mine = []
    for k, L in lines:
        P = [((q[1] - lon) * KX, (q[0] - lat) * KY) for q in L]
        for a, b in zip(P, P[1:]):
            sa, sb = a[0] * ux + a[1] * uy, b[0] * ux + b[1] * uy
            if (sa <= 0 <= sb or sb <= 0 <= sa) and sa != sb:
                t = -sa / (sb - sa); d = (a[0] + t * (b[0] - a[0])) * nx + (a[1] + t * (b[1] - a[1])) * ny
                if abs(d) <= half: mine.append((round(d, 1), k))
    mine = sorted(set(mine))
    print(f'  [{j + 1}] {s:.0f} m ({lat:.5f},{lon:.5f}) 圖上線：', [round(float(a), 1) for a, _ in pk])
    print('       畫的線：', [(d, k[-8:]) for d, k in mine])
    sw, sh = int(2 * half * PPM), int(2 * LEN * PPM)
    strip = Image.new('RGB', (sw, sh + 52), 'white'); sp = strip.load(); src = im0.load()
    for jj in range(sh):
        s_ = LEN - jj / PPM
        for i in range(sw):
            x, y = at(s_, -half + i / PPM); xi, yi = int(round(x)), int(round(y))
            if 0 <= xi < im0.width and 0 <= yi < im0.height: sp[i, jj + 32] = src[xi, yi]
    dd = ImageDraw.Draw(strip)
    dd.text((2, 0), f'[{j + 1}] {s:.0f} m  {lat:.5f},{lon:.5f}', fill=(0, 0, 0), font=font)
    for a_, _ in pk: dd.line([((a_ + half) * PPM, 16), ((a_ + half) * PPM, 31)], fill=(255, 0, 0), width=2)
    for m_ in range(-int(half), int(half) + 1, 5):
        dd.line([((m_ + half) * PPM, 28), ((m_ + half) * PPM, 31)], fill=(0, 0, 0), width=1)
    for d_, k in mine:
        dd.line([((d_ + half) * PPM, sh + 34), ((d_ + half) * PPM, sh + 50)], fill=(0, 100, 255) if k.startswith('股#') else (255, 120, 0), width=3)
        dd.text(((d_ + half) * PPM + 3, sh + 36), k[2:5] if k.startswith('股#') else k[:2], fill=(0, 0, 0), font=font)
    strips.append(strip)
o = Image.new('RGB', (sum(i.width for i in strips) + 10 * len(strips), max(i.height for i in strips)), (190, 190, 190)); x = 0
for i in strips: o.paste(i, (x, 0)); x += i.width + 10
o.save(f'/tmp/xsec/{out}.png'); print(' ', f'/tmp/xsec/{out}.png', o.size)
