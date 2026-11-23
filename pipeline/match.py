import re
from buildings import official
from osm import *
L = official(); seen=set(); L=[x for x in L if not (x['num'] in seen or seen.add(x['num']))]
code={x['code']:x for x in L}
B=buildings()
STOP=set('the of and for hall building bldg center ctr residence res resid hse house mem purdue university w a m e j'.split())
def toks(s):
    s=re.sub(r'\(.*?\)','',s).lower().replace('é','e').replace('ó','o'); return set(w for w in re.findall(r'[a-z0-9]+',s) if w not in STOP)
M={};amb=[]
for b in B:
    n=b['t'].get('name','')+''; c=None
    m=re.search(r'\(([A-Z0-9-]{2,5})\)\s*$',n)
    for k in (m and m[1], b['t'].get('ref')):
        if k in code: c=k;break
    if c: M[b['id']]=(c,'code',1.0,n);continue
    if not n: continue
    tn=toks(n); best=sorted(((len(tn&toks(x['name']))/max(1,len(tn|toks(x['name']))),x['code']) for x in L),reverse=True)[:2]
    if best[0][0]>=0.3: amb.append((round(best[0][0],2),n,best[0][1],code[best[0][1]]['name'],b['id'],round(b['p'].area)))
if __name__=='__main__':
    print(len(B),'buildings; by code',len(M))
    for a in sorted(amb,reverse=True): print(*a,sep=' | ')
    used={m[0] for m in M.values()}|{a[2] for a in amb}
    print('UNMATCHED',len([1 for x in L if x['code'] not in used]),[x['code'] for x in L if x['code'] not in used])
    print('NAMED NOT MATCHED',[b['t']['name'] for b in B if b['t'].get('name') and b['id'] not in M and b['id'] not in {a[4] for a in amb}])
