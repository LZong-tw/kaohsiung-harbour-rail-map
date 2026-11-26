import json,math,sys
from PIL import Image,ImageDraw
Z=int(sys.argv[3]);W,N=float(sys.argv[4]),float(sys.argv[5])
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
gx,gy=xy(W,N);ox=int(gx/256)*256+int((gx/256-int(gx/256))*256);oy=int(gy/256)*256+int((gy/256-int(gy/256))*256)
P=lambda la,lo:(xy(lo,la)[0]-ox,xy(lo,la)[1]-oy)
im=Image.open(sys.argv[1]).convert('RGB');d=ImageDraw.Draw(im,'RGBA')
G=json.load(open('geo_v13.json'))
for k,v in G['seg'].items():
  if k.startswith('lr'):continue
  d.line([P(*p) for p in v],fill=(255,0,255,200),width=4)
for k,parts in G['extra'].items():
  for v in parts:d.line([P(*p) for p in v],fill=(0,200,255,220),width=4)
E=json.load(open('q4.json'))['elements']
for e in E:
  if e.get('tags',{}).get('name')=='凱得街':d.line([P(g['lat'],g['lon']) for g in e['geometry']],fill=(255,255,0,200),width=3)
s=float(sys.argv[6]) if len(sys.argv)>6 else .5
im=im.resize((int(im.width*s),int(im.height*s)));im.save(sys.argv[2])
