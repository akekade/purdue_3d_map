export interface Official { n: string; c: string; t: string }
export interface Bld { i: number; off?: Official[]; name?: string; osm?: string; addr?: string; cat: string; pu?: boolean; h: number; hs: string; hn?: string; fl: number; fe?: boolean; area: number; wn: string; wc: string; x: number; y: number; z?: number; wall: string }
export interface Meta { x0: number; y0: number; x1: number; y1: number; z0: number; tile: number; nb: number; sec: Record<string, [number, number]>; ground: [number, number][]; classes: string[]; tnx: number; tny: number; tstep: number; trees: number }
/** rp/rb/rc roofs, wp/wu/wb walls, ep outlines, gv/gi ground, lp lamps, tz terrain */
export interface Data { meta: Meta; blds: Bld[]; mats: Uint8Array; trees: Uint16Array; rp: Uint16Array; rb: Uint16Array; rc: Uint8Array; wp: Uint16Array; wu: Uint16Array; wb: Uint16Array; ep: Uint16Array; gv: Uint16Array; gi: Uint32Array; lp: Uint16Array; tz: Uint16Array }
const base = import.meta.env.BASE_URL + 'data/';
export const url = (p: string) => base + p;
async function buf(p: string) {
  const r = await fetch(url(p)); if (!r.ok) throw new Error(`${p}: HTTP ${r.status}`);
  return r.arrayBuffer();
}
export async function loadData(step: (f: number, m: string) => void): Promise<Data> {
  let k = 0; const t = <T>(p: Promise<T>) => p.then(v => { step(++k / 5, 'Loading campus…'); return v; });
  const meta: Meta = await t(fetch(url('meta.json')).then(r => r.json()));
  const [blds, mats, trees, gz] = await Promise.all([
    t(fetch(url('buildings.json')).then(r => r.json()) as Promise<Bld[]>), t(buf('mats.bin')), t(buf('trees.bin')), t(buf('geo.bin.gz'))]);
  // Some servers set Content-Encoding for .gz, in which case it arrives already unpacked.
  const u8 = new Uint8Array(gz);
  const g = u8[0] === 0x1f && u8[1] === 0x8b ? await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer() : gz;
  step(1, 'Building model…');
  const u16 = (n: string) => new Uint16Array(g, ...meta.sec[n]), u8a = (n: string) => new Uint8Array(g, ...meta.sec[n]);
  return { meta, blds, mats: new Uint8Array(mats), trees: new Uint16Array(trees), rp: u16('rp'), rb: u16('rb'), rc: u8a('rc'), wp: u16('wp'), wu: u16('wu'), wb: u16('wb'), ep: u16('ep'), gv: u16('gv'), gi: new Uint32Array(g, ...meta.sec.gi), lp: u16('lp'), tz: u16('tz') };
}
/** Ground height (scene units, metres above z0) at scene x / z. */
export function groundAt(d: Data, x: number, z: number) {
  const m = d.meta, fx = Math.min(Math.max((x - m.x0) / m.tstep, 0), m.tnx - 1.001), fy = Math.min(Math.max((-z - m.y0) / m.tstep, 0), m.tny - 1.001);
  const i = Math.floor(fx), j = Math.floor(fy), a = fx - i, b = fy - j, T = d.tz, n = m.tnx, k = j * n + i, z0 = T[k], z11 = T[k + n + 1];
  return (a >= b ? z0 + a * (T[k + 1] - z0) + b * (z11 - T[k + 1]) : z0 + b * (T[k + n] - z0) + a * (z11 - T[k + n])) / 10;
}
