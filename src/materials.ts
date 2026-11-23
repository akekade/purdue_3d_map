import * as THREE from 'three';
import type { Data } from './data';
/** Per-building data texture: 4 texels each: [wall, style] [trim, floors] [floorHeight*20, seed, purdue, state] [photo offset x, y, base height] */
export class Mats {
  tex: THREE.DataTexture; arr: Uint8Array; w = 1024;
  u = { uMat: { value: null as unknown as THREE.Texture }, uHov: { value: -1 }, uNight: { value: 0 }, uDim: { value: 0 }, uLean: { value: new THREE.Matrix3() } };
  constructor(d: Data) {
    const h = Math.ceil(d.meta.nb * 4 / this.w); this.arr = new Uint8Array(this.w * h * 4); this.arr.set(d.mats);
    this.tex = new THREE.DataTexture(this.arr, this.w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
    const [a, b] = d.meta.lean; this.u.uLean.value.set(a[1], a[2], a[3], b[1], b[2], b[3], 0, 0, 0);
    this.tex.needsUpdate = true; this.u.uMat.value = this.tex;
  }
  setState(i: number, v: number) { this.arr[i * 16 + 11] = v; }
  flush() { this.tex.needsUpdate = true; }
}
const COMMON = `uniform sampler2D uMat;uniform float uHov,uNight,uDim;flat varying int vB;varying vec3 vW;
vec4 matTex(int b,int k){int i=b*4+k;return texelFetch(uMat,ivec2(i%1024,i/1024),0);}
vec3 lin(vec3 c){return pow(c,vec3(2.2));}
float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
vec3 mark(vec3 c,float st){ if(uDim>.5&&st<.5){float g=dot(c,vec3(.3,.5,.2));c=mix(c,vec3(g*.45+.16),.82);} return c;}`;
const VERT = `attribute float bid;flat varying int vB;varying vec3 vW;\n`;
function hook(m: THREE.Material, u: Record<string, THREE.IUniform>, f: (s: { vertexShader: string; fragmentShader: string }) => void, key: string) {
  m.onBeforeCompile = s => { Object.assign(s.uniforms, u); f(s); }; m.customProgramCacheKey = () => key;
}
const SEL = `#include <opaque_fragment>
if(matTex(vB,2).a*255.>1.5)gl_FragColor.rgb=mix(gl_FragColor.rgb,vec3(1.,.72,.16),.46);else if(abs(float(vB)-uHov)<.5)gl_FragColor.rgb=mix(gl_FragColor.rgb,vec3(1.,.83,.42),.26);`;
export function wallMaterial(mats: Mats) {
  const m = new THREE.MeshLambertMaterial();
  hook(m, mats.u, s => {
    s.vertexShader = VERT + 'attribute vec3 wuv;varying vec3 vU;\n' + s.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvB=int(bid+.5);vU=wuv;vW=position;');
    s.fragmentShader = COMMON + 'varying vec3 vU;vec3 gEm;\n' + s.fragmentShader.replace('#include <map_fragment>', `
vec4 a0=matTex(vB,0),a1=matTex(vB,1),a2=matTex(vB,2);int style=int(a0.a*255.+.5);
vec3 wall=lin(a0.rgb),trim=lin(a1.rgb);float fls=a1.a*255.,fh=a2.r*255./20.,u=vU.x,len=vU.y,h=vU.z;
float px=max(length(vec2(dFdx(u),dFdy(u))),length(vec2(dFdx(h),dFdy(h))));float far=smoothstep(.35,1.5,px);
vec3 c=wall;gEm=vec3(0.);float fy=fract(h/fh),fl=floor(h/fh);float ok=step(h,fls*fh)*step(2.2,len);
vec3 glassC=mix(vec3(.05,.075,.10),vec3(.16,.22,.28),.5+.5*sin(fl*2.1+floor(u/3.)));
float brick=smoothstep(.12,.02,px);float row=floor(h/.22);
float grain=h21(vec2(floor(u/.45+mod(row,2.)*.5),row))*brick+(1.-brick)*.5;
if(style==5){c*=.93+.07*step(.5,fract(u/.8))*(1.-far);if(h<.8)c*=.85;}
else if(style==4){float o=step(.34,fy)*step(fy,.82)*ok;float pil=step(.07,fract(u/8.5));c=mix(c,vec3(.05),o*pil*(1.-far*.35)*.9);}
else{
 if(style!=2)c*=.91+.18*grain;
 float pitch=style==2?1.6:(style==1?3.:(a2.b>.002?3.4:3.9));float n=max(1.,floor(len/pitch));float q=u/len*n,fx=fract(q),id=floor(q);
 float w=0.,fr=0.;
 if(style==0){w=step(.27,fx)*step(fx,.73)*step(.27,fy)*step(fy,.80);float o=step(.23,fx)*step(fx,.77)*step(.20,fy)*step(fy,.86);fr=o-w;}
 else if(style==1){w=step(.36,fx)*step(fx,.64)*step(3.,h);fr=step(.31,fx)*step(fx,.69)*step(3.,h)-w;float sp=step(.86,fy);c=mix(c,c*.8,w*sp);}
 else if(style==2){w=step(.07,fx)*step(fx,.93)*step(.13,fy);glassC=mix(vec3(.10,.17,.23),trim,.38);}
 else if(style==3){w=step(.42,fx)*step(fx,.58)*step(.35,fy)*step(fy,.7)*step(fl,1.5)*step(1.,mod(id,3.));fr=0.;}
 w*=ok;fr*=ok;vec3 near=mix(mix(c,trim,fr*.75),glassC,w);
 float cov=style==0?.24:(style==1?.26:(style==2?.8:.03));vec3 avg=mix(c,glassC,cov*ok);c=mix(near,avg,far);
 float lit=step(.52,h21(vec2(id+float(vB)*.37,fl+floor(float(vB)*.11))));gEm=vec3(1.,.74,.40)*uNight*lit*mix(w,cov*ok,far)*.85;
 if(a2.b>.002&&style<2&&h<1.1)c=mix(c,trim*.82,.85*(1.-far*.5));
}
diffuseColor.rgb=mark(c,a2.a*255.);`).replace('#include <emissivemap_fragment>', 'totalEmissiveRadiance+=gEm;').replace('#include <opaque_fragment>', SEL);
  }, 'wall');
  return m;
}
export interface TileU { [k: string]: THREE.IUniform; uMap: { value: THREE.Texture }; uRect: { value: THREE.Vector4 } }
export function roofMaterial(mats: Mats, t: TileU) {
  const m = new THREE.MeshLambertMaterial({ flatShading: true });
  hook(m, { ...mats.u, ...t }, s => {
    s.vertexShader = VERT + s.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvB=int(bid+.5);vW=position;');
    s.fragmentShader = COMMON + 'uniform sampler2D uMap;uniform vec4 uRect;uniform mat3 uLean;\n' + s.fragmentShader.replace('#include <map_fragment>', `
vec4 a3=matTex(vB,3);vec2 en=vec2(vW.x,-vW.z);vec2 off=a3.rg*12.-6.+max(vW.y-a3.b*76.5,0.)*(uLean*vec3(1.,en/1000.)).xy;
vec4 a0=matTex(vB,0),a2=matTex(vB,2);vec3 gn=normalize(cross(dFdx(vW),dFdy(vW)));
vec3 rc=lin(texture2D(uMap,(en+off-uRect.xy)/uRect.zw).rgb);
float steep=1.-smoothstep(.34,.5,abs(gn.y));diffuseColor.rgb=mark(mix(rc,lin(a0.rgb)*.92,steep),a2.a*255.);`).replace('#include <opaque_fragment>', SEL);
  }, 'roof');
  return m;
}
export function groundMaterial(mats: Mats, t: TileU) {
  const m = new THREE.MeshLambertMaterial();
  hook(m, { ...t, uDim: mats.u.uDim }, s => {
    s.vertexShader = 'varying vec3 vW;\n' + s.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvW=position;');
    s.fragmentShader = 'uniform sampler2D uMap;uniform vec4 uRect;uniform float uDim;varying vec3 vW;\n' + s.fragmentShader.replace('#include <map_fragment>', `
vec3 gc=pow(texture2D(uMap,(vec2(vW.x,-vW.z)-uRect.xy)/uRect.zw).rgb,vec3(2.2));if(uDim>.5)gc=mix(gc,vec3(dot(gc,vec3(.33))),.55)*.8;diffuseColor.rgb=gc;`);
  }, 'ground');
  return m;
}
