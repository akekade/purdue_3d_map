import * as THREE from 'three';
import { Data, groundAt, url } from './data';
import { Mats, TileU, groundMaterial, roofMaterial, wallMaterial } from './materials';
interface Tile { key: string; cx: number; cz: number; u: TileU; hi?: THREE.Texture; loading?: boolean; used: number }
const MAX_HI = 18;
export class Campus {
  group = new THREE.Group(); mats: Mats; tiles: Tile[] = []; roofGeos: THREE.BufferGeometry[] = []; wallGeo!: THREE.BufferGeometry;
  trees = new THREE.Group(); overview!: THREE.Texture; full: THREE.Vector4; onchange = () => {}; private aniso = 8;
  private treeChunks: { hi: THREE.InstancedMesh; lo: THREE.InstancedMesh; cx: number; cz: number }[] = [];
  constructor(public d: Data, aniso: number) {
    this.mats = new Mats(d); this.aniso = aniso; const m = d.meta;
    this.full = new THREE.Vector4(m.x0, m.y0, m.x1 - m.x0, m.y1 - m.y0);
  }
  private tex(t: THREE.Texture) { t.anisotropy = this.aniso; t.colorSpace = THREE.NoColorSpace; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; return t; }
  async build() {
    const d = this.d, m = d.meta, L = new THREE.TextureLoader();
    this.overview = this.tex(await L.loadAsync(url('tex/overview.webp')));
    // roofs: shared vertex buffers, one draw range per tile
    const rp = new Float32Array(m.rv * 3);
    for (let i = 0; i < m.rv; i++) { rp[i * 3] = d.rp[i * 3] / 10 + m.x0; rp[i * 3 + 1] = d.rp[i * 3 + 2] / 10; rp[i * 3 + 2] = -(d.rp[i * 3 + 1] / 10 + m.y0); }
    const pa = new THREE.BufferAttribute(rp, 3), ba = new THREE.BufferAttribute(d.rid, 1), ia = new THREE.BufferAttribute(d.ri, 1);
    const nrm = new THREE.BufferAttribute(new Int8Array(m.rv * 3).map((_, i) => i % 3 === 1 ? 127 : 0), 3, true);
    const nx = (m.x1 - m.x0) / m.tile, ny = (m.y1 - m.y0) / m.tile, n = m.tile / m.tstep;
    for (let ty = 0; ty < ny; ty++) for (let tx = 0; tx < nx; tx++) {
      const key = `${tx}_${ty}`, x = m.x0 + tx * m.tile, y = m.y0 + ty * m.tile;
      const u: TileU = { uMap: { value: this.overview }, uRect: { value: this.full.clone() } };
      this.tiles.push({ key, cx: x + m.tile / 2, cz: -(y + m.tile / 2), u, used: 0 });
      const pos = new Float32Array((n + 1) ** 2 * 3), idx: number[] = []; let k = 0;
      for (let j = 0; j <= n; j++) for (let i = 0; i <= n; i++) { pos[k++] = x + i * m.tstep; pos[k++] = d.terrain[(ty * n + j) * m.tnx + tx * n + i] / 10; pos[k++] = -(y + j * m.tstep); }
      for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) { const a = j * (n + 1) + i; idx.push(a, a + 1, a + n + 2, a, a + n + 2, a + n + 1); }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
      const gm = new THREE.Mesh(g, groundMaterial(this.mats, u)); gm.receiveShadow = true; this.group.add(gm);
      const r = m.roofs[key]; if (!r) continue;
      const rg = new THREE.BufferGeometry(); rg.setAttribute('position', pa); rg.setAttribute('normal', nrm); rg.setAttribute('bid', ba); rg.setIndex(ia); rg.setDrawRange(r[0], r[1]);
      rg.boundingSphere = new THREE.Sphere(new THREE.Vector3(x + m.tile / 2, 50, -(y + m.tile / 2)), 480);
      const rm = new THREE.Mesh(rg, roofMaterial(this.mats, u)); rm.castShadow = rm.receiveShadow = true; this.group.add(rm); this.roofGeos.push(rg);
    }
    // walls, chunked by tile for culling
    const order = new Map<string, number[]>();
    for (let q = 0; q < m.wq; q++) { const k = `${Math.floor(d.wp[q * 12] / 10 / m.tile)}_${Math.floor(d.wp[q * 12 + 1] / 10 / m.tile)}`; let a = order.get(k); if (!a) order.set(k, a = []); a.push(q); }
    const mat = wallMaterial(this.mats);
    for (const [k, qs] of order) {
      const N = qs.length * 4, p = new Float32Array(N * 3), w = new Float32Array(N * 3), b = new Uint16Array(N), nn = new Int8Array(N * 3), ix = new Uint32Array(qs.length * 6); let v = 0, t = 0;
      for (const q of qs) {
        const s = v, o = q * 12, dx = d.wp[o + 3] - d.wp[o], dy = d.wp[o + 4] - d.wp[o + 1], l = Math.hypot(dx, dy) || 1;
        for (let c = 0; c < 4; c++, v++) {
          const e = o + c * 3; p[v * 3] = d.wp[e] / 10 + m.x0; p[v * 3 + 1] = d.wp[e + 2] / 10; p[v * 3 + 2] = -(d.wp[e + 1] / 10 + m.y0);
          w[v * 3] = d.wu[e] / 10; w[v * 3 + 1] = d.wu[e + 1] / 10; w[v * 3 + 2] = d.wu[e + 2] / 10; b[v] = d.wb[q];
          nn[v * 3] = dy / l * 127; nn[v * 3 + 2] = dx / l * 127;
        }
        ix.set([s, s + 1, s + 2, s, s + 2, s + 3], t); t += 6;
      }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nn, 3, true));
      g.setAttribute('wuv', new THREE.BufferAttribute(w, 3)); g.setAttribute('bid', new THREE.BufferAttribute(b, 1)); g.setIndex(new THREE.BufferAttribute(ix, 1));
      const mesh = new THREE.Mesh(g, mat); mesh.castShadow = mesh.receiveShadow = true; this.group.add(mesh); this.roofGeos.push(g); void k;
    }
    // apron beyond the mapped area
    const ap = new THREE.Mesh(new THREE.PlaneGeometry(60000, 60000), new THREE.MeshLambertMaterial({ color: 0x6f7a55 })); ap.rotation.x = -Math.PI / 2; ap.position.y = -4; this.group.add(ap);
    this.buildTrees();
  }
  private buildTrees() {
    const d = this.d, m = d.meta, by = new Map<string, number[]>();
    for (let i = 0; i < m.trees; i++) { const k = `${Math.floor(d.trees[i * 4] / 10 / m.tile)}_${Math.floor(d.trees[i * 4 + 1] / 10 / m.tile)}`; let a = by.get(k); if (!a) by.set(k, a = []); a.push(i); }
    const blob = (det: number, lobes: number[][], trunk: boolean) => {
      const pos: number[] = [], nm: number[] = [], col: number[] = [], v = new THREE.Vector3();
      for (const [ox, oy, oz, rx, ry] of lobes) {
        const p = new THREE.IcosahedronGeometry(1, det).attributes.position;
        for (let i = 0; i < p.count; i++) {
          v.fromBufferAttribute(p, i); const s = 1 + .16 * Math.sin(v.x * 6 + v.y * 4 + oy * 9) * Math.cos(v.z * 5.3 + ox * 7), y = v.y * s * ry + oy;
          pos.push(v.x * s * rx + ox, y, v.z * s * rx + oz); nm.push(v.x * .6 + ox, v.y * .6 + (y - .55), v.z * .6 + oz); const k = Math.min(1, Math.max(.45, .3 + y * .78)); col.push(k, k, k);
        }
      }
      if (trunk) for (let a = 0; a < 5; a++) { const [A, B] = [a, a + 1].map(t => [Math.cos(t * 1.2566) * .03, Math.sin(t * 1.2566) * .03]);
        for (const t of [[A, 0], [B, 0], [B, .42], [A, 0], [B, .42], [A, .42]] as [number[], number][]) { pos.push(t[0][0], t[1], t[0][1]); nm.push(t[0][0] * 28, 0, t[0][1] * 28); col.push(.75, .42, .3); } }
      const o = new THREE.BufferGeometry(); o.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); o.setAttribute('normal', new THREE.Float32BufferAttribute(nm, 3)); o.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); o.normalizeNormals(); return o;
    };
    const hi = blob(1, [[-.13, .5, .08, .3, .24], [.16, .56, -.07, .28, .25], [.02, .74, .05, .29, .26], [0, .48, -.2, .22, .18]], true), lo = blob(0, [[0, .6, 0, .4, .38]], false), mat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }), M = new THREE.Matrix4(), c = new THREE.Color();
    for (const [k, ids] of by) {
      const [tx, ty] = k.split('_').map(Number), A = new THREE.InstancedMesh(hi, mat, ids.length), B = new THREE.InstancedMesh(lo, mat, ids.length);
      ids.forEach((i, j) => {
        const x = d.trees[i * 4] / 10 + m.x0, z = -(d.trees[i * 4 + 1] / 10 + m.y0), h = d.trees[i * 4 + 3] / 10, r = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1, w = Math.min(h * (.6 + .25 * r), 12.5);
        M.makeRotationY(r * 6.28).scale(new THREE.Vector3(w, h, w)).setPosition(x, groundAt(d, x, z) - .2, z); A.setMatrixAt(j, M); B.setMatrixAt(j, M);
        c.setHSL(.225 + r * .07, .3 + r * .12, .23 + ((r * 7) % 1) * .09); A.setColorAt(j, c); B.setColorAt(j, c);
      });
      for (const q of [A, B]) { q.computeBoundingSphere(); this.trees.add(q); } A.castShadow = true; A.visible = false;
      this.treeChunks.push({ hi: A, lo: B, cx: m.x0 + (tx + .5) * m.tile, cz: -(m.y0 + (ty + .5) * m.tile) });
    }
    this.group.add(this.trees);
  }
  /** Stream sharp tiles near the view; evict the farthest to bound GPU memory. */
  update(cam: THREE.Camera, target: THREE.Vector3) {
    const p = cam.position;
    for (const c of this.treeChunks) { const near = Math.hypot(c.cx - p.x, p.y * .8, c.cz - p.z) < 750; c.hi.visible = near; c.lo.visible = !near; }
    if (p.y > 1900) return;
    const dist = (t: Tile) => Math.hypot(t.cx - target.x, t.cz - target.z) * .65 + Math.hypot(t.cx - p.x, t.cz - p.z) * .35;
    const want = this.tiles.map(t => [dist(t), t] as const).sort((a, b) => a[0] - b[0]).slice(0, MAX_HI).map(a => a[1]), set = new Set(want);
    let busy = this.tiles.filter(t => t.loading).length;
    for (const t of want) {
      if (t.hi || t.loading || busy >= 4) continue; t.loading = true; busy++;
      new THREE.TextureLoader().load(url(`tex/${t.key}.webp`), x => {
        t.loading = false; t.hi = this.tex(x); t.u.uMap.value = x; const m = this.d.meta, [a, b] = t.key.split('_').map(Number);
        t.u.uRect.value.set(m.x0 + a * m.tile, m.y0 + b * m.tile, m.tile, m.tile); this.onchange();
      }, undefined, () => { t.loading = false; t.hi = this.overview; });
    }
    const loaded = this.tiles.filter(t => t.hi && t.hi !== this.overview);
    if (loaded.length > MAX_HI + 6) for (const t of loaded.filter(t => !set.has(t)).sort((a, b) => dist(b) - dist(a)).slice(0, loaded.length - MAX_HI - 6)) { t.u.uMap.value = this.overview; t.u.uRect.value.copy(this.full); t.hi!.dispose(); t.hi = undefined; }
  }
  get pending() { return this.tiles.some(t => t.loading); }
}
