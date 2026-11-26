import json,math
exec(open('rb2.py').read().split('# ---------- main west line')[0])
G=json.load(open('geo_v9.json'));S=G['seg'];X=G['extra']
Z=15
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
def inv(x,y):
    n=2**Z*256;return [round(math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n)))),6),round(x/n*360-180,6)]
def cv(W,N,sc,disp):
    x0,y0=xy(W,N);return lambda X_,Y_:inv(x0+X_*disp/sc,y0+Y_*disp/sc)
kk=cv(120.302,22.600,5,1.05)
old=[kk(*p) for p in [(1240,660),(1100,690),(980,675),(890,632),(848,655),(832,760),(700,822),(620,850),(520,820),(440,760)]]
old=gs(old,12)
attach(old,S['w3'],0,120);attach(old,S['w2'],-1,120)
X['職訓中心側線（原第一臨港線舊線，今高屏澎東分署）']=[old]
cc=cv(120.296,22.616,4.5,1.02)
hs=[cc(*p) for p in [(385,570),(480,555),(600,640),(800,800),(950,960),(1000,1060),(1000,1150)]]
hs=gs(hs,12);hs.insert(0,hs[0]);attach(hs,S['w1'],0,320)
X['戲獅甲線（往十字船渠北端；1955 年圖實線，是否為鐵道待確認）']=[hs]
json.dump(G,open('geo_v10.json','w'),separators=(',',':'));print('ok')
