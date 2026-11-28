"""各條線在各版像片基本圖上有沒有畫：沿線每 10 m 在 ±3 m 內找暗的細線，回報找得到的比例。
用途（第 36 輪之十六）：中島各股、站場各組的年份原本整組相同，用這個看每一股在 1976、1983、1989、1998、2009 年版上是否出現。
限制：像片基本圖會把多股並行簡化成一兩條，所以「比例低」不等於那一股不存在；「比例高」才是正面證據。相鄰兩股相距不到 4 m 時會互相借到對方的線。
cd pipeline && python3 pb_presence.py 關鍵字 [關鍵字…]   （比對 extra 線名與站場組來源；seg 用代碼）"""
import sys, json, math, os, urllib.request
import numpy as np
from PIL import Image
KX, KY, Z = 102700.0, 110800.0, 18; n = 2 ** Z; _T = {}
def tile(layer, tx, ty):
    k = (layer, tx, ty)
    if k not in _T:
        f = f'n/{layer}/{Z}_{tx}_{ty}'; os.makedirs(f'n/{layer}', exist_ok=True)
        if not os.path.exists(f):
            try: open(f, 'wb').write(urllib.request.urlopen(f'https://wmts.nlsc.gov.tw/wmts/{layer}/default/GoogleMapsCompatible/{Z}/{ty}/{tx}', timeout=30).read())
            except Exception: open(f, 'wb').write(b'')
        try: _T[k] = np.asarray(Image.open(f).convert('RGB')).astype(float)
        except Exception: _T[k] = None
    return _T[k]
def ink(layer, x, y):
    lon, lat = x / KX, y / KY; fx = (lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    t = tile(layer, int(fx), int(fy))
    if t is None: return 0.0
    c = t[min(255, int((fy - int(fy)) * 256)), min(255, int((fx - int(fx)) * 256))]
    return 255.0 - c.sum() / 3 if c.max() - c.min() <= 45 else 0.0
def presence(L, layer):
    M = [(p[1] * KX, p[0] * KY) for p in L]; hit = tot = 0
    for a, b in zip(M, M[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d < 1e-6: continue
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d; nx, ny = uy, -ux
        for s in np.arange(0, d, 10.0):
            x, y = a[0] + ux * s, a[1] + uy * s
            pr = [np.mean([ink(layer, x + nx * k + ux * t, y + ny * k + uy * t) for t in (-3, 0, 3)]) for k in np.arange(-9, 9.01, 0.5)]
            c = max(pr[12:25]); side = 0.5 * (min(pr[0:8]) + min(pr[29:37]))     # 中間 ±3 m 的最暗值，減兩側 5–9 m 的背景
            tot += 1; hit += (c - side) >= 35
    return hit / tot if tot else float('nan'), tot
if __name__ == '__main__':
    G = json.load(open('geo_v13.json')); EDS = [('065', 1976), ('072', 1983), ('078', 1989), ('087', 1998), ('098', 2009)]
    items = []
    for kw in sys.argv[1:]:
        if kw in G['seg']: items.append((kw, G['seg'][kw]))
        for k, v in G['extra'].items():
            if kw in k:
                for i, part in enumerate(v): items.append((k[:26] + (f'#{i}' if i else ''), part))
        for g in G['yards']:
            if kw in g['src']:
                for i, l in enumerate(g['lines']): items.append((f"{g['src'][:22]}[{g.get('o')}–{g.get('c')}]#{i}", l))
    print('線'.ljust(44), ' '.join(str(y) for _, y in EDS), ' 取樣點')
    for name, L in items:
        r = [presence(L, 'TOPO05KPHOTO_' + e) for e, _ in EDS]
        print(name.ljust(44), ' '.join(f'{int(round(p * 100)):3d}%' for p, _ in r), f' {r[0][1]}')
