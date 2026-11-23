"""Ground/roof textures: 2023 aerial. Roofs keep true colour; lawns are greened (photo was taken leaf-off)."""
import pickle
from PIL import Image, ImageDraw
from scipy import ndimage as nd
from common import *
R = pickle.load(open(WORK+'/mesh.pkl', 'rb')); D = OUT+'/tex'; os.makedirs(D, exist_ok=True)
from shapely.geometry import box
from shapely.strtree import STRtree
G = [r['poly'].buffer(1.5) for r in R]; tr = STRtree(G); C = STRtree([r['poly'] for r in R if r['codes']])
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    from osm import D as OD, poly
WP = []
for e in OD:
    t = e.get('tags', {})
    if t.get('natural') == 'water' or t.get('waterway') == 'riverbank':
        q = poly(e) if e['type'] != 'node' else None
        if q: WP.append(q)
WT = STRtree(WP); print('water polys', len(WP))
ov = Image.new('RGB', (4400, 4000)); tot = 0; hi = []
for x in range(X0, X1, TILE):
    for y in range(Y0, Y1, TILE):
        im = Image.open(f'{RAW}/aerial/{x}_{y}.jpg').convert('RGB'); n = 1024; a = np.asarray(im.resize((n*2, n*2)), 'f4')/255; N = n*2
        m = Image.new('L', (N, N)); d = ImageDraw.Draw(m); mw = Image.new('L', (N, N)); dw = ImageDraw.Draw(mw); s = N/TILE
        for i in tr.query(box(x, y, x+TILE, y+TILE)):
            for g in getattr(G[i], 'geoms', [G[i]]): d.polygon([((px-x)*s, N-(py-y)*s) for px, py in g.exterior.coords], fill=255)
        for i in WT.query(box(x, y, x+TILE, y+TILE)):
            for g in getattr(WP[i], 'geoms', [WP[i]]): dw.polygon([((px-x)*s, N-(py-y)*s) for px, py in g.exterior.coords], fill=255)
        wat = np.asarray(mw, 'f4')[..., None]/255
        roof = np.asarray(m, 'f4')[..., None]/255
        a = np.clip(a*1.18, 0, 1)
        r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]; lum = a.mean(-1)
        veg = np.clip((g_-b_)/np.maximum(g_, .05)*8.5-.5, 0, 1)*np.clip((g_/np.maximum(r_, .02)-.88)*11, 0, 1)*np.clip((.8-lum)*4, 0, 1)
        veg = nd.gaussian_filter(veg, 1.2)[..., None]
        grn = np.stack([lum*.62+.02, lum*.88+.05, lum*.40+.01], -1); out = a*(1-veg*.85)+grn*veg*.85
        out = out*(1-roof)*(1-wat)+a*roof*(1-wat)+a*wat*np.array([.72, .86, .92])
        o = Image.fromarray((np.clip(out, 0, 1)*255).astype('u1')); big = len(C.query(box(x-60, y-60, x+TILE+60, y+TILE+60))) > 0
        hi += [f'{(x-X0)//TILE}_{(y-Y0)//TILE}'] if big else []
        k = 2048 if big else 1024; p = f'{D}/{(x-X0)//TILE}_{(y-Y0)//TILE}.webp'; o.resize((k, k), Image.LANCZOS).save(p, quality=72 if big else 66, method=4); tot += os.path.getsize(p)
        ov.paste(o.resize((400, 400), Image.LANCZOS), ((x-X0)//TILE*400, 4000-((y-Y0)//TILE+1)*400))
ov = ov.resize((4096, 3724), Image.LANCZOS); ov.save(D+'/overview.webp', quality=70)
print('hi tiles', len(hi), 'total MB', tot/1e6, 'overview KB', os.path.getsize(D+'/overview.webp')//1024)
