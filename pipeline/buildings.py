"""Official building list (number/code/name) joined to OSM footprints."""
import json, re, difflib
import pypdf
from collections import Counter
from common import *
def official():
    out = []; pend = ''
    for pg in pypdf.PdfReader(RAW+'/wl-building-list.pdf').pages:
        for ln in pg.extract_text().split('\n'):
            ln = ln.strip()
            if not ln or re.match(r'(March 2025|Building\s*$|WEST LAFAYETTE|Abbreviation)', ln): continue
            ln = (pend+' '+ln).strip(); m = re.match(r'(\S+) (.+?) (\d{4})$', ln)
            if m: out.append(dict(code=m[1], name=m[2], num=m[3])); pend = ''
            else: pend = ln
    if pend: print('LEFTOVER', pend)
    return out
if __name__ == '__main__':
    L = official(); print(len(L)); print('dup', [k for k, v in Counter(x['code'] for x in L).items() if v > 1], [k for k, v in Counter(x['num'] for x in L).items() if v > 1])
    for x in L: print(x['code'], '|', x['name'], '|', x['num'])
