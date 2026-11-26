"""把目前的主線、側線與站場股道疊到像片基本圖上，檢查站場內的線有沒有重疊、斜穿股道。

python3 yardov.py IMG Z W N OUT.png [SCALE] [YEAR] [GEO]
  IMG：nlsc.py 拼好的圖（左上角為 W, N，縮放層級 Z）
  YEAR：只畫該年顯示的線（主線依 tpl.html 的 SEG 年份，側線依 G['xy']，股道依 G['yards']）
主線紫、支線橘、側線黃、股道青；座標格每 100 px（原圖像素）標一次。
"""
import json, math, re, sys
from PIL import Image, ImageDraw

a = sys.argv[1:]
src, Z, W, N, out = a[0], int(a[1]), float(a[2]), float(a[3]), a[4]
s = float(a[5]) if len(a) > 5 else 1
Y = int(a[6]) if len(a) > 6 else None
G = json.load(open(a[7] if len(a) > 7 else 'geo_v13.json'))


def xy(lon, lat):
    n = 2 ** Z
    return (lon + 180) / 360 * n * 256, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256


ox, oy = xy(W, N)
P = lambda la, lo: ((xy(lo, la)[0] - ox) * s, (xy(lo, la)[1] - oy) * s)
im = Image.open(src).convert('RGB')
im = im.resize((int(im.width * s), int(im.height * s)))
d = ImageDraw.Draw(im, 'RGBA')

tpl = open('tpl.html', encoding='utf-8').read()
segy = {i: (int(o), int(c), k) for i, k, o, c in re.findall(r"\{id:'(\w+)'.*?k:'(\w+)',o:(\d+),c:(\d+)", tpl)}
on = lambda o, c: Y is None or (o <= Y < c)

for gr in G['yards']:
    o, c = gr.get('o'), gr.get('c')
    if Y is not None and o is not None and not on(o, c):
        continue
    for g in gr['lines']:
        d.line([P(*p) for p in g], fill=(0, 200, 220, 200), width=2)
for k, parts in G['extra'].items():
    o, c = G['xy'].get(k, (0, 9999))[:2]
    if not on(o, c):
        continue
    for v in parts:
        d.line([P(*p) for p in v], fill=(240, 200, 0, 220), width=3)
for k, v in G['seg'].items():
    o, c, kind = segy.get(k, (0, 9999, 'main'))
    if k.startswith('lr') or not on(o, c):
        continue
    d.line([P(*p) for p in v], fill=(255, 140, 0, 230) if kind in ('br', 'unc') else (200, 0, 200, 230), width=4)
    x, y = P(*v[len(v) // 2])
    d.text((x + 4, y), k, fill=(200, 0, 0))
for x in range(0, im.width, 100):
    d.text((x, 2), str(int(x / s)), fill=(255, 0, 0))
for y in range(0, im.height, 100):
    d.text((2, y), str(int(y / s)), fill=(255, 0, 0))
im.save(out)
print(out, im.size)
