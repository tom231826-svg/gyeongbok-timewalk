/* 경복궁 타임워크 v0.2 — 걸어다니는 3D 시대여행
   좌표계: 미터. +x=동, -z=북. 배치는 북궐도형·현 경복궁 중심축 근사. */
"use strict";

// ───────────────────────── 시대 정의 ─────────────────────────
// 고증 등급: A=실측(도면·스캔·사진), B=학술 추정, C=상상 보완 포함
const ERAS = [
  { yr:"1395", nm:"태조 창건",   badge:"고증 B·C — 실록 등 문헌 기반 추정 (도면 없음, 상상 보완 포함)", est:true,
    sky:0x9db8d4, skyTop:0x789bc5, skyHorizon:0xe0d3bd, exposure:1.0,
    fog:[0xa8bccd,180,900], hemi:[0xcfe0ee,0x6b6154,0.75], sun:[[120,140,160],0.85,0xfff2dd], fill:[0xbfd3ec,0.18] },
  { yr:"15세기", nm:"세종 시대", badge:"고증 B·C — 문헌 기반 추정 (경회루·집현전·흠경각)", est:true,
    sky:0x87b7e8, skyTop:0x5fa9e7, skyHorizon:0xe7f1fb, exposure:1.04,
    fog:[0xa5c6e4,220,1100], hemi:[0xdceafc,0x77694f,0.9], sun:[[80,220,60],1.0,0xffffff], fill:[0xb9d9ff,0.2] },
  { yr:"1592–1865", nm:"폐허기", badge:"고증 B·C — 문헌 기반 연출, 273년간 방치된 옛터", est:true,
    sky:0x4a4453, skyTop:0x2e2b36, skyHorizon:0x6f5f5b, exposure:0.82,
    fog:[0x544c58,60,420], hemi:[0x6d6377,0x2e2a2c,0.55], sun:[[-100,60,120],0.25,0xc9b6c9], fill:[0x84778a,0.1] },
  { yr:"1888", nm:"고종 중건기", badge:"고증 A·B — 북궐도형 실측 배치 + 회랑 실측 스캔, 일부 추정", est:false,
    sky:0xd9a86c, skyTop:0xb87946, skyHorizon:0xf0c98c, exposure:0.98,
    fog:[0xd9b083,180,950], hemi:[0xf2d9b4,0x6f5b44,0.8], sun:[[-160,70,60],0.95,0xffd9a0], fill:[0xffe0ba,0.16] },
  { yr:"1929", nm:"일제강점기", badge:"고증 A·B — 유리건판 사진·기록 기반 + 회랑 실측 스캔", est:false,
    sky:0xb9b2a2, skyTop:0x8f8b83, skyHorizon:0xd9d1be, exposure:0.9,
    fog:[0xbdb5a4,140,750], hemi:[0xd8d2c2,0x6e685c,0.75], sun:[[60,180,80],0.55,0xf3ecdc], fill:[0xd8d0c2,0.14] },
  { yr:"2026", nm:"현재",        badge:"고증 A — 실측 스캔 원본(회랑), 2차 복원정비 진행 중(~2045)", est:false,
    sky:0x69a8e8, skyTop:0x4f9dec, skyHorizon:0xe4f2ff, exposure:1.06,
    fog:[0xa9cdf0,260,1300], hemi:[0xe8f2ff,0x8a7f6d,0.95], sun:[[-120,240,-40],1.05,0xffffff], fill:[0xbfdcff,0.22] },
];

// ───────────────────────── 기본 세팅 ─────────────────────────
const canvas = document.getElementById("gl");
const renderer = new THREE.WebGLRenderer({ canvas, antialias:true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.shadowMap.autoUpdate = true;
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(72, 1, 0.1, 2000);
const hemi = new THREE.HemisphereLight(0xffffff, 0x777777, 0.8);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 1);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = -0.00012;
sun.shadow.normalBias = 0.035;
Object.assign(sun.shadow.camera, { left:-150, right:150, top:150, bottom:-150, near:10, far:700 });
sun.shadow.camera.updateProjectionMatrix();
const sunDir = new THREE.Vector3(1, 1, 1);   // 시대별 태양 방향(정규화), 매 프레임 플레이어 추적
sun.target.position.set(0, 0, -260);
const fill = new THREE.DirectionalLight(0xbfd6ff, 0.18);
fill.position.set(180, 120, -260);
scene.add(sun, sun.target, fill);

// 후처리 체인은 하늘 돔 정의 뒤에서 초기화 — 여기선 선언만 (resize가 참조)
let composer = null, ssaoPass = null, eraFxPass = null;
const POSTFX_ON = !(/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || (navigator.maxTouchPoints || 0) > 2);

function resize(){
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  if(composer){
    composer.setSize(innerWidth, innerHeight);
    if(ssaoPass) ssaoPass.setSize(innerWidth, innerHeight);
  }
}
addEventListener("resize", resize); resize();

// ───────────────────────── 절차 텍스처 ─────────────────────────
function ctex(w, h, fn, rx=1, ry=1){
  const c = document.createElement("canvas"); c.width=w; c.height=h;
  fn(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry);
  t.encoding = THREE.sRGBEncoding;
  t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return t;
}
function noise(g, w, h, alpha){
  for (let i=0;i<w*h/28;i++){
    g.fillStyle = `rgba(0,0,0,${Math.random()*alpha})`;
    g.fillRect(Math.random()*w, Math.random()*h, 2, 2);
    g.fillStyle = `rgba(255,255,255,${Math.random()*alpha*0.7})`;
    g.fillRect(Math.random()*w, Math.random()*h, 2, 2);
  }
}
const texPaving = ctex(1024,1024,(g,w,h)=>{         // 박석 마당: 불규칙 판석 + 톤 편차
  g.fillStyle="#8f867a"; g.fillRect(0,0,w,h);       // 줄눈(어두운 바탕)
  let y=0, row=0;
  while(y<h){
    const rh = 46 + ((row*37) % 30);
    let x = -((row*29) % 40);
    while(x<w){
      const rw = 64 + ((x*13 + row*71) % 52);
      const t = 168 + ((x*7 + y*11 + row*23) % 34);   // 판석별 밝기 편차
      g.fillStyle = `rgb(${t},${t-7},${t-20})`;
      g.fillRect(x+2, y+2, rw-4, rh-4);
      g.fillStyle = `rgba(255,255,255,${0.04 + (x%5)*0.008})`;   // 윗면 하이라이트
      g.fillRect(x+2, y+2, rw-4, 5);
      x += rw;
    }
    y += rh; row++;
  }
  noise(g,w,h,0.09);
}, 10, 10);                                          // 판석 실측 약 1.2m 스케일
const texEarth = ctex(512,512,(g,w,h)=>{ g.fillStyle="#a9977c"; g.fillRect(0,0,w,h); noise(g,w,h,0.13); });
const texStone = ctex(256,256,(g,w,h)=>{
  g.fillStyle="#cfc8ba"; g.fillRect(0,0,w,h);
  g.strokeStyle="rgba(96,88,76,.5)"; g.lineWidth=3;
  for(let y=0;y<h;y+=42) { g.beginPath(); g.moveTo(0,y); g.lineTo(w,y); g.stroke(); }
  for(let y=0;y<h;y+=42) for(let x=((y/42)%2)*60;x<w;x+=120){ g.beginPath(); g.moveTo(x,y); g.lineTo(x,y+42); g.stroke(); }
  noise(g,w,h,0.08);
});
const texRoof = ctex(256,256,(g,w,h)=>{              // 기와 골
  g.fillStyle="#3a3a40"; g.fillRect(0,0,w,h);
  for(let x=0;x<w;x+=16){ g.fillStyle="rgba(0,0,0,.35)"; g.fillRect(x,0,6,h);
    g.fillStyle="rgba(255,255,255,.06)"; g.fillRect(x+9,0,3,h); }
  noise(g,w,h,0.05);
}, 8, 2);
const texDancheong = ctex(512,64,(g,w,h)=>{          // 처마 밑 단청 띠
  g.fillStyle="#155e52"; g.fillRect(0,0,w,h);
  g.fillStyle="#0c4238"; g.fillRect(0,h-14,w,14);
  for(let x=0;x<w;x+=32){
    g.fillStyle="#d8593c"; g.beginPath(); g.arc(x+16,22,9,0,7); g.fill();
    g.fillStyle="#e8d9a8"; g.beginPath(); g.arc(x+16,22,4,0,7); g.fill();
  }
}, 6, 1);
const texGov = ctex(256,256,(g,w,h)=>{               // 총독부 화강석+창
  g.fillStyle="#b6b3ab"; g.fillRect(0,0,w,h);
  g.fillStyle="#3c3a38";
  for(let y=26;y<h;y+=64) for(let x=18;x<w;x+=52) g.fillRect(x,y,26,40);
  noise(g,w,h,0.05);
}, 4, 2);
const texWater = ctex(256,256,(g,w,h)=>{ g.fillStyle="#4f7a76"; g.fillRect(0,0,w,h); noise(g,w,h,0.06); });
const texDoor = ctex(256,256,(g,w,h)=>{              // 궁문 판문
  g.fillStyle="#5a2d24"; g.fillRect(0,0,w,h);
  g.strokeStyle="rgba(18,10,8,.55)"; g.lineWidth=5;
  for(let x=0;x<w;x+=42){ g.beginPath(); g.moveTo(x,0); g.lineTo(x,h); g.stroke(); }
  g.fillStyle="rgba(238,183,92,.72)";
  for(let y=34;y<h;y+=54) for(let x=22;x<w;x+=42){ g.beginPath(); g.arc(x,y,3,0,7); g.fill(); }
  noise(g,w,h,0.08);
}, 2, 1);
const texWallPanel = ctex(256,256,(g,w,h)=>{         // 회벽+흐린 판선
  g.fillStyle="#e8dfca"; g.fillRect(0,0,w,h);
  g.strokeStyle="rgba(102,78,57,.20)"; g.lineWidth=3;
  for(let y=36;y<h;y+=48){ g.beginPath(); g.moveTo(0,y); g.lineTo(w,y); g.stroke(); }
  for(let x=54;x<w;x+=68){ g.beginPath(); g.moveTo(x,0); g.lineTo(x,h); g.stroke(); }
  noise(g,w,h,0.055);
}, 2, 1);
const texFort = ctex(256,256,(g,w,h)=>{              // 궁장: 상단 기와띠 + 붉은 회벽 + 하단 사고석
  g.fillStyle="#94553f"; g.fillRect(0,0,w,h);
  g.fillStyle="rgba(0,0,0,.16)"; g.fillRect(0,26,w,10);
  g.fillStyle="#3a3a40"; g.fillRect(0,0,w,26);
  g.fillStyle="#b5ac9c"; g.fillRect(0,h-92,w,92);
  g.strokeStyle="rgba(70,62,54,.55)"; g.lineWidth=3;
  for(let y=h-92;y<h;y+=30){ g.beginPath(); g.moveTo(0,y); g.lineTo(w,y); g.stroke(); }
  let r=0;
  for(let y=h-92;y<h;y+=30,r++)
    for(let x=(r%2)*34;x<w;x+=68){ g.beginPath(); g.moveTo(x,y); g.lineTo(x,y+30); g.stroke(); }
  noise(g,w,h,0.06);
}, 22, 1);
const texAO = ctex(32,64,(g,w,h)=>{                  // 처마 밑 그림자 그라데이션
  const gr = g.createLinearGradient(0,0,0,h);
  gr.addColorStop(0,"rgba(0,0,0,.5)"); gr.addColorStop(1,"rgba(0,0,0,0)");
  g.fillStyle = gr; g.fillRect(0,0,w,h);
});
const texEodo = ctex(256,512,(g,w,h)=>{              // 어도(임금의 길): 장대석 판 + 줄눈
  g.fillStyle="#a49a89"; g.fillRect(0,0,w,h);
  g.strokeStyle="rgba(74,66,56,.6)"; g.lineWidth=4;
  for(let y=0;y<h;y+=86){ g.beginPath(); g.moveTo(0,y); g.lineTo(w,y); g.stroke(); }
  g.beginPath(); g.moveTo(w*0.33,0); g.lineTo(w*0.33,h); g.stroke();
  g.beginPath(); g.moveTo(w*0.67,0); g.lineTo(w*0.67,h); g.stroke();
  g.fillStyle="rgba(255,255,255,.05)";
  for(let y=0;y<h;y+=86) g.fillRect(0,y+3,w,6);
  noise(g,w,h,0.09);
}, 1, 44);

// 재질
function mat(opts){ return new THREE.MeshStandardMaterial(Object.assign({ metalness:0, roughness:0.82 }, opts)); }
const M = {
  paving: mat({ map:texPaving, roughness:0.92 }),
  earth:  mat({ map:texEarth, roughness:0.96 }),
  stone:  mat({ map:texStone, roughness:0.74 }),
  roof:   mat({ map:texRoof, roughness:0.58 }),
  wood:   mat({ color:0x6e4237, roughness:0.72 }),
  wall:   mat({ map:texWallPanel, roughness:0.86 }),
  danch:  mat({ map:texDancheong, roughness:0.62 }),
  dark:   mat({ color:0x1c1a1c, roughness:0.78 }),
  trim:   mat({ color:0x8a4a31, roughness:0.68 }),
  door:   mat({ map:texDoor, roughness:0.66 }),
  plaque: mat({ color:0x21332f, roughness:0.55 }),
  brass:  mat({ color:0xd9a75f, roughness:0.42, metalness:0.08 }),
  gov:    mat({ map:texGov, roughness:0.7 }),
  govRoof:mat({ color:0x5d6a5f, roughness:0.64 }),
  water:  mat({ map:texWater, color:0x6e9a96, roughness:0.26, metalness:0.02, transparent:true, opacity:0.88 }),
  grass:  mat({ color:0x50633e, roughness:0.9 }),
  weed:   mat({ color:0x4a5238, roughness:0.94 }),
  banner: mat({ color:0xd8d0b8, roughness:0.76, side:THREE.DoubleSide }),
  fort:   mat({ map:texFort, roughness:0.88 }),
  eodo:   mat({ map:texEodo, roughness:0.9 }),
  ao:     new THREE.MeshBasicMaterial({ map:texAO, transparent:true, depthWrite:false, side:THREE.DoubleSide }),
};

function hex(v){ return "#" + v.toString(16).padStart(6, "0"); }
function skyTexture(top, horizon){
  const c = document.createElement("canvas"); c.width = 32; c.height = 512;
  const g = c.getContext("2d");
  const mid = new THREE.Color(top).lerp(new THREE.Color(horizon), 0.45).getHex();
  const grad = g.createLinearGradient(0, 0, 0, c.height);
  grad.addColorStop(0, hex(top));
  grad.addColorStop(0.56, hex(mid));
  grad.addColorStop(1, hex(horizon));
  g.fillStyle = grad; g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = "rgba(255,255,255,.10)";
  g.fillRect(0, c.height*0.72, c.width, c.height*0.12);
  const t = new THREE.CanvasTexture(c);
  t.encoding = THREE.sRGBEncoding;
  t.wrapS = THREE.ClampToEdgeWrapping;
  t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
}
let activeSky = null;
const skyDome = new THREE.Mesh(
  new THREE.SphereGeometry(1450, 32, 16),
  new THREE.MeshBasicMaterial({ side:THREE.BackSide, depthWrite:false, fog:false })
);
skyDome.position.set(0, 0, -260);
skyDome.renderOrder = -1000;
scene.add(skyDome);
function applySky(E){
  if(activeSky) activeSky.dispose();
  activeSky = skyTexture(E.skyTop || E.sky, E.skyHorizon || E.fog[0]);
  skyDome.material.map = activeSky;
  skyDome.material.needsUpdate = true;
  scene.background = new THREE.Color(E.skyTop || E.sky);
  renderer.toneMappingExposure = E.exposure || 1;
}

// ───────────────────────── v0.5: 후처리 체인 + 시대별 환경광(IBL) ─────────────────────────
const EraFxShader = {   // 1929 세피아·그레인 + 공통 비네트 (그레인은 이동 중 자동 감쇠)
  uniforms: { tDiffuse:{value:null}, uSepia:{value:0}, uVign:{value:0.14}, uGrain:{value:0}, uTime:{value:0} },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
  fragmentShader: [
    "uniform sampler2D tDiffuse; uniform float uSepia, uVign, uGrain, uTime;",
    "varying vec2 vUv;",
    "void main(){",
    "  vec4 c = texture2D(tDiffuse, vUv);",
    "  vec3 sep = vec3(dot(c.rgb, vec3(.393,.769,.189)), dot(c.rgb, vec3(.349,.686,.168)), dot(c.rgb, vec3(.272,.534,.131)));",
    "  c.rgb = mix(c.rgb, sep, uSepia);",
    "  float g = fract(sin(dot(vUv + fract(uTime), vec2(12.9898,78.233))) * 43758.5453);",
    "  c.rgb += (g - 0.5) * uGrain;",
    "  float d = distance(vUv, vec2(0.5));",
    "  c.rgb *= 1.0 - uVign * smoothstep(0.32, 0.78, d);",
    "  gl_FragColor = c;",
    "}",
  ].join("\n"),
};
if(POSTFX_ON && THREE.EffectComposer){
  composer = new THREE.EffectComposer(renderer);
  composer.addPass(new THREE.RenderPass(scene, camera));
  ssaoPass = new THREE.SSAOPass(scene, camera, innerWidth, innerHeight);
  ssaoPass.kernelRadius = 0.6; ssaoPass.minDistance = 0.0012; ssaoPass.maxDistance = 0.09;
  composer.addPass(ssaoPass);
  composer.addPass(new THREE.UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.15, 0.7, 0.87));
  eraFxPass = new THREE.ShaderPass(EraFxShader);
  composer.addPass(eraFxPass);
  const pr = renderer.getPixelRatio();
  composer.addPass(new THREE.SMAAPass(innerWidth*pr, innerHeight*pr));
}
// 시대별 하늘을 광원으로(IBL): 모든 PBR 재질에 하늘빛·지면 반사광이 스며듦
const pmrem = new THREE.PMREMGenerator(renderer);
function makeEnv(E){
  const c = document.createElement("canvas"); c.width = 64; c.height = 32;
  const g = c.getContext("2d");
  const gr = g.createLinearGradient(0, 0, 0, 32);
  gr.addColorStop(0, hex(E.skyTop || E.sky));
  gr.addColorStop(0.5, hex(E.skyHorizon || E.fog[0]));
  gr.addColorStop(0.56, hex(E.fog[0]));
  gr.addColorStop(1, "#5e5344");                     // 지면 반사광(흙 톤)
  g.fillStyle = gr; g.fillRect(0, 0, 64, 32);
  const t = new THREE.CanvasTexture(c);
  t.mapping = THREE.EquirectangularReflectionMapping;
  const env = pmrem.fromEquirectangular(t).texture;
  t.dispose();
  return env;
}
const envMaps = ERAS.map(makeEnv);
let grainBase = 0.035;

// ───────────────────────── 지오메트리 헬퍼 ─────────────────────────
// 곡선 팔작지붕: 처마→용마루 오목 곡선 + 귀솟음
function roofGeo(w, d, h, over=1.6, ridgeRatio=0.42, lift=0.55){
  const rings = 7, pos = [], idx = [];
  const rw = w*ridgeRatio/2;
  for(let i=0;i<=rings;i++){
    const v = i/rings;
    const hx = (w/2+over)*(1-v) + rw*v;
    const hz = (d/2+over)*(1-v) + 0.02*v;
    const y  = h*Math.pow(v,1.5) + lift*Math.pow(1-v,2.2);
    // 링 4귀퉁이 (귀솟음: 모서리만 lift 추가분 이미 포함)
    pos.push(-hx,y,-hz,  hx,y,-hz,  hx,y,hz,  -hx,y,hz);
  }
  for(let i=0;i<rings;i++){
    const a=i*4, b=(i+1)*4;
    for(let s=0;s<4;s++){
      const s2=(s+1)%4;
      idx.push(a+s, a+s2, b+s2,  a+s, b+s2, b+s);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos,3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}
function mesh(geo, mat, x=0, y=0, z=0, shadow=true){
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x,y,z); m.castShadow = shadow; m.receiveShadow = true;
  return m;
}
function box(w,h,d,mat,x,y,z,shadow=true){ return mesh(new THREE.BoxGeometry(w,h,d),mat,x,y,z,shadow); }
function faceBox(g, w, h, mat, x, y, z, shadow=true){
  g.add(box(w, h, 0.08, mat, x, y, z, shadow));
}
function doubleFaceBox(g, w, h, mat, x, y, d, offset=0.07, shadow=true){
  faceBox(g, w, h, mat, x, y,  d/2 + offset, shadow);
  faceBox(g, w, h, mat, x, y, -d/2 - offset, shadow);
}
// 처마 밑 그림자 띠(가짜 AO) — 벽 4면 상단에 위→아래 그라데이션
function aoBand(g, w, d, yTop, hb=1.2){
  const mk = (pw)=>{
    const p = new THREE.Mesh(new THREE.PlaneGeometry(pw, hb), M.ao);
    p.castShadow = false; p.receiveShadow = false; p.renderOrder = 2;
    return p;
  };
  let p = mk(w); p.position.set(0, yTop-hb/2,  d/2+0.03); g.add(p);
  p = mk(w); p.position.set(0, yTop-hb/2, -d/2-0.03); p.rotation.y = Math.PI; g.add(p);
  p = mk(d); p.position.set( w/2+0.03, yTop-hb/2, 0); p.rotation.y =  Math.PI/2; g.add(p);
  p = mk(d); p.position.set(-w/2-0.03, yTop-hb/2, 0); p.rotation.y = -Math.PI/2; g.add(p);
}
// 용마루 + 취두 (지붕 능선 마감)
function ridgeCap(g, len, y, alongX=true){
  const lx = alongX ? len : 0.55, lz = alongX ? 0.55 : len;
  g.add(box(lx, 0.34, lz, M.dark, 0, y+0.17, 0, false));
  for(const s of [-1,1])
    g.add(box(alongX?0.7:0.75, 0.62, alongX?0.75:0.7, M.dark,
              alongX?s*len/2:0, y+0.3, alongX?0:s*len/2, false));
}
function addGateFacadeDetails(g, w, d, baseH, openings, op, tiers){
  const edges = [-w/2, ...openings.flatMap(c=>[c-op/2, c+op/2]), w/2];
  doubleFaceBox(g, w+0.8, 0.35, M.stone, 0, 0.18, d, 0.09);
  doubleFaceBox(g, w, 0.12, M.trim, 0, baseH-0.08, d, 0.1);
  for(let i=0;i<edges.length;i+=2){
    const x0 = edges[i], x1 = edges[i+1], segW = x1-x0;
    if(segW <= 0.3) continue;
    const cx = (x0+x1)/2;
    doubleFaceBox(g, Math.max(0.4, segW-0.5), 0.08, M.trim, cx, baseH*0.42, d, 0.11, false);
    doubleFaceBox(g, Math.max(0.4, segW-0.5), 0.08, M.trim, cx, baseH*0.7, d, 0.11, false);
    for(let x=x0+1.2; x<x1-0.8; x+=1.55){
      doubleFaceBox(g, 0.06, baseH*0.55, M.trim, x, baseH*0.46, d, 0.115, false);
    }
  }
  for(const c of openings){
    for(const side of [-1, 1]){
      const z = side*(d/2+0.14);
      for(const sx of [-1, 1]){
        const colX = c + sx*(op/2 + 0.22);
        const col = mesh(new THREE.CylinderGeometry(0.18,0.23,baseH*0.9,14), M.trim, colX, baseH*0.45, z);
        g.add(col);
        g.add(box(0.58,0.18,0.18,M.stone,colX,0.12,z,false));
        g.add(box(0.48,0.16,0.18,M.brass,colX,baseH*0.91,z,false));
      }
      const leafH = Math.max(2.2, baseH*0.62);
      const leafW = op*0.23;
      for(const sx of [-1, 1]){
        const x = c + sx*op*0.31;
        faceBox(g, leafW, leafH, M.door, x, leafH/2+0.15, z, false);
        faceBox(g, 0.055, leafH*0.92, M.brass, x - sx*leafW*0.42, leafH/2+0.15, z + side*0.01, false);
      }
      faceBox(g, op*0.9, 0.12, M.brass, c, baseH*0.14, z + side*0.01, false);
      faceBox(g, op*0.9, 0.10, M.brass, c, baseH*0.55, z + side*0.01, false);
    }
  }
  for(const side of [-1, 1]){
    const z = side*(d*0.48+0.1);
    for(let x=-w*0.38; x<=w*0.38; x+=1.0){
      g.add(box(0.12,0.18,0.46,M.trim,x,baseH+0.78,z,false));
    }
  }
  doubleFaceBox(g, w*0.44, 0.34, M.plaque, 0, baseH+0.55, d*0.9, 0.11, false);
  doubleFaceBox(g, w*0.36, 0.05, M.brass, 0, baseH+0.55, d*0.9, 0.12, false);
  if(tiers===2){
    const upperD = d*0.7, upperY = baseH+3.4;
    doubleFaceBox(g, w*0.42, 0.82, M.door, 0, upperY, upperD, 0.09, false);
    for(let x=-w*0.18; x<=w*0.18; x+=w*0.09){
      doubleFaceBox(g, 0.045, 0.9, M.brass, x, upperY, upperD, 0.105, false);
    }
    doubleFaceBox(g, w*0.48, 0.08, M.brass, 0, upperY+0.47, upperD, 0.11, false);
    doubleFaceBox(g, w*0.48, 0.08, M.brass, 0, upperY-0.47, upperD, 0.11, false);
  }
}

const colliders = [];   // {x0,x1,z0,z1,eras} — 시대별로 활성화
const mapRects  = [];   // {x0,z0,x1,z1,color,eras} 미니맵용
const procSwapMap = {}; // key → 실측 스캔이 로드되면 시대 3~5에서 숨길 절차 생성물
function collide(x0,x1,z0,z1,eras){ colliders.push({x0,x1,z0,z1,eras}); }
function mapRect(x0,z0,x1,z1,color,eras){ mapRects.push({x0,z0,x1,z1,color,eras}); }
function registerSwap(key, eg){ procSwapMap[key] = eg; }

// 전각: 기단+기둥+몸체+겹지붕
function hall(w, d, opts={}){
  const { tiers=1, podium=1.2, colH=4.2, name="", mapColor="#caa06a" } = opts;
  const g = new THREE.Group();
  g.add(box(w+4, podium, d+4, M.stone, 0, podium/2, 0));
  const colGeo = new THREE.CylinderGeometry(0.33,0.38,colH,10);
  const nx = Math.max(2, Math.round(w/4.4)), nz = Math.max(2, Math.round(d/4.4));
  for(let i=0;i<=nx;i++) for(const zs of [-1,1])
    g.add(mesh(colGeo, M.wood, -w/2+ i*(w/nx), podium+colH/2, zs*d/2));
  for(let j=1;j<nz;j++) for(const xs of [-1,1])
    g.add(mesh(colGeo, M.wood, xs*w/2, podium+colH/2, -d/2 + j*(d/nz)));
  g.add(box(w-1.2, colH-1.4, d-1.2, M.wall, 0, podium+ (colH-1.4)/2 +0.4, 0));
  g.add(box(w+0.6, 1.1, d+0.6, M.danch, 0, podium+colH-0.55, 0));
  let topY = podium+colH;
  const r1h = tiers===2 ? 2.6 : 3.4;
  g.add(mesh(roofGeo(w, d, r1h, 2.0), M.roof, 0, topY, 0));
  aoBand(g, w-1.0, d-1.0, topY+0.3);
  if(tiers===2){
    const w2=w*0.72, d2=d*0.7;
    g.add(box(w2-1, 2.2, d2-1, M.wall, 0, topY+r1h+1.0, 0));
    g.add(box(w2-0.6, 0.9, d2-0.6, M.danch, 0, topY+r1h+2.2, 0));
    g.add(mesh(roofGeo(w2, d2, 3.2, 1.8), M.roof, 0, topY+r1h+2.7, 0));
    aoBand(g, w2-0.8, d2-0.8, topY+r1h+2.3, 0.9);
    ridgeCap(g, w2*0.42, topY+r1h+2.7+3.2);
  } else {
    ridgeCap(g, w*0.42, topY+r1h);
  }
  g.userData.solid = { w:w+4, d:d+4 };
  g.userData.mapColor = mapColor;
  return g;
}
// 문(성문/궁문): 옆 블록 통과형
function gate(w, d, opts={}){
  const { stoneH=0, colH=4.4, tiers=1, openings=[0], op=4.5, mat=null } = opts;
  const g = new THREE.Group();
  const bodyMat = mat || (stoneH>0 ? M.stone : M.wall);
  const baseH = stoneH>0 ? stoneH : colH;
  // 개구부 사이 블록
  const edges = [-w/2, ...openings.flatMap(c=>[c-op/2, c+op/2]), w/2];
  for(let i=0;i<edges.length;i+=2){
    const x0=edges[i], x1=edges[i+1];
    if(x1-x0>0.3){
      g.add(box(x1-x0, baseH, d, bodyMat, (x0+x1)/2, baseH/2, 0));
      g.userData.blocks = g.userData.blocks||[]; g.userData.blocks.push([x0,x1]);
    }
  }
  g.add(box(w, Math.max(1.2, baseH-3.2), d, bodyMat, 0, baseH-Math.max(1.2,baseH-3.2)/2, 0)); // 인방(머리 위)
  // 개구부 표현 — 석축 문(광화문류)만 홍예(아치), 목조 궁문은 사각 개구부 (고증)
  for(const c of openings) for(const zs of [-1,1]){
    const z = zs*(d/2+0.055);
    if(stoneH > 0){
      const archY = Math.max(1.9, baseH - op/2 - 0.12);
      faceBox(g, op*0.84, archY, M.dark, c, archY/2, z, false);
      const arc = new THREE.Mesh(new THREE.RingGeometry(op/2-0.18, op/2+0.12, 28, 1, 0, Math.PI), M.stone);
      arc.position.set(c, archY, zs*(d/2+0.12));
      if(zs<0) arc.rotation.y = Math.PI;
      g.add(arc);
    } else {
      const openH = baseH - 1.1;
      faceBox(g, op*0.92, openH, M.dark, c, openH/2, z, false);
      faceBox(g, op*1.0, 0.28, M.trim, c, openH+0.14, z, false);   // 상인방
      for(const sx of [-1,1])
        faceBox(g, 0.26, openH, M.trim, c + sx*op*0.48, openH/2, z, false);
    }
  }
  // 문루
  g.add(box(w*0.8, 1.0, d*0.9, M.danch, 0, baseH+0.5, 0));
  g.add(mesh(roofGeo(w*0.82, d*0.95, 2.6, 1.8), M.roof, 0, baseH+1.0, 0));
  g.add(box(w*0.44, 0.14, 0.18, M.dark, 0, baseH+3.62, 0, false));
  aoBand(g, w-0.3, d-0.3, baseH, 1.0);
  if(tiers===2){
    g.add(box(w*0.6, 2.0, d*0.7, M.wall, 0, baseH+3.4, 0));
    g.add(mesh(roofGeo(w*0.62, d*0.75, 2.6, 1.6), M.roof, 0, baseH+4.6, 0));
    g.add(box(w*0.34, 0.14, 0.18, M.dark, 0, baseH+7.22, 0, false));
  }
  addGateFacadeDetails(g, w, d, baseH, openings, op, tiers);
  return g;
}
// 회랑 벽체(지붕 딸린 담)
function corridorStrip(len, along="x"){
  const g = new THREE.Group();
  const w = along==="x" ? len : 3.4, d = along==="x" ? 3.4 : len;
  g.add(box(w, 3.0, d, M.wall, 0, 1.5, 0));
  g.add(box(w, 0.8, d, M.danch, 0, 3.2, 0));
  g.add(mesh(roofGeo(w, d, 1.7, 1.1, 0.5), M.roof, 0, 3.6, 0));
  aoBand(g, w-0.4, d-0.4, 3.4, 0.9);
  ridgeCap(g, (along==="x"?w:d)*0.46, 3.6+1.7, along==="x");
  return g;
}
function tree(s=1){
  const g = new THREE.Group();
  g.add(box(0.5*s, 2.4*s, 0.5*s, M.wood, 0, 1.2*s, 0));
  for(let i=0;i<3;i++)
    g.add(mesh(new THREE.ConeGeometry((2.4-i*0.6)*s, 2.2*s, 8), M.grass, 0, (2.6+i*1.3)*s, 0));
  return g;
}

// ───────────────────────── 세계 구축 ─────────────────────────
const eraGroups = [];  // {obj, eras}
function place(obj, x, z, eras, opt={}){
  obj.position.x = x; obj.position.z = z;
  if(opt.ry) obj.rotation.y = opt.ry;
  scene.add(obj);
  eraGroups.push({ obj, eras });
  if(obj.userData.solid){
    const { w, d } = obj.userData.solid;
    if(obj.userData.blocks){          // 문: 개구부는 통과, 옆 블록만 충돌
      for(const b of obj.userData.blocks){
        if(opt.ry) collide(x-d/2, x+d/2, z+b[0], z+b[1], eras);
        else       collide(x+b[0], x+b[1], z-d/2, z+d/2, eras);
      }
    } else {
      collide(x-w/2, x+w/2, z-d/2, z+d/2, eras);
    }
    mapRect(x-w/2, z-d/2, x+w/2, z+d/2, obj.userData.mapColor||"#caa06a", eras);
  }
  return obj;
}
const ALL=[0,1,2,3,4,5];

// 지면
const ground = mesh(new THREE.PlaneGeometry(1600,1600), M.earth, 0, 0, -260, false);
ground.rotation.x = -Math.PI/2; texEarth.repeat.set(90,90); scene.add(ground);
function court(x, z, w, d, mat, eras){
  const p = mesh(new THREE.PlaneGeometry(w,d), mat, x, 0.04, z, false);
  p.rotation.x = -Math.PI/2; place(p, x, z, eras);
}
court(0, -292, 126, 130, M.paving, [0,1,3,4,5]);   // 근정전 마당
court(0, -75, 150, 120, M.paving, [3,5]);          // 흥례문 마당(고종/현재)
court(0, -430, 86, 66, M.paving, [0,1,3,4,5]);     // 사정전 마당

// 궁장(외곽 담) — 전 시대 (남쪽 담은 광화문 자리를 비움)
const wallH=5;
for(const [x,z,w,d] of [
  [0,-565,344,3],                       // 북
  [-93.5,1.5,155,3],[93.5,1.5,155,3],   // 남 (광화문 양옆)
  [-171,-281,3,566],[171,-281,3,566],   // 서·동
]){
  const wl = new THREE.Group();
  wl.add(box(w, wallH, d, M.fort, 0, wallH/2, 0));
  wl.add(box(w+0.4, 0.5, d+1.0, M.roof, 0, wallH+0.22, 0));      // 담장 기와 갓
  wl.add(box(w+0.5, 0.16, d+1.1, M.dark, 0, wallH+0.5, 0, false));
  wl.userData.solid={w,d}; wl.userData.mapColor="#7d5a4a";
  place(wl,x,z,ALL);
}
// 북악산·인왕산 원경 — 능선 실루엣 레이어 (원근·대기감)
function ridgeMesh(w, h, color, peaks){
  // 능선 폴리곤을 지오메트리로 직접 생성 (투명 텍스처 방식보다 확실)
  const shape = new THREE.Shape();
  shape.moveTo(-w/2, 0);
  for(const [fx, fy] of peaks) shape.lineTo((fx-0.5)*w, fy*h);
  shape.lineTo(w/2, 0);
  const m = new THREE.Mesh(new THREE.ShapeGeometry(shape, 6),
    new THREE.MeshBasicMaterial({ color, side:THREE.DoubleSide, fog:false }));
  m.castShadow = false; m.receiveShadow = false;
  m.renderOrder = -900;   // 하늘 돔 다음, 씬보다 먼저
  return m;
}
const ridges = [];   // {m, base, haze} — applyEra에서 시대 안개색과 혼합
{
  const addRidge = (m, base, haze)=>{ scene.add(m); ridges.push({ m, base:new THREE.Color(base), haze }); };
  const bugak = ridgeMesh(1050, 300, 0x3e4c42,
    [[0.06,0.18],[0.2,0.34],[0.34,0.5],[0.46,0.88],[0.55,0.62],[0.68,0.4],[0.83,0.3],[0.97,0.12]]);
  bugak.position.set(30, -4, -820); addRidge(bugak, 0x3e4c42, 0.32);
  const bukhan = ridgeMesh(2000, 380, 0x5b6a70,
    [[0.05,0.2],[0.18,0.42],[0.3,0.62],[0.42,0.5],[0.52,0.78],[0.63,0.58],[0.76,0.66],[0.9,0.3]]);
  bukhan.position.set(-80, -4, -1180); addRidge(bukhan, 0x5b6a70, 0.58);
  const inwang = ridgeMesh(1300, 320, 0x49564e,
    [[0.08,0.2],[0.25,0.5],[0.4,0.8],[0.56,0.6],[0.72,0.66],[0.9,0.25]]);
  inwang.position.set(-620, -4, -420); inwang.rotation.y = Math.PI/2; addRidge(inwang, 0x49564e, 0.4);
  const naksan = ridgeMesh(1100, 200, 0x56604f,
    [[0.1,0.2],[0.3,0.42],[0.5,0.55],[0.7,0.34],[0.9,0.18]]);
  naksan.position.set(560, -4, -420); naksan.rotation.y = -Math.PI/2; addRidge(naksan, 0x56604f, 0.4);
}

// 광화문 (남쪽 정문)
const gwang = gate(30, 11, { stoneH:8.5, tiers:2, openings:[-8.5,0,8.5], op:5 });
gwang.userData.solid={w:30,d:11}; gwang.userData.mapColor="#8f6b4e";
place(gwang, 0, 0, [1,3,5]);
const gwangEarly = gate(22, 9, { colH:5, tiers:1, openings:[0], op:5.5 });   // 창건기 정문(추정)
gwangEarly.userData.solid={w:22,d:9}; place(gwangEarly, 0, 0, [0]);
const gwangMoved = gate(22, 9, { stoneH:7, tiers:1, openings:[0], op:5 });   // 1929 이건된 광화문
gwangMoved.userData.solid={w:22,d:9}; gwangMoved.userData.mapColor="#8f6b4e";
place(gwangMoved, 150, -80, [4], { ry:Math.PI/2 });

// 흥례문 + 좌우 행각
const heung = gate(24, 9, { colH:4.8, tiers:2, openings:[0], op:6 });
heung.userData.solid={w:24,d:9}; heung.userData.mapColor="#8f6b4e";
place(heung, 0, -135, [0,1,3,5]);
for(const xs of [-1,1]){
  const st = corridorStrip(64, "x"); st.userData.solid={w:64,d:3.4}; st.userData.mapColor="#b08d62";
  place(st, xs*44, -135, [0,1,3,5]);
  registerSwap(xs<0 ? "heung_w" : "heung_e", eraGroups[eraGroups.length-1]);
}
// 금천 + 영제교
const stream = mesh(new THREE.PlaneGeometry(150, 7), M.water, 0, 0.05, -176, false);
stream.rotation.x=-Math.PI/2; place(stream, 0, -176, [0,1,2,3,5]);
place(box(14, 1.2, 11, M.stone, 0, 0, 0), 0, -176, [0,1,2,3,5]).position.y=0.6;

// 근정문 + 회랑(마당 사각)
const geunMun = gate(22, 8, { colH:4.6, tiers:2, openings:[0], op:5.5 });
geunMun.userData.solid={w:22,d:8}; geunMun.userData.mapColor="#8f6b4e";
place(geunMun, 0, -228, [0,1,3,4,5]);
const CY={x0:-63,x1:63,z0:-360,z1:-228};
for(const seg of [
  {x:-37,z:CY.z1,len:52,along:"x",swap:"wol_w"},{x:37,z:CY.z1,len:52,along:"x",swap:"wol_e"},
  {x:0,z:CY.z0,len:126,along:"x"},
  {x:CY.x0,z:-294,len:132,along:"z",swap:"corr_w"},{x:CY.x1,z:-294,len:132,along:"z",swap:"corr_e"}]){
  const c = corridorStrip(seg.len, seg.along);
  c.userData.solid = { w:seg.along==="x"?seg.len:3.4, d:seg.along==="x"?3.4:seg.len };
  c.userData.mapColor="#b08d62";
  place(c, seg.x, seg.z, [0,1,3,4,5]);
  if(seg.swap) registerSwap(seg.swap, eraGroups[eraGroups.length-1]);   // 실측 스캔 로드 시 교체
}
// 근정전 (2단 월대 위 중층)
const geun = hall(30, 21, { tiers:2, podium:0.01, colH:5.6, mapColor:"#d8b24a" });
const podium2 = new THREE.Group();
podium2.add(box(58, 1.7, 46, M.stone, 0, 0.85, 0));
podium2.add(box(46, 1.7, 36, M.stone, 0, 2.55, 0));
{ // 상월대 돌난간 (엄지기둥 + 난간대)
  const postG = new THREE.BoxGeometry(0.32, 1.15, 0.32);
  const put = (x,z)=> podium2.add(mesh(postG, M.stone, x, 3.4+0.57, z, false));
  for(let i=-5;i<=5;i++){ put(i*4.5, -17.7); put(i*4.5, 17.7); }
  for(let j=-3;j<=3;j++){ put(-22.7, j*5.0); put(22.7, j*5.0); }
  podium2.add(box(45.6, 0.16, 0.24, M.stone, 0, 3.4+1.05, -17.7, false));
  podium2.add(box(45.6, 0.16, 0.24, M.stone, 0, 3.4+1.05,  17.7, false));
  podium2.add(box(0.24, 0.16, 35.6, M.stone, -22.7, 3.4+1.05, 0, false));
  podium2.add(box(0.24, 0.16, 35.6, M.stone,  22.7, 3.4+1.05, 0, false));
}
podium2.userData.solid={w:58,d:46}; podium2.userData.mapColor="#cfc8ba";
place(podium2, 0, -318, [0,1,2,3,4,5]);           // 월대 돌은 폐허기에도 잔존
geun.position.y = 3.4;
geun.userData.solid={w:34,d:25};
place(geun, 0, -318, [0,1,3,4,5]);
// 품계석 2열 (고종~)
for(let i=0;i<6;i++) for(const xs of [-1,1]){
  const st = box(0.9, 1.1, 0.5, M.stone, 0, 0.55, 0);
  place(st, xs*4.5, -262+i*8, [3,4,5]);
}
// 어도(길 표시)
court(0, -114, 7, 230, M.eodo, [0,1,3,5]);
court(0, -294, 7, 128, M.eodo, [0,1,3,4,5]);

// 사정전 + 강녕전·교태전(침전) + 흠경각
const sajeong = hall(20, 13, { colH:4.4, mapColor:"#caa06a" });
sajeong.userData.solid={w:24,d:17};
place(sajeong, 0, -432, [0,1,3,4,5]);
const gang = hall(24, 15, { colH:4.2 }); gang.userData.solid={w:28,d:19};
place(gang, 0, -495, [0,1,3,5]);
registerSwap("gangnyeongjeon", eraGroups[eraGroups.length-1]);   // 스캔은 [3,5]만 — 1929엔 이건되어 부재
const gyo = hall(20, 13, { colH:4.0 }); gyo.userData.solid={w:24,d:17};
place(gyo, 0, -540, [1,3,5]);
const heumgyeong = hall(9, 7, { colH:3.6, mapColor:"#7fb3a5" }); heumgyeong.userData.solid={w:13,d:11};
place(heumgyeong, -26, -500, [1]);                 // 세종의 자동 물시계 전각
// 집현전(세종) / 수정전(고종~)
const jip = hall(22, 12, { colH:4.2, mapColor:"#7fb3a5" }); jip.userData.solid={w:26,d:16};
place(jip, -98, -300, [1]);
const sujeong = hall(22, 12, { colH:4.2 }); sujeong.userData.solid={w:26,d:16};
place(sujeong, -98, -300, [3,4,5]);

// 경회루 + 연못 (1412 태종 건립 → 세종 시대부터)
const pond = mesh(new THREE.PlaneGeometry(85, 70), M.water, -128, 0.05, -350, false);
pond.rotation.x = -Math.PI/2; place(pond, -128, -350, [1,2,3,4,5]);
const gyeong = new THREE.Group();
for(let i=0;i<6;i++) for(let j=0;j<5;j++)
  gyeong.add(box(1.3, 4.2, 1.3, M.stone, -14+ i*5.6, 2.1, -8+ j*4));
gyeong.userData.stoneOnly = true;
const gyeongUpper = new THREE.Group();
gyeongUpper.add(box(32, 0.9, 20, M.wood, 0, 4.6, 0));
for(let i=0;i<7;i++) for(const zs of [-1,1])
  gyeongUpper.add(box(0.6, 3.4, 0.6, M.wood, -15+ i*5, 6.8, zs*9));
gyeongUpper.add(box(30, 0.9, 18, M.danch, 0, 8.6, 0));
gyeongUpper.add(mesh(roofGeo(33, 21, 4.2, 2.2), M.roof, 0, 9.1, 0));
const gyeongFull = new THREE.Group(); gyeongFull.add(gyeong.clone(), gyeongUpper);
gyeongFull.userData.solid={w:34,d:22}; gyeongFull.userData.mapColor="#d8b24a";
place(gyeongFull, -128, -352, [1,3,4,5]);
registerSwap("gyeonghoeru", eraGroups[eraGroups.length-1]);   // 스캔 로드 시 3~5 교체(세종대는 절차 생성 유지)
const gyeongRuin = gyeong; gyeongRuin.userData.solid={w:34,d:22}; gyeongRuin.userData.mapColor="#9a948a";
place(gyeongRuin, -128, -352, [2]);                // 폐허기: 돌기둥만 잔존

// 조선총독부 청사 (1929)
const gov = new THREE.Group();
gov.add(box(105, 21, 55, M.gov, 0, 10.5, 0));
gov.add(box(30, 25, 58, M.gov, 0, 12.5, 0));
for(let i=0;i<9;i++) gov.add(box(1.6, 12, 1.6, M.gov, -12+ i*3, 8, 29.5));
gov.add(mesh(new THREE.SphereGeometry(9, 20, 12, 0, Math.PI*2, 0, Math.PI/2), M.govRoof, 0, 25, 0));
gov.add(box(3, 4, 3, M.govRoof, 0, 32, 0));
gov.userData.solid={w:105,d:58}; gov.userData.mapColor="#8e8b84";
place(gov, 0, -128, [4]);

// 폐허기: 초석·주춧돌·잡초 / 현재·폐허 나무
for(const [x,z,w,d] of [[0,-135,26,10],[0,-495,26,16],[0,-540,22,14],[-98,-300,24,13]]){
  const f = box(w, 0.4, d, M.stone, 0, 0.2, 0); f.userData.solid={w,d}; f.userData.mapColor="#9a948a";
  place(f, x, z, [2]);
}
let seed = 7;
function rnd(){ seed = (seed*16807)%2147483647; return seed/2147483647; }
for(let i=0;i<70;i++){
  const x = (rnd()-0.5)*300, z = -40 - rnd()*480;
  const c = mesh(new THREE.ConeGeometry(0.8+rnd()*1.4, 1.2+rnd()*1.6, 6), M.weed, x, 0.7, z);
  place(c, x, z, [2]);
}
for(let i=0;i<26;i++){
  const xs = rnd()>0.5?1:-1;
  const t = tree(0.9+rnd()*0.9);
  place(t, xs*(120+rnd()*40), -60-rnd()*460, [2,5]);
}
// 1929 박람회 배너
for(let i=0;i<8;i++){
  const g2 = new THREE.Group();
  g2.add(box(0.25, 9, 0.25, M.dark, 0, 4.5, 0));
  g2.add(box(1.6, 5, 0.06, M.banner, 0, 6, 0));
  place(g2, (i%2?38:-38), -252 - Math.floor(i/2)*26, [4]);
}

// ───────────────────────── v0.5: 시대 소품 세트드레싱 (히어로 동선 우선) ─────────────────────────
if(window.PROPS){
  const P = window.PROPS;
  const put = (fn, x, z, eras, ry)=>{
    if(typeof fn !== "function") return;
    const o = fn(M);
    if(ry) o.rotation.y = ry;
    place(o, x, z, eras);
  };
  // 1888 고종: 드므·등롱·차일·깃대 (근정전 마당·광화문)
  put(P.deumeu, -20, -299, [3]);  put(P.deumeu, 20, -299, [3]);
  put(P.lantern, -5.5, -250, [3]); put(P.lantern, 5.5, -250, [3]);
  put(P.lantern, -5.5, -274, [3]); put(P.lantern, 5.5, -274, [3]);
  put(P.chail, 15, -302, [3], Math.PI/8);
  put(P.flagpole, -14, 16, [1,3]); put(P.flagpole, 14, 16, [1,3]);
  // 1929: 전신주·벤치
  put(P.telegraphPole, 18, 26, [4]); put(P.telegraphPole, 4, -58, [4]); put(P.telegraphPole, -15, -102, [4]);
  put(P.benchOld, -10, -266, [4], Math.PI); put(P.benchOld, 10, -266, [4], Math.PI);
  // 2026: 안내판·관람 로프 (근정전 월대 앞 라인)
  put(P.infoSign, 4, -18, [5], Math.PI); put(P.infoSign, 4.5, -212, [5]); put(P.infoSign, 7, -288, [5]);
  for(let rx=-7.5; rx<=7.5; rx+=3) put(P.ropeBarrier, rx, -296, [5]);
  // 폐허기: 잔해 무더기 (축선 곳곳)
  put(P.rubble, 0, -138, [2]); put(P.rubble, 6, -232, [2]); put(P.rubble, -7, -322, [2]);
  put(P.rubble, 3, -430, [2]); put(P.rubble, -4, -498, [2]);
}

// ───────────────────────── v0.6: 반차도풍 사람들 (기록화 인용 실루엣) ─────────────────────────
if(window.FIGURES && window.FIGURES.texture){
  const mkFig = (kind, seed, x, z, eras, h)=>{
    const t = FIGURES.texture(kind, seed);
    t.anisotropy = 4;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map:t, transparent:true }));
    const hh = h || 1.7;
    s.scale.set(hh/2, hh, 1);
    s.position.set(x, hh/2, z);
    scene.add(s);
    eraGroups.push({ obj:s, eras });
    s.visible = eras.includes(era);
  };
  let fs = 11;
  // 1888 조회 도열 — 문동무서(文東武西): 동쪽 문관, 서쪽 무관, 품계석 열 기준
  for(let r=0; r<2; r++)
    for(let i=0; i<5; i++){
      const z = -260 - i*8;
      mkFig("munkwan", fs++,  5.5 + r*2.6, z, [3]);
      mkFig("mukwan",  fs++, -5.5 - r*2.6, z, [3]);
    }
  mkFig("gunjol", 31,  3.2, -233, [3]); mkFig("gunjol", 32, -3.2, -233, [3]);   // 근정문 수문군
  mkFig("gungnyeo", 41, 18, -306, [3]); mkFig("gungnyeo", 42, 20.5, -303, [3]);
  // 1929 박람회 관람객
  for(let i=0;i<6;i++) mkFig("visitor1929", 50+i, -14 + i*6, -248 - (i%3)*16, [4]);
  // 2026 관광객
  [[3,-15],[-6,-40],[2,-150],[-8,-250],[6,-268],[12,-300],[-15,-290],[4,-214]]
    .forEach((p,i)=> mkFig("tourist", 60+i, p[0], p[1], [5]));
}

// ───────────────────────── 실측 스캔 (v0.3: 국가유산청 원본, 고종대 원형 현존 건물) ─────────────────────────
// 회랑 스캔이 로드되면 절차 생성 회랑(남쪽 좌우·동쪽)을 시대 3~5에서 스캔으로 교체.
// CSP 주의: 아티팩트 호스팅은 blob URL(fetch·worker·img)을 차단 → Draco/내장 텍스처 금지.
// GLB는 지오메트리만(arraybuffer로 직접 parse, fetch 없음), 텍스처는 data URI로 별도 주입.
// SCAN_DATA는 빌드가 주입: { 이름: { glb:"data:...", tex:{ 재질이름부분: "data:..." } } }
// 이 빌드에 없는 건물은 키 자체가 없고, 그 자리는 절차 생성물이 유지된다.
const SCAN_DATA = /*__SCAN_DATA__*/{};   // 빌드 시 치환 (소스 단독으로도 문법 유효)
const SCANS = [
  { name:"seowollang",    target:{ x:-37, z:-228, len:52,  ry:0 },         swap:"wol_w",  label:"근정문 서월랑" },
  { name:"dongwollang",   target:{ x: 37, z:-228, len:52,  ry:0 },         swap:"wol_e",  label:"근정문 동월랑" },
  { name:"donghaenggak",  target:{ x: 63, z:-294, len:132, ry:Math.PI/2 }, swap:"corr_e", label:"동행각" },
  { name:"seohaenggak",   target:{ x:-63, z:-294, len:132, ry:Math.PI/2 }, swap:"corr_w", label:"서행각" },
  { name:"heung_w",       target:{ x:-44, z:-135, len:64,  ry:0 },         swap:"heung_w", eras:[3,5], label:"흥례문 서행각" },
  { name:"heung_e",       target:{ x: 44, z:-135, len:64,  ry:0 },         swap:"heung_e", eras:[3,5], label:"흥례문 동행각" },
  { name:"sajeongmun",    target:{ x:0,   z:-362, len:20,  ry:0 },         swap:null,     label:"사정문" },
  { name:"gyeonghoeru",   target:{ x:-128,z:-352, len:36,  ry:0 },         swap:"gyeonghoeru", label:"경회루" },
  { name:"gangnyeongjeon",target:{ x:0,   z:-495, len:30,  ry:0 },         swap:"gangnyeongjeon", eras:[3,5], label:"강녕전" },
];
let scansLoaded = 0, scansExpected = 0;
function b64buf(s){
  const bin = atob(s.split(",").pop());
  const a = new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) a[i] = bin.charCodeAt(i);
  return a.buffer;
}
function dataTexture(dataURI){
  const img = new Image();
  const t = new THREE.Texture(img);
  t.encoding = THREE.sRGBEncoding;
  t.flipY = false;                      // glTF UV 규약
  img.onload = ()=>{ t.needsUpdate = true; };
  img.src = dataURI;
  return t;
}
// 시대별 스캔 텍스처 (P1-A): 1888=새 궁(파생), 1929=퇴락(파생), 2026=원본 낡음
const scanTexBindings = [];             // {material, pack, key}
const eraTexCache = new Map();          // dataURI → THREE.Texture (시대 간 재사용)
function pickScanURI(p, key){
  if(era === 3 && p.tex1888 && p.tex1888[key]) return p.tex1888[key];
  if(era === 4){
    if(p.tex1929 && p.tex1929[key]) return p.tex1929[key];
    if(p.tex1888 && p.tex1888[key]) return p.tex1888[key];
  }
  return p.tex ? p.tex[key] : null;
}
function applyScanTex(b){
  const uri = pickScanURI(b.pack, b.key);
  if(!uri || uri.length < 100) return;
  let t = eraTexCache.get(uri);
  if(!t){
    t = dataTexture(uri);
    t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    eraTexCache.set(uri, t);
  }
  if(b.material.map !== t){ b.material.map = t; b.material.needsUpdate = true; }
}
function initScanLoader(){
  const loader = new THREE.GLTFLoader();
  const note = document.getElementById("scanNote");
  SCANS.forEach((s)=>{
    const pack = SCAN_DATA[s.name];
    if(!pack || !pack.glb || pack.glb.length < 100) return;    // 이 빌드에 미포함
    const scanEras = s.eras || [3,4,5];
    scansExpected++;
    loader.parse(b64buf(pack.glb), "", (gltf)=>{
      const g = gltf.scene;
      g.traverse(o=>{
        if(o.isMesh){
          o.castShadow = true; o.receiveShadow = true;
          const name = (o.material && o.material.name) || o.name || "";
          for(const key in (pack.tex || {})){
            if(name.indexOf(key) >= 0 && pack.tex[key] && pack.tex[key].length > 100){
              const b = { material: o.material, pack, key };
              scanTexBindings.push(b);
              applyScanTex(b);           // 현재 시대에 맞는 텍스처로 즉시 적용
              break;
            }
          }
          if("metalness" in o.material) o.material.metalness = 0;
          if("roughness" in o.material) o.material.roughness = 0.86;
          if("envMapIntensity" in o.material) o.material.envMapIntensity = 0.45;
        }
      });
      // 자동 맞춤: 긴 축 기준 스케일 → 회전 → 바닥 y=0, 중심을 목표 좌표로
      let box = new THREE.Box3().setFromObject(g);
      let size = box.getSize(new THREE.Vector3());
      const long0 = Math.max(size.x, size.z);
      const sc = s.target.len / long0;
      g.scale.setScalar(sc);
      g.rotation.y = s.target.ry;
      g.updateMatrixWorld(true);
      box = new THREE.Box3().setFromObject(g);
      const c = box.getCenter(new THREE.Vector3());
      g.position.x += s.target.x - c.x;
      g.position.z += s.target.z - c.z;
      g.position.y += -box.min.y;
      scene.add(g);
      eraGroups.push({ obj:g, eras:scanEras.slice() });
      g.visible = scanEras.includes(era);
      swapProc(s.swap, scanEras);        // 같은 자리 절차 생성물을 해당 시대에서 숨김
      scansLoaded++;
      if(note){
        note.textContent = `실측 스캔 ${scansLoaded}/${scansExpected} 로드 — 국가유산청 3D 원형데이터`;
        if(scansLoaded === scansExpected) setTimeout(()=>{ note.style.opacity = 0; }, 4000);
      }
    }, (e)=>{ console.error("GLB 로드 실패", s.label, e); });
  });
}
function swapProc(key, scanEras){
  const eg = key && procSwapMap[key];
  if(!eg) return;
  eg.eras = eg.eras.filter(e => !scanEras.includes(e));
  eg.obj.visible = eg.eras.includes(era);
}

// ───────────────────────── 플레이어 · 조작 ─────────────────────────
const player = { x:0, z:-206, yaw:0, pitch:0 };
const keys = new Set();
// 숫자키 명소 이동 (로드뷰의 '즐겨찾기 점프')
const LANDMARKS = [
  [0, 22, "광화문 앞"], [0, -108, "흥례문 앞"], [0, -186, "영제교"],
  [0, -206, "근정문 앞"], [0, -292, "근정전 마당"], [-94, -352, "경회루"],
];
addEventListener("keydown", e=>{
  keys.add(e.code);
  // 투어 중 이동 입력 = 자유탐험으로 이탈 (AC 디스커버리 투어 방식)
  if(typeof tour !== "undefined" && tour.on){
    if(/^(Key[WASD]|Arrow)/.test(e.code) || e.code === "Escape"){ tourEnd(false); return; }
  }
  const n = landmarkIndexFromKey(e);
  if(n >= 0){
    e.preventDefault();
    glideTo(LANDMARKS[n][0], LANDMARKS[n][1]);
    toast(LANDMARKS[n][2] + "(으)로 이동");
  }
});
addEventListener("keyup",   e=>{ keys.delete(e.code); });
function landmarkIndexFromKey(e){
  const byKey = "123456".indexOf(e.key);
  if(byKey >= 0) return byKey;
  const byCode = /^(?:Digit|Numpad)([1-6])$/.exec(e.code || "");
  return byCode ? Number(byCode[1]) - 1 : -1;
}

let lookId=null, joyId=null, lx=0, ly=0, joyOx=0, joyOy=0, joyVx=0, joyVy=0;
const joyEl = document.getElementById("joy"), joyKnob = document.getElementById("joyknob");
canvas.addEventListener("pointerdown", e=>{
  document.getElementById("hint").style.opacity=0;
  dragDist = 0;                          // 핫스팟 클릭 판정용 (드래그와 구분)
  if(e.pointerType==="touch" && e.clientX < innerWidth*0.45 && e.clientY > innerHeight*0.5 && joyId===null){
    if(typeof tour !== "undefined" && tour.on) tourEnd(false);
    joyId=e.pointerId; joyOx=e.clientX; joyOy=e.clientY;
    joyEl.style.display="block"; joyEl.style.left=(joyOx-50)+"px"; joyEl.style.top=(joyOy-50)+"px";
  } else if(lookId===null){ lookId=e.pointerId; lx=e.clientX; ly=e.clientY; }
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointermove", e=>{
  if(e.pointerId===lookId){
    dragDist += Math.abs(e.clientX-lx) + Math.abs(e.clientY-ly);
    player.yaw   -= (e.clientX-lx)*0.0032;
    player.pitch = Math.max(-1.15, Math.min(1.15, player.pitch + (e.clientY-ly)*0.0032));
    lx=e.clientX; ly=e.clientY;
  } else if(e.pointerId===joyId){
    joyVx = Math.max(-1, Math.min(1, (e.clientX-joyOx)/45));
    joyVy = Math.max(-1, Math.min(1, (e.clientY-joyOy)/45));
    joyKnob.style.transform = `translate(${joyVx*30}px,${joyVy*30}px)`;
  }
});
function endPtr(e){
  if(e.pointerId===lookId) lookId=null;
  if(e.pointerId===joyId){ joyId=null; joyVx=joyVy=0; joyEl.style.display="none"; joyKnob.style.transform=""; }
}
canvas.addEventListener("pointerup", endPtr); canvas.addEventListener("pointercancel", endPtr);
// 더블클릭 순간이동 (로드뷰식)
const ray = new THREE.Raycaster();
canvas.addEventListener("dblclick", e=>{
  ray.setFromCamera({ x:e.clientX/innerWidth*2-1, y:-(e.clientY/innerHeight)*2+1 }, camera);
  const hit = ray.intersectObject(ground)[0];
  if(hit){
    const target = doubleClickTarget(hit.point);
    glideTo(target.x, target.z);
  }
});
const DOUBLE_CLICK_MIN_STEP = 18;
function doubleClickTarget(point){
  let dx = point.x - player.x;
  let dz = point.z - player.z;
  const dist = Math.hypot(dx, dz);
  if(dist >= DOUBLE_CLICK_MIN_STEP) return point;
  if(dist < 0.001){
    dx = Math.sin(player.yaw);
    dz = -Math.cos(player.yaw);
  } else {
    dx /= dist;
    dz /= dist;
  }
  return { x: player.x + dx * DOUBLE_CLICK_MIN_STEP, z: player.z + dz * DOUBLE_CLICK_MIN_STEP };
}
function movePlayerTo(x, z){
  player.x = Math.max(-168, Math.min(168, x));
  player.z = Math.max(-560, Math.min(55, z));
}
// 로드뷰식 이동 트윈 — 순간이동 대신 짧게 미끄러져서 멀미 방지 (yawTo 지정 시 시선도 함께 회전)
let glide = null;
function glideTo(x, z, yawTo){
  glide = { x0:player.x, z0:player.z,
            x1:Math.max(-168, Math.min(168, x)), z1:Math.max(-560, Math.min(55, z)),
            yaw0:player.yaw, yaw1:null,
            t:0, dur:Math.min(0.9, 0.3 + Math.hypot(x-player.x, z-player.z)/220) };
  if(typeof yawTo === "number"){
    let d = yawTo - player.yaw;
    d = ((d + Math.PI) % (2*Math.PI) + 2*Math.PI) % (2*Math.PI) - Math.PI;   // 최단 회전
    glide.yaw1 = player.yaw + d;
  }
}
function resolveCollisions(){
  for(const c of colliders){
    if(!c.eras.includes(era)) continue;
    if(player.x>c.x0-0.6 && player.x<c.x1+0.6 && player.z>c.z0-0.6 && player.z<c.z1+0.6){
      const dx = Math.min(player.x-(c.x0-0.6), (c.x1+0.6)-player.x);
      const dz = Math.min(player.z-(c.z0-0.6), (c.z1+0.6)-player.z);
      if(dx<dz) player.x += (player.x-(c.x0+c.x1)/2 > 0 ? dx : -dx);
      else      player.z += (player.z-(c.z0+c.z1)/2 > 0 ? dz : -dz);
    }
  }
}

// ───────────────────────── 시대 전환 ─────────────────────────
let era = 3;   // 시작: 1888 고종 중건기
const fadeEl = document.getElementById("fade");
function applyEra(i, first=false){
  era = i;
  const E = ERAS[i];
  for(const { obj, eras } of eraGroups) obj.visible = eras.includes(i);
  applySky(E);
  scene.environment = envMaps[i];                    // IBL — 시대 하늘빛이 재질에 스며듦
  scene.fog = new THREE.Fog(E.fog[0], E.fog[1], E.fog[2]);
  hemi.color.set(E.hemi[0]); hemi.groundColor.set(E.hemi[1]);
  hemi.intensity = E.hemi[2] * 0.6;                  // ambient 몫을 환경광이 대체
  if(eraFxPass){
    eraFxPass.uniforms.uSepia.value = (i === 4) ? 0.32 : 0;
    eraFxPass.uniforms.uVign.value  = (i === 4) ? 0.38 : (i === 2 ? 0.26 : 0.14);
    grainBase = (i === 4) ? 0.10 : 0.03;
  }
  scanTexBindings.forEach(applyScanTex);             // 시대별 스캔 텍스처 스왑 (P1-A)
  if(typeof AudioEng !== "undefined") AudioEng.rebuild();   // 시대별 앰비언스 교체
  sunDir.set(...E.sun[0]).normalize();
  sun.intensity = E.sun[1]; sun.color.set(E.sun[2]);
  for(const r of ridges)   // 능선을 시대 안개색으로 물들여 대기 원근감 표현
    r.m.material.color.copy(r.base).lerp(new THREE.Color(E.fog[0]), r.haze);
  fill.color.set(E.fill ? E.fill[0] : E.hemi[0]); fill.intensity = E.fill ? E.fill[1] : 0.16;
  document.querySelector("#eraLabel .year").textContent = E.yr;
  document.querySelector("#eraLabel .name").textContent = E.nm;
  const bd = document.getElementById("badge");
  bd.textContent = E.badge; bd.classList.toggle("est", E.est);
  document.querySelectorAll(".eraChip").forEach(b =>
    b.classList.toggle("active", +b.dataset.era === i));
  if(document.getElementById("card").classList.contains("open")) renderCard();
  drawMapBase();
}
function setEra(i){
  if(i===era) return;
  fadeEl.style.opacity = 1;
  setTimeout(()=>{ applyEra(i); fadeEl.style.opacity = 0; }, 260);
}
document.querySelectorAll(".eraChip").forEach(b =>
  b.addEventListener("click", ()=> setEra(+b.dataset.era)));

// ───────────────────────── 미니맵 ─────────────────────────
const mapC = document.getElementById("map"), mg = mapC.getContext("2d", { willReadFrequently:true });
const MW = mapC.width, MH = mapC.height;
function w2m(x, z){ return [ (x+180)/360*MW, (z+580)/635*MH ]; }   // 북쪽이 위
let mapBase = null;
function drawMapBase(){
  mg.fillStyle = "#171719"; mg.fillRect(0,0,MW,MH);
  mg.strokeStyle = "#5a4a3a"; mg.lineWidth = 2;
  const [wx0,wy0] = w2m(-171, 3), [wx1,wy1] = w2m(171, -565);
  mg.strokeRect(wx0, wy0, wx1-wx0, wy1-wy0);
  for(const r of mapRects){
    if(!r.eras.includes(era)) continue;
    const [ax,ay] = w2m(r.x0, r.z0), [bx,by] = w2m(r.x1, r.z1);
    mg.fillStyle = r.color;
    mg.fillRect(Math.min(ax,bx), Math.min(ay,by), Math.max(2,Math.abs(bx-ax)), Math.max(2,Math.abs(by-ay)));
  }
  mapBase = mg.getImageData(0,0,MW,MH);
}
function drawMap(){
  if(!mapBase) return;
  mg.putImageData(mapBase,0,0);
  const [px,py] = w2m(player.x, player.z);
  mg.fillStyle = "#ff5544";
  mg.beginPath();
  mg.moveTo(px + 7*Math.sin(-player.yaw), py - 7*Math.cos(-player.yaw));
  mg.lineTo(px + 3.5*Math.sin(-player.yaw+2.5), py - 3.5*Math.cos(-player.yaw+2.5));
  mg.lineTo(px + 3.5*Math.sin(-player.yaw-2.5), py - 3.5*Math.cos(-player.yaw-2.5));
  mg.fill();
}
mapC.addEventListener("click", e=>{
  const r = mapC.getBoundingClientRect();
  const mx = (e.clientX-r.left)*(MW/r.width), my = (e.clientY-r.top)*(MH/r.height);
  glideTo(mx/MW*360-180, my/MH*635-580);
});
document.getElementById("mapBtn").addEventListener("click", ()=>{
  const hidden = getComputedStyle(mapC).display === "none";
  mapC.style.display = hidden ? "block" : "none";
  document.getElementById("maplabel").style.display = hidden ? "block" : "none";
});

// ───────────────────────── 공유 링크 (시대+위치+시선까지 담은 URL) ─────────────────────────
function applyHash(){
  const h = new URLSearchParams(location.hash.slice(1));
  if(!h.has("e")) return;
  const e = Math.max(0, Math.min(5, +h.get("e")||0));
  player.x = +h.get("x")||0; player.z = +h.get("z")||34;
  player.yaw = +h.get("yaw")||0; player.pitch = +h.get("p")||0;
  movePlayerTo(player.x, player.z);
  applyEra(e);
}
function toast(msg){
  const t = document.getElementById("toast");
  t.textContent = msg; t.style.opacity = 1;
  setTimeout(()=> t.style.opacity = 0, 1800);
}
document.getElementById("shareBtn").addEventListener("click", ()=>{
  const h = `#e=${era}&x=${player.x.toFixed(1)}&z=${player.z.toFixed(1)}&yaw=${player.yaw.toFixed(2)}&p=${player.pitch.toFixed(2)}`;
  try { history.replaceState(null, "", h); } catch(_e){}
  const url = location.href.split("#")[0] + h;
  (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject())
    .then(()=> toast("이 장면의 링크를 복사했어요"))
    .catch(()=> toast(url));
});

// ───────────────────────── v0.6: 소리 (웹오디오 합성 — 오디오 파일 0바이트) ─────────────────────────
const AudioEng = (()=>{
  let ctx = null, master = null, muted = false, eraNodes = [], chirpTimer = null, noiseBuf = null;
  function noiseSrc(){
    const s = ctx.createBufferSource(); s.buffer = noiseBuf; s.loop = true; return s;
  }
  function ensure(){
    if(ctx) return false;
    const AC = window.AudioContext || window.webkitAudioContext;
    if(!AC) return false;
    ctx = new AC();
    noiseBuf = ctx.createBuffer(1, ctx.sampleRate*2, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for(let i=0;i<d.length;i++) d[i] = Math.random()*2-1;
    master = ctx.createGain(); master.gain.value = 0.55; master.connect(ctx.destination);
    rebuild();
    return true;
  }
  function stopEra(){
    eraNodes.forEach(n=>{ try{ n.stop && n.stop(); }catch(_e){} try{ n.disconnect && n.disconnect(); }catch(_e){} });
    eraNodes = [];
    if(chirpTimer){ clearInterval(chirpTimer); chirpTimer = null; }
  }
  function rebuild(){
    if(!ctx) return;
    stopEra();
    // 바람 — 모든 시대 (폐허기는 거세게)
    const wind = noiseSrc();
    const wf = ctx.createBiquadFilter(); wf.type = "lowpass"; wf.frequency.value = era===2 ? 480 : 320;
    const wg = ctx.createGain(); wg.gain.value = era===2 ? 0.10 : 0.035;
    const lfo = ctx.createOscillator(); lfo.frequency.value = 0.13;
    const lg = ctx.createGain(); lg.gain.value = era===2 ? 0.05 : 0.015;
    lfo.connect(lg); lg.connect(wg.gain);
    wind.connect(wf); wf.connect(wg); wg.connect(master);
    wind.start(); lfo.start();
    eraNodes.push(wind, lfo, wf, wg, lg);
    // 군중 웅성 — 1888(조정)·1929(박람회)·2026(관광객)
    if(era===3 || era===4 || era===5){
      const cr = noiseSrc();
      const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 420; bp.Q.value = 1.2;
      const cg = ctx.createGain(); cg.gain.value = era===4 ? 0.045 : (era===3 ? 0.03 : 0.022);
      cr.connect(bp); bp.connect(cg); cg.connect(master); cr.start();
      eraNodes.push(cr, bp, cg);
    }
    // 새소리 — 폐허·1929 제외
    if(era !== 2 && era !== 4){
      chirpTimer = setInterval(()=>{
        if(!ctx || muted || Math.random() < 0.45) return;
        const o = ctx.createOscillator(), g = ctx.createGain();
        const f0 = 2400 + Math.random()*1600, t0 = ctx.currentTime;
        o.frequency.setValueAtTime(f0, t0);
        o.frequency.exponentialRampToValueAtTime(f0*(0.7+Math.random()*0.6), t0+0.12);
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(0.02, t0+0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t0+0.18);
        o.connect(g); g.connect(master);
        o.start(t0); o.stop(t0+0.2);
      }, 1400);
    }
  }
  function step(run){
    if(!ctx || muted) return;
    const src = ctx.createBufferSource(); src.buffer = noiseBuf;
    const f = ctx.createBiquadFilter(); f.type = "bandpass";
    f.frequency.value = 700 + Math.random()*300; f.Q.value = 1.5;
    const g = ctx.createGain(); const t0 = ctx.currentTime;
    g.gain.setValueAtTime(run ? 0.05 : 0.035, t0);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.07);
    src.connect(f); f.connect(g); g.connect(master);
    src.start(t0, Math.random()*1.5, 0.09);
  }
  function toggle(){ muted = !muted; if(master) master.gain.value = muted ? 0 : 0.55; return muted; }
  return { ensure, rebuild, step, toggle };
})();
document.getElementById("soundBtn").addEventListener("click", ()=>{
  const isNew = AudioEng.ensure();
  const m = isNew ? false : AudioEng.toggle();
  document.getElementById("soundBtn").textContent = m ? "🔇" : "🔊";
  toast(m ? "소리 끔" : "소리 켬 — 시대마다 소리가 다릅니다");
});
canvas.addEventListener("pointerdown", ()=>{ AudioEng.ensure(); }, { once:true });

// ───────────────────────── v0.6: 가이드 투어 "왕의 하루" ─────────────────────────
const TOUR = /*__TOUR__*/null;
const subEl = document.getElementById("subtitle");
const subTxt = subEl.querySelector(".txt");
const subWho = subEl.querySelector(".who");
const tour = { on:false, st:0, ln:0, timer:null };
function tourStart(){
  if(!TOUR){ toast("이 빌드에는 투어가 없습니다"); return; }
  AudioEng.ensure();
  tour.on = true;
  subEl.style.display = "block";
  if(TOUR.intro) toast(TOUR.intro);
  tourStation(0);
}
function tourStation(i){
  if(!tour.on) return;
  if(i >= TOUR.stations.length){ tourEnd(true); return; }
  tour.st = i; tour.ln = 0;
  const s = TOUR.stations[i];
  subWho.textContent = "史官 — " + TOUR.title + " · " + s.name + " (" + (i+1) + "/" + TOUR.stations.length + ")";
  if(era !== s.era) setEra(s.era);
  glideTo(s.pos[0], s.pos[1], s.yaw);
  tourLine();
}
function tourLine(){
  if(!tour.on) return;
  const s = TOUR.stations[tour.st];
  if(tour.ln >= s.lines.length){ tourStation(tour.st + 1); return; }
  const L = s.lines[tour.ln];
  subTxt.textContent = L.t;
  clearTimeout(tour.timer);
  tour.timer = setTimeout(()=>{ tour.ln++; tourLine(); }, (L.dur || 5) * 1000);
}
function tourEnd(finished){
  if(!tour.on) return;
  tour.on = false;
  clearTimeout(tour.timer);
  subEl.style.display = "none";
  toast(finished ? "왕의 하루가 저물었습니다 — 이제 자유롭게 시간을 걸어보세요"
                 : "투어에서 나왔습니다 (📜 버튼으로 다시)");
}
document.getElementById("tourBtn").addEventListener("click", ()=>{ tour.on ? tourEnd(false) : tourStart(); });
document.getElementById("subNext").addEventListener("click", ()=>{ clearTimeout(tour.timer); tourStation(tour.st + 1); });
document.getElementById("subPrev").addEventListener("click", ()=>{ clearTimeout(tour.timer); tourStation(Math.max(0, tour.st - 1)); });
document.getElementById("subExit").addEventListener("click", ()=> tourEnd(false));

// ───────────────────────── 기록 카드 ─────────────────────────
const CARDS = [
  { t:"1395 — 새 궁궐 준공", q:"태조 4년, 새 궁궐이 준공되었다. 규모는 약 390여 칸.",
    p:"정도전이 전각마다 이름을 붙였습니다 — '부지런히 정치하라'는 근정전(勤政殿)이 그것입니다. 창건기 모습은 도면이 없어 실록 기록으로 추정한 시안입니다.",
    img:null, cap:"", src:["태조실록 1395.9.29 / 10.7 기사","https://sillok.history.go.kr/id/kaa_10409029_006"] },
  { t:"15세기 — 세종의 경복궁", q:"",
    p:"세종은 경복궁에 가장 오래 머문 임금입니다. 1438년 침전 곁에 자동 물시계 전각 흠경각을 세웠고(시각마다 인형이 나타나는 장치가 실록에 상세히 기록), 집현전이 서쪽에 있었습니다. 경회루는 1412년(태종) 건립되어 이 시대의 연회 무대였습니다.",
    img:null, cap:"", src:["세종실록 1438.1.7 흠경각 기사","https://sillok.history.go.kr/id/kda_12001007_003"] },
  { t:"1592–1865 — 273년의 폐허", q:"“경복궁·창덕궁·창경궁 세 궁궐이 일시에 모두 타버렸다.” — 선조수정실록, 1592",
    p:"선조가 도성을 버리고 피난한 뒤, 성난 백성들이 궁에 불을 질렀다고 실록은 기록합니다. 이후 273년간 — 조선 역사의 절반 — 경복궁은 터로만 남았습니다. 경회루의 돌기둥만 연못가에 서 있었습니다.",
    img:null, cap:"", src:["선조수정실록 1592.4.14 기사","https://sillok.history.go.kr/id/knb_12504014_028"] },
  { t:"1888 — 고종 중건기의 법궁", q:"“300년 동안 미처 하지 못하던 일을 이렇게 완공하였으니.” — 고종, 1868",
    p:"1865년 신정왕후의 하교로 시작된 중건은 40개월 만에 끝났고, 전성기의 경복궁은 약 500동 규모였습니다. 1887년 정월 이 마당에서 문무백관이 도열한 팔순 진하례가 열렸습니다.",
    img:"%%CARD_1888%%", cap:"근정전 정면, 1910년대 유리건판 — 건물은 고종대 원형 (국립중앙박물관, 공공누리 제1유형)",
    src:["고종실록 1868.7.2 / 1887.1.1 기사","https://sillok.history.go.kr/id/kza_12401001_001"] },
  { t:"1929 — 박람회장이 된 궁궐", q:"",
    p:"1915년 공진회를 명분으로 전각 4천여 칸이 철거되고, 흥례문 자리에 조선총독부 청사가 세워졌습니다(1926년경). 광화문은 동쪽으로 옮겨졌고, 1929년 조선박람회에서 근정전 일대는 행사장으로 쓰였습니다.",
    img:"%%CARD_1929%%", cap:"1929년 조선박람회 당시 식장으로 쓰인 근정전 (퍼블릭 도메인)",
    src:["국가기록원 — 경복궁","https://theme.archives.go.kr/next/koreaOfRecord/royalPalace.do"] },
  { t:"2026 — 다시 세워지는 궁궐", q:"",
    p:"1990년 시작된 복원으로 총독부 청사는 철거(1995)되고 광화문(2010)과 월대(2023)가 제자리를 찾았습니다. 2차 복원정비사업은 2045년까지 이어집니다 — 목표는 고종대의 약 41%인 205동.",
    img:null, cap:"", src:["국가유산청 궁능유적본부 — 경복궁","https://royal.khs.go.kr/ROYAL/contents/R101010000.do"] },
];
const card = document.getElementById("card");
function renderCard(){
  const c = CARDS[era];
  card.innerHTML = "<h2>"+c.t+"</h2>"
    + (c.q ? "<blockquote>"+c.q+"</blockquote>" : "")
    + "<p>"+c.p+"</p>"
    + (c.img ? "<img src='"+c.img+"' alt=''><div class='cap'>"+c.cap+"</div>" : "")
    + "<div class='src'>출처: <a href='"+c.src[1]+"' target='_blank' rel='noopener'>"+c.src[0]+"</a></div>";
}
document.getElementById("infoBtn").addEventListener("click", ()=>{
  if(!card.classList.contains("open")) renderCard();
  card.classList.toggle("open");
});

// ───────────────────────── v0.5: 건물 핫스팟 (구글 아트앤컬처 ⓘ 패턴) ─────────────────────────
const BUILDING_CARDS = /*__BCARDS__*/[];
const hotspotSprites = [];
{
  const c = document.createElement("canvas"); c.width = c.height = 96;
  const g = c.getContext("2d");
  g.fillStyle = "rgba(16,16,20,.78)"; g.beginPath(); g.arc(48,48,42,0,7); g.fill();
  g.strokeStyle = "rgba(255,255,255,.85)"; g.lineWidth = 4; g.beginPath(); g.arc(48,48,42,0,7); g.stroke();
  g.fillStyle = "#fff"; g.font = "700 52px Georgia"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText("i", 48, 52);
  const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding;
  const sm = new THREE.SpriteMaterial({ map: t, depthTest: true, transparent: true });
  for(const bc of BUILDING_CARDS){
    const s = new THREE.Sprite(sm);
    s.scale.set(2.6, 2.6, 1);
    s.position.set(bc.anchor.x, bc.anchor.y, bc.anchor.z);
    scene.add(s);
    eraGroups.push({ obj: s, eras: bc.eras });
    s.userData.bc = bc;
    hotspotSprites.push(s);
  }
}
function openBuildingCard(bc){
  const gradeColor = bc.grade === "실측 스캔" ? "#8fd0a0" : (bc.grade === "도면 기반 재현" ? "#e8c88a" : "#f0a8a0");
  card.innerHTML = "<h2>" + bc.name + " <span style='opacity:.55;font-weight:400'>" + bc.hanja + "</span></h2>"
    + "<div style='font-size:11px;margin-bottom:8px'><span style='color:" + gradeColor + "'>● " + bc.grade + "</span></div>"
    + "<blockquote>" + bc.meaning + "</blockquote>"
    + "<p>" + bc.story + "</p>"
    + "<div class='src'>출처: <a href='" + bc.source[1] + "' target='_blank' rel='noopener'>" + bc.source[0] + "</a></div>";
  card.classList.add("open");
}
let dragDist = 0;
canvas.addEventListener("click", (e)=>{
  if(dragDist > 6 || !hotspotSprites.length) return;
  ray.setFromCamera({ x: e.clientX/innerWidth*2-1, y: -(e.clientY/innerHeight)*2+1 }, camera);
  const hits = ray.intersectObjects(hotspotSprites.filter(s => s.visible));
  if(hits.length) openBuildingCard(hits[0].object.userData.bc);
});

// ───────────────────────── 루프 ─────────────────────────
const clock = new THREE.Clock();
let lastPX = 0, lastPZ = 0, stepAcc = 0;
function frame(){
  const dt = Math.min(0.05, clock.getDelta());
  if(glide){
    glide.t += dt;
    const k = Math.min(1, glide.t/glide.dur);
    const e = k<.5 ? 2*k*k : 1-Math.pow(-2*k+2,2)/2;   // easeInOut
    player.x = glide.x0 + (glide.x1-glide.x0)*e;
    player.z = glide.z0 + (glide.z1-glide.z0)*e;
    if(glide.yaw1 !== null) player.yaw = glide.yaw0 + (glide.yaw1-glide.yaw0)*e;
    if(k>=1){ glide=null; resolveCollisions(); }
  } else {
    let mx=0, mz=0;
    if(keys.has("KeyW")||keys.has("ArrowUp")) mz-=1;
    if(keys.has("KeyS")||keys.has("ArrowDown")) mz+=1;
    if(keys.has("KeyA")||keys.has("ArrowLeft")) mx-=1;
    if(keys.has("KeyD")||keys.has("ArrowRight")) mx+=1;
    mx += joyVx; mz += joyVy;
    const len = Math.hypot(mx,mz);
    if(len>0.01){
      const sp = (keys.has("ShiftLeft")||keys.has("ShiftRight") ? 30 : 14) * dt / Math.max(1,len);
      const s=Math.sin(player.yaw), c=Math.cos(player.yaw);
      movePlayerTo(player.x + (mx*c - mz*s)*sp, player.z + (mx*s + mz*c)*sp);
    }
    resolveCollisions();
  }
  camera.position.set(player.x, 1.7, player.z);
  camera.rotation.set(0,0,0);
  camera.rotateY(player.yaw); camera.rotateX(player.pitch);
  // 그림자 카메라가 플레이어를 따라다님 (좁은 범위 = 선명한 그림자)
  sun.position.set(player.x + sunDir.x*280, Math.max(70, sunDir.y*280), player.z + sunDir.z*280);
  sun.target.position.set(player.x, 0, player.z);
  sun.target.updateMatrixWorld();
  const movedDist = Math.hypot(player.x - lastPX, player.z - lastPZ);
  if(eraFxPass){
    eraFxPass.uniforms.uTime.value += dt;
    eraFxPass.uniforms.uGrain.value = grainBase * ((glide || movedDist > 0.01) ? 0.4 : 1);   // 이동 중 그레인 감쇠
  }
  if(!glide && movedDist > 0.005){                    // 발소리 (걷기·달리기)
    stepAcc += movedDist;
    if(stepAcc > 0.85){ AudioEng.step(movedDist/dt > 20); stepAcc = 0; }
  }
  lastPX = player.x; lastPZ = player.z;
  if(composer) composer.render();
  else renderer.render(scene, camera);
  drawMap();
  requestAnimationFrame(frame);
}
setTimeout(()=>{ document.getElementById("hint").style.opacity = 0; }, 6000);
applyEra(3, true);
applyHash();          // 공유 링크로 들어온 경우 시대·위치·시선 복원
initScanLoader();     // 실측 스캔 스트리밍 시작
frame();
