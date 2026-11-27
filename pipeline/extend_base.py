"""把專案 z15 框架往東擴（第 31 輪：林園線畫到大寮）。

框架左上角仍是 120.262°E、22.680°N，南界不變，東界由 120.372°E 擴到 E。舊範圍的像素一律保留原值，
只補上新的東側條帶：

- base.png：直接從 base_full.png（tiles.py，OSM z15）裁出新框架。
- base.jpg：網頁用灰階底圖。舊範圍沿用原檔；新條帶以 base.png 灰階值經查表轉換。查表由舊範圍
  （同一像素的 base.png 灰階值 → base.jpg 值，取中位數）建立，讓新條帶與舊底圖色調一致。
- water.npy：水域遮罩。舊範圍沿用原檔；新條帶依 OSM 水域顏色（#aad3df，容差 12）判定。
  在舊範圍上用同一規則重算，與原遮罩的一致率會印出來供檢查。

    python3 extend_base.py [E]
"""
import math, sys
import numpy as np
from PIL import Image

E = float(sys.argv[1]) if len(sys.argv) > 1 else 120.420
Z = 15


def xy(lon, lat):
    n = 2 ** Z
    return (lon + 180) / 360 * n * 256, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256


OX, OY = xy(120.262, 22.680)
fX, fY = xy(120.258, 22.682)                      # base_full.png 的左上角
old = Image.open('base.png').convert('RGB')
H, W0 = old.height, old.width
W1 = round(xy(E, 22.680)[0] - OX)
full = Image.open('base_full.png').convert('RGB')
new = full.crop((round(OX - fX), round(OY - fY), round(OX - fX) + W1, round(OY - fY) + H))
same = np.asarray(new)[:, :W0] == np.asarray(old)
print('base.png', old.size, '->', new.size, '舊範圍相同像素比例', round(same.all(2).mean(), 4))

# base.jpg
jpg = np.asarray(Image.open('base.jpg').convert('L'))
L0 = np.asarray(old.convert('L'))
lut = np.zeros(256, np.uint8)
for v in range(256):
    m = jpg[L0 == v]
    lut[v] = np.median(m) if m.size else 0
filled = np.where(np.array([(L0 == v).any() for v in range(256)]))[0]
lut = np.interp(np.arange(256), filled, lut[filled]).round().astype(np.uint8)
Lnew = np.asarray(new.convert('L'))
out = np.concatenate([jpg, lut[Lnew[:, W0:]]], 1)
Image.fromarray(out).save('base.jpg', quality=90)

# water.npy
rgb = np.asarray(new).astype(int)
col = np.all(np.abs(rgb - np.array([170, 211, 223])) <= 12, 2)
wold = np.load('water.npy')
print('水域規則在舊範圍的一致率', round((col[:, :W0] == wold).mean(), 4))
np.save('water.npy', np.concatenate([wold, col[:, W0:]], 1))
new.save('base.png')
print('E =', E, 'width', W1, '→', E)
