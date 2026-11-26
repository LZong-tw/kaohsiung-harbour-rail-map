"""站場股道示意圖：把某一組股道（灰）、目前的主線與側線（彩色）畫在白底上，附像素格線，用來選路徑錨點。

python3 yarddiag.py GROUP X0 Y0 X1 Y1 SCALE OUT.png [BG.png]
  GROUP：G['yards'] 的組別序號；座標為高雄港站 z18 像素（左上角 120.2715, 22.6270）
  BG：可選的底圖（同一像素座標系的拼接圖），淡化後墊在下面
"""
import json, math, sys
from PIL import Image, ImageDraw

a = sys.argv[1:]
gi, X0, Y0, X1, Y1 = int(a[0]), *map(int, a[1:5])
s, out = float(a[5]), a[6]
bg = a[7] if len(a) > 7 else None
G = json.load(open('geo_v13.json'))
Z, W, N = 18, 120.2715, 22.6270


def xy(lon, lat):
    n = 2 ** Z
    return (lon + 180) / 360 * n * 256, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256


ox, oy = xy(W, N)
P = lambda p: ((xy(p[1], p[0])[0] - ox - X0) * s, (xy(p[1], p[0])[1] - oy - Y0) * s)
w, h = int((X1 - X0) * s), int((Y1 - Y0) * s)
if bg:
    im = Image.open(bg).convert('L').crop((X0, Y0, X1, Y1)).resize((w, h))
    im = Image.eval(im, lambda v: 150 + v * 105 // 255).convert('RGB')
else:
    im = Image.new('RGB', (w, h), 'white')
d = ImageDraw.Draw(im, 'RGBA')
for x in range((X0 // 50 + 1) * 50, X1, 50):
    d.line([((x - X0) * s, 0), ((x - X0) * s, h)], fill=(0, 0, 255, 40 if x % 100 else 90))
    if x % 100 == 0:
        d.text(((x - X0) * s + 2, 2), str(x), fill=(0, 0, 200))
for y in range((Y0 // 50 + 1) * 50, Y1, 50):
    d.line([(0, (y - Y0) * s), (w, (y - Y0) * s)], fill=(0, 0, 255, 40 if y % 100 else 90))
    if y % 100 == 0:
        d.text((2, (y - Y0) * s + 2), str(y), fill=(0, 0, 200))
for k, g in enumerate(G['yards'][gi]['lines']):
    d.line([P(p) for p in g], fill=(0, 0, 0, 255), width=2)
    x, y = P(g[len(g) // 2])
    if 0 < x < w and 0 < y < h:
        d.text((x + 2, y - 10), str(k), fill=(0, 140, 0))
for k, v in G['seg'].items():
    if k.startswith('lr'):
        continue
    d.line([P(p) for p in v], fill=(220, 0, 220, 120), width=5)
for k, parts in G['extra'].items():
    for v in parts:
        d.line([P(p) for p in v], fill=(255, 150, 0, 140), width=4)
for n, p in G['st'].items():
    x, y = P(p)
    d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=(255, 0, 0), width=2)
im.save(out)
print(out, im.size)
