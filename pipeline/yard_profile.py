"""站場橫剖面：沿一條線每隔 STEP 公尺取一道橫剖面，在像片基本圖上找並行股道（暗線）各自離這條線多遠。

為什麼寫這支（第 36 輪之十七）：pb_track.py 只追一條最黑的線，站場裡六、七股並行時量不出每一股的位置；
鼓山站場各股要用 parallel（沿縱貫線平移）畫，需要每一股的側距和起迄。

cd pipeline && python3 yard_profile.py LINE（seg 代碼、側線名，或 '緯,經;緯,經' 座標串） [LAYER=TOPO05KPHOTO_072] [YEAR=1983] [S0 S1] [STEP=50] [HALF=35]
輸出：每道剖面一列，列出暗線峰值的側距（公尺，正＝行進方向右側）。剖面沿線方向取 ±12 m 平均，枕木符號（垂直於軌道的短線）會被平均掉。
判讀：道路邊線、圍牆、字也會成峰；要對照 figcrop.py 的裁切圖。只抓剖面涵蓋的圖磚。
"""
import sys, json, math, os, urllib.request
import numpy as np
from PIL import Image
a = sys.argv
lname = a[1]; layer = a[2] if len(a) > 2 else 'TOPO05KPHOTO_072'; yr = int(a[3]) if len(a) > 3 else 1983
S0 = float(a[4]) if len(a) > 4 else 0.0; S1 = float(a[5]) if len(a) > 5 else 1e9
STEP = float(a[6]) if len(a) > 6 else 50.0; HALF = float(a[7]) if len(a) > 7 else 35.0
KX, KY, Z = 102700.0, 110800.0, 18
G = json.load(open('geo_v13.json'))
if ';' in lname:      # 也可以直接給座標：'緯,經;緯,經;…'（站場股道沒有線名時用）
    L = [[float(v) for v in q.split(',')] for q in lname.split(';')]
elif lname in G['seg']:
    alt = [r for r in G.get('alt', {}).get(lname, []) if r[0] <= yr < r[1]]; L = alt[0][2] if alt else G['seg'][lname]
else:
    L = max(dict(G['extra'])[lname] if isinstance(G['extra'], list) else G['extra'][lname], key=len)
M = [(p[1] * KX, p[0] * KY) for p in L]
cum = [0.0]
for p, q in zip(M, M[1:]): cum.append(cum[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
n = 2 ** Z; _T = {}
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
    lon, lat = x / KX, y / KY
    fx = (lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    t = tile(int(fx), int(fy))
    if t is None: return 0.0
    c = t[min(255, int((fy - int(fy)) * 256)), min(255, int((fx - int(fx)) * 256))]
    return 255.0 - c.sum() / 3 if c.max() - c.min() <= 45 else 0.0
def at(s):
    i = max(0, min(len(cum) - 2, int(np.searchsorted(cum, s)) - 1))
    d = (cum[i + 1] - cum[i]) or 1e-9; t = (s - cum[i]) / d; p, q = M[i], M[i + 1]
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), ((q[0] - p[0]) / d, (q[1] - p[1]) / d)
offs = np.arange(-HALF, HALF + 0.01, 0.5)
print(f'== {lname}（{layer}）：里程 緯度,經度  各暗線的側距 m（正＝右側）')
s = S0
while s <= min(S1, cum[-1]):
    prof = np.zeros(len(offs)); k = 0
    for ds in np.arange(-12, 12.1, 1.5):
        if not 0 <= s + ds <= cum[-1]: continue
        (x, y), (ux, uy) = at(s + ds); nx, ny = uy, -ux
        prof += np.array([ink(x + nx * o, y + ny * o) for o in offs]); k += 1
    prof /= max(k, 1); base = np.median(prof)
    pk = [float(offs[i]) for i in range(1, len(offs) - 1) if prof[i] >= prof[i - 1] and prof[i] > prof[i + 1] and prof[i] - base > 28]
    mg = []
    for o in pk:
        if mg and o - mg[-1] < 2.0: continue
        mg.append(o)
    (x, y), _ = at(s)
    print(f'{s:7.0f} {y / KY:.5f},{x / KX:.5f}  ' + ' '.join(f'{o:+.1f}' for o in mg))
    s += STEP
