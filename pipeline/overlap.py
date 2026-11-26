"""逐年檢查看得見的線之間有沒有不合理的重疊或交叉。

python3 overlap.py [geo_v13.json] [YEAR ...]

年份規則與 tpl.html 相同：主線、支線依 SEG 的 [o, c)（只檢查營運中的，不含停用後的灰線與輕軌），
線形依 G['alt']／G['xalt'] 換成該年代的版本，
側線依 G['xy']，站場股道依 G['yards'] 的組別年份（沒有年份的組依最近車站）。

檢查三種情形：
1. 交叉：兩條線（主線、支線、側線）相交，而且交點不在任一條的端點附近（端點附近視為接點）；
2. 疊線：兩條線在 12 m 內平行、間距幾乎不變地並行超過 30 m，看起來像同一條線畫了兩次（間距一路拉開的轉轍器分岐不算）；
3. 斜穿股道：主線、支線、側線與站場股道以 8° 以上的角度相交（線應該沿著某一股走，而不是橫越站場）。
"""
import json, math, re, sys
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

args = sys.argv[1:]
gpath = args.pop(0) if args and args[0].endswith('.json') else 'geo_v13.json'
G = json.load(open(gpath))
YEARS = [int(a) for a in args] or [1915, 1935, 1950, 1965, 1977, 1985, 1995, 2005, 2010, 2015]

tpl = open('tpl.html', encoding='utf-8').read()
SEG = {i: (int(o), int(c), k, n) for i, n, k, o, c in
       re.findall(r"\{id:'(\w+)',(?:lb:'[^']*',)?name:'([^']*)',k:'(\w+)',o:(\d+),c:(\d+)", tpl)}
STN = [(n, int(o), int(c)) for n, o, c in re.findall(r"\['([^']+)',(\d+),(\d+),'\w+'\]", tpl.split('const STN=')[1].split(';')[0])]

lat0, lon0 = 22.61, 120.30
KX, KY = math.cos(math.radians(lat0)) * 111320, 110540
xy = lambda p: ((p[1] - lon0) * KX, (p[0] - lat0) * KY)
ll = lambda x, y: (round(y / KY + lat0, 6), round(x / KX + lon0, 6))


def yard_years(gr, g):
    if gr.get('o') is not None:
        return gr['o'], gr['c']
    best = None
    for n, o, c in STN:
        p = G['st'].get(n)
        if not p:
            continue
        d = math.hypot(p[0] - g[0][0], (p[1] - g[0][1]) * .92)
        if best is None or d < best[0]:
            best = (d, o, c)
    return best[1], best[2]


def pick_alt(alts, y, default):
    """與 tpl.html 的 pickAlt 相同：該年所在年代的線形；晚於最後一個年代用最後一個；否則用預設線形。"""
    if not alts:
        return default
    for o, c, g in alts:
        if o <= y < c:
            return g
    last = max(alts, key=lambda r: r[1])
    return last[2] if y >= last[1] else default


def lines(y):
    L = []  # (名稱, 類別, LineString)
    for i, (o, c, k, n) in SEG.items():
        if k == 'lr' or not (o <= y < c):
            continue
        g = pick_alt(G.get('alt', {}).get(i), y, G['seg'][i])
        L.append((f'{i}:{n}', 'yd' if k == 'yd' else 'main', LineString([xy(p) for p in g])))
    for n, parts in G['extra'].items():
        r = G['xy'].get(n)
        if r and not ((r[0] is None or y >= r[0]) and (r[1] is None or y < r[1])):
            continue
        parts = pick_alt(G.get('xalt', {}).get(n), y, parts)
        for v in parts:
            L.append((n, 'extra', LineString([xy(p) for p in v])))
    for ti, t in enumerate(G.get('tt', [])):
        if t['o'] <= y < t['c']:
            for si, sp in enumerate(t['spokes']):
                L.append((f'轉車台[{ti}.{si}]', 'yard', LineString([xy(p) for p in sp])))
    for gi, gr in enumerate(G['yards']):
        for li, g in enumerate(gr['lines']):
            o, c = yard_years(gr, g)
            if o <= y < c:
                L.append((f'股道[{gi}.{li}] {gr["src"]}', 'yard', LineString([xy(p) for p in g])))
    return L


def heading(ls, d):
    a, b = ls.interpolate(max(0, d - 3)), ls.interpolate(min(ls.length, d + 3))
    return math.atan2(b.y - a.y, b.x - a.x)


def angdiff(a, b):
    d = abs(a - b) % math.pi
    return min(d, math.pi - d)


def check(y):
    L = lines(y)
    tree = STRtree([g for _, _, g in L])
    out = {'交叉': [], '疊線': [], '斜穿股道': {}}
    for i, (na, ka, ga) in enumerate(L):
        if ka == 'yard':
            continue
        for j in tree.query(ga.buffer(8)):
            if j == i:
                continue
            nb, kb, gb = L[j]
            if nb == na:
                continue
            # 1 & 3：交叉
            if (kb != 'yard' and j > i) or kb == 'yard':
                inter = ga.intersection(gb)
                pts = [inter] if inter.geom_type == 'Point' else [g for g in getattr(inter, 'geoms', []) if g.geom_type == 'Point']
                for p in pts:
                    da, db = ga.project(p), gb.project(p)
                    near_end = min(da, ga.length - da) < 8 or min(db, gb.length - db) < 8
                    if near_end:
                        continue
                    ang = math.degrees(angdiff(heading(ga, da), heading(gb, db)))
                    if ang < 3 and ga.distance(gb) < 0.5:   # 共線（兩線刻意畫在同一條軌道上），不算交叉
                        continue
                    if kb == 'yard':
                        if ang >= 8:
                            out['斜穿股道'].setdefault(na, []).append((ll(p.x, p.y), round(ang)))
                    else:
                        out['交叉'].append((na, nb, ll(p.x, p.y), round(ang)))
            # 2：疊線（不含股道）：12 m 內平行、間距幾乎不變（差 < 3 m）並行超過 30 m。
            #    間距一路拉開的是轉轍器分岐，不算。
            if kb != 'yard' and j > i:
                runs, seq = [], []
                for s_ in range(int(ga.length // 5) + 1):
                    d = s_ * 5
                    p = ga.interpolate(d)
                    dist = gb.distance(p)
                    if dist <= 12 and angdiff(heading(ga, d), heading(gb, gb.project(p))) < math.radians(12):
                        seq.append((p, dist))
                    else:
                        if seq: runs.append(seq)
                        seq = []
                if seq: runs.append(seq)
                for r in runs:
                    if len(r) * 5 <= 30:
                        continue
                    ds = [x[1] for x in r]
                    if max(ds) - min(ds) < 3 and min(ds) >= 0.8:
                        out['疊線'].append((na, nb, ll(r[0][0].x, r[0][0].y), len(r) * 5, round(min(ds), 1), round(max(ds), 1)))
    return out


for y in YEARS:
    r = check(y)
    print(f'== {y}')
    for a, b, p, ang in r['交叉']:
        print(f'  交叉 {ang:>3}° {p}  {a} × {b}')
    for a, b, p, run, d0, d1 in r['疊線']:
        print(f'  疊線 {run:>4} m 間距 {d0}–{d1} m {p}  {a} ‖ {b}')
    for a, v in r['斜穿股道'].items():
        print(f'  斜穿股道 {len(v):>3} 處  {a}  例：{v[0][0]} {v[0][1]}°')
