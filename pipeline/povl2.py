import json,math,sys
from PIL import Image,ImageDraw
src,out,Z,W,N=sys.argv[1],sys.argv[2],int(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]);s=float(sys.argv[6]);gj=sys.argv[7] if len(sys.argv)>7 else 'geo_v13.json'
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
ox,oy=xy(W,N);P=lambda la,lo:((xy(lo,la)[0]-ox)*s,(xy(lo,la)[1]-oy)*s)
im=Image.open(src).convert('RGB');im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
T=json.load(open('/tmp/tri.json'))
for e in T['elements']:
  if e['type']=='relation' and e['tags'].get('name') in ('台電經貿一次配電變電所','勞動部勞動力發展署高屏澎東分署'):
    b=e['bounds'];d.rectangle([P(b['maxlat'],b['minlon']),P(b['minlat'],b['maxlon'])],outline=(255,230,0,255),width=2)
G=json.load(open(gj))
for k,v in G['seg'].items():
  d.line([P(*p) for p in v],fill=(255,0,255,170) if not k.startswith('lr') else (0,0,0,60),width=3)
for k,parts in G['extra'].items():
  for v in parts:d.line([P(*p) for p in v],fill=(0,170,255,190),width=3)
for x in range(0,im.width,100):d.text((x,2),str(x),fill=(255,0,0))
for y in range(0,im.height,100):d.text((2,y),str(y),fill=(255,0,0))
im.save(out)
