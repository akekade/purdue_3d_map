export interface Official { n: string; c: string; t: string }
export interface Bld { i: number; off?: Official[]; name?: string; osm?: string; addr?: string; cat: string; pu?: boolean; h: number; hs: string; hn?: string; fl: number; fe?: boolean; area: number; wn: string; wc: string; x: number; y: number; z?: number; wall: string }
export interface Meta { x0: number; y0: number; x1: number; y1: number; z0: number; tile: number; nb: number; rv: number; ri: number; wq: number; roofs: Record<string, [number, number]>; tnx: number; tny: number; tstep: number; trees: number; lean: [number[], number[]] }
export interface Data { meta: Meta; blds: Bld[]; mats: Uint8Array; terrain: Uint16Array; trees: Uint16Array; rp: Uint16Array; rid: Uint16Array; wp: Uint16Array; wu: Uint16Array; wb: Uint16Array; ri: Uint32Array }
const base = import.meta.env.BASE_URL + 'data/';
export const url = (p: string) => base + p;
async function buf(p: string) {
  const r = await fetch(url(p)); if (!r.ok) throw new Error(`${p}: HTTP ${r.status}`);
  return r.arrayBuffer();
}
export async function loadData(step: (f: number, m: string) => void): Promise<Data> {
  let k = 0; const t = <T>(p: Promise<T>) => p.then(v => { step(++k / 7, 'Loading campus…'); return v; });
  const meta: Meta = await t(fetch(url('meta.json')).then(r => r.json()));
  const [blds, mats, terrain, trees, gz] = await Promise.all([
    t(fetch(url('buildings.json')).then(r => r.json()) as Promise<Bld[]>), t(buf('mats.bin')), t(buf('terrain.bin')), t(buf('trees.bin')), t(buf('geo.bin.gz'))]);
  // Some servers set Content-Encoding for .gz, in which case it arrives already unpacked.
  const u8 = new Uint8Array(gz);
  const g = u8[0] === 0x1f && u8[1] === 0x8b ? await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer() : gz;
  step(1, 'Building model…');
  let o = 0; const u16 = (n: number) => { const a = new Uint16Array(g, o, n); o += n * 2; return a; };
  const rp = u16(meta.rv * 3), rid = u16(meta.rv), wp = u16(meta.wq * 12), wu = u16(meta.wq * 12), wb = u16(meta.wq);
  if (o % 4) o += 2;
  return { meta, blds, mats: new Uint8Array(mats), terrain: new Uint16Array(terrain), trees: new Uint16Array(trees), rp, rid, wp, wu, wb, ri: new Uint32Array(g, o, meta.ri) };
}
/** Ground height (scene units, metres above z0) at scene x / z. */
export function groundAt(d: Data, x: number, z: number) {
  const m = d.meta, fx = Math.min(Math.max((x - m.x0) / m.tstep, 0), m.tnx - 1.001), fy = Math.min(Math.max((-z - m.y0) / m.tstep, 0), m.tny - 1.001);
  const i = Math.floor(fx), j = Math.floor(fy), a = fx - i, b = fy - j, T = d.terrain, n = m.tnx;
  return ((T[j * n + i] * (1 - a) + T[j * n + i + 1] * a) * (1 - b) + (T[(j + 1) * n + i] * (1 - a) + T[(j + 1) * n + i + 1] * a) * b) / 10;
}
