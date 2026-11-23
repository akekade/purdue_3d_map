"""List the USGS LiDAR nodes that cover the model area."""
import json,urllib.request
B='https://s3-us-west-2.amazonaws.com/usgs-lidar-public/IN_Statewide_Opt2_B2_2017/'
g=lambda p:json.loads(urllib.request.urlopen(B+p,timeout=60).read())
import sys;sys.path.insert(0,'pipeline')
from common import *
e=g('ept.json');b=e['bounds'];print(e['schema'][:3],[s['name'] for s in e['schema']],e.get('span'),e['srs'].get('horizontal'))
from pyproj import Transformer
t=Transformer.from_crs(4326,3857,always_xy=True)
x0,y0=t.transform(W,S);x1,y1=t.transform(E,N)
H={}
def load(k):
    h=g(f'ept-hierarchy/{k}.json')
    for a,v in h.items():
        H[a]=v
def ok(k):
    d,x,y,z=map(int,k.split('-'));s=(b[3]-b[0])/2**d
    return b[0]+x*s<x1 and b[0]+(x+1)*s>x0 and b[1]+y*s<y1 and b[1]+(y+1)*s>y0
load('0-0-0-0')
todo=True
done=set()
while todo:
    todo=[k for k,v in H.items() if v==-1 and ok(k) and k not in done]
    for k in todo: done.add(k);load(k)
sel={k:v for k,v in H.items() if ok(k) and v>0}
from collections import Counter
c=Counter();n=Counter()
for k,v in sel.items(): c[int(k.split('-')[0])]+=v;n[int(k.split('-')[0])]+=1
for d in sorted(c): print(d,n[d],c[d],'spacing',(b[3]-b[0])/2**d/e['span'])
json.dump(sel,open('data/raw/ept_sel.json','w'));json.dump(e,open('data/raw/ept.json','w'))
