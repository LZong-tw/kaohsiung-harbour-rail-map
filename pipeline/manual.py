"""人工定線（第 36 輪起）：控制點由人在附經緯度格線的放大圖上讀出，程式只做平滑與接到母線。

使用者（第 36 輪）：「你一直用程式描，你沒辦法手動微調程式得到接近手動畫的效果嗎」
「多出來的線理論上一定是連中島線或臨港線才對，不會獨立一小段在那邊」。

apply_reg.py 在最後呼叫 apply(G, S, X)：
- 每條線的控制點（緯度, 經度）寫在 manual_lines.py 的 LINES；
- on0／on1 指定起點／終點接在哪條線上（S 的路段代碼，或 X 的側線名稱；也可以是同一批裡先定義的線）：
  端點投影到母線上，並以母線在該處的走向為切線離開（轉轍器），所以線一定接在某條線上；
- 控制點之間用向心 Catmull-Rom 曲線（通過每個控制點、不會過衝），每 3 m 取一點；
- 寫入 X[name]、G['xy'][name]（顯示年份）、G['xb'][name]（年代與線形的依據，網頁點選時顯示）；
- replaces：這條線取代的舊線名（刪除舊線）；
- parallel=母線、off=公尺、pts=[起, 迄]：沿母線平移的並行股道（兩端漸收回母線），用在圖上畫成兩、三股並行的地方；
- yard='來源說明'：這條是站場股道（並行的第二、三股），放進 G['yards'] 的對應年份組，不列為具名的線。
"""
import math

import numpy as np

from regularize import nearest_on, toLL, toM, unit


def _cr(P, step=3.0):
    """向心 Catmull-Rom：P 為公尺座標的點（含頭尾各一個虛點），回傳通過 P[1..-2] 的折線。"""
    out = [P[1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.hypot(*(p1 - p0)) ** 0.5, 1e-6)
        t2 = t1 + max(np.hypot(*(p2 - p1)) ** 0.5, 1e-6)
        t3 = t2 + max(np.hypot(*(p3 - p2)) ** 0.5, 1e-6)
        n = max(2, int(np.hypot(*(p2 - p1)) / step))
        for k in range(1, n + 1):
            t = t1 + (t2 - t1) * k / n
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return out


def _herm(p0, t0, p1, t1, step=3.0):
    L = float(np.hypot(*(p1 - p0)))
    n = max(2, int(L / step))
    out = []
    for k in range(n + 1):
        u = k / n
        out.append((2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * L * t0
                   + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * L * t1)
    return out


LAT_MIN = 10.0     # 離母線不到這個距離的控制點落在轉轍器的漸離段，位置讀不準（本線本身也有幾公尺誤差），不用
FROG = 5.0         # 接點到第一個控制點：沿母線的距離至少是側距的幾倍（太短會變成斜插進母線）


def _attach(P, parent):
    """P[0] 那一端接到母線：回傳從母線上的接點以切線離開、到第一個夠遠的控制點的曲線（含該點），以及剩下的控制點。"""
    e = P[0]
    k = 0
    while k < len(P) - 1 and nearest_on(toLL(P[k]), parent)[0] < LAT_MIN:
        k += 1
    far = P[k]
    d, i, f, t, u = nearest_on(toLL(far), parent)
    pe = nearest_on(toLL(e), parent)[2]
    sgn = 1.0 if (pe - f) @ u >= 0 else -1.0
    if k == 0:                       # 端點本身就離母線夠遠：往「遠離下一個控制點」的方向退
        nxt = P[1]
        sgn = -1.0 if (nxt - far) @ u >= 0 else 1.0
    along = max(FROG * d, abs(float((pe - f) @ u)))
    along = min(along, 150.0)
    q = nearest_on(toLL(f + sgn * u * along), parent)
    q, uq = q[2], q[4]
    if (far - q) @ uq < 0:
        uq = -uq
    t1 = unit(P[k + 1] - far) if k + 1 < len(P) else unit(far - q)
    t1 = unit(t1 + unit(far - q))    # 末端切線取「往下一點」與「自接點而來」的平均，避免在第一個控制點折一下
    return _herm(q, uq, far, t1), P[k + 1:]


def _parallel(parent, a, b, off, taper=25.0, step=3.0):
    """母線上 a→b 之間的一段，往側邊平移 off 公尺（正值為行進方向左側），兩端各以 taper 公尺漸收回母線（轉轍器）。"""
    M = [toM(p) for p in parent]
    ia, ib = nearest_on(a, parent), nearest_on(b, parent)
    ka, kb = ia[1] + ia[3], ib[1] + ib[3]
    if ka > kb:
        M = M[::-1]
        parent = parent[::-1]
        ia, ib = nearest_on(a, parent), nearest_on(b, parent)
    seg = [ia[2]] + M[ia[1] + 1:ib[1] + 1] + [ib[2]]
    # 重新取樣
    D = [0.0]
    for p, q in zip(seg, seg[1:]):
        D.append(D[-1] + float(np.hypot(*(q - p))))
    L = D[-1]
    out = []
    n = max(2, int(L / step))
    for k in range(n + 1):
        d = L * k / n
        j = max(1, min(len(D) - 1, int(np.searchsorted(D, d))))
        t = (d - D[j - 1]) / ((D[j] - D[j - 1]) or 1e-9)
        p = seg[j - 1] + (seg[j] - seg[j - 1]) * t
        u = unit(seg[j] - seg[j - 1])
        w = min(1.0, d / taper, (L - d) / taper)
        w = 0.5 - 0.5 * math.cos(math.pi * max(0.0, w))
        out.append(p + np.array([-u[1], u[0]]) * off * w)
    return [toLL(p) for p in out]


def geom(spec, lookup):
    if spec.get('parallel'):
        return _parallel(lookup(spec['parallel']), spec['pts'][0], spec['pts'][1], spec['off'])
    P = [toM(p) for p in spec['pts']]
    head, tail = [], []
    if spec.get('on0'):
        head, P = _attach(P, lookup(spec['on0']))
    if spec.get('on1'):
        tail, P = _attach(P[::-1], lookup(spec['on1']))
        tail, P = tail[::-1], P[::-1]
    mid = head[-1:] + P + tail[:1]
    if len(mid) >= 2:
        g0 = head[-3] if len(head) >= 3 else 2 * mid[0] - mid[1]
        g1 = tail[2] if len(tail) >= 3 else 2 * mid[-1] - mid[-2]
        mid = _cr([g0] + mid + [g1])
    out = head[:-1] + mid + tail[1:] if head or tail else mid
    return [toLL(p) for p in out]


YARD = {}


def apply(G, S, X, lines):
    def lookup(k):
        if k in S:
            return S[k]
        if k in YARD:
            return YARD[k]
        return X[k][0]
    G.setdefault('xb', {})
    for spec in lines:
        for old in spec.get('replaces', []):
            X.pop(old, None); G['xy'].pop(old, None)
        n = spec['name']
        if spec.get('yard'):
            # 站場股道（與別的股道並行的第二、三股）：放進 G['yards']，依來源與年份分組；不是具名的線，但同樣接在母線上
            src, (o, c) = spec['yard'], spec['yrs']
            gr = next((g for g in G['yards'] if g['src'] == src and g['o'] == o and g['c'] == c), None)
            if gr is None:
                gr = {'src': src, 'o': o, 'c': c, 'lines': []}
                G['yards'].append(gr)
            g = geom(spec, lookup)
            gr['lines'].append(g)
            YARD[n] = g
            print('manual 股道', n, len(g), '點')
            continue
        X[n] = [geom(spec, lookup)]
        G['xy'][n] = list(spec['yrs'])
        G['xb'][n] = spec['basis']
        print('manual', n, round(sum(float(np.hypot(*(toM(b) - toM(a)))) for a, b in zip(X[n][0], X[n][0][1:]))), 'm')
