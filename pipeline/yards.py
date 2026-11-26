"""站場股道：從國土測繪中心 1:5000 像片基本圖描出高雄港站、前鎮車場與高雄機廠的股道。

python3 yards.py

1. 用 nlsc.py 下載並拼接像片基本圖（z18）：
   - 高雄港站：民國 65 年（1976，TOPO05KPHOTO_065）、民國 87 年（1998，TOPO05KPHOTO_087）
   - 前鎮車場、高雄機廠：民國 87 年（1998）
2. 用 yardtrace.py 在站場範圍（yard_poly_*.json，像素多邊形）內描出股道；
3. 輸出 yard_ks1976.json、yard_ks1998.json、yard_qz1998.json，檢查圖寫到 /tmp/yard_*_ov.png。
"""
import subprocess

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
