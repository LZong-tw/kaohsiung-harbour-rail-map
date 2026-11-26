"""站場股道：從國土測繪中心 1:5000 像片基本圖描出高雄港站、前鎮車場與高雄機廠的股道。

python3 yards.py

1. 用 nlsc.py 下載並拼接像片基本圖（z18）：
   - 高雄港站：民國 65 年（1976，TOPO05KPHOTO_065）、民國 87 年（1998，TOPO05KPHOTO_087）
   - 前鎮車場、高雄機廠：民國 87 年（1998）
2. 用 yardtrace.py 在站場範圍（yard_poly_*.json，像素多邊形）內描出股道；
3. 輸出 yard_ks1976.json、yard_ks1998.json、yard_qz1998.json，檢查圖寫到 /tmp/yard_*_ov.png。

第 28、29 輪另加（中研院高雄百年歷史地圖，khh.py 下載）：
4. 1970 年 1:1200 都市計畫航測地形圖 → yardtrace_line.py → yard_ks1970.json；轉車台 → turntable.py → tt_ks1970.json；
5. 1984 年都市計畫航測地形圖 → yardtrace.py（以 yard_ks1970.json 當方向場，YT_PRIOR）→ yard_ks1984.json。
   這張圖的枕木畫成橫跨整束股道的長橫線，結構張量的主方向會被橫線帶走，所以借 1970 年描線的走向。
"""
import json, subprocess

JOBS = [
    # 輸出名, 圖層, 範圍 W E S N, 站場範圍
    ('ks1998', 'TOPO05KPHOTO_087', (120.2715, 120.2860, 22.6150, 22.6270), 'yard_poly_ks.json'),
    ('ks1976', 'TOPO05KPHOTO_065', (120.2715, 120.2860, 22.6150, 22.6270), 'yard_poly_ks.json'),
    ('qz1998', 'TOPO05KPHOTO_087', (120.3150, 120.3370, 22.5990, 22.6200), 'yard_poly_qz.json'),
]
for name, layer, (W, E, S, N), poly in JOBS:
    img = f'/tmp/yard_{name}.png'
    subprocess.run(['python3', 'nlsc.py', layer, '18', str(W), str(E), str(S), str(N), img], check=True)
    subprocess.run(['python3', 'yardtrace.py', img, '18', str(W), str(N), poly, f'yard_{name}.json',
                    f'/tmp/yard_{name}_ov.png', 'geo_v13.json'], check=True)

KS = (120.2715, 120.2860, 22.6150, 22.6270)
subprocess.run(['python3', 'khh.py', 'Kaohsiung_1.2K_1970', '18', *map(str, KS), '/tmp/k70.png'], check=True)
subprocess.run(['python3', 'yardtrace_line.py', '/tmp/k70.png', '18', str(KS[0]), str(KS[3]), 'yard_poly_ks70.json',
                'yard_ks1970.json', '/tmp/yard_ks1970_ov.png'], check=True)
subprocess.run(['python3', 'turntable.py', '/tmp/k70.png', '18', str(KS[0]), str(KS[3]), '917', '1362', 'tt_ks1970.json',
                '/tmp/tt_ks1970_ov.png', 'yard_ks1970.json', 'tt_caps_1970.json'], check=True)
subprocess.run(['python3', 'khh.py', 'Kaohsiung_1984', '18', *map(str, KS), '/tmp/k84.png'], check=True)
import os
# 1984 年組的範圍：1970 年組範圍的西側頂點（x < 1000）再往西 15 px（約 8 m）
json.dump([[x - 15, y] if x < 1000 else [x, y] for x, y in json.load(open('yard_poly_ks70.json'))['include']],
          open('yard_poly_ks84.json', 'w'))
subprocess.run(['python3', 'yardtrace.py', '/tmp/k84.png', '18', str(KS[0]), str(KS[3]), 'yard_poly_ks84.json',
                'yard_ks1984.json', '/tmp/yard_ks1984_ov.png'], check=True, env={**os.environ, 'YT_PRIOR': 'yard_ks1970.json'})

