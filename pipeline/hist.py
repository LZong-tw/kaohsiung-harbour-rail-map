import math,os,sys,time,urllib.request,io
from PIL import Image
L,ext,Z=sys.argv[1],sys.argv[2],int(sys.argv[3])
W,E,S,N=[float(x) for x in sys.argv[4:8]]
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
x0,y0=xy(W,N);x1,y1=xy(E,S)
os.makedirs(f'h/{L}',exist_ok=True)
img=Image.new('RGB',((int(x1)-int(x0)+1)*256,(int(y1)-int(y0)+1)*256),'white')
for tx in range(int(x0),int(x1)+1):
  for ty in range(int(y0),int(y1)+1):
    f=f'h/{L}/{Z}_{tx}_{ty}.{ext}'
    if not os.path.exists(f):
      try:
        d=urllib.request.urlopen(f'https://gis.sinica.edu.tw/tileserver/file-exists.php?img={L}-{ext}-{Z}-{tx}-{ty}',timeout=30).read()
      except Exception as e: d=b''
      open(f,'wb').write(d);time.sleep(.05)
    try: img.paste(Image.open(f).convert('RGB'),((tx-int(x0))*256,(ty-int(y0))*256))
    except Exception: pass
img=img.crop((int((x0-int(x0))*256),int((y0-int(y0))*256),int((x1-int(x0))*256),int((y1-int(y0))*256)))
img.save(sys.argv[8] if len(sys.argv)>8 else f"h_{L}_{Z}.png");print(img.size)
