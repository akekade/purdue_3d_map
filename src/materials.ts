import * as THREE from 'three';
import type { Data } from './data';
/** Per-building data texture, 4 texels each: [wall, style] [trim, floors] [floorHeight*20, seed, purdue, state] [unused] */
export class Mats {
  tex: THREE.DataTexture; arr: Uint8Array; w = 1024;
  u = { uMat: { value: null as unknown as THREE.Texture }, uHov: { value: -1 }, uNight: { value: 0 }, uDim: { value: 0 }, uLamp: { value: null as unknown as THREE.Texture }, uExt: { value: new THREE.Vector4() } };
  grad: THREE.DataTexture;
  constructor(d: Data) {
    const h = Math.ceil(d.meta.nb * 4 / this.w); this.arr = new Uint8Array(this.w * h * 4); this.arr.set(d.mats);
    this.tex = new THREE.DataTexture(this.arr, this.w, h, THREE.RGBAFormat, THREE.UnsignedByteType); this.tex.needsUpdate = true; this.u.uMat.value = this.tex;
    // three flat light bands give the cartoon shading
    this.grad = new THREE.DataTexture(new Uint8Array([150, 205, 255]), 3, 1, THREE.RedFormat); this.grad.minFilter = this.grad.magFilter = THREE.NearestFilter; this.grad.needsUpdate = true;
    const m = d.meta; this.u.uExt.value.set(m.x0, m.y0, m.x1 - m.x0, m.y1 - m.y0);
  }
  toon(o: THREE.MeshToonMaterialParameters = {}) { return new THREE.MeshToonMaterial({ gradientMap: this.grad, ...o }); }
  setState(i: number, v: number) { this.arr[i * 16 + 11] = v; }
  flush() { this.tex.needsUpdate = true; }
}
const COMMON = `uniform sampler2D uMat,uLamp;uniform float uHov,uNight,uDim;uniform vec4 uExt;flat varying int vB;varying vec3 vW;
vec4 matTex(int b,int k){int i=b*4+k;return texelFetch(uMat,ivec2(i%1024,i/1024),0);}
vec3 lin(vec3 c){return pow(c,vec3(2.2));}
float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
vec3 vivid(vec3 c){float g=dot(c,vec3(.3,.55,.15));return clamp(mix(vec3(g),c,1.22)*1.08,0.,1.);}
vec3 lamp(){return vec3(1.,.78,.42)*texture2D(uLamp,(vec2(vW.x,-vW.z)-uExt.xy)/uExt.zw).r*uNight;}
vec3 mark(vec3 c,float st){ if(uDim>.5&&st<.5){float g=dot(c,vec3(.3,.5,.2));c=mix(c,vec3(g*.35+.34),.85);} return c;}\n`;
const VERT = `attribute float bid;flat varying int vB;varying vec3 vW;\n`;
function hook(m: THREE.Material, u: Record<string, THREE.IUniform>, f: (s: { vertexShader: string; fragmentShader: string }) => void, key: string) {
  m.onBeforeCompile = s => { Object.assign(s.uniforms, u); f(s); }; m.customProgramCacheKey = () => key;
}
const SEL = `#include <opaque_fragment>
if(matTex(vB,2).a*255.>1.5)gl_FragColor.rgb=mix(gl_FragColor.rgb,vec3(1.,.72,.16),.5);else if(abs(float(vB)-uHov)<.5)gl_FragColor.rgb=mix(gl_FragColor.rgb,vec3(1.,.83,.42),.3);`;
/** Plain coloured walls with simple window shapes that light up at night. */
export function wallMaterial(mats: Mats) {
  const m = mats.toon();
  hook(m, mats.u, s => {
    s.vertexShader = VERT + 'attribute vec4 wuv;varying vec4 vU;\n' + s.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvB=int(bid+.5);vU=wuv;vW=position;');
    s.fragmentShader = COMMON + 'varying vec4 vU;vec3 gEm;\n' + s.fragmentShader.replace('#include <map_fragment>', `
vec4 a0=matTex(vB,0),a1=matTex(vB,1),a2=matTex(vB,2);int style=int(a0.a*255.+.5);bool pu=a2.b>.002;
vec3 wall=vivid(lin(a0.rgb)),trim=lin(a1.rgb);float fls=a1.a*255.,fh=a2.r*255./20.,u=vU.x,len=vU.y,h=vU.z,top=vU.w;
float px=max(length(vec2(dFdx(u),dFdy(u))),length(vec2(dFdx(h),dFdy(h))));float far=smoothstep(.45,1.8,px);
vec3 c=wall;gEm=vec3(0.);float fy=fract(h/fh),fl=floor(h/fh);float ok=step(0.,h)*step((fl+.9)*fh,top)*step(2.2,len);
vec3 glassC=vec3(.16,.33,.48);
if(style==4){float o=step(.36,fy)*step(fy,.8)*ok;c=mix(c,vec3(.10,.10,.12),o*(1.-far*.4));gEm=vec3(1.,.8,.5)*uNight*o*.3;}
else if(style!=5){
 float pitch=style==2?2.6:(style==1?3.4:(pu?4.2:4.0));float n=max(1.,floor(len/pitch));float q=u/len*n,fx=fract(q),id=floor(q),w=0.;
 if(style==0)w=step(.28,fx)*step(fx,.72)*step(.28,fy)*step(fy,.78);
 else if(style==1)w=step(.34,fx)*step(fx,.66)*step(3.,h);
 else if(style==2){w=step(.08,fx)*step(fx,.92)*step(.14,fy)*step(fy,.94);glassC=vec3(.30,.55,.70);}
 else w=step(.4,fx)*step(fx,.6)*step(.35,fy)*step(fy,.7)*step(fl,1.5)*step(1.,mod(id,3.));
 w*=ok;float cov=(style==0?.22:(style==1?.3:(style==2?.66:.03)))*ok;vec3 near=mix(c,glassC,w);c=mix(near,mix(c,glassC,cov),far);
 float lit=step(.38,h21(vec2(id+float(vB)*.37,fl+floor(float(vB)*.11))));gEm=vec3(1.,.80,.42)*uNight*mix(w*lit,cov*.62,far)*1.15;
}
if(pu&&style!=5){float cap=step(top-.75,h)+step(h,.9)*step(0.,top-4.);c=mix(c,trim,clamp(cap,0.,1.)*(1.-far*.5));gEm*=1.-step(top-.75,h);}
c=mark(c,a2.a*255.);gEm+=c*lamp()*smoothstep(8.,0.,h)*.8;diffuseColor.rgb=c;`).replace('#include <emissivemap_fragment>', 'totalEmissiveRadiance+=gEm;').replace('#include <opaque_fragment>', SEL);
  }, 'wall');
  return m;
}
export function roofMaterial(mats: Mats) {
  const m = mats.toon({ vertexColors: true }); (m as unknown as { flatShading: boolean }).flatShading = true;
  hook(m, mats.u, s => {
    s.vertexShader = VERT + s.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvB=int(bid+.5);vW=position;');
    s.fragmentShader = COMMON + s.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb=mark(diffuseColor.rgb,matTex(vB,2).a*255.);').replace('#include <opaque_fragment>', SEL);
  }, 'roof');
  return m;
}
export function groundMaterial(mats: Mats) {
  const m = new THREE.MeshLambertMaterial({ vertexColors: true });
  hook(m, mats.u, s => {
    s.vertexShader = 'varying vec3 vW;\n' + s.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvW=position;');
    s.fragmentShader = 'uniform sampler2D uLamp;uniform float uDim,uNight;uniform vec4 uExt;varying vec3 vW;\n' + s.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
if(uDim>.5)diffuseColor.rgb=mix(diffuseColor.rgb,vec3(dot(diffuseColor.rgb,vec3(.33))),.6);`).replace('#include <emissivemap_fragment>', 'totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.,.78,.42)*texture2D(uLamp,(vec2(vW.x,-vW.z)-uExt.xy)/uExt.zw).r*uNight*1.15;');
  }, 'ground');
  return m;
}
