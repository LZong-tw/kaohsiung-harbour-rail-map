import json,math,sys,subprocess
from PIL import Image,ImageDraw
# usage: z15ov.py LAYER EXT Z name W E S N scale
LY,EX,Z,name=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
W,E,S,N,s=map(float,sys.argv[5:10])
subprocess.run(['python3','hist.py',LY,EX,str(Z),str(W),str(E),str(S),str(N),f'/tmp/{name}_raw.png'],check=True,capture_output=True)
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
ox,oy=xy(W,N);P=lambda la,lo:((xy(lo,la)[0]-ox)*s,(xy(lo,la)[1]-oy)*s)
im=Image.open(f'/tmp/{name}_raw.png').convert('RGB');im=im.resize((int(im.width*s),int(im.height*s)),Image.BICUBIC);d=ImageDraw.Draw(im,'RGBA')
G=json.load(open('geo_v13.json'))
for k,v in G['seg'].items():
    if not k.startswith('lr'):d.line([P(*p) for p in v],fill=(0,120,255,110),width=2)
for k,v in G['extra'].items():d.line([P(*p) for p in v[0]],fill=(0,200,120,130),width=2)
for x in range(0,im.width,100):d.text((x+2,2),f'{W+x/s/(2**Z*256/360):.4f}',fill=(200,0,0))
for y in range(0,im.height,100):
    n=2**Z*256;gy=oy+y/s;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*gy/n))))
    d.text((2,y+2),f'{lat:.4f}',fill=(200,0,0))
im.save(f'/tmp/{name}.png');print(name,im.size)
