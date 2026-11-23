import * as THREE from 'three';
import { Data, groundAt } from './data';
/** Thin structures that LiDAR cannot capture. Coordinates are local metres (east, north). */
export function landmarks(d: Data, ids: Record<string, number>) {
  const g = new THREE.Group(), pick: { geo: THREE.BufferGeometry; id: number }[] = [];
  const mat = (c: number) => new THREE.MeshLambertMaterial({ color: c, flatShading: true, side: THREE.DoubleSide });
  const brick = mat(0x96644b), stone = mat(0xe4dccb), roof = mat(0x6b4a35), steel = mat(0x45382f), slate = mat(0x4a4f57), dark = mat(0x23262a), white = mat(0xe6e1d6);
  const add = (geo: THREE.BufferGeometry, m: THREE.Material, x: number, y: number, z: number, ry = 0, id?: number) => {
    const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.rotation.y = ry; o.castShadow = o.receiveShadow = true; g.add(o);
    if (id !== undefined) { o.updateMatrix(); pick.push({ geo: geo.clone().applyMatrix4(o.matrix), id }); }
  };
  const beam = (a: THREE.Vector3, b: THREE.Vector3, r0: number, r1: number, m: THREE.Material, id?: number) => {
    const l = a.distanceTo(b), c = new THREE.CylinderGeometry(r1, r0, l, 5), q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    c.applyQuaternion(q); const p = a.clone().add(b).multiplyScalar(.5); add(c, m, p.x, p.y, p.z, 0, id);
  };
  // Bell Tower: about 48 m, brick shaft, limestone belfry, pyramid roof
  { const x = 789.2, z = -186.4, y = groundAt(d, x, z), r = -Math.PI / 4 + .03, id = ids.BELL;
    add(new THREE.BoxGeometry(6.2, 3, 6.2), stone, x, y + 1.2, z, r, id); add(new THREE.BoxGeometry(5.2, 26, 5.2), brick, x, y + 15, z, r, id);
    add(new THREE.BoxGeometry(5.5, 6, 5.5), stone, x, y + 31, z, r, id);
    for (let k = 0; k < 4; k++) { const a = r + k * Math.PI / 2, f = new THREE.CircleGeometry(1.5, 20); add(f, white, x + Math.sin(a) * 2.79, y + 31, z + Math.cos(a) * 2.79, a); add(new THREE.RingGeometry(1.4, 1.65, 24), dark, x + Math.sin(a) * 2.81, y + 31, z + Math.cos(a) * 2.81, a); const h = new THREE.PlaneGeometry(.2, 1.15); add(h, dark, x + Math.sin(a) * 2.82, y + 31.5, z + Math.cos(a) * 2.82, a); }
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const px = sx * 2.1, pz = sz * 2.1; add(new THREE.BoxGeometry(1.1, 7, 1.1), stone, x + px * Math.cos(r) + pz * Math.sin(r), y + 37.5, z - px * Math.sin(r) + pz * Math.cos(r), r, id); }
    add(new THREE.BoxGeometry(5.8, 1, 5.8), stone, x, y + 41.2, z, r, id); add(new THREE.ConeGeometry(4, 6.4, 4), roof, x, y + 44.9, z, r + Math.PI / 4, id); add(new THREE.CylinderGeometry(.08, .12, 2, 5), steel, x, y + 48.6, z); }
  // Engineering Fountain: four curved concrete fins
  { const x = 812.9, z = -338, y = groundAt(d, x, z); add(new THREE.CylinderGeometry(9, 9.4, .7, 36), stone, x, y + .3, z); add(new THREE.CylinderGeometry(8.2, 8.2, .1, 36), mat(0x5d8ea0), x, y + .68, z);
    const s = new THREE.Shape(); s.moveTo(1, 0); s.lineTo(8.6, 0); s.quadraticCurveTo(3.4, 1.6, 2.3, 11.6); s.lineTo(1.4, 11.6); s.quadraticCurveTo(1.3, 5, 1, 0);
    for (let k = 0; k < 4; k++) { const e = new THREE.ExtrudeGeometry(s, { depth: 1.1, bevelEnabled: false, curveSegments: 10 }); e.translate(0, 0, -.55); add(e, white, x, y + .4, z, k * Math.PI / 2 + Math.PI / 4); }
    add(new THREE.ConeGeometry(.5, 10, 8), new THREE.MeshLambertMaterial({ color: 0xd8eef5, transparent: true, opacity: .65 }), x, y + 5.4, z); }
  // Gateway arch on Stadium Avenue
  { const a = [597, 616], b = [583, 604.5], pts: THREE.Vector3[] = [], r = Math.atan2(b[1] - a[1], b[0] - a[0]);
    for (const p of [a, b]) { const y = groundAt(d, p[0], -p[1]); add(new THREE.BoxGeometry(2, 4.6, 2), stone, p[0], y + 2.2, -p[1], r); add(new THREE.BoxGeometry(1.5, 2, 1.5), stone, p[0], y + 5.4, -p[1], r); add(new THREE.BoxGeometry(.9, 1.2, .9), mat(0xd9c48a), p[0], y + 7, -p[1], r); add(new THREE.ConeGeometry(.8, .8, 4), steel, p[0], y + 8, -p[1], r); }
    for (let t = 0; t <= 12; t++) { const f = t / 12, x = a[0] + (b[0] - a[0]) * f, z = -(a[1] + (b[1] - a[1]) * f); pts.push(new THREE.Vector3(x, groundAt(d, x, z) + 5 + Math.sin(f * Math.PI) * 2.4, z)); }
    for (const o of [0, .75]) { const c = new THREE.CatmullRomCurve3(pts.map(p => p.clone().setY(p.y + o))); add(new THREE.TubeGeometry(c, 24, .11, 5), steel, 0, 0, 0); } }
  // University Hall spire
  { const x = 702, z = 46, y = groundAt(d, x, z); add(new THREE.BoxGeometry(4.6, 3.4, 4.6), mat(0xac735c), x, y + 22.6, z); add(new THREE.CylinderGeometry(1.9, 2.2, 3.4, 8), white, x, y + 26, z); add(new THREE.ConeGeometry(2.5, 9, 8), slate, x, y + 32, z); }
  // Slayter Center: suspended canopy on a steel tripod
  { const y = groundAt(d, 66, -692), id = ids.SCPA, V = (e: number, n: number, h: number) => new THREE.Vector3(e, y + h, -n), top = V(66, 692, 21);
    for (const f of [V(80.5, 714, 0), V(48, 693.5, 0), V(77, 683.5, 0)]) beam(f, top, 1.1, .35, steel, id);
    const s = new THREE.Shape([[72.5, 706.5], [52.5, 694], [68, 683], [78, 691]].map(p => new THREE.Vector2(p[0] - 66, p[1] - 692))), e = new THREE.ExtrudeGeometry(s, { depth: 1.1, bevelEnabled: false }); e.rotateX(-Math.PI / 2); add(e, white, 66, y + 8, -692, 0, id);
    const w = new THREE.ExtrudeGeometry(new THREE.Shape([[-9, 1], [0, -7], [7, 0], [6, 1], [0, -5], [-8, 2.4]].map(p => new THREE.Vector2(...p as [number, number]))), { depth: 8, bevelEnabled: false }); w.rotateX(-Math.PI / 2); add(w, white, 66, y, -691, 0, id);
    for (const f of [V(72, 704, 9), V(54.5, 694, 9), V(68, 684.5, 9)]) beam(f, top, .1, .1, steel);
    const st = new THREE.Shape([[80, 712], [49, 693], [67, 681], [84, 689]].map(p => new THREE.Vector2(p[0] - 66, p[1] - 692))), se = new THREE.ExtrudeGeometry(st, { depth: 1, bevelEnabled: false }); se.rotateX(-Math.PI / 2); add(se, stone, 66, y - .3, -692, 0, id); }
  return { group: g, pick };
}
