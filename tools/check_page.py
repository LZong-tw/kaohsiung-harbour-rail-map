"""在 Chromium 檢查互動地圖成品。用法：python tools/check_page.py _site/index.html"""

import asyncio
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
    for (const segment of segments) sample(segment.name, lines[segment.id]);
    for (const line of extras) sample(line._xn, line);
    return {misses, sides: extras.filter(visible).length, yards: yards.filter(visible).length,
            branches: branches.filter(visible).length};
}"""


async def set_year(page, year):
    await page.get_by_role('slider', name='年份').fill(str(year))
    await expect(page.locator('#yr')).to_have_text(str(year))


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
    copied_url = page.url
    restored = await context.new_page()
    try:
        await restored.goto(copied_url)
        await expect(restored.locator('#yr')).to_have_text('2007')
        await expect(restored.get_by_role('checkbox', name='顯示側線與糖鐵')).not_to_be_checked()
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
            await check_boundaries(page)
            await check_source_popup(page)
            await page.goto(uri)
            await check_keyboard_and_share(context, page)
            assert not errors, f'JavaScript 錯誤：{errors}'
        finally:
            await browser.close()


if __name__ == '__main__':
    with serve(sys.argv[1] if len(sys.argv) > 1 else 'site/index.html') as uri:
        asyncio.run(main(uri))
