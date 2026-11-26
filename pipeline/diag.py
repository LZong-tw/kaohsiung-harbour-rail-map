import json,math
from PIL import Image,ImageDraw,ImageFont
Z=15
def xy(lon,lat):
    n=2**Z;x=(lon+180)/360*n*256;y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256;return x,y
W,N=120.258,22.682;ox,oy=xy(W,N)
P=lambda lon,lat:(xy(lon,lat)[0]-ox,xy(lon,lat)[1]-oy)
im=Image.open('base_full.png').convert('L').convert('RGB')
im=Image.blend(im,Image.new('RGB',im.size,'white'),0.5)
d=ImageDraw.Draw(im)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22) if __import__('os').path.exists('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc') else None
col={'rail':'black','disused':'orange','abandoned':'red','light_rail':'green','subway':None,'platform':None,'construction':None,'proposed':None}
E=json.load(open('rail.json'))['elements']
for e in E:
  if e['type']!='way':continue
  t=e.get('tags',{});r=t.get('railway')
  if r is None:
    r='abandoned' if any('railway' in k for k in t) else None
  c=col.get(r,'purple')
  if not c:continue
  pts=[P(g['lon'],g['lat']) for g in e['geometry']]
  d.line(pts,fill=c,width=5 if r!='rail' else 4)
  if r in('disused','abandoned') or (r=='rail' and not t.get('name')):
    m=pts[len(pts)//2];d.text(m,str(e['id'])[-5:],fill='blue',font=font)
im.save('diag.png');im.resize((im.width//2,im.height//2)).save('diag_s.png')
