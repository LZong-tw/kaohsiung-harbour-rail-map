import math,os,time,urllib.request
from PIL import Image
Z=15
def xy(lon,lat):
    n=2**Z;x=(lon+180)/360*n;y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n;return x,y
W,E,S,N=120.258,120.422,22.540,22.682   # 第 31 輪：東界由 120.372 擴到 120.422（林園線到大寮）
x0,y0=xy(W,N);x1,y1=xy(E,S)
tx0,ty0,tx1,ty1=int(x0),int(y0),int(x1),int(y1)
os.makedirs('t',exist_ok=True)
img=Image.new('RGB',((tx1-tx0+1)*256,(ty1-ty0+1)*256))
for tx in range(tx0,tx1+1):
  for ty in range(ty0,ty1+1):
    f=f't/{tx}_{ty}.png'
    if not os.path.exists(f):
      r=urllib.request.Request(f'https://tile.openstreetmap.org/{Z}/{tx}/{ty}.png',headers={'User-Agent':'KaohsiungRailHistoryMap/1.0 (personal research)'})
      open(f,'wb').write(urllib.request.urlopen(r,timeout=30).read());time.sleep(0.15)
    img.paste(Image.open(f).convert('RGB'),((tx-tx0)*256,(ty-ty0)*256))
# crop to bbox
cx0,cy0=(x0-tx0)*256,(y0-ty0)*256;cx1,cy1=(x1-tx0)*256,(y1-ty0)*256
img=img.crop((int(cx0),int(cy0),int(cx1),int(cy1)))
img.save('base_full.png');print(img.size,(tx1-tx0+1)*(ty1-ty0+1),'tiles')
