import json,sys
from tr import ll2px
from PIL import Image,ImageDraw
R=json.load(open('retrace.json'))
box=[float(x) for x in sys.argv[2:6]]
im=Image.open('h_TM25K_1989_15.png').convert('RGB');d=ImageDraw.Draw(im,'RGBA')
for k,s in R.items():d.line([ll2px(*p) for p in s],fill=(0,170,0,170),width=3)
x0,y0=ll2px(box[2],box[1]);x1,y1=ll2px(box[0],box[3])
c=im.crop((int(x0),int(y0),int(x1),int(y1)));c.resize((c.width*2,c.height*2)).save(sys.argv[1])
