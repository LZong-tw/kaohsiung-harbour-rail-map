import math,os,sys,time,urllib.request
from PIL import Image
L,Z=sys.argv[1],int(sys.argv[2]);W,E,S,N=[float(x) for x in sys.argv[3:7]];out=sys.argv[7]
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
x0,y0=xy(W,N);x1,y1=xy(E,S);os.makedirs(f'n/{L}',exist_ok=True)
img=Image.new('RGB',((int(x1)-int(x0)+1)*256,(int(y1)-int(y0)+1)*256))
for tx in range(int(x0),int(x1)+1):
  for ty in range(int(y0),int(y1)+1):
    f=f'n/{L}/{Z}_{tx}_{ty}'
    if not os.path.exists(f):
      try:open(f,'wb').write(urllib.request.urlopen(f'https://wmts.nlsc.gov.tw/wmts/{L}/default/GoogleMapsCompatible/{Z}/{ty}/{tx}',timeout=30).read())
      except Exception as e:open(f,'wb').write(b'')
    try:img.paste(Image.open(f).convert('RGB'),((tx-int(x0))*256,(ty-int(y0))*256))
    except Exception:pass
img=img.crop((int((x0-int(x0))*256),int((y0-int(y0))*256),int((x1-int(x0))*256),int((y1-int(y0))*256)));img.save(out);print(img.size)
