"""第 36 輪比對圖改成看得懂的檔名（使用者要求：檔名要寫成有意義的字眼）。
舊名是工作時隨手取的縮寫；這裡依「地點_內容_年份」改名，並把各文件、腳本裡的引用一起換掉。只需跑一次，留作對照表。"""
import os, re, subprocess, sys
D = os.path.join(os.path.dirname(__file__), '..', 'scratch', 'r36')
RULES = [  # (舊檔名樣式, 新檔名)
    (r'fix_a205_(\d+)', r'205兵工廠側線_修正後疊圖_\1'), (r'fix_alkali_(\d+)', r'台灣鹼業線_修正後疊圖_\1'),
    (r'fix_fan_(\d+)', r'成功二路西側股道_修正後疊圖_\1'), (r'fix_lizinei_(\d+)', r'台糖籬仔內線_修正後疊圖_\1'),
    (r'fix_steel_(\d+)', r'臺機鋼品廠線_修正後疊圖_\1'), (r'fix_taipower_(\d+)', r'台電南部發電所環線_修正後疊圖_\1'),
    (r'a205_(\d+)', r'205兵工廠側線_修正前疊圖_\1'), (r'fan_south_(\d+)', r'成功二路西側股道南段_修正前疊圖_\1'),
    (r'fan_(\d+)', r'成功二路西側股道_修正前疊圖_\1'),
    (r'lizinei_link_(\d+)', r'台糖籬仔內線_凱旋四路接點_\1'), (r'lizinei_north_(\d+)', r'台糖籬仔內線_北段_\1'),
    (r'lizinei_(\d+)', r'台糖籬仔內線_全段_\1'),
    (r'mob_zd_(\d+)', r'網頁截圖_手機_中島_\1年'), (r'page_zd_(\d+)', r'網頁截圖_桌機_中島_\1年'),
    (r's2_(\d+)', r'第二臨港線北段_疊圖_\1'), (r'steel_(\d+)', r'臺機鋼品廠線_修正前疊圖_\1'),
    (r'symbol_1983_bundle', '像片基本圖符號_多股並行_1983'), (r'symbol_1983_double_track_trunk', '像片基本圖符號_複線_縱貫線_1983'),
    (r'symbol_1983_two_single_tracks', '像片基本圖符號_兩條單線_1983'),
    (r'taipower_(\d+)', r'台電南部發電所線_修正前疊圖_\1'), (r'triangle_1998_overview', '前鎮三角線一帶_總覽_1998'),
    (r'tsg_kaixuan_(\d+)', r'臺糖倉庫_中山四路凱旋四路口_\1'), (r'xiaogang_(\d+)', r'往小港方向_台糖轉運線_\1'),
    (r'zd_new_north_(\d+)', r'中島線本線_北半_依像片基本圖重定_\1'), (r'zd_new_(\d+)', r'中島線本線_依像片基本圖重定_\1'),
    (r'zd_trace_(\d+)', r'中島_自動描線底稿_\1'),
    (r'zdm_north_(\d+)', r'中島北半_人工定線疊圖_\1'), (r'zdm_south_(\d+)', r'中島南半與中島車場_人工定線疊圖_\1'),
    (r'zhongdao_1983_overview', '中島_總覽_1983'), (r'zhongdao_east_(\d+)', r'中島東岸_修正前疊圖_\1'),
    (r'zhongdao_north_1983_a', '中島北段_修正前疊圖_1983_西'), (r'zhongdao_north_1983_b', '中島北段_修正前疊圖_1983_東'),
    (r'zhongdao_west_(\d+)', r'中島西岸_修正前疊圖_\1'), (r'zhongdao_yard_(\d+)', r'中島車場_擴建路_修正前疊圖_\1'),
]
REFS = ['WORKLOG.md', 'METHODS.md', 'FILES.md', 'SOURCES.md', 'CLAUDE.md', 'pipeline/r36_figs.py', 'pipeline/manual_lines.py', 'pipeline/zhongdao.py', 'pipeline/archive_figs.py']
root = os.path.join(os.path.dirname(__file__), '..')
table = []
for f in sorted(os.listdir(D)):
    stem, ext = os.path.splitext(f)
    for pat, new in RULES:
        if re.fullmatch(pat, stem):
            table.append((f, re.sub(pat, new, stem) + ext)); break
for old, new in table:
    subprocess.run(['git', 'mv', os.path.join(D, old), os.path.join(D, new)], check=True)
for r in REFS:
    p = os.path.join(root, r); s = open(p, encoding='utf8').read(); t = s
    for old, new in sorted(table, key=lambda x: -len(x[0])):
        t = t.replace('r36/' + old, 'r36/' + new)
    if t != s: open(p, 'w', encoding='utf8').write(t)
with open(os.path.join(D, '檔名對照.tsv'), 'w', encoding='utf8') as o:
    o.write('舊檔名\t新檔名\n' + ''.join(f'{a}\t{b}\n' for a, b in table))
print(len(table), '個檔改名')
