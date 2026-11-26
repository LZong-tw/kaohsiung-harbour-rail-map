import json,math,sys
from PIL import Image,ImageDraw
src,Z,W,N,out,dlat=sys.argv[1],int(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),sys.argv[5],float(sys.argv[6])
sc=float(sys.argv[7]) if len(sys.argv)>7 else 1
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
x0,y0=xy(W,N);ox=int(x0)*256+int((x0-int(x0))*256);oy=int(y0)*256+int((y0-int(y0))*256)
P=lambda la,lo:((xy(lo,la+dlat)[0]*256-ox)*sc,(xy(lo,la+dlat)[1]*256-oy)*sc)
im=Image.open(src).convert('RGB');im=im.resize((int(im.width*sc),int(im.height*sc)),Image.LANCZOS);d=ImageDraw.Draw(im,'RGBA')
G=json.load(open('geo_v13.json'))
for k,v in G['seg'].items():
  if k.startswith('lr'):continue
  d.line([P(*p) for p in v],fill=(255,0,255,170),width=3)
for k,parts in G['extra'].items():
  for v in parts:d.line([P(*p) for p in v],fill=(0,150,255,170),width=3)
for e in json.load(open('q7.json'))['elements']:
  t=e.get('tags',{})
  if e['type']=='way' and 'geometry' in e and (t.get('railway') in ('rail','disused','abandoned') ):
    d.line([P(g['lat'],g['lon']) for g in e['geometry']],fill=(0,200,0,150),width=2)
for la,lo,c in [(22.62173,120.27556,(255,0,0)),(22.62467,120.27725,(255,120,0))]:
  x,y=P(la,lo);d.ellipse((x-7,y-7,x+7,y+7),outline=c,width=3)
# grid every 0.001 deg
for k in range(0,40):
  lo=120.270+k*0.001;x,_=P(22.62,lo);d.line([(x,0),(x,im.height)],fill=(0,0,255,40));d.text((x+2,2),f'{lo:.3f}',fill=(0,0,255))
  la=22.610+k*0.001;_,y=P(la,120.28);d.line([(0,y),(im.width,y)],fill=(0,0,255,40));d.text((2,y+2),f'{la:.3f}',fill=(0,0,255))
im.save(out);print(im.size)
