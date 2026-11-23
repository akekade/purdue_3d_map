"""Download 2023 State of Indiana aerial tiles (exact local-metre squares)."""
import io, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from common import *
B = 'https://di-ingov.img.arcgis.com/arcgis/rest/services/DynamicWebMercator/Indiana_2023_Imagery/ImageServer/exportImage'
D = os.path.join(RAW, 'aerial'); os.makedirs(D, exist_ok=True)
def one(t):
    x, y = t; p = f'{D}/{x}_{y}.jpg'
    if os.path.exists(p): return
    u = f'{B}?bbox={OX+x},{OY+y},{OX+x+TILE},{OY+y+TILE}&bboxSR=26916&imageSR=26916&size=2048,2048&format=jpg&compressionQuality=92&f=image'
    for a in range(5):
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
            im = Image.open(io.BytesIO(b)); im.load(); assert im.size == (2048, 2048)
            open(p, 'wb').write(b); return
        except Exception as e:
            if a == 4: print('FAIL', t, e)
            time.sleep(2+3*a)
ts = [(x, y) for x in range(X0, X1, TILE) for y in range(Y0, Y1, TILE)]
with ThreadPoolExecutor(3) as ex: list(ex.map(one, ts))
print(len(os.listdir(D)), 'of', len(ts))
