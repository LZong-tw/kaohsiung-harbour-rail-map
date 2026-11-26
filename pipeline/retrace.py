import json
from tr import *
NE=(22.615,120.300,22.645,120.335);QZB=(22.585,120.300,22.615,120.335);CSB=(22.538,120.335,22.572,120.372);HMB=(22.612,120.265,22.632,120.292)
c=lambda b,x,y:crop2ll(b,x,y)
R={}
R['e1']=trace((22.6086,120.3258),c(NE,1040,820),c(NE,930,430),c(NE,760,318))
R['p205']=trace(c(QZB,1048,645),c(QZB,900,500),c(QZB,632,470))
R['tw']=trace(c(QZB,776,962),c(QZB,1000,952))
R['cy_corner']=trace((22.5704,120.3369),c(CSB,390,135))
R['xg']=trace(c(CSB,390,135),c(CSB,490,300),c(CSB,440,410),c(CSB,330,480))
R['hg']=trace(c(HMB,590,560),c(HMB,1050,830))
json.dump(R,open('retrace.json','w'))
for k,v in R.items():print(k,len(v),v[0],v[-1])
