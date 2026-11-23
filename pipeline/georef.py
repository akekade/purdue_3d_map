"""Georeference Purdue's campus map PDF labels; report code -> footprint proposals."""
import pypdfium2 as pdfium, json, re
from shapely.geometry import Point
from shapely.strtree import STRtree
from match import *
pg=pdfium.PdfDocument(RAW+'/campusmap.pdf')[1]; tp=pg.get_textpage()
n=tp.count_rects(); lab=[]
for i in range(n):
    l,b,r,t=tp.get_rect(i); s=tp.get_text_bounded(l,b,r,t).strip()
    if s in code: lab.append((s,(l+r)/2,(b+t)/2,t-b))
print(n,len(lab))
pos={}
for s,x,y,h in lab: pos.setdefault(s,[]).append((x,y))
cen={M[b['id']][0]:b['p'].representative_point() for b in B if b['id'] in M}
P=[(s,*pos[s][0],cen[s].x,cen[s].y) for s in pos if s in cen and len(pos[s])==1]
A=np.array([[x,y,1] for _,x,y,_,_ in P]);T=np.array([[u,v] for *_,u,v in P]);ok=np.ones(len(P),bool)
for _ in range(8):
    C,*_=np.linalg.lstsq(A[ok],T[ok],rcond=None);r=np.hypot(*(A@C-T).T);ok=r<max(60,np.median(r)*3)
print('fit',len(P),ok.sum(),'median res m',np.median(r[ok]).round(1)); print(C)
print('outliers',[(P[i][0],round(r[i])) for i in range(len(P)) if not ok[i]])
json.dump(C.tolist(),open(WORK+'/georef.json','w'))
def to(x,y): return np.array([x,y,1])@C
used={m[0] for m in M.values()}|{a[2] for a in amb}
free=[b for b in B if b['id'] not in M and b['id'] not in {a[4] for a in amb}]
tr=STRtree([b['p'] for b in free])
for s in sorted(pos):
    if s in used: continue
    for x,y in pos[s]:
        u,v=to(x,y);q=Point(u,v);c=sorted((free[i]['p'].distance(q),-free[i]['p'].area,free[i]['id'],free[i]['t'].get('name') or free[i]['t'].get('building')) for i in tr.query(q.buffer(60)))[:3]
        print(s,code[s]['name'][:34],(round(u),round(v)),[(round(d),round(-a),i,nm) for d,a,i,nm in c])
im=pg.render(scale=5).to_pil(); im.save(WORK+'/campusmap.png'); print(im.size)
