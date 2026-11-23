import './style.css';
import * as THREE from 'three';
import { MapControls } from 'three/examples/jsm/controls/MapControls.js';
import { Bld, groundAt, loadData } from './data';
import { Campus } from './scene';
import { landmarks } from './landmarks';
import { Picker } from './picking';
import { chips, panel, search, tag, title } from './ui';
const $ = <T extends HTMLElement>(s: string) => document.querySelector(s) as T;
async function boot() {
  const canvas = $<HTMLCanvasElement>('#gl'), lab = $<HTMLCanvasElement>('#labels'), lc = lab.getContext('2d')!;
  let r: THREE.WebGLRenderer;
  try { r = new THREE.WebGLRenderer({ canvas, antialias: true, logarithmicDepthBuffer: false, powerPreference: 'high-performance' }); }
  catch { throw new Error('This page needs WebGL 2. Turn on hardware acceleration or try another browser.'); }
  const d = await loadData((f, m) => { $('#lbar').style.width = f * 100 + '%'; $('#lmsg').textContent = m; });
  r.toneMapping = THREE.NoToneMapping; r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap; r.shadowMap.autoUpdate = false;
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(42, 1, 2, 16000), ctl = new MapControls(cam, canvas);
  ctl.enableDamping = true; ctl.dampingFactor = .12; ctl.maxPolarAngle = 1.5; ctl.minDistance = 30; ctl.maxDistance = 5200; ctl.zoomToCursor = true; ctl.screenSpacePanning = false;
  const sun = new THREE.DirectionalLight(0xffffff, 3), hemi = new THREE.HemisphereLight(0xcfe0f5, 0xa39a88, 1.3); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -.0006; sun.shadow.normalBias = .6; scene.add(sun, sun.target, hemi); scene.fog = new THREE.Fog(0xcfdcec, 4500, 14000);
  const campus = new Campus(d, r.capabilities.getMaxAnisotropy()); await campus.build(); scene.add(campus.group);
  const byCode = new Map<string, Bld>(), ids: Record<string, number> = {}; for (const b of d.blds) for (const o of b.off ?? []) { if (!byCode.has(o.c) || b.h * Math.sqrt(b.area) > byCode.get(o.c)!.h * Math.sqrt(byCode.get(o.c)!.area)) { byCode.set(o.c, b); ids[o.c] = b.i; } }
  const lm = landmarks(d, ids); scene.add(lm.group);
  const picker = new Picker(campus.roofGeos, lm.pick, []);
  let dirty = 2, sel: Bld | null = null, filter: string | null = null, shadowKey = '', walk = false, W = 1, H = 1; const need = () => { dirty = 2; }; campus.onchange = need;
  // --- camera -----------------------------------------------------------------
  const HOME = { t: new THREE.Vector3(640, 38, -130), p: new THREE.Vector3(470, 760, 900) }; let fly: null | { t0: number; dur: number; p0: THREE.Vector3; p1: THREE.Vector3; a0: THREE.Vector3; a1: THREE.Vector3 } = null;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const flyTo = (t: THREE.Vector3, p: THREE.Vector3, dur = 1100) => { if (reduce) { ctl.target.copy(t); cam.position.copy(p); need(); return; } fly = { t0: performance.now(), dur, p0: cam.position.clone(), p1: p, a0: ctl.target.clone(), a1: t }; need(); };
  cam.position.copy(HOME.p); ctl.target.copy(HOME.t); canvas.addEventListener('pointerdown', () => fly = null); canvas.addEventListener('wheel', () => fly = null, { passive: true });
  const size = () => { W = innerWidth; H = innerHeight; const pr = Math.min(devicePixelRatio, 2); r.setPixelRatio(pr); r.setSize(W, H, false); cam.aspect = W / H; cam.updateProjectionMatrix(); lab.width = W * pr; lab.height = H * pr; lc.setTransform(pr, 0, 0, pr, 0, 0); need(); }; addEventListener('resize', size); size();
  ctl.addEventListener('change', need); ctl.update();
  // --- sun --------------------------------------------------------------------
  const sdir = new THREE.Vector3();
  const setTime = (h: number) => {
    const lat = .7055, dec = .26, ha = (h - 13.8) / 24 * Math.PI * 2, el = Math.asin(Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(ha)), az = Math.atan2(Math.sin(ha), Math.cos(ha) * Math.sin(lat) - Math.tan(dec) * Math.cos(lat));
    const day = THREE.MathUtils.smoothstep(el, -.1, .2), gold = 1 - THREE.MathUtils.smoothstep(el, .05, .55), e = Math.max(el, .16); sdir.set(-Math.sin(az) * Math.cos(e), Math.sin(e), Math.cos(az) * Math.cos(e));
    sun.color.setRGB(1, 1 - .3 * gold, 1 - .55 * gold).lerp(new THREE.Color(.45, .55, .85), 1 - day); sun.intensity = .3 + 1.75 * day; hemi.intensity = .4 + 1.35 * day; hemi.color.set(0xcfe0f5).lerp(new THREE.Color(0x27365c), 1 - day);
    const sky = new THREE.Color(0xc3d7ee).lerp(new THREE.Color(0xf0c39a), gold * day * .75).lerp(new THREE.Color(0x0d1526), 1 - day); scene.background = sky; (scene.fog as THREE.Fog).color.copy(sky); campus.mats.u.uNight.value = 1 - day;
    const hh = Math.floor(h), mm = Math.round((h - hh) * 60); $('#timeout').textContent = `${(hh + 11) % 12 + 1}${mm ? ':' + String(mm).padStart(2, '0') : ''} ${hh < 12 ? 'AM' : 'PM'}`; shadowKey = ''; need();
  };
  const ti = $<HTMLInputElement>('#time'); ti.oninput = () => setTime(+ti.value); setTime(+ti.value);
  const shadows = () => {
    const dist = cam.position.distanceTo(walk ? cam.position : ctl.target), s = THREE.MathUtils.clamp((walk ? 220 : dist) * .75, 140, 1500), c = walk ? cam.position : ctl.target, g = s / 12, x = Math.round(c.x / g) * g, z = Math.round(c.z / g) * g, k = `${x.toFixed()},${z.toFixed()},${(s / 40).toFixed()}`; if (k === shadowKey) return; shadowKey = k;
    const y = groundAt(d, x, z); sun.target.position.set(x, y, z); sun.position.copy(sdir).multiplyScalar(1800).add(sun.target.position); const o = sun.shadow.camera; o.left = o.bottom = -s; o.right = o.top = s; o.near = 100; o.far = 3600; o.updateProjectionMatrix(); sun.shadow.normalBias = s / 900; r.shadowMap.needsUpdate = true;
  };
  const states = () => { const sc = new Set(sel?.off?.map(o => o.c)); d.blds.forEach(b => campus.mats.setState(b.i, sel && (b === sel || b.off?.some(o => sc.has(o.c))) ? 2 : filter && b.off && b.cat === filter ? 1 : 0)); campus.mats.flush(); };
  // --- selection ----------------------------------------------------------------
  const select = (b: Bld | null, go = false) => {
    sel = b; states(); panel(b, () => select(null)); const c = b?.off?.[0].c; history.replaceState(null, '', c ? '#' + encodeURIComponent(c) : location.pathname + location.search);
    if (b && go) { if (walk) setWalk(false); const y = groundAt(d, b.x, -b.y), R = THREE.MathUtils.clamp(Math.sqrt(b.area) * 2.1 + b.h * 2, 130, 620), t = new THREE.Vector3(b.x, y + b.h * .35, -b.y); flyTo(t, new THREE.Vector3(b.x - R * .22, y + R * .72, -b.y + R * .85)); } need();
  };
  const inBox = (x: number, y: number) => picker.at(r, cam, x, y, W, H), valid = (i: number) => i >= 0 && i < d.blds.length ? d.blds[i] : null;
  let down = [0, 0, 0], moved = false, hoverAt = 0, hx = -1, hy = -1; const tip = $('#tip');
  canvas.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY, performance.now()]; moved = false; $('#hint').classList.add('gone'); (document.activeElement as HTMLElement)?.blur?.(); });
  canvas.addEventListener('pointermove', e => { if (Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) moved = true; if (e.pointerType === 'mouse') { hx = e.clientX; hy = e.clientY; if (e.buttons) { tip.hidden = true; hx = -1; } } });
  canvas.addEventListener('pointerleave', () => { hx = -1; tip.hidden = true; if (campus.mats.u.uHov.value !== -1) { campus.mats.u.uHov.value = -1; need(); } });
  canvas.addEventListener('pointerup', e => { if (moved || e.button !== 0 || performance.now() - down[2] > 600) return; select(valid(inBox(e.clientX, e.clientY))); });
  canvas.addEventListener('dblclick', e => { const b = valid(inBox(e.clientX, e.clientY)); if (b) select(b, true); });
  const hover = (now: number) => {
    if (hx < 0 || now - hoverAt < 70) return; hoverAt = now; const b = valid(inBox(hx, hy)), id = b ? b.i : -1; if (id !== campus.mats.u.uHov.value) { campus.mats.u.uHov.value = id; need(); canvas.style.cursor = b ? 'pointer' : ''; }
    if (b && (b.off || b.name)) { tip.textContent = b.off ? `${b.off.map(o => o.n).join(', ')} · ${tag(b)} · ${title(b)}` : title(b); tip.hidden = false; tip.style.transform = `translate(${Math.min(hx + 14, W - tip.offsetWidth - 8)}px,${Math.min(hy + 16, H - 40)}px)`; } else tip.hidden = true;
  };
  search(d.blds, b => select(b, true));
  chips(d.blds, c => { filter = c; campus.mats.u.uDim.value = c ? 1 : 0; states(); need(); });
  // --- buttons --------------------------------------------------------------------
  const az = () => Math.atan2(cam.position.x - ctl.target.x, cam.position.z - ctl.target.z);
  const orbit = (pol: number, a = az()) => { const R = cam.position.distanceTo(ctl.target); flyTo(ctl.target.clone(), new THREE.Vector3(Math.sin(a) * Math.sin(pol), Math.cos(pol), Math.cos(a) * Math.sin(pol)).multiplyScalar(R).add(ctl.target), 700); };
  const zoom = (f: number) => { const v = cam.position.clone().sub(ctl.target); flyTo(ctl.target.clone(), v.multiplyScalar(THREE.MathUtils.clamp(v.length() * f, 60, 5000) / v.length()).add(ctl.target), 350); };
  $('#b-north').onclick = () => orbit(ctl.getPolarAngle(), 0); $('#b-in').onclick = () => zoom(.62); $('#b-out').onclick = () => zoom(1.6); $('#b-top').onclick = () => orbit(.002, 0); $('#b-tilt').onclick = () => orbit(.92); $('#b-home').onclick = () => { if (walk) setWalk(false); flyTo(HOME.t.clone(), HOME.p.clone()); };
  $<HTMLInputElement>('#c-labels').onchange = need; $<HTMLInputElement>('#c-trees').onchange = e => { campus.trees.visible = (e.target as HTMLInputElement).checked; shadowKey = ''; need(); };
  // --- walk mode ---------------------------------------------------------------------
  const keys = new Set<string>(); let yaw = 0, pitch = 0; const K: Record<string, string> = { arrowup: 'w', arrowdown: 's', arrowleft: 'a', arrowright: 'd' };
  const setWalk = (on: boolean) => {
    walk = on; ctl.enabled = !on; fly = null; $('#walkui').hidden = !on; document.body.classList.toggle('walking', on); tip.hidden = true; keys.clear();
    if (on) { yaw = az(); pitch = 0; cam.position.set(ctl.target.x, 0, ctl.target.z); cam.position.y = groundAt(d, cam.position.x, cam.position.z) + 1.8; cam.near = .3; }
    else { cam.near = 2; const f = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)); ctl.target.copy(cam.position).addScaledVector(f, 30); ctl.target.y = groundAt(d, ctl.target.x, ctl.target.z); cam.position.addScaledVector(f, -220); cam.position.y += 220; ctl.update(); } cam.updateProjectionMatrix(); shadowKey = ''; need();
  };
  $('#b-walk').onclick = () => setWalk(!walk); $('#b-exit').onclick = () => setWalk(false);
  addEventListener('keydown', e => { if ((e.target as HTMLElement).tagName === 'INPUT' && (e.target as HTMLInputElement).type === 'search') return; if (e.key === 'Escape') { if (walk) setWalk(false); else select(null); } const k = e.key.toLowerCase(); if (walk) { if (K[k]) e.preventDefault(); keys.add(K[k] ?? k); } });
  addEventListener('keyup', e => { const k = e.key.toLowerCase(); keys.delete(K[k] ?? k); }); addEventListener('blur', () => keys.clear());
  $('#pad').querySelectorAll('button').forEach(b => { const k = b.dataset.k!; b.onpointerdown = () => keys.add(k); b.onpointerup = b.onpointerleave = b.onpointercancel = () => keys.delete(k); });
  canvas.addEventListener('pointermove', e => { if (walk && e.buttons) { yaw += e.movementX * .0042; pitch = THREE.MathUtils.clamp(pitch + e.movementY * .0035, -1.1, 1.2); need(); } });
  // --- labels -----------------------------------------------------------------------
  const L = d.blds.filter(b => b.off && b.off.some(o => byCode.get(o.c) === b)).sort((a, b) => b.area - a.area).map(b => ({ b, t: tag(b), v: new THREE.Vector3(b.x, (b.z ?? 0) + b.h + 5, -b.y) })), v = new THREE.Vector3();
  const drawLabels = () => {
    lc.clearRect(0, 0, W, H); const used: number[][] = []; lc.font = '600 12px ui-sans-serif,system-ui,sans-serif'; lc.textAlign = 'center'; lc.textBaseline = 'middle';
    const box = (b: Bld, t: string, p: THREE.Vector3, on: boolean) => {
      v.copy(p).project(cam); if (v.z > 1 || Math.abs(v.x) > 1.05 || Math.abs(v.y) > 1.05) return; const x = (v.x + 1) / 2 * W, y = (1 - v.y) / 2 * H, w = lc.measureText(t).width + 12, q = [x - w / 2 - 2, y - 11, x + w / 2 + 2, y + 11];
      if (!on && used.some(u => q[0] < u[2] && q[2] > u[0] && q[1] < u[3] && q[3] > u[1])) return; used.push(q);
      lc.fillStyle = on ? '#ffc23d' : 'rgba(27,25,22,.82)'; lc.beginPath(); lc.roundRect(x - w / 2, y - 9, w, 18, 4); lc.fill(); if (on) { lc.beginPath(); lc.moveTo(x - 5, y + 8); lc.lineTo(x + 5, y + 8); lc.lineTo(x, y + 15); lc.fill(); } lc.fillStyle = on ? '#1b1916' : '#f7f3ea'; lc.fillText(t, x, y + .5); void b;
    };
    if (sel) box(sel, sel.off ? sel.off.map(o => o.n).join(' / ') : title(sel).slice(0, 28), new THREE.Vector3(sel.x, (sel.z ?? 0) + sel.h + 8, -sel.y), true);
    if (!$<HTMLInputElement>('#c-labels').checked) return; const far = walk ? 350 : 3000;
    for (const l of L) { if (l.b === sel || (filter && l.b.cat !== filter) || l.v.distanceTo(cam.position) > far) continue; box(l.b, l.t, l.v, false); }
  };
  // --- loop --------------------------------------------------------------------------
  let last = performance.now(); const needle = document.querySelector('#needle') as SVGGElement, stats = { frames: 0, calls: 0, tris: 0 };
  const frame = (now: number) => {
    requestAnimationFrame(frame); const dt = Math.min((now - last) / 1000, .1); last = now;
    if (fly) { const f = Math.min((now - fly.t0) / fly.dur, 1), e = f < .5 ? 4 * f ** 3 : 1 - (-2 * f + 2) ** 3 / 2; cam.position.lerpVectors(fly.p0, fly.p1, e); ctl.target.lerpVectors(fly.a0, fly.a1, e); if (f >= 1) fly = null; need(); }
    if (walk) {
      const f = (keys.has('w') ? 1 : 0) - (keys.has('s') ? 1 : 0), s = (keys.has('d') ? 1 : 0) - (keys.has('a') ? 1 : 0), sp = (keys.has('shift') ? 22 : 8) * dt;
      if (f || s) { cam.position.x += (-Math.sin(yaw) * f + Math.cos(yaw) * s) * sp; cam.position.z += (-Math.cos(yaw) * f - Math.sin(yaw) * s) * sp; need(); }
      cam.position.x = THREE.MathUtils.clamp(cam.position.x, d.meta.x0 + 20, d.meta.x1 - 20); cam.position.z = THREE.MathUtils.clamp(cam.position.z, -d.meta.y1 + 20, -d.meta.y0 - 20); cam.position.y = groundAt(d, cam.position.x, cam.position.z) + 1.8; cam.rotation.set(pitch, yaw, 0, 'YXZ');
    } else {
      ctl.update(); const t = ctl.target, cx = THREE.MathUtils.clamp(t.x, d.meta.x0, d.meta.x1), cz = THREE.MathUtils.clamp(t.z, -d.meta.y1, -d.meta.y0); cam.position.x += cx - t.x; cam.position.z += cz - t.z; t.x = cx; t.z = cz;
      const gy = groundAt(d, cam.position.x, cam.position.z) + 4; if (cam.position.y < gy) cam.position.y = gy;
      const want = cam.position.y > 900 ? 12 : 2; if (cam.near !== want) { cam.near = want; cam.updateProjectionMatrix(); }
    }
    hover(now); if (dirty <= 0) return; dirty--;
    campus.update(cam, walk ? cam.position : ctl.target); shadows(); r.render(scene, cam); stats.frames++; stats.calls = r.info.render.calls; stats.tris = r.info.render.triangles; drawLabels(); needle.style.transform = `rotate(${walk ? yaw : az()}rad)`;
  };
  requestAnimationFrame(frame); $('#loading').classList.add('done'); setTimeout(() => $('#loading').remove(), 600); setTimeout(() => $('#hint').classList.add('gone'), 12000);
  const fromHash = () => { const c = decodeURIComponent(location.hash.slice(1)).toUpperCase(), b = byCode.get(c) ?? d.blds.find(x => x.off?.some(o => o.n === c)); if (b) select(b, true); }; fromHash(); addEventListener('hashchange', fromHash);
  Object.assign(window as unknown as Record<string, unknown>, { __app: { d, cam, ctl, select, byCode, campus, stats, need, setTime, get sel() { return sel; }, screen(b: Bld, up = .9) { v.set(b.x, (b.z ?? 0) + b.h * up, -b.y).project(cam); return [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H]; }, idle: () => !fly && dirty <= 0 && !campus.pending } });
}
boot().catch(e => { console.error(e); $('#lmsg').textContent = e?.message ?? 'Could not load the campus data.'; $('#loading').classList.add('err'); });
