"""產生比對用的裁切圖（存進 scratch/，附出處列）。

python3 figcrop.py LAYER Z W E S N OUT.jpg [--year Y] [--scale S] [--overlay solid|dotted|none] [--geo geo_v13.json] [--note 文字]

LAYER 可用：
  TOPO05KPHOTO_xxx   國土測繪中心 1/5000 像片基本圖（民國 xxx 年），圖磚經 nlsc.py 的快取 n/LAYER/
  其他               中研院「臺灣百年歷史地圖」圖層，經 hist.py 的快取 h/LAYER/（CC BY-NC）

不支援中研院「高雄百年歷史地圖」（hk/）：該服務標示「中央研究院版權所有，非經允許，不得作為商業使用」，
疊圖不收進 repo，檢查時另外放 /tmp。

出處列的依據：
  國土測繪圖資服務雲使用規範（maps.nlsc.gov.tw/pro/use_clause.jsp）第 2 條：可在網路、論文發表等合法用途中
  公開顯示內容並附上來源資訊，但不得大量下載內容；第 9 條：不得改變、移除或遮蔽識別資料或版權聲明。
  所以只收裁切後的比對圖，圖磚快取不收（n/ 已列入 .gitignore）。
"""
import argparse
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('layer'); ap.add_argument('z', type=int)
ap.add_argument('W', type=float); ap.add_argument('E', type=float); ap.add_argument('S', type=float); ap.add_argument('N', type=float)
ap.add_argument('out')
ap.add_argument('--year', type=int, default=None)
ap.add_argument('--scale', type=float, default=1.0)
ap.add_argument('--overlay', default='dotted')
ap.add_argument('--geo', default='geo_v13.json')
ap.add_argument('--note', default='')
a = ap.parse_args()

if a.layer.startswith('Kaohsiung_'):
    raise SystemExit('高雄百年歷史地圖的疊圖不收進 repo（版權所有），請改放 /tmp')

tmp = f'/tmp/figcrop_{os.getpid()}.png'
if a.layer.startswith('TOPO05KPHOTO_'):
    subprocess.run(['python3', 'nlsc.py', a.layer, str(a.z), str(a.W), str(a.E), str(a.S), str(a.N), tmp], check=True,
                   stdout=subprocess.DEVNULL)
    roc = int(a.layer.split('_')[1])
    src = f'底圖：內政部國土測繪中心 1/5000 像片基本圖 民國 {roc} 年（{roc + 1911}）'
else:
    ext = 'jpg' if a.layer in ('JM20K_1904', 'JM25K_1921', 'JM50K_1924', 'TM25K_1989', 'TM25K_1993', 'TM25K_2001') else 'png'
    subprocess.run(['python3', 'hist.py', a.layer, ext, str(a.z), str(a.W), str(a.E), str(a.S), str(a.N), tmp], check=True,
                   stdout=subprocess.DEVNULL)
    src = f'底圖：中央研究院人社中心「臺灣百年歷史地圖」{a.layer}（CC BY-NC）'
img = Image.open(tmp).convert('RGB')
os.remove(tmp)

n = 2 ** a.z * 256
def px(lat, lon):
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x0 = (a.W + 180) / 360 * n
    y0 = (1 - math.asinh(math.tan(math.radians(a.N))) / math.pi) / 2 * n
    return (x - x0) * a.scale, (y - y0) * a.scale

if a.scale != 1:
    img = img.resize((int(img.width * a.scale), int(img.height * a.scale)), Image.LANCZOS)

legend = ''
if a.overlay != 'none':
    G = json.load(open(a.geo))
    yr = a.year
    d = ImageDraw.Draw(img, 'RGBA')
    def parts(v):
        return [v] if isinstance(v[0][0], (int, float)) else v
    L = []
    for k, v in G['seg'].items():
        alt = G.get('alt', {}).get(k)
        if yr is not None and alt:
            for o, c, g in alt:
                if o <= yr < c:
                    v = g
        L.append(((255, 0, 255, 210), v))
    for k, v in G['extra'].items():
        o, c = G['xy'].get(k, [0, 9999])
        if yr is None or o <= yr < c:
            L.append(((255, 120, 0, 230), v))
    for y in G.get('yards', []):
        if y.get('o') is not None and (yr is None or y['o'] <= yr < y['c']):
            for l in y['lines']:
                L.append(((0, 160, 255, 200), l))
    w = max(2, int(round(2 * a.scale))) if a.scale >= 1 else 2
    for col, vv in L:
        for v in parts(vv):
            P = [px(p[0], p[1]) for p in v]
            if a.overlay == 'dotted':
                for i in range(0, len(P) - 1, 2):
                    d.line([P[i], P[i + 1]], fill=col, width=w)
            else:
                d.line(P, fill=col, width=w)
    legend = f'洋紅：本研究的主線、支線；橘：側線、糖鐵；藍：站場股道（{"全部年份" if yr is None else f"{yr} 年顯示者"}）'

font = None
for f in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
          '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'):
    if os.path.exists(f):
        font = ImageFont.truetype(f, 18)
        break
if font is None:
    font = ImageFont.load_default()
lines = [src, f'範圍 {a.W:.4f}–{a.E:.4f}°E，{a.S:.4f}–{a.N:.4f}°N，z{a.z}']
if legend:
    lines.append(legend)
if a.note:
    lines.append(a.note)
bar = 8 + 26 * len(lines)
out = Image.new('RGB', (img.width, img.height + bar), 'white')
out.paste(img, (0, 0))
d = ImageDraw.Draw(out)
for i, t in enumerate(lines):
    d.text((8, img.height + 4 + 26 * i), t, fill=(0, 0, 0), font=font)
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
out.save(a.out, quality=82)
print(a.out, out.size)
