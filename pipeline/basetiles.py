"""把網頁底圖 base.jpg 切成圖磚（z12～z15），輸出到 ../site/t/{z}/{x}/{y}.webp。

python3 basetiles.py [base.jpg]

原本底圖是一張 2563×3332 的大圖，用 L.imageOverlay 放在地圖上。放大到 z17 時這張圖會被
撐到一萬多像素寬，超過許多瀏覽器與手機 GPU 的單張貼圖上限，縮放時底圖跟不上線條、畫面卡頓。
改成標準圖磚後，每次只畫看得到的 256×256 小圖；z16、z17 由 Leaflet 放大 z15 的圖磚
（maxNativeZoom 15），解析度與原本相同。

base.jpg 的左上角是 120.262°E、22.680°N，像素對齊 z15 的全球像素格（誤差小於半像素）。
"""
import math
import os
import shutil
import sys

from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else 'base.jpg'  # 網頁用的灰階底圖（由 base.png 轉成）
OUT = '../site/t'
W, N, Z0 = 120.262, 22.680, 15


def gx(lon, z):
    return (lon + 180) / 360 * 2 ** z * 256


def gy(lat, z):
    return (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2 ** z * 256


base = Image.open(SRC).convert('L')
alpha = Image.new('L', base.size, 255)  # 底圖範圍以外透明，深色模式下才不會多出一圈色塊
shutil.rmtree(OUT, ignore_errors=True)
count = 0
for z in range(12, Z0 + 1):
    s = 2 ** (z - Z0)
    size = (round(base.width * s), round(base.height * s))
    im = base if s == 1 else base.resize(size, Image.LANCZOS)
    al = alpha if s == 1 else alpha.resize(size, Image.NEAREST)
    x0, y0 = round(gx(W, z)), round(gy(N, z))
    tx0, ty0 = x0 // 256, y0 // 256
    tx1, ty1 = (x0 + im.width - 1) // 256, (y0 + im.height - 1) // 256
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            tile = Image.new('LA', (256, 256), (0, 0))
            tile.paste(Image.merge('LA', (im, al)), (x0 - tx * 256, y0 - ty * 256))
            os.makedirs(f'{OUT}/{z}/{tx}', exist_ok=True)
            tile.convert('RGBA').save(f'{OUT}/{z}/{tx}/{ty}.webp', quality=80, method=6)
            count += 1
print('tiles', count)
