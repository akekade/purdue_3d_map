import json, pickle, re, struct, hashlib
from heights import *
import sys, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from match import code, L, D as OSMD, pts
    from osm import ll
import shapely
from shapely.geometry import Point, Polygon
R = pickle.load(open(WORK+'/mesh.pkl', 'rb')); MT = json.load(open(ROOT+'/pipeline/materials.json')) if 'json' in globals() else None
top, solid, dtm = load(); Z0 = 150.0
PARK = set('PGG PGU PGW PGNW PGH PGMD TER1 WWG'.split()); DINE = set('FORD WDCT LG RAD'.split())
RES = set('CQE CQW CQS CQNE CQNW OWEN TARK WILY HILL HARR MCUT SHRV ERHT MRDH MRDS PKRF PKRW HCRN HCRS FSTC FSTE FSTW HAWK VAWT WARN WOOD DUHM SHLY WSAN WSAS ADPA ADPB ADPC WEST'.split())
ATH = set('MACK STDM MOLL KFPC LAMB CREC AQUA SCHW TREC BRES BBCH BBPB SBCH SBPB SOCC DYE SPUR VOIN PAGE BOAT HULL TURF'.split())
UTIL = set('WADE NWCP UPOB UPOF UPSB GMF GMGF MMDC MMS1 PRSV PFSB TSWF HMMT LMSB ASB COAL CTEB ADM TEL DMNT'.split())
AIR = set('TERM AERO NISW HGR4 HGR5 HGR6 HGR8 FOPN SIML COMP TH-1 ASB'.split())
STU = set('PMU PMUC KRCH HIKS BCC LCCP AACC NACC PUSH SLAYT SCPA BELL ELLT UC'.split())
GLH = set('HGRH LSR AAPF GMGF'.split())
def cat(cs, t):
    for s, n in ((PARK, 'parking'), (DINE, 'dining'), (RES, 'residence'), (ATH, 'athletics'), (AIR, 'airport'), (UTIL, 'facilities'), (STU, 'student')):
        if any(c in s for c in cs): return n
    if any(c.startswith('HA') and c[2:].isdigit() for c in cs): return 'residence'
    return 'academic'
def hexf(h): h = h.lstrip('#'); return [int(h[i:i+2], 16) for i in (0, 2, 4)]
SID = ['#d9d4c7', '#c9c6bd', '#b9c0c4', '#e2ded4', '#a9a596', '#c7b79c', '#9aa5a8', '#d3cbb9']; CBR = ['#a0705c', '#b08a74', '#94604e']
def mat(r):
    cs, t = r['codes'], r['t']; rnd = int(hashlib.md5(r['id'].encode()).hexdigest()[:6], 16)
    for k in ('photo', 'described'):
        for c in cs:
            if c in MT[k]: return (*MT[k][c], k)
    if any(c in PARK for c in cs) or t.get('building') == 'parking' or t.get('amenity') == 'parking': return '#bdb6a8', '#8a8579', 4, 'Concrete parking deck (assumed)', 'typical'
    if any(c in GLH for c in cs) or t.get('building') == 'greenhouse': return '#c7d6d6', '#eef2f2', 2, 'Greenhouse glass (assumed)', 'typical'
    if any(c in AIR for c in cs) and not set(cs) & {'NISW', 'TERM', 'SIML'}: return '#c3c5c3', '#8f9496', 5, 'Metal hangar cladding (assumed)', 'typical'
    if cs or r['purdue']:
        if any(c in UTIL for c in cs) and not set(cs) & {'WADE', 'TEL', 'DMNT', 'NWCP'}: return '#c2bdb2', '#8f8c86', 5, 'Metal / utility cladding (assumed)', 'typical'
        d = MT['default']; w = hexf(d['wall']); j = (rnd % 17)-8; return '#%02x%02x%02x' % tuple(np.clip([w[0]+j, w[1]+j, w[2]+j//2], 0, 255).astype(int)), d['trim'], d['style'], d['note']+' (assumed)', 'typical'
    bt = t.get('building')
    if r['area'] < 450 and not t.get('name'): return (SID[rnd % 8] if rnd % 10 < 7 else CBR[rnd % 3]), '#efece4', 0, 'Generic', 'generic'
    return (CBR+SID)[rnd % 11], '#d8d4ca', 0 if bt != 'retail' else 1, 'Generic', 'generic'
# ---- buildings.json ----------------------------------------------------------
recs = []; rows = []; LN = json.load(open(WORK+'/lean.json'))
enc = lambda v: int(np.clip(round((v+6)/12*255), 0, 255))
for i, r in enumerate(R):
    t = r['t']; cs = r['codes']; w, tr, st, note, conf = mat(r)
    lv = t.get('building:levels'); lest = False
    try: lv = int(float(lv))
    except (TypeError, ValueError): lv = None
    if lv is None and r.get('levels'): lv = r['levels']
    fl = lv or max(1, round(min(r['h'], max(r.get('eave', r['h']), r['h']*.75))/(3.9 if r['purdue'] else 3.1))); lest = lv is None
    adr = ' '.join(x for x in (t.get('addr:housenumber'), t.get('addr:street')) if x) or None
    o = [dict(n=code[c]['num'], c=c, t=code[c]['name']) for c in cs]
    nm = t.get('name'); nm = re.sub(r'\s*\([A-Z0-9-]{2,5}\)$', '', nm) if nm else None
    recs.append(dict(i=i, off=o, name=(None if o else nm), osm=nm, addr=adr if t.get('addr:street') else None, cat=cat(cs, t) if o or r['purdue'] else 'town', pu=bool(o or r['purdue']),
        h=round(r['h'], 1), hs=r['hsrc'], hn=r.get('hnote'), fl=fl, fe=lest, area=round(r['area']), wn=note, wc=conf, x=round(r['c'][0], 1), y=round(r['c'][1], 1), z=round(r['base']-Z0, 1), wall=w))
    rows.append([*hexf(w), st, *hexf(tr), int(np.clip(fl, 1, 40)), int(np.clip(r['h']/max(fl, 1)*20, 40, 255)), rnd if False else i % 251, 1 if recs[-1]['pu'] else 0, 0, *(enc(LN['q'][k][0]+LN['res'].get(r['id'], [0, 0])[k]) for k in (0, 1)), int(np.clip((r['base']-Z0)/.3, 0, 255)), 0])
recs_js = [{k: v for k, v in x.items() if v not in (None, [], False)} for x in recs]
json.dump(recs_js, open(OUT+'/buildings.json', 'w'), separators=(',', ':'))
np.array(rows, 'u1').tofile(OUT+'/mats.bin')
# ---- meshes: u16 positions (0.1 m, offset by X0/Y0/Z0) -----------------------
def q(a): return np.clip(np.rint(a*10), 0, 65535).astype('u2')
groups = {}; W = []; WB = []
for i, r in enumerate(R):
    if r['T'] is None: continue
    T = r['T'].astype('f8'); c = T[:, :, :2].mean(1); tx = ((c[:, 0]-X0)//TILE).astype(int); ty = ((c[:, 1]-Y0)//TILE).astype(int)
    for k in set(zip(tx.tolist(), ty.tolist())): groups.setdefault(k, []).append((i, T[(tx == k[0]) & (ty == k[1])]))
    if len(r['W']): W.append(r['W']); WB.append(np.full(len(r['W']), i))
meta = {}; P = []; ID = []; IX = []; vo = 0; io_ = 0
for k in sorted(groups):
    s = io_
    for i, T in groups[k]:
        v = np.c_[q(T[..., 0].ravel()-X0), q(T[..., 1].ravel()-Y0), q(T[..., 2].ravel()-Z0)]; u, inv = np.unique(v, axis=0, return_inverse=True); f = inv.reshape(-1, 3)
        f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
        P.append(u); ID.append(np.full(len(u), i, 'u2')); IX.append((f+vo).astype('u4')); vo += len(u); io_ += f.size
    meta[f'{k[0]}_{k[1]}'] = [s, io_-s]
P = np.vstack(P); ID = np.concatenate(ID); IX = np.concatenate(IX).ravel()
W = np.concatenate(W).astype('f8'); WB = np.concatenate(WB).astype('u2')
v = np.stack([q(W[..., 0]-X0), q(W[..., 1]-Y0), q(W[..., 2]-Z0)], -1)
wh = np.zeros(W.shape[:2]); wh[:, 2:] = W[:, 2:, 2]-W[:, :2, 2][:, ::-1]
wu = np.stack([q(np.maximum(W[..., 3], 0)), q(W[..., 4]), q(wh)], -1)
import gzip
with gzip.open(OUT+'/geo.bin.gz', 'wb', 9) as f:
    for a in (P.astype('u2'), ID.astype('u2'), v.astype('u2'), wu.astype('u2'), WB, np.zeros((-(P.size+ID.size+v.size+wu.size+WB.size)) % 2, 'u2'), IX.astype('u4')): f.write(a.tobytes())
# ---- terrain, 10 m grid ------------------------------------------------------
gx = np.arange(X0, X1+1, 10); gy = np.arange(Y0, Y1+1, 10); GX, GY = np.meshgrid(gx, gy); Z = sample(dtm, 2.0, GX, GY); q(Z-Z0).tofile(OUT+'/terrain.bin')
if os.path.exists(OUT+'/geo.bin'): os.remove(OUT+'/geo.bin')
# ---- trees -------------------------------------------------------------------
S = 1.0; nx = int((X1-X0)/S); ny = int((Y1-Y0)/S)
tg = np.array(top).reshape(ny, 2, nx, 2).max((1, 3)); c = (np.mgrid[0:ny, 0:nx]+.5)*S; hag = tg-sample(dtm, 2.0, X0+c[1], Y0+c[0]); hag[tg < 0] = 0
from PIL import Image, ImageDraw
im = Image.new('L', (nx, ny)); dr = ImageDraw.Draw(im)
for r in R:
    for g in getattr(r['poly'].buffer(2.2), 'geoms', [r['poly'].buffer(2.2)]): dr.polygon([((x-X0)/S, (y-Y0)/S) for x, y in g.exterior.coords], fill=1)
for e in OSMD:     # keep roads, runways and water clear
    t = e.get('tags', {}); g = e.get('geometry')
    if e['type'] != 'way' or not g: continue
    if t.get('highway') in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'service') or t.get('aeroway') in ('runway', 'taxiway'): dr.line([((x-X0)/S, (y-Y0)/S) for x, y in pts(g)], fill=1, width=5 if t['highway' if 'highway' in t else 'aeroway'] in ('residential', 'service', 'unclassified') else 9)
bm = np.array(im) > 0
hag[bm | (hag > 34)] = 0; can = nd.uniform_filter((hag > 2.5).astype('f4'), 5); sm = nd.gaussian_filter(hag, 1.0); pk = (nd.maximum_filter(sm, 7) == sm) & (hag > 4) & (can > .35)
yy, xx = np.where(pk); hh = hag[yy, xx]; tx = X0+(xx+.5)*S; ty = Y0+(yy+.5)*S
cx = np.array([[r['c'][0], r['c'][1]] for r in R if r['codes']]); from scipy.spatial import cKDTree
d, _ = cKDTree(cx).query(np.c_[tx, ty]); rng = np.random.default_rng(1); keep = (d < 220) | (rng.random(len(d)) < .33); tx, ty, hh, d = tx[keep], ty[keep], hh[keep], d[keep]
o = np.argsort(d); tx, ty, hh = tx[o], ty[o], hh[o]
Tr = np.c_[q(tx-X0), q(ty-Y0), q(sample(dtm, 2.0, tx, ty)-Z0), q(hh)]; Tr.astype('u2').tofile(OUT+'/trees.bin')
json.dump(dict(lean=LN['q'], x0=X0, y0=Y0, x1=X1, y1=Y1, z0=Z0, tile=TILE, nb=len(R), rv=len(P), ri=len(IX), wq=len(W), roofs=meta, tnx=len(gx), tny=len(gy), tstep=10, trees=len(Tr)), open(OUT+'/meta.json', 'w'), separators=(',', ':'))
# ---- reports -----------------------------------------------------------------
used = {c for r in R for c in r['codes']}; un = [x for x in L if x['code'] not in used]
open(ROOT+'/data/unmatched.md', 'w').write('# Listed Purdue buildings with no identified footprint\n\n'+'\n'.join(f"- {x['num']} {x['code']} {x['name']}" for x in un)+'\n')
from collections import Counter
print('listed', len(L), 'placed', len(used), 'unplaced', len(un), 'clickable official footprints', sum(1 for r in R if r['codes']))
print('wall conf', Counter(x['wc'] for x in recs if x.get('off')), 'cats', Counter(x['cat'] for x in recs if x.get('off')))
print('verts', len(P), 'tris', len(IX)//3, 'walls', len(W), 'trees', len(Tr)); [print(f, os.path.getsize(OUT+'/'+f)//1024, 'KB') for f in sorted(os.listdir(OUT)) if os.path.isfile(OUT+'/'+f)]
print('unplaced:', ' '.join(x['code'] for x in un))
