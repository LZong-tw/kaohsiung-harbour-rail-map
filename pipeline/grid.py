import sys
from PIL import Image,ImageDraw
src,out=sys.argv[1],sys.argv[2];x0,y0,x1,y1=[int(v) for v in sys.argv[3:7]];s=float(sys.argv[7]) if len(sys.argv)>7 else 2
im=Image.open(src).convert('RGB').crop((x0,y0,x1,y1));im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS);d=ImageDraw.Draw(im)
st=50
for x in range((x0//st+1)*st,x1,st):X=(x-x0)*s;d.line([(X,0),(X,im.height)],fill=(0,120,255),width=1);d.text((X+2,2),str(x),fill=(0,0,255))
for y in range((y0//st+1)*st,y1,st):Y=(y-y0)*s;d.line([(0,Y),(im.width,Y)],fill=(0,120,255),width=1);d.text((2,Y+2),str(y),fill=(0,0,255))
im.save(out);print(im.size)
