import json,math,sys,numpy as np
from qa import resample,toll
W=np.load('water.npy')
Z=15
def xy(lon,lat):
    n=2**Z;return (lon+180)/360*n*256,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n*256
OX,OY=xy(120.262,22.680)
G=json.load(open(sys.argv[1]))
lines={k:v for k,v in G['seg'].items() if not k.startswith('lr')};lines.update({k:v[0] for k,v in G['extra'].items()})
for n,L in lines.items():
    R,s=resample(L,2);w=np.array([W[int(xy(toll(v)[1],toll(v)[0])[1]-OY),int(xy(toll(v)[1],toll(v)[0])[0]-OX)] for v in R]);i=0
    while i<len(w):
        if w[i]:
            j=i
            while j<len(w) and w[j]:j+=1
            if s[j-1]-s[i]>=20:print(n,round(s[i]),round(s[j-1]),[round(x,5) for x in toll(R[(i+j)//2])])
            i=j
        else:i+=1
