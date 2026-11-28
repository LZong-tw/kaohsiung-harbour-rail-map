"""【檔名】本檔輸出的是工作時的縮寫檔名；repo 裡已改成「地點_內容_年份」（對照表：scratch/r36/檔名對照.tsv，改名規則：rename_r36_figs.py）。
重跑本檔後要再跑一次 rename_r36_figs.py。
第 36 輪的比對圖（前鎮—中島一帶，像片基本圖）→ ../scratch/r36/

python3 r36_figs.py

座標框：多數裁切以「中島框」（z18，左上角 120.284°E、22.611°N）的像素座標表示，這裡換成經緯度再交給 figcrop.py。
"""
import math
import subprocess

Z = 18
n = 2 ** Z * 256


def lon(x, W):
    return W + x / n * 360


def lat(y, N):
    y0 = (1 - math.asinh(math.tan(math.radians(N))) / math.pi) / 2 * n
    t = math.pi * (1 - 2 * (y0 + y) / n)
    return math.degrees(math.atan(math.sinh(t)))


def box(W, N, x0, y0, x1, y1):
    return lon(x0, W), lon(x1, W), lat(y1, N), lat(y0, N)


def fig(layer, bb, out, year=None, scale=1.0, overlay='dotted', note=''):
    cmd = ['python3', 'figcrop.py', layer, str(Z), *[f'{v:.6f}' for v in bb], f'../scratch/r36/{out}',
           '--scale', str(scale), '--overlay', overlay]
    if year is not None:
        cmd += ['--year', str(year)]
    if note:
        cmd += ['--note', note]
    subprocess.run(cmd, check=True)


ED = {'065': 1976, '072': 1983, '078': 1989, '087': 1998, '098': 2009}
ZW, ZN = 120.284, 22.611   # 中島框

# 1. 中島全區（1983），疊第 35 輪的線
fig('TOPO05KPHOTO_072', (120.284, 120.306, 22.589, 22.611), 'zhongdao_1983_overview.jpg', 1983, 0.35, 'solid',
    '使用者指出：中島北段沿倉庫南側道路的軌道、倉庫列之間的軌道都沒對上（本圖洋紅線斜穿倉庫）')
# 2. 中島北段（1983），兩組軌道
fig('TOPO05KPHOTO_072', box(ZW, ZN, 100, 0, 1400, 1100), 'zhongdao_north_1983_a.jpg', 1983, 1.0, 'dotted',
    '北段：倉庫列之間一組（雙線符號）、沿倉庫南側道路一組（三條線）')
fig('TOPO05KPHOTO_072', box(ZW, ZN, 900, 800, 2100, 2000), 'zhongdao_north_1983_b.jpg', 1983, 1.0, 'dotted')
fig('TOPO05KPHOTO_072', box(ZW, ZN, 500, 1500, 2100, 3000), 'zhongdao_west_1983.jpg', 1983, 0.8, 'dotted',
    '中島西岸另有一組「高港支線」（船舶調度室一帶分成數股），未畫')
# 3. 中島調車場（擴建路北側）各版
for code, yr in ED.items():
    fig(f'TOPO05KPHOTO_{code}', box(ZW, ZN, 2850, 3950, 3700, 4330), f'zhongdao_yard_{yr}.jpg', None, 2.0, 'none',
        '擴建路北側：兩條各有橫刻的線＝兩股單線並行（中島調車場，市府 2010 年計畫書：擴建路與新生路口，約 0.82 公頃）')
    fig(f'TOPO05KPHOTO_{code}', box(ZW, ZN, 3500, 3700, 4101, 4100), f'zhongdao_east_{yr}.jpg', None, 2.0, 'none',
        '東端：北來（成功路側）與東來（凱旋路側）各一股，往西併成兩股並行')
# 4. 符號判讀（由已知線反推）
fig('TOPO05KPHOTO_072', box(ZW, ZN, 3700, 3780, 4101, 4000), 'symbol_1983_two_single_tracks.jpg', None, 3.0, 'none',
    '符號：單線鐵路＝一條線加短橫刻；兩條各有橫刻的線＝兩股單線')
fig('TOPO05KPHOTO_072', box(ZW, ZN, 1380, 1280, 1720, 1480), 'symbol_1983_bundle.jpg', None, 4.0, 'none',
    '中島北段：西側三條線、東側兩條靠近且共用橫刻的線')
fig('TOPO05KPHOTO_072', box(120.280, 22.656, 250, 100, 400, 500), 'symbol_1983_double_track_trunk.jpg', None, 4.0, 'none',
    '對照：縱貫線（複線）畫成兩條靠近、共用橫刻的線')
# 5. 南部發電廠（台電線）環線
QW, QN = 120.284, 22.611
fig('TOPO05KPHOTO_072', box(QW, QN, 2550, 1750, 4101, 2700), 'taipower_1983.jpg', 1983, 0.85, 'dotted',
    '使用者指出：廠區內是環線，南股沿第五船渠北岸往西，未畫')
fig('TOPO05KPHOTO_087', box(QW, QN, 2550, 1750, 4101, 2700), 'taipower_1998.jpg', 1998, 0.85, 'dotted',
    '1998 年：環線已改成道路')
# 6. 5.4K 三角、台糖中心倉庫、鋼品廠（1998）
fig('TOPO05KPHOTO_087', (120.296, 120.312, 22.586, 22.598), 'triangle_1998_overview.jpg', 1998, 0.6, 'solid',
    '使用者指出：成功二路往西南的一束股道漏畫、台糖中心倉庫線走向不對；凱旋四路往西北那股確定進臺機鋼品廠')

# 7. 成功二路西側那束股道（台肥三廠、台糖中心倉庫、嘉吉飼料）、鋼品廠線、籬仔內、往小港一帶
for code, yr in [('065', 1976), ('072', 1983), ('078', 1989), ('087', 1998)]:
    fig(f'TOPO05KPHOTO_{code}', (120.30143, 120.30573, 22.59442, 22.59838), f'fan_{yr}.jpg', yr, 1.0, 'dotted')
    fig(f'TOPO05KPHOTO_{code}', (120.3055, 120.3110, 22.5922, 22.5972), f'steel_{yr}.jpg', yr, 0.8, 'dotted')
for code, yr in [('065', 1976), ('078', 1989), ('087', 1998)]:
    fig(f'TOPO05KPHOTO_{code}', (120.2995, 120.3060, 22.5915, 22.5965), f'fan_south_{yr}.jpg', yr, 0.8, 'dotted')
for code, yr in [('072', 1983), ('087', 1998)]:
    fig(f'TOPO05KPHOTO_{code}', (120.3140, 120.3240, 22.5915, 22.5990), f'tsg_kaixuan_{yr}.jpg', yr, 0.6, 'dotted',
        '中山四路×凱旋四路東南：1983 年圖標「臺糖鐵路」「臺糖倉庫」「臺糖副產品加工廠」')
for code, yr in [('065', 1976), ('072', 1983), ('078', 1989)]:
    fig(f'TOPO05KPHOTO_{code}', (120.3175, 120.3310, 22.5790, 22.6010), f'lizinei_{yr}.jpg', yr, 0.5, 'solid')
    fig(f'TOPO05KPHOTO_{code}', (120.3160, 120.3300, 22.5960, 22.6120), f'lizinei_north_{yr}.jpg', yr, 0.5, 'solid')
    fig(f'TOPO05KPHOTO_{code}', (120.3190, 120.3265, 22.5975, 22.6065), f'lizinei_link_{yr}.jpg', yr, 0.7, 'dotted',
        '籬子內線北端（籬仔內站）與凱旋四路的第一臨港線之間約 350 m 沒有畫')
fig('TOPO05KPHOTO_072', (120.318, 120.346, 22.562, 22.598), 'xiaogang_1983.jpg', 1983, 0.75, 'solid',
    '使用者指出：1979 年院轄高雄市街圖上，自凱旋／中山路圓環南下、再往東彎向小港的鐵路，地圖上沒有對應')
fig('TOPO05KPHOTO_065', (120.318, 120.346, 22.562, 22.598), 'xiaogang_1976.jpg', 1976, 0.75, 'solid')
for code, yr in [('072', 1983), ('078', 1989)]:
    subprocess.run(['python3', 'figcrop.py', f'TOPO05KPHOTO_{code}', '17', '120.312', '120.342', '22.566', '22.600',
                    f'../scratch/r36/s2_{yr}.jpg', '--year', str(yr), '--overlay', 'dotted', '--scale', '0.8'], check=True)

# 8. 中島：自動描線（只供吸附）與修正後的中島線本線
for code, yr in [('065', 1976), ('072', 1983), ('078', 1989), ('087', 1998)]:
    subprocess.run(['python3', 'figcrop.py', f'TOPO05KPHOTO_{code}', '18', '120.284', '120.306', '22.586', '22.6125',
                    f'../scratch/r36/zd_trace_{yr}.jpg', '--overlay', 'none', '--trace', f'yard_zd{yr}.json', '--scale', '0.42',
                    '--note', '自動描線（zhongdao.py）：只供中島線本線吸附，不畫上地圖'], check=True)
    fig(f'TOPO05KPHOTO_{code}', (120.284, 120.306, 22.586, 22.6125), f'zd_new_{yr}.jpg', yr, 0.42, 'solid',
        '第 36 輪修正後的中島線本線（洋紅）')
for code, yr in [('072', 1983), ('087', 1998)]:
    fig(f'TOPO05KPHOTO_{code}', (120.2840, 120.2970, 22.5990, 22.6105), f'zd_new_north_{yr}.jpg', yr, 0.6, 'solid',
        '第 36 輪修正後：中島線本線北段沿倉庫南側道路那組走到西端')
