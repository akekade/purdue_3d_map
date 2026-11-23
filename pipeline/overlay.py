import sys,contextlib,io
with contextlib.redirect_stdout(io.StringIO()):
    from match import *
from PIL import Image,ImageDraw,ImageFont
import pypdfium2 as pdfium
C=np.array(json.load(open(WORK+'/georef.json')));Ainv=np.linalg.inv(C[:2])
s=14;im=pdfium.PdfDocument(RAW+'/campusmap.pdf')[1].render(scale=s).to_pil().convert('RGB');H=im.size[1]
d=ImageDraw.Draw(im);f=ImageFont.load_default(26)
named={a[4] for a in amb if a[0]>=.5}|set(M)
for b in B:
    for g in getattr(b['p'],'geoms',[b['p']]):
        q=[tuple(((np.array(c)-C[2])@Ainv)*[s,-s]+[0,H]) for c in g.exterior.coords]
        d.line(q,fill=(0,150,0) if b['id'] in named else (230,0,0),width=4)
    if b['id'] not in named and b['p'].area>60:
        c=b['p'].representative_point();x,y=((np.array([c.x,c.y])-C[2])@Ainv)*[s,-s]+[0,H]
        d.text((x-40,y-12),b['id'],fill=(0,0,255),font=f,stroke_width=2,stroke_fill='white')
for i,a in enumerate(sys.argv[1:]):
    x0,y0,x1,y1=map(float,a.split(','));p=[((np.array(v)-C[2])@Ainv)*[s,-s]+[0,H] for v in ((x0,y1),(x1,y0))]
    z=im.crop((*map(int,p[0]),*map(int,p[1])));k=min(1,1900/max(z.size));z.resize((int(z.size[0]*k),int(z.size[1]*k))).save(f'{WORK}/ov{i}.png');print(z.size)
