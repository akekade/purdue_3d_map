import type { Bld } from './data';
const $ = <T extends HTMLElement>(s: string) => document.querySelector(s) as T;
const esc = (s: string) => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
export const CATS: [string, string][] = [['academic', 'Academic & admin'], ['residence', 'Residence'], ['dining', 'Dining'], ['student', 'Student life'], ['athletics', 'Athletics'], ['parking', 'Parking'], ['facilities', 'Facilities'], ['airport', 'Airport']];
const catName = (c: string) => CATS.find(x => x[0] === c)?.[1] ?? 'West Lafayette';
export const title = (b: Bld) => b.off ? b.off.map(o => o.t).join(' / ') : b.name ?? (b.pu ? 'Unnamed campus building' : b.addr ?? 'Building');
export const tag = (b: Bld) => b.off?.map(o => o.c).join('/') ?? '';
export function panel(b: Bld | null, close: () => void) {
  const p = $('#panel'); if (!b) { p.hidden = true; document.body.classList.remove('open'); return; }
  const ft = Math.round(b.h * 3.281), one = b.off?.length === 1;
  const num = b.off ? (one ? `<div class="num"><small>Building number</small><strong>${b.off[0].n}</strong><em>${esc(b.off[0].c)}</em></div><h2>${esc(b.off[0].t)}</h2>`
    : `<div class="multi"><small>${b.off.length} buildings share this footprint</small>${b.off.map(o => `<div><strong>${o.n}</strong><em>${esc(o.c)}</em><span>${esc(o.t)}</span></div>`).join('')}</div>`)
    : `<div class="num none"><small>Building number</small><strong>Not listed</strong></div><h2>${esc(title(b))}</h2>`;
  const row = (k: string, v?: string) => v ? `<dt>${k}</dt><dd>${v}</dd>` : '';
  const src = { photo: 'Checked against a photo', described: 'From a published description', typical: 'Assumed, not verified', generic: 'Generic, not a Purdue record' }[b.wc] ?? '';
  p.innerHTML = `<button class="x" aria-label="Close">×</button>${num}<dl>${row('Type', catName(b.cat))}${b.osm && b.off && !title(b).toLowerCase().includes(b.osm.toLowerCase()) ? row('Map name', esc(b.osm)) : ''}${row('Address', b.addr && esc(b.addr))}
  ${b.fe && (b.hs === 'custom' || !['academic', 'residence', 'dining', 'student', 'town'].includes(b.cat)) ? '' : row('Floors', `${b.fe ? 'about ' : ''}${b.fl}${b.fe ? ' <i>estimated from height</i>' : ''}`)}${row('Height', `${b.h < 10 ? b.h.toFixed(1) : Math.round(b.h)} m (${ft} ft)${b.hs === 'lidar' ? ' <i>measured, 2017 LiDAR</i>' : b.hs === 'estimated' ? ` <i>estimated: ${esc(b.hn ?? '')}</i>` : ' <i>approximate</i>'}`)}
  ${row('Footprint', `${Math.round(b.area * 10.764).toLocaleString()} sq ft`)}${row('Walls', `<span class="sw" style="background:${b.wall}"></span>${esc(b.wn)}<i>${src}</i>`)}</dl>${b.off ? '<button class="share">Copy link</button>' : ''}`;
  p.hidden = false; document.body.classList.add('open'); p.querySelector<HTMLButtonElement>('.x')!.onclick = close;
  const s = p.querySelector<HTMLButtonElement>('.share'); if (s) s.onclick = async () => { try { await navigator.clipboard.writeText(location.href); s.textContent = 'Copied'; } catch { s.textContent = location.hash; } };
}
export function search(blds: Bld[], go: (b: Bld) => void) {
  const q = $<HTMLInputElement>('#q'), ul = $('#results'); let hits: Bld[] = [], at = 0;
  const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const idx = blds.filter(b => b.off || b.name).map(b => ({ b, nums: b.off?.map(o => o.n) ?? [], codes: b.off?.map(o => o.c.toLowerCase()) ?? [], text: norm(`${title(b)} ${b.osm ?? ''} ${b.addr ?? ''}`) }));
  const run = () => {
    const s = norm(q.value.trim()); if (!s) { ul.hidden = true; hits = []; return; }
    const w = s.split(/\s+/);
    hits = idx.map(e => {
      let k = 0; if (e.nums.includes(s) || e.codes.includes(s)) k = 100; else if (e.nums.some(n => n.startsWith(s)) || e.codes.some(c => c.startsWith(s))) k = 60; else if (w.every(x => e.text.includes(x))) k = 30 + (e.text.startsWith(s) ? 15 : w.every(x => new RegExp('\\b' + x.replace(/\W/g, '')).test(e.text)) ? 8 : 0);
      return [k ? k + (e.b.off ? 20 : 0) + Math.min(e.b.area / 2000, 5) : 0, e.b] as const;
    }).filter(x => x[0] > 0).sort((a, b) => b[0] - a[0]).slice(0, 8).map(x => x[1]); at = 0; draw();
  };
  const draw = () => {
    ul.hidden = false; ul.innerHTML = hits.length ? hits.map((b, i) => `<li role="option" aria-selected="${i === at}" data-i="${i}"><b>${b.off ? b.off.map(o => o.n).join(', ') : '—'}</b><span>${esc(title(b))}</span><em>${esc(tag(b))}</em></li>`).join('') : '<li class="no">No building matches. Try a code like POTR or a number like 1154.</li>';
  };
  const pick = (i: number) => { const b = hits[i]; if (!b) return; ul.hidden = true; q.value = ''; q.blur(); go(b); };
  q.oninput = run; q.onfocus = run; q.onkeydown = e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); at = Math.max(0, Math.min(hits.length - 1, at + (e.key === 'ArrowDown' ? 1 : -1))); draw(); }
    else if (e.key === 'Enter') pick(at); else if (e.key === 'Escape') { q.value = ''; ul.hidden = true; q.blur(); } e.stopPropagation();
  };
  ul.onpointerdown = e => { const li = (e.target as HTMLElement).closest('li'); if (li?.dataset.i) { e.preventDefault(); pick(+li.dataset.i); } };
  q.onblur = () => setTimeout(() => ul.hidden = true, 120);
  addEventListener('keydown', e => { if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); } });
}
export function chips(blds: Bld[], on: (c: string | null) => void) {
  const n = $('#chips'); let cur: string | null = null;
  n.innerHTML = CATS.map(([k, v]) => `<button data-c="${k}" aria-pressed="false">${v} <small>${blds.filter(b => b.off && b.cat === k).length}</small></button>`).join('');
  n.onclick = e => { const b = (e.target as HTMLElement).closest('button'); if (!b) return; cur = cur === b.dataset.c ? null : b.dataset.c!; n.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.c === cur))); on(cur); };
}
