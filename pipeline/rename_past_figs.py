"""scratch/past/ 的 626 張舊圖改成看得懂的檔名（第 36 輪，使用者：「所謂比對圖是包含 Past/ 資料夾裡的，中繼資料更不用說了，都要弄得看得懂才行」）。

舊檔名是第 1–35 輪在 /tmp 隨手取的（a.jpg、c55.jpg、qv_th.jpg…）。新檔名由我逐張看縮圖後命名：「底圖或圖的種類_地點_內容」，
後面接兩個底線與舊檔名，方便對回 WORKLOG 裡當時的說法。對照表在 scratch/past/檔名對照.tsv，本檔讀它來改名並重寫 MANIFEST.tsv。
命名只看縮圖，地點是就圖上認得出的地名寫的；認不出細節的只寫到底圖種類與大略位置。只需跑一次。
"""
import csv, os, subprocess
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scratch', 'past')
SRC = [(('1904', '1921', '1924', '1942', '1944', '1945', '1950', '1955', '1966', '1989', '1993', '2001', '經建版'), '中研院「臺灣百年歷史地圖」圖磚（CC BY-NC）'),
       (('像片基本圖',), '內政部國土測繪中心 1/5000 像片基本圖'),
       (('正射影像',), '內政部國土測繪中心正射影像'),
       (('網頁', '網站', '線上網站', 'OSM'), '本研究網頁或 OSM 底圖（© OpenStreetMap contributors）'),
       (('空白',), '空白圖（該圖層在該位置或縮放層級沒有資料；留作查過的紀錄）')]
def source(n):
    for keys, s in SRC:
        if n.startswith(keys): return s
    return '本研究的拼圖、檢查圖（底圖為上列圖資之一）'
old = {r[0]: r for r in csv.reader(open(os.path.join(D, 'MANIFEST.tsv'), encoding='utf8'), delimiter='\t')}
rows = list(csv.reader(open(os.path.join(D, '檔名對照.tsv'), encoding='utf8'), delimiter='\t'))[1:]
out = [['檔名', '內容', '舊檔名', '當時的暫存檔', '輪次', '原尺寸', '底圖']]
for o, n, desc in rows:
    if os.path.exists(os.path.join(D, o)):
        subprocess.run(['git', 'mv', os.path.join(D, o), os.path.join(D, n)], check=True)
    m = old.get(o, [o, '', o.split('/')[0][1:], '', ''])
    out.append([n, desc.replace('_', '，'), o, m[1], m[2], m[3], source(desc)])
csv.writer(open(os.path.join(D, 'MANIFEST.tsv'), 'w', encoding='utf8', newline=''), delimiter='\t', lineterminator='\n').writerows(out)
print(len(rows), '個檔')
