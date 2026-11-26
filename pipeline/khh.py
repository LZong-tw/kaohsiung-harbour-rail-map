"""下載並拼接中研院「高雄百年歷史地圖」圖層（gis.sinica.edu.tw/kaohsiung）。

python3 khh.py LAYER Z W E S N OUT.png

常用圖層（站場股道判讀用）：
  Kaohsiung_1.2K_1970   高雄市一千二百分之一都市計畫航測地形圖（1970）
  Kaohsiung_1984        高雄市都市計畫航測地形圖（1984）
  Kaohsiung_1986        高雄市都市計畫航測地形圖（1986）
  Kaohsiung_1K_2000     高雄市一千分之一都市計畫航測地形圖（2000）
  Kaohsiung_6K_1962     高雄港擴建區域地形圖（1962）
  Kaohsiung_aerialphoto_1945 / 1947 / 1956 / 1959 / 1960 / 1960b / 1969 / 1970s / 1984  高雄市舊航照影像

圖磚快取在 hk/LAYER/（不進 git：該服務標示「中央研究院版權所有，非經允許，不得作為商業使用」，
本專案只描出線形，不轉載影像）。
"""
import io, math, os, sys, time, urllib.request
from PIL import Image

L, Z = sys.argv[1], int(sys.argv[2])
W, E, S, N = [float(x) for x in sys.argv[3:7]]
out = sys.argv[7]


def xy(lon, lat):
    n = 2 ** Z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


x0, y0 = xy(W, N)
x1, y1 = xy(E, S)
os.makedirs(f'hk/{L}', exist_ok=True)
img = Image.new('RGB', ((int(x1) - int(x0) + 1) * 256, (int(y1) - int(y0) + 1) * 256), 'white')
for tx in range(int(x0), int(x1) + 1):
    for ty in range(int(y0), int(y1) + 1):
        f = f'hk/{L}/{Z}_{tx}_{ty}.png'
        if not os.path.exists(f):
            try:
                d = urllib.request.urlopen(
                    f'https://gis.sinica.edu.tw/kaohsiung/file-exists.php?img={L}-png-{Z}-{tx}-{ty}', timeout=30).read()
            except Exception:
                d = b''
            open(f, 'wb').write(d)
            time.sleep(.03)
        try:
            t = Image.open(f).convert('RGBA')
            bg = Image.new('RGBA', t.size, 'white')
            img.paste(Image.alpha_composite(bg, t).convert('RGB'), ((tx - int(x0)) * 256, (ty - int(y0)) * 256))
        except Exception:
            pass
img = img.crop((int((x0 - int(x0)) * 256), int((y0 - int(y0)) * 256),
                int((x1 - int(x0)) * 256), int((y1 - int(y0)) * 256)))
img.save(out)
print(out, img.size)
