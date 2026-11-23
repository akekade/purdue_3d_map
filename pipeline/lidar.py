"""Stream USGS EPT lidar nodes from the public AWS mirror into local metric grids."""
import io, json, sys, time, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import laspy
from common import *
B = 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public/IN_Statewide_Opt2_B2_2017/'
sel = json.load(open(os.path.join(RAW, 'ept_sel.json')))
R = 0.5; NX = int((X1-X0)/R); NY = int((Y1-Y0)/R); G = 2.0; GX = int((X1-X0)/G); GY = int((Y1-Y0)/G)
top = np.full(NX*NY, -9999, 'f4'); solid = np.full(NX*NY, -9999, 'f4')
gs = np.zeros(GX*GY, 'f8'); gn = np.zeros(GX*GY, 'i4')
lock = threading.Lock(); cls = Counter(); done = [0]
def work(k):
    for a in range(5):
        try:
            b = urllib.request.urlopen(urllib.request.Request(B+f'ept-data/{k}.laz', headers=UA), timeout=90).read(); break
        except Exception as e:
            if a == 4: print('FAIL', k, e); return
            time.sleep(1+a*2)
    p = laspy.read(io.BytesIO(b)); x, y = merc(np.array(p.x), np.array(p.y)); z = np.array(p.z, 'f4')
    c = np.array(p.classification); nr = np.array(p.number_of_returns); rn = np.array(p.return_number)
    m = (x >= X0) & (x < X1) & (y >= Y0) & (y < Y1) & (c != 7) & (c != 18) & (z > 120) & (z < 330)
    x, y, z, c, nr, rn = x[m], y[m], z[m], c[m], nr[m], rn[m]
    i = ((y-Y0)/R).astype('i8')*NX + ((x-X0)/R).astype('i8')
    g = c == 2; gi = ((y[g]-Y0)/G).astype('i8')*GX + ((x[g]-X0)/G).astype('i8')
    s = nr == 1
    with lock:
        np.maximum.at(top, i, z); np.maximum.at(solid, i[s], z[s])
        np.add.at(gs, gi, z[g]); np.add.at(gn, gi, 1)
        cls.update(dict(zip(*[v.tolist() for v in np.unique(c, return_counts=True)])))
        done[0] += 1
        if done[0] % 300 == 0: print(done[0], len(sel), flush=True)
with ThreadPoolExecutor(8) as ex: list(ex.map(work, sel))
print(cls)
top = top.reshape(NY, NX); solid = solid.reshape(NY, NX); gn = gn.reshape(GY, GX)
dtm = np.where(gn > 0, gs.reshape(GY, GX)/np.maximum(gn, 1), np.nan).astype('f4')
print('ground cells filled', np.isfinite(dtm).mean(), 'top filled', (top > 0).mean(), 'solid', (solid > 0).mean())
np.save(WORK+'/top.npy', top); np.save(WORK+'/solid.npy', solid); np.save(WORK+'/dtm_raw.npy', dtm)
