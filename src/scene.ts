import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { Data, groundAt } from './data';
import { Mats, groundMaterial, roofMaterial, wallMaterial } from './materials';
const ROOF = ['#f1eee6', '#d5d2cb', '#a9a6a1', '#6c6b72', '#cf6a50', '#9c7660', '#d9c29b', '#86b086', '#7788a0', '#cfa46f'];
const GROUND: Record<string, string> = { grass: '#a3c97c', lawn: '#afd488', fairway: '#bce58c', wood: '#86bb68', farm: '#dccf8e', built: '#d8d5c8', sand: '#f2e2ab', water: '#6fc3ea', parking: '#bfc3cb', kerb: '#e9e5da', path: '#f3e8cf', plaza: '#ecdcc0', road: '#8f959f', runway: '#a9adb5', pitch: '#74c25f', track: '#dd7d60', court: '#62a8a2', rail: '#93836f', line: '#ffe28c', pool: '#58ccf2' };
export class Campus {
  group = new THREE.Group(); mats: Mats; pickGeos: THREE.BufferGeometry[] = []; trees = new THREE.Group();
  private chunks: { hi: THREE.Object3D; lo: THREE.Object3D; cx: number; cz: number }[] = [];
  private glow!: THREE.PointsMaterial; private headMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  constructor(public d: Data) { this.mats = new Mats(d); }
  build() { this.buildings(); this.ground(); this.lamps(); this.buildTrees(); }
  private xyz(a: Uint16Array, n: number) { const m = this.d.meta, o = new Float32Array(n * 3); for (let i = 0; i < n; i++) { o[i * 3] = a[i * 3] / 10 + m.x0; o[i * 3 + 1] = a[i * 3 + 2] / 10; o[i * 3 + 2] = -(a[i * 3 + 1] / 10 + m.y0); } return new THREE.BufferAttribute(o, 3); }
  private tileKey(x: number, y: number) { return Math.floor(x / 10 / 1000) + '_' + Math.floor(y / 10 / 1000); }
  private buildings() {
    const d = this.d, lin = ROOF.map(h => new THREE.Color(h)), pick = <T extends Uint16Array>(src: T, st: number, ids: number[]) => { const o = new Uint16Array(ids.length * st); ids.forEach((q, i) => o.set(src.subarray(q * st, q * st + st), i * st)); return o; };
    const bucket = (src: Uint16Array, st: number) => { const M = new Map<string, number[]>(); for (let q = 0; q < src.length / st; q++) { const k = this.tileKey(src[q * st], src[q * st + 1]); let a = M.get(k); if (!a) M.set(k, a = []); a.push(q); } return M; };
    const rm = roofMaterial(this.mats), wm = wallMaterial(this.mats), em = new THREE.LineBasicMaterial({ color: 0x3a2f2a, transparent: true, opacity: .38 });
    for (const ids of bucket(d.rp, 9).values()) {
      const N = ids.length * 3, b = new Uint16Array(N), c = new Float32Array(N * 3); ids.forEach((q, i) => { const k = lin[d.rc[q]]; for (let v = 0; v < 3; v++) { b[i * 3 + v] = d.rb[q]; c.set([k.r, k.g, k.b], (i * 3 + v) * 3); } });
      const g = new THREE.BufferGeometry(); g.setAttribute('position', this.xyz(pick(d.rp, 9, ids), N)); g.computeVertexNormals(); g.setAttribute('bid', new THREE.BufferAttribute(b, 1)); g.setAttribute('color', new THREE.BufferAttribute(c, 3)); this.add(g, rm);
    }
    for (const ids of bucket(d.wp, 12).values()) {
      const N = ids.length * 4, b = new Uint16Array(N), u = new Float32Array(N * 4), nn = new Int8Array(N * 3), ix = new Uint32Array(ids.length * 6);
      ids.forEach((q, i) => {
        const o = q * 12, dx = d.wp[o + 3] - d.wp[o], dy = d.wp[o + 4] - d.wp[o + 1], l = Math.hypot(dx, dy) || 1, s = i * 4;
        for (let c = 0; c < 4; c++) { const v = s + c, e = q * 16 + c * 4; b[v] = d.wb[q]; u[v * 4] = d.wu[e] / 10; u[v * 4 + 1] = d.wu[e + 1] / 10; u[v * 4 + 2] = d.wu[e + 2] / 10 - 3; u[v * 4 + 3] = d.wu[e + 3] / 10 - 3; nn[v * 3] = dy / l * 127; nn[v * 3 + 2] = dx / l * 127; }
        ix.set([s, s + 1, s + 2, s, s + 2, s + 3], i * 6);
      });
      const g = new THREE.BufferGeometry(); g.setAttribute('position', this.xyz(pick(d.wp, 12, ids), N)); g.setAttribute('normal', new THREE.BufferAttribute(nn, 3, true)); g.setAttribute('wuv', new THREE.BufferAttribute(u, 4)); g.setAttribute('bid', new THREE.BufferAttribute(b, 1)); g.setIndex(new THREE.BufferAttribute(ix, 1)); this.add(g, wm);
    }
    for (const ids of bucket(d.ep, 6).values()) { const g = new THREE.BufferGeometry(); g.setAttribute('position', this.xyz(pick(d.ep, 6, ids), ids.length * 2)); this.group.add(new THREE.LineSegments(g, em)); }
  }
  private add(g: THREE.BufferGeometry, m: THREE.Material) { const o = new THREE.Mesh(g, m); o.castShadow = o.receiveShadow = true; this.group.add(o); this.pickGeos.push(g); }
  private ground() {
    const d = this.d, m = d.meta, n = d.gv.length / 3, p = new Float32Array(n * 3), c = new Float32Array(n * 3), nm = new Int8Array(n * 3), cols = m.classes.map(k => new THREE.Color(GROUND[k]));
    for (let i = 0; i < n; i++) { const x = d.gv[i * 3] / 10 + m.x0, z = -(d.gv[i * 3 + 1] / 10 + m.y0), k = cols[d.gv[i * 3 + 2]]; p[i * 3] = x; p[i * 3 + 1] = groundAt(d, x, z); p[i * 3 + 2] = z; c[i * 3] = k.r; c[i * 3 + 1] = k.g; c[i * 3 + 2] = k.b; nm[i * 3 + 1] = 127; }
    const pa = new THREE.BufferAttribute(p, 3), ca = new THREE.BufferAttribute(c, 3), na = new THREE.BufferAttribute(nm, 3, true), ia = new THREE.BufferAttribute(d.gi, 1), mat = groundMaterial(this.mats), w = (m.x1 - m.x0) / m.tile;
    m.ground.forEach(([s, l], t) => {
      if (!l) return; const g = new THREE.BufferGeometry(); g.setAttribute('position', pa); g.setAttribute('color', ca); g.setAttribute('normal', na); g.setIndex(ia); g.setDrawRange(s, l);
      g.boundingSphere = new THREE.Sphere(new THREE.Vector3(m.x0 + (t % w + .5) * m.tile, 35, -(m.y0 + (Math.floor(t / w) + .5) * m.tile)), 375); const o = new THREE.Mesh(g, mat); o.receiveShadow = true; this.group.add(o);
    });
    const ap = new THREE.Mesh(new THREE.PlaneGeometry(60000, 60000), new THREE.MeshLambertMaterial({ color: GROUND.grass })); ap.rotation.x = -Math.PI / 2; ap.position.y = -4; this.group.add(ap);
  }
  private lamps() {
    const d = this.d, m = d.meta, n = d.lp.length / 4, paint = (g: THREE.BufferGeometry, x: number, y: number, z: number) => g.translate(x, y, z);
    const strip = (g: THREE.BufferGeometry) => { const q = g.index ? g.toNonIndexed() : g; q.deleteAttribute('uv'); return q; };
    const pole = this.mats.toon({ color: 0x4a4f5c }), kinds = [
      { body: [paint(new THREE.CylinderGeometry(.09, .14, 7, 5), 0, 3.5, 0), paint(new THREE.BoxGeometry(1.9, .12, .12), .9, 6.95, 0)], head: paint(new THREE.BoxGeometry(.85, .2, .42), 1.75, 6.83, 0), hx: 1.75, hy: 6.8 },
      { body: [paint(new THREE.CylinderGeometry(.07, .11, 3.6, 5), 0, 1.8, 0)], head: paint(new THREE.IcosahedronGeometry(.34, 1), 0, 3.85, 0), hx: 0, hy: 3.85 }];
    // light map: soft pools of light painted once, added to the ground at night
    const cv = document.createElement('canvas'), S = .5; cv.width = (m.x1 - m.x0) * S; cv.height = (m.y1 - m.y0) * S; const g2 = cv.getContext('2d')!; g2.fillRect(0, 0, cv.width, cv.height); g2.globalCompositeOperation = 'lighter';
    const sp = document.createElement('canvas'); sp.width = sp.height = 32; const s2 = sp.getContext('2d')!, gr = s2.createRadialGradient(16, 16, 0, 16, 16, 16); gr.addColorStop(0, 'rgba(255,255,255,.8)'); gr.addColorStop(.45, 'rgba(255,255,255,.38)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); s2.fillStyle = gr; s2.fillRect(0, 0, 32, 32);
    const heads: number[] = [], M = new THREE.Matrix4();
    kinds.forEach((k, kind) => {
      const by = new Map<string, number[]>(); for (let i = 0; i < n; i++) if (d.lp[i * 4 + 3] === kind) { const t = this.tileKey(d.lp[i * 4], d.lp[i * 4 + 1]); let a = by.get(t); if (!a) by.set(t, a = []); a.push(i); }
      const body = mergeGeometries(k.body.map(strip))!, head = strip(k.head);
      for (const ids of by.values()) {
        const A = new THREE.InstancedMesh(body, pole, ids.length), B = new THREE.InstancedMesh(head, this.headMat, ids.length); let cx = 0, cz = 0;
        ids.forEach((i, j) => { const x = d.lp[i * 4] / 10 + m.x0, y = d.lp[i * 4 + 1] / 10 + m.y0, a = d.lp[i * 4 + 2] / 1000, gy = groundAt(d, x, -y); M.makeRotationY(a).setPosition(x, gy, -y); A.setMatrixAt(j, M); B.setMatrixAt(j, M); cx += x / ids.length; cz -= y / ids.length;
          const hx = x + Math.cos(a) * k.hx, hz = -y - Math.sin(a) * k.hx; heads.push(hx, gy + k.hy, hz); const r = (kind ? 13 : 21) * S; g2.globalAlpha = kind ? .6 : 1; g2.drawImage(sp, (hx - m.x0) * S - r, cv.height - (-hz - m.y0) * S - r, r * 2, r * 2); });
        A.computeBoundingSphere(); B.computeBoundingSphere(); const G = new THREE.Group(); G.add(A, B); this.group.add(G); this.chunks.push({ hi: G, lo: new THREE.Object3D(), cx, cz });
      }
    });
    const lt = new THREE.CanvasTexture(cv); lt.colorSpace = THREE.NoColorSpace; lt.generateMipmaps = false; lt.minFilter = THREE.LinearFilter; this.mats.u.uLamp.value = lt;
    const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.Float32BufferAttribute(heads, 3)); const pt = new THREE.CanvasTexture(sp);
    this.glow = new THREE.PointsMaterial({ map: pt, size: 7, color: 0xffd27a, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }); this.group.add(new THREE.Points(pg, this.glow));
  }
  setNight(n: number) { this.mats.u.uNight.value = n; this.glow.opacity = n * .9; this.glow.visible = n > .02; this.headMat.color.setRGB(.95, .95, .92).lerp(new THREE.Color(1, .84, .5), n); }
  private buildTrees() {
    const d = this.d, m = d.meta, by = new Map<string, number[]>();
    for (let i = 0; i < m.trees; i++) { const con = (Math.abs(Math.sin(i * 78.233) * 43758.5453) % 1) < .14 ? 'c' : 'r', k = con + Math.floor(d.trees[i * 4] / 10 / m.tile) + '_' + Math.floor(d.trees[i * 4 + 1] / 10 / m.tile); let a = by.get(k); if (!a) by.set(k, a = []); a.push(i); }
    const shade = (g: THREE.BufferGeometry, c: [number, number, number]) => { const q = g.index ? g.toNonIndexed() : g; q.deleteAttribute('uv'); q.setAttribute('color', new THREE.Float32BufferAttribute(Array.from({ length: q.attributes.position.count }, () => c).flat(), 3)); return q; };
    const trunk = () => shade(new THREE.CylinderGeometry(.035, .05, .4, 5).translate(0, .2, 0), [1.15, .62, .5]), ball = (k: number) => { const g = new THREE.IcosahedronGeometry(1, k), p = g.attributes.position; g.setAttribute('normal', p.clone()); return shade(g.scale(.5, .4, .5).translate(0, .6, 0), [1, 1, 1]); };
    const cone = (k: number) => shade(new THREE.ConeGeometry(.36, .82, k).translate(0, .59, 0), [1, 1, 1]);
    const G: Record<string, [THREE.BufferGeometry, THREE.BufferGeometry]> = { r: [mergeGeometries([ball(2), trunk()])!, ball(0)], c: [mergeGeometries([cone(9), trunk()])!, cone(5)] };
    const mat = this.mats.toon({ vertexColors: true }), M = new THREE.Matrix4(), c = new THREE.Color();
    for (const [k, ids] of by) {
      const [tx, ty] = k.slice(1).split('_').map(Number), con = k[0] === 'c', A = new THREE.InstancedMesh(G[k[0]][0], mat, ids.length), B = new THREE.InstancedMesh(G[k[0]][1], mat, ids.length);
      ids.forEach((i, j) => {
        const x = d.trees[i * 4] / 10 + m.x0, z = -(d.trees[i * 4 + 1] / 10 + m.y0), h = d.trees[i * 4 + 3] / 10 * .88, r = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1, w = Math.min(h * (.62 + .2 * r), 12) * (con ? .85 : 1);
        M.makeRotationY(r * 6.28).scale(new THREE.Vector3(w, h, w)).setPosition(x, groundAt(d, x, z) - .2, z); A.setMatrixAt(j, M); B.setMatrixAt(j, M); if (con) c.setHSL(.37 + r * .03, .34, .27 + r * .05); else c.setHSL(.26 + r * .075, .42, .31 + ((r * 7) % 1) * .09); A.setColorAt(j, c); B.setColorAt(j, c);
      });
      for (const q of [A, B]) { q.computeBoundingSphere(); this.trees.add(q); } A.castShadow = true; A.visible = false;
      this.chunks.push({ hi: A, lo: B, cx: m.x0 + (tx + .5) * m.tile, cz: -(m.y0 + (ty + .5) * m.tile) });
    }
    this.group.add(this.trees);
  }
  update(cam: THREE.Camera) { const p = cam.position; for (const c of this.chunks) { const near = Math.hypot(c.cx - p.x, p.y * .8, c.cz - p.z) < 850; c.hi.visible = near; c.lo.visible = !near; } }
}
