import json,math,sys
from PIL import Image,ImageDraw
Z=15
def mp(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=mp(120.262,22.680)
P=lambda la,lo:(mp(lo,la)[0]-OX,mp(lo,la)[1]-OY)
G=json.load(open('geo_ll.json'))
src=sys.argv[1];out=sys.argv[2];box=[float(x) for x in sys.argv[3:7]]  # S W N E
im=Image.open(src).convert('RGB');d=ImageDraw.Draw(im,'RGBA')
for k,s in G['seg'].items():
  if k.startswith('lr'):continue
  d.line([P(*p) for p in s],fill=(255,0,255,140),width=3)
for n,parts in G['extra'].items():
  for s in parts:d.line([P(*p) for p in s],fill=(0,160,255,160),width=3)
x0,y0=P(box[2],box[1]);x1,y1=P(box[0],box[3])
c=im.crop((int(x0),int(y0),int(x1),int(y1)));c=c.resize((c.width*2,c.height*2),Image.LANCZOS);c.save(out);print(c.size)
