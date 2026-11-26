import json,math,sys
from PIL import Image,ImageDraw
Z=15
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680);base=Image.open('base.png').convert('RGB');G=json.load(open('geo_v13.json'))
def crop(lat,lon,half,s,out):
    x0,y0=xy(lon-half,lat+half*0.92);x1,y1=xy(lon+half,lat-half*0.92)
    c=base.crop((int(x0-OX),int(y0-OY),int(x1-OX),int(y1-OY))).resize((int((x1-x0)*s),int((y1-y0)*s)),Image.LANCZOS);d=ImageDraw.Draw(c)
    T=lambda p:((xy(p[1],p[0])[0]-int(x0-OX)-OX)*s,(xy(p[1],p[0])[1]-int(y0-OY)-OY)*s)
    for k,v in G['seg'].items():
        if not k.startswith('lr'):d.line([T(p) for p in v],fill=(200,0,200),width=3)
    for k,v in G['extra'].items():d.line([T(p) for p in v[0]],fill=(0,140,255),width=3)
    c.save(out)
for a in sys.argv[1:]:
    la,lo,h,s,o=a.split(',');crop(float(la),float(lo),float(h),float(s),o)
