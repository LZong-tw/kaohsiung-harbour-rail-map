import json,math,subprocess,sys,os
from PIL import Image,ImageDraw
G=json.load(open('geo_v13.json'))
LAY0=[('AMCityPlan_1945','png',16,'1945'),('TM25K_1955','png',15,'1955'),('TM25K_1966','png',15,'1966'),('TM25K_1989','jpg',16,'1989')]
LAY=[x for x in LAY0+[('TM25K_1993','jpg',16,'1993'),('TM25K_2001','jpg',16,'2001')] if x[3] in os.environ.get('YRS','1945,1955,1966,1989').split(',')]
def xy(lon,lat,Z):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
def panel(name,pts,lay,box):
    L,ext,Z,lab=lay;S,W,N,E=box
    out=f'/tmp/ev_{abs(hash((name,L)))}.png'
    subprocess.run(['python3','hist.py',L,ext,str(Z),str(W),str(E),str(S),str(N),out],capture_output=True)
    try: im=Image.open(out).convert('RGB')
    except Exception: im=Image.new('RGB',(300,300),'white')
    ox,oy=xy(W,N,Z);sc=300/max(im.width,im.height);im=im.resize((max(1,int(im.width*sc)),max(1,int(im.height*sc))))
    d=ImageDraw.Draw(im,'RGBA')
    P=[((xy(p[1],p[0],Z)[0]-ox)*sc,(xy(p[1],p[0],Z)[1]-oy)*sc) for p in pts]
    d.line(P,fill=(0,200,80,110),width=3);d.rectangle([0,0,44,14],fill='white');d.text((2,1),lab,fill='black')
    c=Image.new('RGB',(300,300),'white');c.paste(im,(0,0));return c
names=sys.argv[2:];rows=[]
for n in names:
    pts=G['extra'][n][0]
    if len(pts)>60: pts=pts[len(pts)//2-30:len(pts)//2+30]
    la=[p[0] for p in pts];lo=[p[1] for p in pts];m=0.0012
    cx,cy=(min(lo)+max(lo))/2,(min(la)+max(la))/2;h=max(max(lo)-min(lo),max(la)-min(la))/2+m
    box=(cy-h,cx-h,cy+h,cx+h)
    row=Image.new('RGB',(305*len(LAY),322),'white');d=ImageDraw.Draw(row);d.text((4,304),n,fill='black')
    for i,ly in enumerate(LAY):row.paste(panel(n,pts,ly,box),(i*305,0))
    rows.append(row)
sheet=Image.new('RGB',(305*len(LAY),322*len(rows)),'white')
for i,r in enumerate(rows):sheet.paste(r,(0,i*322))
sheet.save(sys.argv[1]);print(sheet.size)
