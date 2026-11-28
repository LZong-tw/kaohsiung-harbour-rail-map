"""中島（前鎮加工出口區一帶）的股道：依 1976、1983、1989、1998 年像片基本圖逐版描出（第 36 輪）。

python3 zhongdao.py [來源目錄]

使用者：「然後中島車場如果能找到股道精確數量的話也試著補上去」「中島其他路線的鐵路好像變化速度極大極快」，
並在 1983 年像片基本圖上指出中島北段實際有兩組軌道，現行中島線斜穿倉庫、兩組都沒對上。

做法：
1. 用 nlsc.py 拼出 120.284–120.318°E、22.585–22.612°N 的 z18 像片基本圖（各版），yardtrace.py 在整個範圍描線
   → trace_qd{年}.json（整個範圍的描線，含雜訊，留給之後處理前鎮其他側線用）。
2. 只取中島範圍（ZD_POLY）內、長度 ≥ MIN_LEN 公尺的片段，去掉圖幅方格線（grid_like）→ yard_zd{年}.json。apply_reg.py 讀入時再經 yardclean.py 過濾。
3. 中島線本線依各版描線改走實際的軌道（yardlines.py 的 PLAN，錨點在 ZD_ANCHORS，人工依圖選定）。描線本身不畫上地圖。

符號（由已知線反推，見 scratch/r36/symbol_*.jpg）：單線＝一條線加短橫刻；兩條各有橫刻的線＝兩股單線；
兩條靠近、共用橫刻的線＝複線（兩股）。描線把每一條線當一股。
"""
import json
import math
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.'
EDITIONS = {1976: '065', 1983: '072', 1989: '078', 1998: '087'}
MIN_LEN = 45.0

# 中島範圍（緯度, 經度）：北端高港倉庫一帶到南側擴建路，東側到 5.4K 三角以西，不含港池對岸的南部發電廠；水域由描線本身排除
ZD_POLY = [(22.6125, 120.2835), (22.6125, 120.2925), (22.6080, 120.2975), (22.5975, 120.2975),
           (22.5960, 120.2995), (22.5935, 120.3005), (22.5935, 120.3050), (22.5895, 120.3050), (22.5880, 120.2990),
           (22.5860, 120.2950), (22.5860, 120.2835)]

KX = 111320 * math.cos(math.radians(22.6))
KY = 110574


def inside(pt, poly):
    la, lo = pt
    c = False
    for i in range(len(poly)):
        (a1, o1), (a2, o2) = poly[i], poly[i - 1]
        if (a1 > la) != (a2 > la) and lo < (o2 - o1) * (la - a1) / (a2 - a1) + o1:
            c = not c
    return c


def length(P):
    return sum(math.hypot((b[0] - a[0]) * KY, (b[1] - a[1]) * KX) for a, b in zip(P, P[1:]))


def clip(P):
    """把片段切成落在範圍內的連續段。"""
    out, cur = [], []
    for p in P:
        if inside(p, ZD_POLY):
            cur.append(p)
        else:
            if len(cur) > 1:
                out.append(cur)
            cur = []
    if len(cur) > 1:
        out.append(cur)
    return out


def grid_like(P):
    """像片基本圖的圖幅方格線：幾乎正南北或正東西的長直線（偏差 < 2°、全長 ≥ 120 m、中間點偏離直線 < 2 m）。
    中島一帶的股道都是西北—東南向，不會被誤刪。"""
    a, b = P[0], P[-1]
    dx, dy = (b[1] - a[1]) * KX, (b[0] - a[0]) * KY
    L = math.hypot(dx, dy)
    if L < 120:
        return False
    ang = abs(math.degrees(math.atan2(dy, dx))) % 90
    if min(ang, 90 - ang) > 2:
        return False
    for p in P[1:-1]:
        px, py = (p[1] - a[1]) * KX, (p[0] - a[0]) * KY
        if abs(px * dy - py * dx) / L > 2:
            return False
    return True


def main():
    for yr, code in EDITIONS.items():
        L = json.load(open(f'{SRC}/trace_qd{yr}.json'))
        keep = [q for P in L for q in clip(P) if length(q) >= MIN_LEN and not grid_like(q)]
        json.dump(keep, open(f'yard_zd{yr}.json', 'w'), separators=(',', ':'))
        print(yr, '描線', len(L), '段 → 中島範圍內、≥', MIN_LEN, 'm：', len(keep), '段，共', round(sum(map(length, keep))), 'm')


if __name__ == '__main__':
    main()


# 第 36 輪曾試過把描線片段以本線為根、依距離與走向自動接成路網（端點 70 m 內、走向差 30° 內以 Hermite 曲線接上），
# 各版接上 36–51 段、接不上 56–92 段，結果仍有多餘的線與不合理的接法。使用者要求改為人工定線、程式只做吸附與規整，
# 這個做法已拿掉（程式見 git 歷史）。
