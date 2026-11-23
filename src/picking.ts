import * as THREE from 'three';
/** GPU picking: renders building ids into one pixel. */
export class Picker {
  scene = new THREE.Scene(); rt = new THREE.WebGLRenderTarget(1, 1); buf = new Uint8Array(4); cam = new THREE.PerspectiveCamera();
  constructor(geos: THREE.BufferGeometry[], extra: { geo: THREE.BufferGeometry; id: number }[], ground: THREE.BufferGeometry[]) {
    const m = new THREE.ShaderMaterial({ side: THREE.DoubleSide, vertexShader: 'attribute float bid;flat varying int b;void main(){b=int(bid+.5)+1;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}', fragmentShader: 'flat varying int b;void main(){gl_FragColor=vec4(float(b&255),float((b>>8)&255),0.,255.)/255.;}' });
    const add = (g: THREE.BufferGeometry) => this.scene.add(new THREE.Mesh(g, m)); geos.forEach(add);
    for (const e of extra) { const g = e.geo.clone(); g.setAttribute('bid', new THREE.BufferAttribute(new Uint16Array(g.attributes.position.count).fill(e.id), 1)); add(g); }
    const gm = new THREE.MeshBasicMaterial({ color: 0 }); ground.forEach(g => this.scene.add(new THREE.Mesh(g, gm))); this.scene.background = new THREE.Color(0);
  }
  at(r: THREE.WebGLRenderer, cam: THREE.PerspectiveCamera, x: number, y: number, w: number, h: number) {
    this.cam.copy(cam); this.cam.setViewOffset(w, h, x, y, 1, 1); const cs = r.outputColorSpace; r.outputColorSpace = THREE.LinearSRGBColorSpace; const sm = r.shadowMap.enabled; r.shadowMap.enabled = false;
    r.setRenderTarget(this.rt); r.render(this.scene, this.cam); r.readRenderTargetPixels(this.rt, 0, 0, 1, 1, this.buf); r.setRenderTarget(null); r.outputColorSpace = cs; r.shadowMap.enabled = sm;
    return this.buf[0] + this.buf[1] * 256 - 1;
  }
}
