"""把全部線形輸出成開放格式 GeoJSON（RFC 7946，WGS84 經緯度），讓這份資料不靠本專案的網頁與腳本也能檢視、修改、轉檔。

為什麼要有這個檔（使用者要求，第 36 輪之十七：「必須做一個能獨自修改可被檢視的公開檔案格式，這樣才有相容性可言」）：
geo_v13.json 是給 tpl.html 用的內部格式（緯度在前、線名當鍵、年份與說明散在 tpl.html 的 JavaScript 裡），別的軟體讀不了。
GeoJSON 是公開標準：GitHub 直接顯示成地圖，geojson.io 可在瀏覽器裡改，QGIS／ArcGIS／Leaflet／OpenLayers／GDAL(ogr2ogr) 都能讀寫，
可再轉成 KML、GeoPackage、Shapefile。

cd pipeline && python3 export_geojson.py            # 寫 ../data/kaohsiung-harbour-rail-1900-2024.geojson（全部）與各分層檔
cd pipeline && python3 export_geojson.py --check    # 只驗證既有的檔是否與 geo_v13.json、tpl.html 一致（CI 用）

一筆 feature 是「一條線在一段年代的線形」：同一條線若依年代換線形（G['alt']、G['xalt']），每個年代各一筆，id 相同、geometry_from／geometry_to 不同。
欄位說明見 ../data/README.md。方向是單向的：這個檔由 geo_v13.json 產生；直接改這個檔不會回到網頁，要回饋請改 pipeline 的來源（見 README）。
"""
import json
import os
import re
import sys

OUT_DIR = '../data'
BASE = 'kaohsiung-harbour-rail-1900-2024'
G = json.load(open('geo_v13.json'))
TPL = open('tpl.html').read()

KIND = {  # tpl.html 的 k → (英文代碼, 中文, 線色)；線色與網頁圖例相同，寫進 simplestyle 欄位讓 GitHub、geojson.io 直接上色
    'trunk': ('trunk', '縱貫線、屏東線', '#1d4e89'),
    'main': ('harbour_main', '臨港線', '#7b2d8e'),
    'br': ('harbour_branch', '臨港線支線', '#c2620a'),
    'red': ('second_harbour', '第二臨港線', '#c1121f'),
    'lr': ('light_rail', '環狀輕軌', '#2f9e44'),
}


def js_objects(block):
    """SEG=[{…},{…}] 這種每筆一個 {} 的 JavaScript 陣列，逐筆取出欄位（值只有字串與數字）。"""
    out = []
    for m in re.finditer(r'\{id:\'[^\n]*?\}(?=,\n|\];)', block):
        o = {}
        for k, v in re.findall(r"(\w+):('(?:[^'\\]|\\.)*'|-?\d+)", m.group(0)):
            o[k] = v[1:-1] if v.startswith("'") else int(v)
        out.append(o)
    return out


SEG = js_objects(TPL[TPL.index('const SEG=['):TPL.index('const STN=')])
STN = json.loads(re.search(r'const STN=(\[\[.*?\]\]);', TPL).group(1).replace("'", '"'))
STX = json.loads(re.sub(r"'", '"', re.search(r'const STX=(\{.*?\});', TPL).group(1)))
assert len(SEG) >= 20 and len(STN) >= 10, (len(SEG), len(STN))


def yr(v):
    return None if v is None or v >= 9999 or v >= 2100 else v


def ll(L):
    return [[round(p[1], 7), round(p[0], 7)] for p in L]


def geom(parts):
    parts = [ll(p) for p in parts if len(p) >= 2]
    return {'type': 'LineString', 'coordinates': parts[0]} if len(parts) == 1 else {'type': 'MultiLineString', 'coordinates': parts}


def feat(g, **props):
    return {'type': 'Feature', 'properties': {k: v for k, v in props.items()}, 'geometry': g}


F = {'lines': [], 'sidings': [], 'yard_tracks': [], 'points': []}

# 1) 主線、支線、輕軌
for s in SEG:
    k = s['id']
    if k not in G['seg']:
        continue
    code, zh, col = KIND[s['k']]
    eras = G.get('alt', {}).get(k) or [[None, None, G['seg'][k]]]
    for o, c, L in eras:
        F['lines'].append(feat(geom([L]), id=k, name=s['name'], label=s.get('lb'), layer='line', kind=code, kind_zh=zh,
                               start_year=yr(s['o']), end_year=yr(s['c']), geometry_from=yr(o), geometry_to=yr(c),
                               history=s.get('t'), today=s.get('now'), basis=None, source=None,
                               **{'stroke': col, 'stroke-width': 3, 'stroke-opacity': 1}))
missing = sorted(set(G['seg']) - {s['id'] for s in SEG} - {'qy1', 'qy2'})
assert not missing, ('tpl.html 的 SEG 少了路段', missing)

# 2) 側線、糖鐵
for n, parts in G['extra'].items():
    o, c = (G['xy'].get(n) or [None, None])[:2]
    sugar = n.startswith('糖鐵')
    eras = G.get('xalt', {}).get(n) or [[None, None, parts]]
    for go, gc, P in eras:
        F['sidings'].append(feat(geom(P), id='x-' + n, name=n, label=None, layer='siding', kind='sugar_railway' if sugar else 'siding',
                                 kind_zh='糖業鐵道' if sugar else '專用側線、並行股', start_year=yr(o), end_year=yr(c),
                                 geometry_from=yr(go), geometry_to=yr(gc), history=None, today=None, basis=(G.get('xb') or {}).get(n), source=None,
                                 **{'stroke': '#7a5c3a' if sugar else '#c2620a', 'stroke-width': 2, 'stroke-opacity': 1}))


# 3) 站場股道（每股一筆）
def nearest_station_years(p):
    best = None
    for n, o, c, _ in STN:
        q = G['st'].get(n)
        if q:
            d = (q[0] - p[0]) ** 2 + ((q[1] - p[1]) * .92) ** 2
            if best is None or d < best[0]:
                best = (d, o, c)
    return best[1], best[2]


for gi, gr in enumerate(G['yards']):
    for li, L in enumerate(gr['lines']):
        if len(L) < 2:
            continue
        o, c = gr.get('o'), gr.get('c')
        if o is None:
            o, c = nearest_station_years(L[0])       # 與網頁相同：沒有年份的組依最近車站
        F['yard_tracks'].append(feat(geom([L]), id=f'yard-{gi}-{li}', name=None, label=None, layer='yard_track', kind='yard_track', kind_zh='站場股道',
                                     start_year=yr(o), end_year=yr(c), geometry_from=None, geometry_to=None, history=None, today=None, basis=None,
                                     source=gr['src'], **{'stroke': '#7b2d8e', 'stroke-width': 1, 'stroke-opacity': 0.8}))

# 4) 點：車站、分歧點、轉車台
for n, o, c, _ in STN:
    if n in G['st']:
        p = G['st'][n]
        F['points'].append(feat({'type': 'Point', 'coordinates': [round(p[1], 7), round(p[0], 7)]}, id='st-' + n, name=n, layer='station', kind='station', kind_zh='車站、車場',
                                start_year=yr(o), end_year=yr(c), name_periods=[{'from': a, 'to': yr(b), 'name': nm} for a, b, nm in STX.get(n, [])] or None))
for n, p in G['br'].items():
    F['points'].append(feat({'type': 'Point', 'coordinates': [round(p[1], 7), round(p[0], 7)]}, id='br-' + n, name=n, layer='junction', kind='junction', kind_zh='分歧點',
                            start_year=None, end_year=None, name_periods=None))
for i, t in enumerate(G.get('tt', [])):
    p = t['center']
    F['points'].append(feat({'type': 'Point', 'coordinates': [round(p[1], 7), round(p[0], 7)]}, id=f'tt-{i}', name='轉車台', layer='turntable', kind='turntable', kind_zh='轉車台',
                            start_year=yr(t.get('o')), end_year=yr(t.get('c')), name_periods=None, radius_m=t.get('r'), source=t.get('src')))

META = {
    'name': '高雄臨港線 1900–2024',
    'description': '高雄臨港線系統各線（主線、支線、專用側線、糖業鐵道、站場股道、車站）的位置與年代。年份區間為 [start_year, end_year)，end_year 當年起不再營運；null＝不詳或仍在營運。',
    'schema': 'data/README.md',
    'crs_note': 'WGS84 經緯度（RFC 7946）；座標順序為 [經度, 緯度]',
    'generated_from': 'pipeline/geo_v13.json + pipeline/tpl.html（pipeline/export_geojson.py）',
    'repository': 'https://github.com/LZong-tw/kaohsiung-harbour-rail-map',
    'attribution': '線形由本研究依歷史地圖與像片基本圖判讀；各線依據見 properties.basis、properties.source 與 METHODS.md。非商業學術用途。',
}


def collection(feats, part):
    return {'type': 'FeatureCollection', **META, 'part': part, 'features': feats}


FILES = {
    f'{BASE}.geojson': collection(F['lines'] + F['sidings'] + F['yard_tracks'] + F['points'], '全部'),
    f'{BASE}_lines.geojson': collection(F['lines'], '主線、支線、輕軌'),
    f'{BASE}_sidings.geojson': collection(F['sidings'], '專用側線、並行股、糖業鐵道'),
    f'{BASE}_yard-tracks.geojson': collection(F['yard_tracks'], '站場股道'),
    f'{BASE}_points.geojson': collection(F['points'], '車站、分歧點、轉車台'),
}


def validate(fc):
    n = 0
    for f in fc['features']:
        g, p = f['geometry'], f['properties']
        cs = g['coordinates']
        pts = [cs] if g['type'] == 'Point' else cs if g['type'] == 'LineString' else [q for part in cs for q in part]
        assert pts and all(120.0 < x < 121.0 and 22.0 < y < 23.0 for x, y in pts), ('座標超出範圍', p.get('id'))
        if g['type'] != 'Point':
            assert all(len(part) >= 2 for part in ([cs] if g['type'] == 'LineString' else cs)), ('線少於兩點', p.get('id'))
        a, b = p.get('start_year'), p.get('end_year')
        assert a is None or b is None or a < b, ('年份顛倒', p.get('id'), a, b)
        assert p.get('id') and p.get('layer') and p.get('kind'), p
        n += 1
    return n


def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    check = '--check' in sys.argv
    os.makedirs(OUT_DIR, exist_ok=True)
    bad = []
    for fn, fc in FILES.items():
        n = validate(fc)
        txt = dumps(fc) + '\n'
        path = os.path.join(OUT_DIR, fn)
        if check:
            if not os.path.exists(path) or open(path).read() != txt:
                bad.append(fn)
        else:
            open(path, 'w').write(txt)
        print(('檢查' if check else '寫出'), fn, n, '筆', round(len(txt.encode()) / 1024), 'KB')
    if bad:
        sys.exit('GeoJSON 與 geo_v13.json／tpl.html 不一致，請重跑 export_geojson.py：' + '、'.join(bad))
