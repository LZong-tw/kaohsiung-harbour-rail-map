"""逐年連通檢查：每一年營運中的線要能經由路網接到縱貫線（糖鐵另以糖廠路網為根）。

python3 connect_check.py [geo_v13.json] [--report OUT.txt]

第 36 輪使用者指出：船渠北岸造船所線 A、B 從 1941 年就顯示，但它們接的成功路北段（w1）1944 年才通，
1941–1943 年地圖上是兩條不跟任何線相連的側線。原因是側線年份「取所接母線的通車年」時取錯母線。
這個檢查找出同類的錯：

- 年份規則與 tpl.html 相同：主線、支線依 SEG 的 [o, c)；側線、糖鐵依 G['xy'] 的 [o, c)；依年代換線形的用 G['alt']、G['xalt']。
- 只看營運中的線（停用後的灰線、輕軌不算），站場股道不算。
- 兩條線相連：一條線的端點落在另一條線上（距離 ≤ 3 m）。
- 根：縱貫線（zg_n，1900 年起一直在）；名稱以「糖鐵」開頭的線自成糖廠路網，也當根
  （窄軌，與臺鐵在車站轉運，不一定有共用的軌道節點）。
- 每一年列出接不到根的線。有一筆就以非零結束。
"""
import json
import math
import re
import sys

geo = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'geo_v13.json'
report = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else None
G = json.load(open(geo))
tpl = open('tpl.html', encoding='utf-8').read()
SEG = {i: (int(o), int(c), k) for i, n, k, o, c in
       re.findall(r"\{id:'(\w+)',(?:lb:'[^']*',)?name:'([^']*)',k:'(\w+)',o:(\d+),c:(\d+)", tpl)}

LAT0 = 22.6
KX = 111320 * math.cos(math.radians(LAT0))
KY = 110574


def xy(p):
    return (p[1] * KX, p[0] * KY)


def parts(v):
    return [v] if isinstance(v[0][0], (int, float)) else v


def geom_at(table, key, base, year):
    for o, c, g in table.get(key, []):
        if o <= year < c:
            return g
    return base


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def near(p, P, tol=3.0):
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        if min(a[0], b[0]) - tol <= p[0] <= max(a[0], b[0]) + tol and min(a[1], b[1]) - tol <= p[1] <= max(a[1], b[1]) + tol:
            if seg_dist(p, a, b) <= tol:
                return True
    return False


def lines_at(year):
    L = {}
    for k, (o, c, kind) in SEG.items():
        if kind == 'lrt' or k.startswith('lr') or not (o <= year < c) or k not in G['seg']:
            continue
        L[k] = [[xy(p) for p in geom_at(G.get('alt', {}), k, G['seg'][k], year)]]
    for k, v in G['extra'].items():
        o, c = G['xy'].get(k, [0, 9999])
        if not (o <= year < c):
            continue
        L[k] = [[xy(p) for p in P] for P in parts(geom_at(G.get('xalt', {}), k, v, year))]
    return L


def orphans(year):
    L = lines_at(year)
    keys = list(L)
    par = {k: k for k in keys}

    def find(k):
        while par[k] != k:
            par[k] = par[par[k]]
            k = par[k]
        return k
    for a in keys:
        ends = [P[0] for P in L[a]] + [P[-1] for P in L[a]]
        for b in keys:
            if a == b or find(a) == find(b):
                continue
            if any(near(e, P) for e in ends for P in L[b]):
                par[find(a)] = find(b)
    roots = {find(k) for k in keys if k == 'zg_n' or k.startswith('糖鐵')}
    return sorted(k for k in keys if find(k) not in roots)


out = []
bad = 0
prev = None
for y in range(1900, 2027):
    o = orphans(y)
    if o:
        bad += 1
    if o != prev:
        out.append(f'{y}: ' + ('、'.join(o) if o else '全部相連'))
        prev = o
text = '\n'.join(out)
print(text)
if report:
    open(report, 'w').write(text + '\n')
print(f'有孤立線的年份：{bad}')
sys.exit(1 if bad else 0)
