"""沿一條線在像片基本圖上追鐵路符號（圖上最黑的連續細線），回報它相對現有線形的橫向位置。

為什麼另寫這支（第 36 輪之十三）：hk_offset.py 的 MODE=dark 只在 ±15 m 內找，而且每一道剖面各自判定。
線形錯超過 15 m 時它印出的是空的 []，看起來像「這裡沒有符號」，不是「這裡偏很多」——愛河鐵橋（w0）偏了 17–20 m、
苓雅寮北側彎道（w1 前 350 m）偏了 13 m，都是這樣漏掉的。這支在 ±HALF m（預設 45）內用動態規劃找一條連續的暗線，
所以偏很多也找得到；找不到（暗度不足）會標「弱」，和「有找到、偏 0」分得開。

cd pipeline && python3 pb_track.py LINE [LAYER=TOPO05KPHOTO_072] [YEAR=1985] [HALF=45] [STEP=10] [S0 S1]
  LINE：seg 代碼或 extra 線名（取 YEAR 當年的線形）；S0、S1：只量這段里程（公尺）。
輸出：每 100 m 一列（里程、位置、橫向位置的中位數與範圍、有符號的比例）；正值＝圖上的線在行進方向右側。
另存 /tmp/xsec/pbtrack_<LINE>_<LAYER>.tsv（每 STEP 一列）與 .jpg（紅點＝追到的線，洋紅＝現有線形）供目視確認。
只抓線兩側 HALF m 走廊內的圖磚（z18），不抓整個範圍：國土測繪圖資服務雲使用規範不許大量下載。
判讀：這是「最黑的連續細線」，行政界、道路邊線、字也可能被追到；凡是要據以改線的段落，先看 .jpg 確認追到的是鐵路符號。
"""
import sys, json, math, os, urllib.request
import numpy as np
from PIL import Image, ImageDraw
os.makedirs('/tmp/xsec', exist_ok=True)
lname = sys.argv[1]
layer = sys.argv[2] if len(sys.argv) > 2 else 'TOPO05KPHOTO_072'
yr = int(sys.argv[3]) if len(sys.argv) > 3 else 1985
HALF = float(sys.argv[4]) if len(sys.argv) > 4 else 45.0
STEP = float(sys.argv[5]) if len(sys.argv) > 5 else 10.0
S0 = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
S1 = float(sys.argv[7]) if len(sys.argv) > 7 else 1e9
KX, KY, Z, DK = 102700.0, 110800.0, 18, 0.5
G = json.load(open('geo_v13.json'))
if lname in G['seg']:
    alt = [a for a in G.get('alt', {}).get(lname, []) if a[0] <= yr < a[1]]
    L = alt[0][2] if alt else G['seg'][lname]
else:
    xa = [a for a in G.get('xalt', {}).get(lname, []) if a[0] <= yr < a[1]]
    L = xa[0][2] if xa else max(G['extra'][lname], key=len)
    if isinstance(L[0][0], list): L = max(L, key=len)
M = [(p[1] * KX, p[0] * KY) for p in L]
cum = [0.0]
for a, b in zip(M, M[1:]): cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
n = 2 ** Z
_T = {}
def tile(tx, ty):
    if (tx, ty) not in _T:
        f = f'n/{layer}/{Z}_{tx}_{ty}'; os.makedirs(f'n/{layer}', exist_ok=True)
        if not os.path.exists(f):
            try: open(f, 'wb').write(urllib.request.urlopen(f'https://wmts.nlsc.gov.tw/wmts/{layer}/default/GoogleMapsCompatible/{Z}/{ty}/{tx}', timeout=30).read())
            except Exception: open(f, 'wb').write(b'')
        try: _T[(tx, ty)] = np.asarray(Image.open(f).convert('RGB')).astype(float)
        except Exception: _T[(tx, ty)] = None
    return _T[(tx, ty)]
def ink(x, y):
    """(x, y) 公尺座標處的墨色暗度：灰階且暗才算，有顏色的（道路粉紅、水域青）算 0。"""
    lon, lat = x / KX, y / KY
    fx = (lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    t = tile(int(fx), int(fy))
    if t is None: return 0.0
    c = t[min(255, int((fy - int(fy)) * 256)), min(255, int((fx - int(fx)) * 256))]
    return 255.0 - c.sum() / 3 if c.max() - c.min() <= 45 else 0.0
def at(s):
    i = max(0, min(len(cum) - 2, int(np.searchsorted(cum, s)) - 1))
    t = (s - cum[i]) / ((cum[i + 1] - cum[i]) or 1e-9); a, b = M[i], M[i + 1]; d = (cum[i + 1] - cum[i]) or 1e-9
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
ds = np.arange(-HALF, HALF + 1e-6, DK); st = []; R = []; pos = []
s = max(S0, 0.0)
while s <= min(S1, cum[-1]):
    (x, y), (ux, uy) = at(s); nx, ny = uy, -ux                       # 行進方向右側
    prof = np.array([np.mean([ink(x + nx * d + ux * a, y + ny * d + uy * a) for a in (-4, -2, 0, 2, 4)]) for d in ds])
    w = int(3.0 / DK)                                                 # 細線才算：減掉兩側 3 m 處的暗度，壓掉大片的暗色（屋頂、陰影）
    ridge = prof.copy(); ridge[w:-w] = prof[w:-w] - 0.5 * (prof[:-2 * w] + prof[2 * w:]); ridge[:w] = 0; ridge[-w:] = 0
    R.append(np.clip(ridge, 0, None)); st.append(s); pos.append(((x, y), (nx, ny))); s += STEP
R = np.array(R); N_, K = R.shape
LAM, MAXJ = 3.0, int(3.0 / DK)
best = R[0].copy(); back = np.zeros((N_, K), int)
for i in range(1, N_):
    nb = np.full(K, -1e18)
    for j in range(-MAXJ, MAXJ + 1):
        sh = np.full(K, -1e18)
        if j >= 0: sh[j:] = best[:K - j] if j else best
        else: sh[:K + j] = best[-j:]
        sc = sh - LAM * j * j
        m = sc > nb; nb[m] = sc[m]; back[i][m] = np.arange(K)[m] - j
    best = nb + R[i]
k = int(np.argmax(best)); path = [k]
for i in range(N_ - 1, 0, -1): k = back[i][k]; path.append(k)
path = path[::-1]
rows = [(st[i], ds[path[i]], R[i][path[i]]) for i in range(N_)]
THR = float(os.environ.get('THR', 35))
tag = f'{lname[:14]}_{layer[-3:]}'
with open(f'/tmp/xsec/pbtrack_{tag}.tsv', 'w') as f:
    for (s, d, v), ((x, y), _) in zip(rows, pos): f.write(f'{s:.0f}\t{y / KY:.6f}\t{x / KX:.6f}\t{d:+.1f}\t{v:.0f}\n')
print(f'== {lname}（{layer}，{yr} 年線形，±{HALF:.0f} m）：里程 緯度,經度  橫向位置中位數［範圍］m  有符號的比例')
b0 = st[0]
while b0 <= st[-1]:
    blk = [(r, p) for r, p in zip(rows, pos) if b0 <= r[0] < b0 + 100]
    if blk:
        strong = [r[1] for r, _ in blk if r[2] >= THR]; (x, y), _ = blk[len(blk) // 2][1]
        if len(strong) >= max(2, len(blk) // 3):
            print(f'  {b0:5.0f} {y / KY:.5f},{x / KX:.5f}  {np.median(strong):+6.1f} [{min(strong):+.1f}…{max(strong):+.1f}]  {len(strong)}/{len(blk)}')
        else:
            print(f'  {b0:5.0f} {y / KY:.5f},{x / KX:.5f}     弱（找不到連續的暗線）  {len(strong)}/{len(blk)}')
    b0 += 100
# 轉正的長條圖：沿線方向朝右、行進方向左側在上，1 px = 0.5 m，每列 700 m；洋紅短線＝現有線形（中線），紅點＝追到的暗線
def rgb(x, y):
    lon, lat = x / KX, y / KY
    fx_ = (lon + 180) / 360 * n; fy_ = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    t = tile(int(fx_), int(fy_))
    return (255, 255, 255) if t is None else tuple(int(v) for v in t[min(255, int((fy_ - int(fy_)) * 256)), min(255, int((fx_ - int(fx_)) * 256))])
if os.environ.get('STRIP', '1') != '0':
    PX, ROWM = 0.5, 700.0; hh = int(HALF / PX); s_a, s_b = st[0], st[-1]
    nrow = int(math.ceil((s_b - s_a) / ROWM)) or 1; RW = int(ROWM / PX)
    sim = Image.new('RGB', (RW + 60, nrow * (2 * hh + 22)), (255, 255, 255)); sd = ImageDraw.Draw(sim)
    for r in range(nrow):
        y0 = r * (2 * hh + 22) + 14
        for c in range(RW):
            s_ = s_a + r * ROWM + c * PX
            if s_ > s_b: break
            (x, y), (ux, uy) = at(s_); nx, ny = uy, -ux
            for j in range(-hh, hh):
                sim.putpixel((c + 50, y0 + hh + j), rgb(x + nx * j * PX, y + ny * j * PX))
            if int(s_ / PX) % 12 < 4: sim.putpixel((c + 50, y0 + hh), (255, 0, 255))
            if abs(s_ % 100) < PX / 2:
                sd.line([(c + 50, y0 - 4), (c + 50, y0)], fill=(0, 0, 0)); sd.text((c + 52, y0 - 13), f'{s_:.0f}', fill=(0, 0, 0))
        sd.text((2, y0 + 2), f'左 -{HALF:.0f}', fill=(0, 0, 0)); sd.text((2, y0 + 2 * hh - 12), f'右 +{HALF:.0f}', fill=(0, 0, 0))
    for (s_, d, v) in rows:
        if v >= THR and int(s_) % 20 == 0:
            r = min(nrow - 1, int((s_ - s_a) // ROWM)); c = int(((s_ - s_a) - r * ROWM) / PX); y0 = r * (2 * hh + 22) + 14
            Y = y0 + hh + int(d / PX); sd.ellipse([c + 48, Y - 2, c + 52, Y + 2], outline=(255, 0, 0))
    sim.save(f'/tmp/xsec/pbstrip_{tag}.png'); print(f'  長條圖 /tmp/xsec/pbstrip_{tag}.png {sim.size}')
# 疊圖：走廊圖磚拼起來，縮到長邊 2400 px
xs = [p[0][0] + p[1][0] * d for p in pos for d in (-HALF, HALF)]; ys = [p[0][1] + p[1][1] * d for p in pos for d in (-HALF, HALF)]
W_, E_, S_, N__ = min(xs) / KX, max(xs) / KX, min(ys) / KY, max(ys) / KY
fx = lambda lon: (lon + 180) / 360 * n; fy = lambda lat: (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
tx0, tx1, ty0, ty1 = int(fx(W_)), int(fx(E_)), int(fy(N__)), int(fy(S_))
if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) <= 900:
    im = Image.new('RGB', ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), (255, 255, 255))
    for (tx, ty), t in _T.items():
        if t is not None: im.paste(Image.fromarray(t.astype('uint8')), ((tx - tx0) * 256, (ty - ty0) * 256))
    d_ = ImageDraw.Draw(im); P = lambda x, y: ((fx(x / KX) - tx0) * 256, (fy(y / KY) - ty0) * 256)
    d_.line([P(*m) for m in M], fill=(255, 0, 255), width=1)
    for (s, d, v), ((x, y), (nx, ny)) in zip(rows, pos):
        if v >= THR:
            X, Y = P(x + nx * d, y + ny * d); d_.ellipse([X - 2, Y - 2, X + 2, Y + 2], outline=(255, 0, 0))
    im.save(f'/tmp/xsec/pbtrack_{tag}.png'); print(f'  疊圖 /tmp/xsec/pbtrack_{tag}.png {im.size}')
