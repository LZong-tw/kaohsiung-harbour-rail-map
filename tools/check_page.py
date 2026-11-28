"""在 Chromium 檢查互動地圖成品。用法：python tools/check_page.py _site/index.html"""

import asyncio
import json
import os
import re
import sys
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import which
from threading import Thread
from urllib.parse import quote

from playwright.async_api import async_playwright, expect

YEARS = [1900, 1930, 1945, 1960, 1977, 1995, 2010, 2024]
HARBOUR = '濱線（商港側，往海關碼頭）'
LINYUAN = '糖鐵林園線（鳳山—大寮）'
SECOND_LINE = '第二臨港線（6.8K—草衙車場）'

# 沿著當年可見的路線抽樣，包含虛線與共線路廊。
CHECK_PICKS = """() => {
    const {segments, lines, extras, yards, branches, pickAt} = window.__railCheck;
    const visible = line => window.__map.hasLayer(line);
    const misses = [];
    function sample(name, line) {
        if (!visible(line)) return;
        for (const part of line._parts || []) {
            const step = Math.max(1, Math.floor(part.length / 8));
            for (let i = 0; i < part.length; i += step) {
                if (!pickAt(part[i], 8).some(hit => hit.t === name)) {
                    misses.push(name);
                    return;
                }
            }
        }
    }
    const year = Number(document.querySelector('#sl').value);
    for (const segment of segments) {
        sample(window.__railCheck.routeForYear(segment, year).name, lines[segment.id]);
    }
    for (const line of extras) sample(line._xn, line);
    return {misses, sides: extras.filter(visible).length, yards: yards.filter(visible).length,
            branches: branches.filter(visible).length};
}"""


async def set_year(page, year):
    await page.get_by_role('slider', name='年份').fill(str(year))
    await expect(page.locator('#yr')).to_have_text(str(year))


# 按實際圖層與原始年代核對每個清單按鈕、筆數和圖例，再比對 SVG 的顏色與虛實。
CHECK_LISTS = r"""({year, extraYears}) => {
    const {segments, lines, extras, routeForYear} = window.__railCheck;
    const extrasOn = document.querySelector('#ex').checked;
    const expected = {la: new Map(), lc: new Map()};
    const kinds = new Set();
    const check = (ok, message) => { if (!ok) throw Error(year + ' 側線=' + extrasOn + ' ' + message); };
    function stroke(node) {
        const dash = (node.getAttribute('stroke-dasharray') || '').trim().replace(/[,\s]+/g, ' ');
        return node.getAttribute('stroke') + '/' + dash;
    }
    function add(id, name, o, c, kind, layer, showClosed, enabled = true) {
        const closed = year >= c;
        const visible = enabled && year >= o && (!closed || showClosed);
        check(window.__map.hasLayer(layer) === visible, id + ' 地圖顯示狀態');
        if (!visible) return;
        const key = closed ? 'closed' : kind;
        const record = {name, date: closed ? c : o, kind: key, style: stroke(layer.getElement())};
        expected[closed ? 'lc' : 'la'].set(id, record);
        kinds.add(key);
    }
    for (const s of segments) {
        const route = routeForYear(s, year);
        add(s.id, route.name, s.o, s.c, route.k, lines[s.id], !s.lr);
    }
    for (const layer of extras) {
        const name = layer._xn;
        const main = name === '獅子公園三角線東側（原主線弧線）';
        const kind = main ? 'main' : name.startsWith('糖鐵') ? 'sugar' : 'extra';
        const [o, c] = extraYears[name];
        add('x-' + name, name, o, c, kind, layer, main, main || extrasOn);
    }

    const legend = new Map();
    for (const entry of document.querySelectorAll('#key [data-kind]')) {
        const kind = entry.dataset.kind;
        check(!legend.has(kind) && kinds.has(kind), '多餘或重複圖例 ' + kind);
        legend.set(kind, stroke(entry.querySelector('line')));
    }
    check(legend.size === kinds.size, '缺少圖例 ' + [...kinds].filter(k => !legend.has(k)));
    for (const [list, counts] of [['la', 'na'], ['lc', 'nc']]) {
        let previous = -Infinity;
        const remaining = expected[list];
        const number = Number(document.getElementById(counts).textContent);
        check(number === remaining.size, list + ' 筆數 ' + number + ' 預期 ' + remaining.size);
        for (const button of document.querySelectorAll('#' + list + ' button[data-id]')) {
            const id = button.dataset.id;
            const row = remaining.get(id);
            check(row, list + ' 多餘或重複 ' + id);
            check(button.querySelector('b').textContent === row.name, id + ' 路線名稱');
            check(previous <= row.date, id + ' 年代排序');
            check(stroke(button.querySelector('line')) === row.style, id + ' 清單與地圖線型');
            check(legend.get(row.kind) === row.style, id + ' 圖例與地圖線型 ' + row.kind);
            previous = row.date;
            remaining.delete(id);
        }
        check(!remaining.size, list + ' 漏列 ' + [...remaining.keys()]);
    }
}"""


async def check_annual_lists(page):
    geometry = Path(__file__).resolve().parents[1] / 'pipeline' / 'geo_v13.json'
    extra_years = json.loads(geometry.read_text(encoding='utf-8'))['xy']
    checkbox = page.get_by_role('checkbox', name='顯示側線與糖鐵')
    for year in range(1900, 2027):
        await set_year(page, year)
        for on in [True, False]:
            await checkbox.set_checked(on)
            await page.evaluate(CHECK_LISTS, {'year': year, 'extraYears': extra_years})
    await checkbox.check()
    print('逐年清單、排序、筆數、線型和圖例：1900–2026，側線開／關皆通過')


async def check_railway_history(page):
    cases = [
        (1900, 'west', 'trunk', '縱貫線'),
        (1906, 'zg_s', None, ''), (1906, 'pt', None, ''),
        (1907, 'zg_s', 'trunk', '鳳山支線'), (1907, 'pt', 'trunk', '鳳山支線'),
        (1941, 'zg_s', 'trunk', '縱貫線'), (1941, 'pt', 'trunk', '屏東線'),
        (1941, 'west', 'main', '西臨港線'),
        (2007, 'west', 'main', '西臨港線'), (2008, 'west', 'closed', '西臨港線'),
    ]
    for route_id in ['zg_n', 'zg_s', 'pt']:
        cases.extend([(2017, route_id, 'trunk', ''), (2018, route_id, 'underground', '地下')])
    for year, route_id, kind, text in cases:
        await set_year(page, year)
        button = page.locator(f'.ls button[data-id="{route_id}"]')
        if kind is None:
            await expect(button).to_have_count(0)
            continue
        section = '#lc' if kind == 'closed' else '#la'
        button = page.locator(f'{section} button[data-id="{route_id}"]')
        await expect(button).to_have_count(1)
        if text:
            await expect(button.locator('b')).to_contain_text(text)
        swatch = page.locator(f'#key [data-kind="{kind}"] line')
        await expect(swatch).to_have_count(1)
        for attr in ['stroke', 'stroke-dasharray']:
            assert await button.locator('line').get_attribute(attr) == await swatch.get_attribute(attr), (
                f'{year} {route_id} {kind} {attr}'
            )


TRUNK_GEOMETRY = r"""(y)=>{
 const R=window.__railCheck,m=__map,st=R.stations;
 const sta=n=>{const v=st[n];if(!v||!m.hasLayer(v.mk))return null;
  return {name:v.mk.getTooltip().getContent(),on:v.mk.options.fillColor==='#fff',ll:[v.mk.getLatLng().lat,v.mk.getLatLng().lng]}};
 const g=id=>m.hasLayer(R.lines[id])?R.lines[id].getLatLngs().map(p=>[p.lat,p.lng]):null;
 return {zgs:g('zg_s'),fso:g('fso'),fsoOff:R.lines.fso.options.dashArray==='7 7',
  yards:R.yards.filter(l=>m.hasLayer(l)&&l.getLatLngs()[0].lat<22.627).length,
  old:sta('打狗停車場'),port:sta('高雄港站'),gushan:sta('鼓山'),skc:sta('三塊厝')};
}"""


async def check_trunk_geometry(page):
    """一般鐵路依年代換線形與站位（第 34 輪）：第 33 輪只換了線名，這裡檢查線形與車站本身。"""
    async def at(year):
        await set_year(page, year)
        return await page.evaluate(TRUNK_GEOMETRY, year)
    r = await at(1900)
    assert r['old'] and r['old']['name'] == '打狗' and abs(r['old']['ll'][0] - 22.6265) < 0.0005, r['old']
    assert r['port'] is None and r['yards'] == 0 and r['zgs'] is None and r['fso'] is None, r
    assert r['gushan'] is None and r['skc'] is None, (r['gushan'], r['skc'])
    r = await at(1907)
    assert r['old'] and r['port'] is None and r['yards'] == 0, r
    assert r['zgs'][0][1] > 120.292, ('1907 年鳳山支線不應走 1941 年新線', r['zgs'][0])
    assert r['fso'] and not r['fsoOff'] and r['fso'][0][1] < 120.284, r['fso'][:2]
    r = await at(1908)
    assert r['old'] is None and r['port'] and r['yards'] > 0, r
    r = await at(1929)
    assert r['gushan']['name'] == '田町' and r['gushan']['on'], r['gushan']
    r = await at(1941)
    assert r['zgs'][0][1] < 120.283, ('1941 年起縱貫線經鼓山南側新線', r['zgs'][0])
    assert r['fso'] and not r['fsoOff'], '1941 年後舊線仍在（1942 年圖）'
    r = await at(1950)
    assert r['gushan']['name'] == '鼓山', r['gushan']
    r = await at(1963)
    assert r['fsoOff'], '舊線停用（推定）後轉灰'
    r = await at(1987)
    assert r['skc'] and not r['skc']['on'], r['skc']
    r = await at(2010)
    assert r['gushan'] and not r['gushan']['on'], r['gushan']
    r = await at(2018)
    assert r['gushan']['on'] and r['skc']['on'], (r['gushan'], r['skc'])
    print('一般鐵路線形與站位：1900 打狗停車場、1907 鳳山支線舊線、1908 遷站、1941 新線、田町／鼓山、三塊厝停用期皆通過')


async def check_siding_zoom(page):
    await set_year(page, 1964)
    target = page.locator('#la').get_by_role('button', name=re.compile(re.escape(HARBOUR)))
    await target.click()
    # 確認定位後能看見完整路線，並確實放大到局部街廓。
    await page.wait_for_function("""name => {
        const map = window.__map;
        const tracks = window.__railCheck.extras.filter(line => line._xn === name);
        return tracks.length && map.getZoom() >= 15 &&
            tracks.every(line => map.getBounds().contains(line.getBounds()));
    }""", arg=HARBOUR, timeout=5000)


async def check_boundaries(page):
    for year, status in [(1976, 'absent'), (1977, 'open'), (2010, 'open'), (2011, 'closed')]:
        await set_year(page, year)
        for selector, present in [('#la', status == 'open'), ('#lc', status == 'closed')]:
            await expect(page.locator(selector).get_by_text(SECOND_LINE, exact=True)).to_have_count(int(present))
        actual = await page.evaluate("""() => {
            const line = window.__railCheck.lines.s2;
            if (!window.__map.hasLayer(line)) return 'absent';
            return line.getElement().getAttribute('stroke-dasharray') ? 'closed' : 'open';
        }""")
        assert actual == status, f'{year} {SECOND_LINE} 圖層狀態 {actual}，預期 {status}'

    for name, opening, closing in [(HARBOUR, 1908, 1965), (LINYUAN, 1909, 1992)]:
        for year, present in [(opening - 1, False), (opening, True), (closing - 1, True), (closing, False)]:
            await set_year(page, year)
            visible = await page.evaluate("""name => window.__railCheck.extras
                .filter(line => line._xn === name)
                .map(line => window.__map.hasLayer(line))""", name)
            assert visible and all(state == present for state in visible), f'{year} {name} 可見狀態 {visible}'


async def check_source_popup(page):
    await set_year(page, 1991)
    # 鳳山—大寮段上實際的經緯度；將此處移到畫面中央，用滑鼠點取圖面。
    await page.evaluate("""() => window.__map.setView([22.6116122, 120.3921168], 16, {animate: false})""")
    pos = await page.evaluate("""() => {
        const point = window.__map.latLngToContainerPoint([22.6116122, 120.3921168]);
        return {x: point.x, y: point.y};
    }""")
    await page.locator('#map').click(position=pos)
    popup = page.locator('.leaflet-popup-content')
    for phrase in [LINYUAN, '1909', '1991', '推定', '1989', '1993']:
        await expect(popup).to_contain_text(phrase)


async def check_basemap(page, visible):
    state = await page.evaluate("""() => {
        const map = window.__map;
        let tiles = false;
        map.eachLayer(layer => { if (layer instanceof L.TileLayer) tiles = true; });
        return {tiles, rail: map.hasLayer(window.__railCheck.lines.s2)};
    }""")
    assert state == {'tiles': visible, 'rail': True}, f'現代底圖或 2007 年第二臨港線狀態錯誤：{state}'


async def check_keyboard_and_share(context, page):
    await set_year(page, 2007)
    for key, name in [('Enter', '前鎮橋（今成功橋旁）'), ('Space', SECOND_LINE)]:
        target = page.locator('#la').get_by_role('button', name=re.compile(re.escape(name)))
        await target.focus()
        await expect(target).to_be_focused()
        await page.evaluate("""() => {
            window.routeMoveFinished = false;
            window.__map.once('moveend', () => { window.routeMoveFinished = true; });
        }""")
        await target.press(key)
        await page.wait_for_function('window.routeMoveFinished', timeout=5000)

    get_view = """() => {
        const map = window.__map, center = map.getCenter();
        return [center.lat, center.lng, map.getZoom()];
    }"""
    # 新分頁開同一網址，必須重現原本的年份與視野。
    view = await page.evaluate(get_view)
    await page.get_by_role('checkbox', name='顯示側線與糖鐵').uncheck()
    await page.get_by_role('checkbox', name='顯示現代底圖').uncheck()
    await check_basemap(page, visible=False)
    copied_url = page.url
    restored = await context.new_page()
    try:
        await restored.goto(copied_url)
        await expect(restored.locator('#yr')).to_have_text('2007')
        await expect(restored.get_by_role('checkbox', name='顯示側線與糖鐵')).not_to_be_checked()
        basemap = restored.get_by_role('checkbox', name='顯示現代底圖')
        await expect(basemap).not_to_be_checked()
        await check_basemap(restored, visible=False)
        await basemap.check()
        await check_basemap(restored, visible=True)
        restored_view = await restored.evaluate(get_view)
        for a, b, tolerance in zip(view, restored_view, [0.0001, 0.0001, 0.01]):
            assert abs(a - b) < tolerance, f'分享前 {view}，重開後 {restored_view}'
    finally:
        await restored.close()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@contextmanager
def serve(path):
    document = Path(path).resolve(strict=True)
    handler = partial(QuietHandler, directory=str(document.parent))
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/{quote(document.name)}'
        finally:
            server.shutdown()
            worker.join()


async def main(uri):
    errors = []
    async with async_playwright() as p:
        executable = os.environ.get('CHROME') or which('google-chrome') or which('chromium')
        browser = await p.chromium.launch(executable_path=executable)
        try:
            context = await browser.new_context(viewport={'width': 1600, 'height': 1400})
            # 離線地圖使用系統字型即可，避免外部字型服務影響測試。
            await context.route('https://fonts.googleapis.com/**', lambda route: route.abort())
            context.on('page', lambda page: page.on('pageerror', lambda error: errors.append(str(error))))
            page = await context.new_page()
            await page.goto(uri)
            await expect(page.locator('#yr')).to_have_text('1977')
            for year in YEARS:
                await set_year(page, year)
                result = await page.evaluate(CHECK_PICKS)
                print(f"{year} 側線 {result['sides']} 股道 {result['yards']} 分歧點 {result['branches']}")
                assert not result['misses'], f"{year} 查不到：{result['misses']}"
            await check_annual_lists(page)
            await check_railway_history(page)
            await check_trunk_geometry(page)
            await check_boundaries(page)
            await check_siding_zoom(page)
            await page.goto(uri)
            await check_source_popup(page)
            await page.goto(uri)
            await check_keyboard_and_share(context, page)
            assert not errors, f'JavaScript 錯誤：{errors}'
        finally:
            await browser.close()


if __name__ == '__main__':
    with serve(sys.argv[1] if len(sys.argv) > 1 else 'site/index.html') as uri:
        asyncio.run(main(uri))
