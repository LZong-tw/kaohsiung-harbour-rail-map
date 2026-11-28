"""把第 1–35 輪留在工作環境 /tmp 的比對圖收進 scratch/past/（第 36 輪，使用者：「過往的圖也要放進 git，不然太浪費了」）。

python3 archive_figs.py /tmp/inv.tsv

只在第 36 輪執行一次：/tmp 是工作環境的暫存區，之後不會再有同一批檔案。這裡保留篩選規則，讓收了什麼、沒收什麼可以查。

篩選：
1. 不收圖磚快取（256×256 的單張圖磚、badtiles/、khh/ 的試抓圖磚）與 r28_private/。
2. 不收中研院「高雄百年歷史地圖」的圖與疊圖（服務頁標示「中央研究院版權所有，非經允許，不得作為商業使用」）：
   1970 年 1:1200 圖、1984／1986 年都市計畫圖、2000 年 1:1000 圖、1962 年港擴建圖、舊航照，以及由這些圖做出的濾波圖、拼貼圖。
   依檔名與逐張目視（17 張縮圖總表）判定，清單見 EXCLUDE。
3. 不收 1977 年臺糖鐵道路線圖、分佈圖（Google Drive，授權未標示）、上傳圖總表（含街景截圖）。
4. 來源看不出來的（例如彩色土地使用圖 qz_a–e、混了灰階舊圖的拼貼）也不收。
5. 第 36 輪本身的圖由 r36_figs.py 重新產生到 scratch/r36/，這裡不收。

收進來的圖：轉成 JPEG（品質 78，長邊最多 1600 px），依建立時間對到第幾輪（以各輪 commit 時間為界），
寫到 scratch/past/rNN/，並在 scratch/past/MANIFEST.tsv 記下原檔名、輪次、尺寸與來源類別（依檔名推定）。
"""
import os
import re
import sys
import datetime as dt

from PIL import Image

INV = sys.argv[1] if len(sys.argv) > 1 else '/tmp/inv.tsv'
OUT = '../scratch/past'

EXCLUDE_RE = [
    r'Kaohsiung', r'khh', r'(^|/)hk_', r'(^|/)hk6', r'(^|/)hs', r'(^|/)k70', r'(^|/)k62', r'(^|/)y70', r'(^|/)y84',
    r'(^|/)poly70', r'yard_ks1970_ov', r'(^|/)tt', r'(^|/)cz8[46]', r'(^|/)cz4', r'(^|/)d84[abcd]', r'(^|/)s84', r'(^|/)s70',
    r'(^|/)[ceilu]84', r'(^|/)e84', r'(^|/)f84', r'(^|/)fh8[46]', r'(^|/)h84', r'(^|/)[nj]84', r'(^|/)[nj]8984', r'(^|/)j8489',
    r'(^|/)k84', r'(^|/)b84', r'(^|/)b8984', r'(^|/)w84', r'(^|/)w8489', r'(^|/)t84', r'(^|/)t8984', r'(^|/)c84',
    r'(^|/)qz_[a-e]\.png$', r'Google_Drive', r'(^|/)xg_', r'uploads_sheet', r'(^|/)a56z', r'(^|/)a69z', r'(^|/)m70z',
    r'/aud/fso\.png$', r'(^|/)late[35]', r'(^|/)f_1K_2000', r'(^|/)clean_1', r'(^|/)lost3', r'(^|/)x3\.png$',
    # 股道示意圖（yarddiag.py 等）：底下襯著淡化的 1970 年 1:1200 圖或 1945 年舊航照，第一次收錄時漏看，回顧時發現後移除
    r'(^|/)d(45|70|76|84)', r'(^|/)r(70|76)', r'(^|/)reach7[06]', r'(^|/)n70a',
    r'(^|/)r45c?\.png$', r'(^|/)tri2?\.png$', r'(^|/)g1\.png$', r'(^|/)cr\.png$', r'(^|/)s84z',
]
SKIP_DIR = re.compile(r'/(badtiles|khh|junk|r28_private|sheets)/')

# 各輪 commit 時間（本地時間）；圖的建立時間落在前一輪 commit 之後、這一輪 commit 之前，就算這一輪
ROUNDS = [
    ('2026-11-26 18:17', 19), ('2026-11-26 19:33', 21), ('2026-11-26 19:55', 23), ('2026-11-26 20:44', 24),
    ('2026-11-26 21:18', 25), ('2026-11-26 21:31', 26), ('2026-11-27 00:28', 27), ('2026-11-27 01:42', 28),
    ('2026-11-27 02:28', 29), ('2026-11-27 03:52', 30), ('2026-11-27 10:05', 31), ('2026-11-28 13:55', 34),
    ('2026-11-28 14:27', 35), ('2026-11-28 14:40', 36),
]


def round_of(t):
    for lim, r in ROUNDS:
        if t <= dt.datetime.strptime(lim, '%Y-%m-%d %H:%M'):
            return r
    return None


def source_of(name):
    n = name.lower()
    if re.search(r'topo05kphoto|ks_0|ks76|ks_tr|qz_087|qz_ov|qz_c[12]|qz_zoom|yard_ks19(76|98)|yard_qz|stn_yard|ridge|raw_c|clean_[234]|ov98|both', n):
        return '國土測繪中心 1/5000 像片基本圖（民國 65、87 年）'
    if re.search(r'ph|sub19|ne19|bl5|bl6|tw_ph|tw2_ph|tw3|fsph|e1ph|zx|pier', n) and not re.search(r'p(55|66|89)', n):
        return '國土測繪中心正射影像（PHOTO2）或疊圖'
    if re.search(r'1904|1921|1924|1942|^o42|^c24|^c04|^k_19|^j24|^j42|^g42|^f42|^l42|^m19|^o19|^n42|^v42|^fe_|^b5|sh42|^c42', n):
        return '中研院臺灣百年歷史地圖：日治地形圖（JM20K_1904、JM50K_1924、JM25K_1942 等，CC BY-NC）'
    if re.search(r'45|am45|amcity|m45|s45|z45|a45|gk45|tc1945', n):
        return '中研院臺灣百年歷史地圖：1945 年美軍高雄市街圖（AMCityPlan_1945，CC BY-NC）'
    if re.search(r'55|66|5566|1950|50a|v50|e55|e66|s55|s66', n):
        return '中研院臺灣百年歷史地圖：1950、1955、1966 年地形圖（CC BY-NC）'
    if re.search(r'89|93|2001|01|tm25k|sug|scan', n):
        return '中研院臺灣百年歷史地圖：1989、1993、2001 年經建版（CC BY-NC）'
    if re.search(r'tm5k|tm10k|corona', n):
        return '中研院臺灣百年歷史地圖：TM5K_1962、TM10K_1970／1974、Corona 1969（CC BY-NC）'
    return '本研究網頁截圖、OSM 底圖（© OpenStreetMap contributors）或描線圖（依檔名推定，個別圖可能為上列圖資）'


def main():
    rows = [l.rstrip('\n').split('\t') for l in open(INV)]
    os.makedirs(OUT, exist_ok=True)
    man = ['檔名\t原檔\t輪次\t原尺寸\t來源（依檔名推定）']
    kept = skipped = 0
    for t, p, s, w, h, *_ in rows:
        w, h = int(w), int(h)
        if (w == 256 and h == 256) or SKIP_DIR.search(p) or p.startswith('/tmp/figcrop'):
            continue
        # inv.tsv 的時間多加了 8 小時（工作環境已是本地時間），這裡扣回
        tt = dt.datetime.strptime(t, '%Y-%m-%d %H:%M') - dt.timedelta(hours=8)
        r = round_of(tt)
        if r is None or r >= 36:
            continue
        if any(re.search(x, p) for x in EXCLUDE_RE):
            skipped += 1
            continue
        try:
            im = Image.open(p).convert('RGB')
        except Exception:
            continue
        im.thumbnail((1600, 1600), Image.LANCZOS)
        rel = p[len('/tmp/'):].replace('/', '__')
        name = os.path.splitext(rel)[0] + '.jpg'
        d = f'{OUT}/r{r:02d}'
        os.makedirs(d, exist_ok=True)
        im.save(f'{d}/{name}', quality=78, optimize=True)
        man.append(f'r{r:02d}/{name}\t{p}\t{r}\t{w}×{h}\t{source_of(os.path.basename(p))}')
        kept += 1
    open(f'{OUT}/MANIFEST.tsv', 'w').write('\n'.join(man) + '\n')
    print('收', kept, '張；依授權或來源不明不收', skipped, '張')


if __name__ == '__main__':
    main()
