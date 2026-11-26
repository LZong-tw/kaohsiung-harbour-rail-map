import json,math
exec(open('final2.py').read().split('# ---- east line')[0])
G=json.load(open('geo_r.json'));S=G['seg'];X=G['extra']
def snap(L,targets,idx,tol=200):
    p=L[idx];best=None
    for tk in targets:
        T=S[tk] if isinstance(tk,str) else tk
        r=nearest_on(p,T)
        if best is None or r[0]<best[0]:best=(r[0],T,r[1],r[2],r[3])
    if best and best[0]<tol:
        d,T,i,q,t=best
        if 0<t<1:T.insert(i+1,q)
        else:q=T[i] if t==0 else T[i+1]
        L[idx]=q
    else:print('nosnap',best and round(best[0]))
    return L
def join(a,b):  # make b start exactly at a's end (chain)
    S[b][0]=S[a][-1]
snap(S['west'],['zg_n','zg_s'],-1)
snap(S['nb'],['west'],0)
join('nb','w0');join('w0','w1');join('w1','br');S['e1'][0]=S['br'][-1]
snap(S['e1'],['pt'],-1,300)
snap(S['zd'],['w1'],0);snap(S['s2'],['br','w1'],0);S['s2b'][0]=S['s2'][-1]
snap(S['c2'],['s2'],0);snap(S['c3'],['s2','s2b'],0)
snap(S['hm'],['west','nb'],0,250);snap(S['ob'],['nb','west'],0,300)
snap(X['濱線（商港側，往海關碼頭）'][0],[S['hm']],0)
snap(X['中岸壁線'][0],[S['ob']],0);snap(X['裏岸壁線'][0],[X['中岸壁線'][0]],0)
snap(X['中化公司／硫酸錏廠側線'][0],['e1','br'],0)
snap(X['臺糖倉庫側線'][0],['br','s2','w1'],0)
snap(X['小港糖廠線'][0],['s2b'],0)
snap(X['淺野線（臺泥側線）'][0],['zg_n','zg_s','west'],0,150)
G['br']={'5.4K 中島線分歧':S['zd'][0],'6.8K 第二臨港線分歧':S['s2'][0]}
G['st']['前鎮車場']=S['br'][-1];G['st']['高雄港站']=S['nb'][0]
for n,ref,seg in [('苓雅寮車場',(22.6158,120.2950),'w1'),('新光',(22.6108,120.3012),'w1'),('中島車場',(22.6005,120.2985),'zd'),('高雄機廠',(22.6135,120.3290),'e1')]:
    G['st'][n]=nearest_on(ref,S[seg])[2]
json.dump(G,open('geo_t.json','w'),separators=(',',':'));print('ok')
