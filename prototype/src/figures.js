/* 경복궁 타임워크 — 반차도(班次圖) 화풍 인물 텍스처 생성기
   전역 THREE(three.js, app.js보다 먼저 <script>로 로드됨) 위에서 동작.
   모듈 시스템 없이 순수 canvas 2D로 256×512 캔버스에 인물을 그려
   THREE.CanvasTexture로 반환한다. IIFE로 감싸 전역에는 FIGURES만 노출.

   화풍: 납작한 정면 서기 자세, 원근·명암 없음, 어두운 먹선 외곽 + 차분한 담채.
   얼굴은 살구빛 타원뿐(이목구비 없음), 손은 소매에 숨김 — 기록화처럼 익명 처리. */
"use strict";

window.FIGURES = (function () {
  const W = 256, H = 512;
  const CX = W / 2;

  const KINDS = ["munkwan", "mukwan", "gunjol", "gungnyeo", "visitor1929", "tourist"];

  // Park-Miller 최소표준 LCG — seed(정수) → [0,1) 결정적 난수열.
  // Math.random 대신 이걸 써서 같은 seed면 항상 같은 옷 색조가 나오게 한다.
  function makeRng(seed) {
    let s = (Math.abs(Math.floor(seed || 0)) % 2147483646) + 1;
    return function () {
      s = (s * 16807) % 2147483647;
      return s / 2147483647;
    };
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // hsl 색을 seed 기반으로 미세 변주(h/s/l 각각 지터 폭 지정) — 탁하고 차분한 담채용
  function tone(rnd, h, s, l, jh, js, jl) {
    const hh = ((h + (rnd() - 0.5) * (jh || 0)) % 360 + 360) % 360;
    const ss = clamp(s + (rnd() - 0.5) * (js || 0), 0, 100);
    const ll = clamp(l + (rnd() - 0.5) * (jl || 0), 0, 100);
    return "hsl(" + hh.toFixed(1) + ", " + ss.toFixed(1) + "%, " + ll.toFixed(1) + "%)";
  }

  const INK = "#2a2118";                     // 먹선 외곽 — 순흑 대신 짙은 갈흑
  const SKIN = "hsl(28, 32%, 74%)";          // 살구빛 얼굴(이목구비 없음)

  // 닫힌 다각형 채우기 + 먹선 외곽. pts=[[x,y],...]
  function poly(g, pts, fill, lineW) {
    g.beginPath();
    g.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
    g.closePath();
    g.fillStyle = fill;
    g.fill();
    g.strokeStyle = INK;
    g.lineWidth = lineW || 4;
    g.lineJoin = "round";
    g.stroke();
  }

  function ellipse(g, cx, cy, rx, ry, fill, lineW) {
    g.beginPath();
    g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    g.fillStyle = fill;
    g.fill();
    g.strokeStyle = INK;
    g.lineWidth = lineW || 4;
    g.stroke();
  }

  // ───────────────────────── 공통 신체 앵커 ─────────────────────────
  // 발=캔버스 하단, 머리(이마~턱)는 전체 키(머리끝~발)의 약 1/6
  const FEET_Y = 498;
  const HEAD_TOP = 78;
  const NECK_Y = 150;
  const FACE_CY = (HEAD_TOP + NECK_Y) / 2;   // 114
  const FACE_RX = 22;
  const FACE_RY = (NECK_Y - HEAD_TOP) / 2;   // 36

  function drawFace(g) {
    ellipse(g, CX, FACE_CY, FACE_RX, FACE_RY, SKIN, 3.5);
  }

  // 옷 실루엣: pts=[[y, 반너비],...] 목선(위)→아래 순서로. 좌우 대칭 로브 다각형 생성.
  function robeSilhouette(g, pts, fill, lineW) {
    const left = pts.map(function (p) { return [CX - p[1], p[0]]; });
    const right = pts.slice().reverse().map(function (p) { return [CX + p[1], p[0]]; });
    poly(g, left.concat(right), fill, lineW);
  }

  // 다리(바지) 두 기둥 — 로브가 짧은 종류(군졸·관광객)에서 공용으로 사용
  function drawLegs(g, hemY, color) {
    poly(g, [[CX - 28, hemY - 4], [CX - 5, hemY - 4], [CX - 5, FEET_Y], [CX - 28, FEET_Y]], color, 3.5);
    poly(g, [[CX + 5, hemY - 4], [CX + 28, hemY - 4], [CX + 28, FEET_Y], [CX + 5, FEET_Y]], color, 3.5);
  }

  // 머리 위를 덮는 단순 머리카락 캡(현대 인물·궁녀 공용) — 이마 위쪽만 덮어 턱선은 살구빛으로 남김
  function drawHairCap(g, color) {
    ellipse(g, CX, HEAD_TOP + 18, 21, 20, color, 2.5);
  }

  // ───────────────────────── 사모(문관·무관 공용 관모) ─────────────────────────
  // 둥근 검은 관모 돔 + 좌우로 뻗은 납작한 뿔(날개)
  function drawSamo(g) {
    ellipse(g, CX, 92, 27, 19, "#18140f", 3);
    const wingY = 96, wingH = 7, wingLen = 30, capEdge = 26;
    poly(g, [[CX - capEdge - wingLen, wingY], [CX - capEdge, wingY],
              [CX - capEdge, wingY + wingH], [CX - capEdge - wingLen, wingY + wingH]], "#18140f", 2.2);
    poly(g, [[CX + capEdge, wingY], [CX + capEdge + wingLen, wingY],
              [CX + capEdge + wingLen, wingY + wingH], [CX + capEdge, wingY + wingH]], "#18140f", 2.2);
  }

  // ───────────────────────── 1. 문관 / 2. 무관 (단령 로브) ─────────────────────────
  // 진한 청록/남색(문관) or 적갈/진홍(무관) 단령 + 흉배 + 홀(笏) + 사모
  function danryeong(kind, rnd) {
    const base = kind === "munkwan" ? { h: 200, s: 45, l: 24 } : { h: 8, s: 42, l: 32 };
    return function (g) {
      const robeColor = tone(rnd, base.h, base.s, base.l, 10, 8, 6);
      robeSilhouette(g, [
        [NECK_Y, 22], [NECK_Y + 40, 36], [NECK_Y + 80, 50],
        [NECK_Y + 120, 34], [NECK_Y + 190, 40], [FEET_Y, 56]
      ], robeColor);

      // 흉배: 가슴 사각, 로브보다 살짝 밝은 톤
      const badgeColor = tone(rnd, base.h, base.s - 10, base.l + 22, 6, 6, 6);
      poly(g, [
        [CX - 17, NECK_Y + 34], [CX + 17, NECK_Y + 34],
        [CX + 17, NECK_Y + 72], [CX - 17, NECK_Y + 72]
      ], badgeColor, 2.5);

      drawFace(g);

      // 홀(笏): 두 손 모아 든 얇은 밝은 판 — 손 자체는 소매에 숨겨 그리지 않음
      poly(g, [
        [CX - 6, NECK_Y + 90], [CX + 6, NECK_Y + 90],
        [CX + 6, NECK_Y + 150], [CX - 6, NECK_Y + 150]
      ], "hsl(42, 35%, 82%)", 2);

      drawSamo(g);
    };
  }

  // ───────────────────────── 3. 군졸 ─────────────────────────
  // 소색 짧은 상의 + 바지 + 전립(넓은 검은 챙) + 캔버스 위까지 닿는 창
  function drawGunjol(rnd) {
    return function (g) {
      const jacketColor = tone(rnd, 40, 22, 74, 8, 8, 6);
      robeSilhouette(g, [
        [NECK_Y, 24], [NECK_Y + 30, 34], [NECK_Y + 70, 40],
        [NECK_Y + 110, 36], [NECK_Y + 150, 38]
      ], jacketColor);

      const pantColor = tone(rnd, 40, 18, 60, 6, 6, 6);
      drawLegs(g, NECK_Y + 150, pantColor);

      drawFace(g);

      // 전립(戰笠): 낮은 관모 + 넓은 챙
      ellipse(g, CX, 80, 20, 14, "#1c1a16", 3);
      ellipse(g, CX, 98, 50, 13, "#1c1a16", 3);

      // 창(槍): 캔버스 상단까지 이어지는 장대 + 창날
      const spearX = CX + 44;
      poly(g, [[spearX - 3, 10], [spearX + 3, 10], [spearX + 3, 460], [spearX - 3, 460]], "#4a3527", 2.5);
      poly(g, [[spearX - 9, 10], [spearX, -16], [spearX + 9, 10]], "#3a3530", 2.5);
    };
  }

  // ───────────────────────── 4. 궁녀 ─────────────────────────
  // 남색 치마(넓은 종 모양) + 연두/옥색 저고리 + 검은 머리(쪽진 형태 단순 타원)
  function drawGungnyeo(rnd) {
    return function (g) {
      const skirtColor = tone(rnd, 224, 40, 26, 8, 8, 6);
      robeSilhouette(g, [
        [NECK_Y + 70, 30], [NECK_Y + 130, 50], [NECK_Y + 210, 66], [FEET_Y, 80]
      ], skirtColor);

      const jeogoriColor = tone(rnd, 155, 22, 66, 10, 8, 8);
      robeSilhouette(g, [
        [NECK_Y, 24], [NECK_Y + 35, 32], [NECK_Y + 70, 34]
      ], jeogoriColor);

      drawFace(g);
      drawHairCap(g, "#14110d");
    };
  }

  // ───────────────────────── 5. 1929 관람객 ─────────────────────────
  // seed에 따라: (A) 흰 두루마기 + 갓  또는 (B) 갈색 양복 + 중절모
  function drawVisitor(rnd) {
    return function (g) {
      const variantA = rnd() < 0.5;
      if (variantA) {
        const robeColor = tone(rnd, 42, 14, 88, 6, 6, 5);
        robeSilhouette(g, [
          [NECK_Y, 20], [NECK_Y + 40, 32], [NECK_Y + 100, 34], [NECK_Y + 200, 42], [FEET_Y, 54]
        ], robeColor);

        // 옷고름(가슴 매듭 리본) 힌트
        poly(g, [
          [CX - 3, NECK_Y + 30], [CX + 14, NECK_Y + 46],
          [CX + 11, NECK_Y + 50], [CX - 6, NECK_Y + 34]
        ], "#8a3b2e", 2);

        drawFace(g);

        // 갓: 높은 통형 관모 + 넓은 챙
        poly(g, [[CX - 13, 44], [CX + 13, 44], [CX + 13, 92], [CX - 13, 92]], "#151310", 3);
        ellipse(g, CX, 92, 58, 11, "#151310", 3);
      } else {
        const suitColor = tone(rnd, 28, 35, 36, 6, 8, 6);
        robeSilhouette(g, [
          [NECK_Y, 24], [NECK_Y + 40, 34], [NECK_Y + 120, 32], [NECK_Y + 190, 34]
        ], suitColor);

        const pantColor = tone(rnd, 28, 20, 24, 4, 6, 6);
        drawLegs(g, NECK_Y + 190, pantColor);

        drawFace(g);

        // 중절모: 둥근 정수리 + 챙
        ellipse(g, CX, 84, 24, 18, "#1c1712", 3);
        ellipse(g, CX, 100, 34, 8, "#1c1712", 3);
      }
    };
  }

  // ───────────────────────── 6. 현대 관광객 ─────────────────────────
  // seed%3으로 티셔츠+배낭 / 원피스 / 점퍼 중 하나. 같은 먹선+담채 톤 유지.
  function drawTourist(rnd) {
    return function (g) {
      const variant = Math.floor(rnd() * 3);
      const hue = rnd() * 360;
      const hairColor = rnd() < 0.5 ? "#1c1712" : "#3a2a1e";

      if (variant === 0) {
        // 티셔츠 + 바지 + 배낭(어깨 뒤로 살짝 삐져나온 실루엣)
        const bagColor = tone(rnd, 30, 25, 42, 6, 6, 6);
        poly(g, [
          [CX - 40, NECK_Y + 10], [CX + 40, NECK_Y + 10],
          [CX + 34, NECK_Y + 110], [CX - 34, NECK_Y + 110]
        ], bagColor, 3);

        const shirtColor = tone(rnd, hue, 45, 64, 10, 8, 6);
        robeSilhouette(g, [
          [NECK_Y, 26], [NECK_Y + 30, 34], [NECK_Y + 100, 32], [NECK_Y + 130, 30]
        ], shirtColor);

        const pantColor = tone(rnd, 215, 30, 38, 6, 6, 6);
        drawLegs(g, NECK_Y + 130, pantColor);

        drawFace(g);
        drawHairCap(g, hairColor);
      } else if (variant === 1) {
        // 원피스 — 다리 분리 없는 A라인 실루엣 + 반팔 소매
        const dressColor = tone(rnd, hue, 40, 68, 10, 8, 6);
        robeSilhouette(g, [
          [NECK_Y, 24], [NECK_Y + 30, 34], [NECK_Y + 90, 36], [NECK_Y + 200, 44], [FEET_Y, 58]
        ], dressColor);
        ellipse(g, CX - 30, NECK_Y + 14, 12, 8, dressColor, 2.5);
        ellipse(g, CX + 30, NECK_Y + 14, 12, 8, dressColor, 2.5);

        drawFace(g);
        drawHairCap(g, hairColor);
      } else {
        // 점퍼(패딩) — 박스형 상의 + 바지 + 목깃 힌트
        const jumperColor = tone(rnd, hue, 40, 58, 10, 8, 6);
        robeSilhouette(g, [
          [NECK_Y, 30], [NECK_Y + 30, 42], [NECK_Y + 100, 44], [NECK_Y + 150, 40]
        ], jumperColor);

        const pantColor = tone(rnd, 30, 15, 30, 4, 6, 6);
        drawLegs(g, NECK_Y + 150, pantColor);

        drawFace(g);
        ellipse(g, CX, NECK_Y + 6, 20, 10, jumperColor, 2.5);
        drawHairCap(g, hairColor);
      }
    };
  }

  const BUILDERS = {
    munkwan: function (rnd) { return danryeong("munkwan", rnd); },
    mukwan: function (rnd) { return danryeong("mukwan", rnd); },
    gunjol: drawGunjol,
    gungnyeo: drawGungnyeo,
    visitor1929: drawVisitor,
    tourist: drawTourist
  };

  function texture(kind, seed) {
    const rnd = makeRng(typeof seed === "number" ? seed : 0);
    const build = BUILDERS[kind] || BUILDERS.tourist;   // 미지정 kind 방어적 대체
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const g = canvas.getContext("2d");
    g.clearRect(0, 0, W, H);            // 투명 배경
    build(rnd)(g);
    const tex = new THREE.CanvasTexture(canvas);
    tex.encoding = THREE.sRGBEncoding;
    return tex;
  }

  return { KINDS: KINDS, texture: texture };
})();
