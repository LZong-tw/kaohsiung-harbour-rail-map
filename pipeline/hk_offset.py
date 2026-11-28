"""量 1984 年都市計畫航測地形圖（或別的 hk 圖層）相對於現有線形的橫向偏移。

沿指定的線每隔 STEP 公尺取一道剖面，找出剖面上「有橫刻跨過」的線（鐵路符號），列出它們相對現有線的橫向位置。
現有線若是依像片基本圖定的，這個位置就是該圖幅在這裡的橫向對位誤差（加上兩股並行時認哪一股的 ±2 m）。
底圖在 hk/ 快取，不收；結果印在畫面上，另存 /tmp/xsec/offset_<名稱>.tsv。

cd pipeline && python3 hk_offset.py LINE [STEP=60] [HALF=22] [YEAR=1985] [LAYER=Kaohsiung_1984] [LAT0 LAT1]
"""
import sys, json, math, subprocess, os
import numpy as np
from PIL import Image
os.makedirs('/tmp/xsec', exist_ok=True)
lname = sys.argv[1]
STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
HALF = float(sys.argv[3]) if len(sys.argv) > 3 else 22.0
yr = int(sys.argv[4]) if len(sys.argv) > 4 else 1985
layer = sys.argv[5] if len(sys.argv) > 5 else 'Kaohsiung_1984'
LAT0 = float(sys.argv[6]) if len(sys.argv) > 6 else -90
LAT1 = float(sys.argv[7]) if len(sys.argv) > 7 else 90
KX, KY, SC, ALONG = 102700.0, 110800.0, 3.0, 30.0
G = json.load(open('geo_v13.json'))
if lname in G['seg']:
    alt = [a for a in G.get('alt', {}).get(lname, []) if a[0] <= yr < a[1]]
    L = alt[0][2] if alt else G['seg'][lname]
else:
    L = G['extra'][lname][0]
cum = [0.0]
for a, b in zip(L, L[1:]): cum.append(cum[-1] + math.hypot((b[0] - a[0]) * KY, (b[1] - a[1]) * KX))
n = 2 ** 18 * 256
rows = []
s = STEP / 2
while s < cum[-1]:
    i = max(0, min(len(cum) - 2, int(np.searchsorted(cum, s)) - 1))
    t = (s - cum[i]) / ((cum[i + 1] - cum[i]) or 1e-9); a, b = L[i], L[i + 1]
    lat, lon = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
    ll = cum[i + 1] - cum[i] or 1e-9
    ux, uy = (b[1] - a[1]) * KX / ll, (b[0] - a[0]) * KY / ll; nx, ny = uy, -ux
    s += STEP
    if not (LAT0 <= lat <= LAT1): continue
    D = 0.0007; W, E, S, N = lon - D, lon + D, lat - D, lat + D
    tmp = '/tmp/xsec/_off.png'
    r = subprocess.run(['python3', 'khh.py' if layer.startswith('Kaohsiung') else 'nlsc.py', layer, '18', str(W), str(E), str(S), str(N), tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode: continue
    im = Image.open(tmp).convert('L'); im = im.resize((int(im.width * SC), int(im.height * SC)), Image.LANCZOS)
    g = 255 - np.asarray(im).astype(float)
    x0 = (W + 180) / 360 * n; y0 = (1 - math.asinh(math.tan(math.radians(N))) / math.pi) / 2 * n
    def val(sa, d):
        la = lat + (uy * sa + ny * d) / KY; lo = lon + (ux * sa + nx * d) / KX
        x = ((lo + 180) / 360 * n - x0) * SC; y = ((1 - math.asinh(math.tan(math.radians(la))) / math.pi) / 2 * n - y0) * SC
        xi, yi = int(round(x)), int(round(y))
        return g[yi, xi] if 0 <= xi < g.shape[1] and 0 <= yi < g.shape[0] else 0.0
    sa = np.arange(-ALONG, ALONG + 0.01, 0.2); ds = np.arange(-HALF, HALF + 0.05, 0.1)
    M = np.array([[val(x, d) for x in sa] for d in ds])          # [橫向, 沿線]
    prof = np.convolve(np.median(M, axis=1), np.ones(3) / 3, mode='same')
    INK = float(os.environ.get('INK', 0))      # 像片基本圖用：只認墨色的線（暗度門檻），底下的航照灰階不算
    thr = max(40.0, 0.5 * np.percentile(prof, 99), INK); pk = []
    for k in range(1, len(prof) - 1):
        if prof[k] > thr and prof[k] >= prof[k - 1] and prof[k] > prof[k + 1]:
            if pk and ds[k] - ds[pk[-1]] < 0.9:
                if prof[k] > prof[pk[-1]]: pk[-1] = k
            else: pk.append(k)
    tracks = []
    if os.environ.get('MODE') == 'dark':
        # 像片基本圖：鐵路符號是圖上最黑的細線。取 ±15 m 內最暗、寬度不到 3 m 的一條（橫刻太短，偵測不穩）
        cand = []
        for k in pk:
            if abs(ds[k]) > 15: continue
            hm = prof[k] * 0.6; l = k
            while l > 0 and prof[l] > hm: l -= 1
            r_ = k
            while r_ < len(prof) - 1 and prof[r_] > hm: r_ += 1
            if (r_ - l) * 0.1 <= 3.0: cand.append((prof[k], round(float(ds[k]), 1)))
        cand.sort(reverse=True)
        tracks = [(c[1], int(c[0])) for c in cand[:2]]
        pk = []
    for k in pk:
        # 橫刻：線兩側各 1.6 m 處，同一個沿線位置都是深色的短段
        k1, k2 = k - 16, k + 16
        if k1 < 0 or k2 >= len(ds): continue
        both = np.minimum(M[k1], M[k2]) > max(70.0, INK)
        runs = []; st = None
        for j, v in enumerate(both):
            if v and st is None: st = j
            if (not v or j == len(both) - 1) and st is not None:
                ln = (j - st) * 0.2
                if 0.2 <= ln <= 2.5: runs.append((st + j) / 2 * 0.2 - ALONG)
                st = None
        if len(runs) >= 2: tracks.append((round(float(ds[k]), 1), len(runs)))
    rows.append((round(s - STEP), round(lat, 5), round(lon, 5), round(math.degrees(math.atan2(ux, uy)) % 360), tracks))
out = open(f'/tmp/xsec/offset_{lname[:12]}.tsv', 'w')
print(f'== {lname}（{layer}）每 {STEP:.0f} m：里程 緯度 經度 方位  有橫刻的線（橫向位置 m，正值在行進方向右側；橫刻數）')
for r in rows:
    print(f'  {r[0]:5d} {r[1]:.5f} {r[2]:.5f} {r[3]:3d}°  {r[4]}')
    out.write('\t'.join(map(str, r[:4])) + '\t' + json.dumps(r[4]) + '\n')
