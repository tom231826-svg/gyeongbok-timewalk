/* 경복궁 타임워크 — 절차적 소품 라이브러리
   전역 THREE(three.js r147, app.js보다 먼저 <script>로 로드됨) 위에서 동작.
   각 PROPS.xxx(M)은 재질 딕셔너리 M을 받아 THREE.Group을 반환한다.
   좌표계: 미터, 원점=바닥 중앙. 저폴리곤(원기둥 8~12세그, 구 12x8 이하). */
"use strict";

window.PROPS = (function () {
  const PROPS = {};

  // 기본 파트: geo+material로 Mesh 하나 만들고 위치/회전 및 그림자 플래그 세팅
  function part(geo, material, x, y, z, rx, ry, rz) {
    const m = new THREE.Mesh(geo, material);
    m.castShadow = true;
    m.receiveShadow = true;
    m.position.set(x || 0, y || 0, z || 0);
    if (rx || ry || rz) m.rotation.set(rx || 0, ry || 0, rz || 0);
    return m;
  }

  // 두 점 사이를 잇는 얇은 판(Box) — 처진 천, 늘어진 널빤지 근사용
  function beam(ax, ay, az, bx, by, bz, thickness, width, material) {
    const dir = new THREE.Vector3(bx - ax, by - ay, bz - az);
    const len = dir.length();
    const geo = new THREE.BoxGeometry(len, thickness, width);
    const m = new THREE.Mesh(geo, material);
    m.castShadow = true;
    m.receiveShadow = true;
    m.position.set((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir.normalize());
    return m;
  }

  // 두 점 사이를 잇는 원기둥(Rod) — 로프, 팔대 등 둥근 부재 근사용
  function rod(ax, ay, az, bx, by, bz, radius, segments, material) {
    const dir = new THREE.Vector3(bx - ax, by - ay, bz - az);
    const len = dir.length();
    const geo = new THREE.CylinderGeometry(radius, radius, len, segments);
    const m = new THREE.Mesh(geo, material);
    m.castShadow = true;
    m.receiveShadow = true;
    m.position.set((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    return m;
  }

  // ───────────────────────── 1. 드므 ─────────────────────────
  // 화재막이 청동 물독: 낮은 석재 받침 + 위로 벌어진 대야형 몸통 + 테두리 립
  PROPS.deumeu = function (M) {
    const g = new THREE.Group();
    const baseH = 0.15;
    g.add(part(new THREE.CylinderGeometry(0.62, 0.68, baseH, 12), M.stone, 0, baseH / 2, 0));
    const bodyH = 0.65;
    g.add(part(new THREE.CylinderGeometry(0.6, 0.5, bodyH, 12), M.brass, 0, baseH + bodyH / 2, 0));
    g.add(part(new THREE.TorusGeometry(0.61, 0.05, 6, 12), M.brass, 0, baseH + bodyH, 0, Math.PI / 2, 0, 0));
    return g;
  };

  // ───────────────────────── 2. 석등롱/등롱대 ─────────────────────────
  // 목재 기둥 2.2m + 사각 등집(광목 4면 + 목재 모서리대) + 소형 지붕 + 받침돌
  PROPS.lantern = function (M) {
    const g = new THREE.Group();
    const baseH = 0.15;
    g.add(part(new THREE.CylinderGeometry(0.22, 0.26, baseH, 8), M.stone, 0, baseH / 2, 0));
    const poleH = 2.2;
    g.add(part(new THREE.CylinderGeometry(0.055, 0.07, poleH, 8), M.wood, 0, baseH + poleH / 2, 0));
    const boxW = 0.36, boxH = 0.4;
    const boxY = baseH + poleH + boxH / 2;
    g.add(part(new THREE.BoxGeometry(boxW, boxH, boxW), M.banner, 0, boxY, 0));
    [[1, 1], [1, -1], [-1, 1], [-1, -1]].forEach(function (o) {
      g.add(part(new THREE.BoxGeometry(0.03, boxH, 0.03), M.wood, o[0] * (boxW / 2 - 0.015), boxY, o[1] * (boxW / 2 - 0.015)));
    });
    const roofH = 0.22;
    g.add(part(new THREE.ConeGeometry(0.32, roofH, 4), M.roof, 0, boxY + boxH / 2 + roofH / 2, 0, 0, Math.PI / 4, 0));
    g.add(part(new THREE.SphereGeometry(0.04, 8, 6), M.brass, 0, boxY + boxH / 2 + roofH + 0.04, 0));
    return g;
  };

  // ───────────────────────── 3. 깃대 ─────────────────────────
  // 목재 깃대 7m + 상단 옆으로 뻗은 팔대 + 세로로 긴 광목 깃발
  PROPS.flagpole = function (M) {
    const g = new THREE.Group();
    const baseH = 0.15;
    g.add(part(new THREE.BoxGeometry(0.3, baseH, 0.3), M.stone, 0, baseH / 2, 0));
    const poleH = 7;
    g.add(part(new THREE.CylinderGeometry(0.035, 0.06, poleH, 8), M.wood, 0, baseH + poleH / 2, 0));
    const armY = baseH + poleH - 0.25;
    const armLen = 0.5;
    g.add(rod(0, armY, 0, armLen, armY, 0, 0.025, 6, M.wood));
    const flagW = 0.5, flagH = 1.7;
    g.add(part(new THREE.BoxGeometry(0.02, flagH, flagW), M.banner, armLen, armY - flagH / 2, 0));
    return g;
  };

  // ───────────────────────── 4. 차일 기둥 세트 ─────────────────────────
  // 마당 의례용 차양 기둥 2개(4m) + 처진 천(3개 판으로 곡면 근사)
  PROPS.chail = function (M) {
    const g = new THREE.Group();
    const poleH = 4, spacing = 2.6;
    [-spacing / 2, spacing / 2].forEach(function (x) {
      g.add(part(new THREE.CylinderGeometry(0.055, 0.07, poleH, 8), M.wood, x, poleH / 2, 0));
    });
    const sagY = poleH - 0.35;
    const depth = 1.3;
    g.add(beam(-spacing / 2, poleH, 0, -spacing * 0.15, sagY, 0, 0.03, depth, M.banner));
    g.add(beam(-spacing * 0.15, sagY, 0, spacing * 0.15, sagY, 0, 0.03, depth, M.banner));
    g.add(beam(spacing * 0.15, sagY, 0, spacing / 2, poleH, 0, 0.03, depth, M.banner));
    return g;
  };

  // ───────────────────────── 5. 1920년대 전신주 ─────────────────────────
  // 위로 가늘어지는 나무 기둥 8m + 가로대 2개 + 애자 4개(전선은 생략)
  PROPS.telegraphPole = function (M) {
    const g = new THREE.Group();
    const h = 8;
    g.add(part(new THREE.CylinderGeometry(0.08, 0.17, h, 8), M.wood, 0, h / 2, 0));
    [h * 0.86, h * 0.74].forEach(function (y) {
      g.add(part(new THREE.CylinderGeometry(0.03, 0.03, 1.1, 6), M.wood, 0, y, 0, 0, 0, Math.PI / 2));
      [-0.55, 0.55].forEach(function (x) {
        g.add(part(new THREE.SphereGeometry(0.045, 8, 6), M.dark, x, y + 0.07, 0));
      });
    });
    return g;
  };

  // ───────────────────────── 6. 1920년대 나무 벤치 ─────────────────────────
  // 등받이 있는 단순형, 길이 1.6m
  PROPS.benchOld = function (M) {
    const g = new THREE.Group();
    const length = 1.6, seatH = 0.45, depth = 0.4;
    g.add(part(new THREE.BoxGeometry(length, 0.05, depth), M.wood, 0, seatH, 0));
    g.add(part(new THREE.BoxGeometry(length, 0.35, 0.05), M.wood, 0, seatH + 0.2, -depth / 2 + 0.02));
    [-length / 2 + 0.08, length / 2 - 0.08].forEach(function (x) {
      [-depth / 2 + 0.04, depth / 2 - 0.04].forEach(function (z) {
        g.add(part(new THREE.BoxGeometry(0.06, seatH, 0.06), M.wood, x, seatH / 2, z));
      });
      g.add(part(new THREE.BoxGeometry(0.06, 0.4, 0.06), M.wood, x, seatH + 0.2, -depth / 2 + 0.02));
    });
    return g;
  };

  // ───────────────────────── 7. 현대 안내판 ─────────────────────────
  // 기둥 2개(높이 1.1m 근사) + 뒤로 기운 어두운 패널 + 위에 밝은 면판
  PROPS.infoSign = function (M) {
    const g = new THREE.Group();
    const postH = 0.78;
    [-0.32, 0.32].forEach(function (x) {
      g.add(part(new THREE.CylinderGeometry(0.028, 0.028, postH, 8), M.brass, x, postH / 2, 0));
    });
    const panelW = 0.85, panelH = 0.45, tilt = -0.3;
    const backing = part(new THREE.BoxGeometry(panelW, panelH, 0.03), M.dark, 0, postH + 0.18, 0, tilt, 0, 0);
    g.add(backing);
    backing.add(part(new THREE.BoxGeometry(panelW - 0.08, panelH - 0.08, 0.01), M.wall, 0, 0, 0.02));
    return g;
  };

  // ───────────────────────── 8. 현대 관람 로프 ─────────────────────────
  // 지주 2개(0.9m) + 사이에 처진 로프(3분절 원기둥으로 곡선 근사), 폭 1.5m
  PROPS.ropeBarrier = function (M) {
    const g = new THREE.Group();
    const postH = 0.9, width = 1.5;
    [-width / 2, width / 2].forEach(function (x) {
      g.add(part(new THREE.CylinderGeometry(0.035, 0.04, postH, 8), M.brass, x, postH / 2, 0));
      g.add(part(new THREE.SphereGeometry(0.045, 8, 6), M.brass, x, postH + 0.03, 0));
    });
    const ropeY = postH - 0.04, sag = 0.09;
    g.add(rod(-width / 2, ropeY, 0, -width * 0.15, ropeY - sag, 0, 0.015, 6, M.dark));
    g.add(rod(-width * 0.15, ropeY - sag, 0, width * 0.15, ropeY - sag, 0, 0.015, 6, M.dark));
    g.add(rod(width * 0.15, ropeY - sag, 0, width / 2, ropeY, 0, 0.015, 6, M.dark));
    return g;
  };

  // ───────────────────────── 9. 폐허 잔해 더미 ─────────────────────────
  // 깨진 석재·기와 무더기(상자/원기둥 6~10개 무작위 회전), 지름 약 1.7m
  PROPS.rubble = function (M) {
    const g = new THREE.Group();
    const count = 6 + Math.floor(Math.random() * 5);
    for (let i = 0; i < count; i++) {
      const mat = Math.random() < 0.4 ? M.roof : M.stone;
      const size = 0.2 + Math.random() * 0.35;
      const geo = Math.random() < 0.5
        ? new THREE.BoxGeometry(size, size * 0.6, size * 0.8)
        : new THREE.CylinderGeometry(size * 0.4, size * 0.45, size * 0.5, 8);
      const angle = Math.random() * Math.PI * 2;
      const r = Math.random() * 0.85;
      const x = Math.cos(angle) * r;
      const z = Math.sin(angle) * r;
      const y = size * 0.25 + Math.random() * 0.15;
      const rx = Math.random() * 0.6 - 0.3;
      const ry = Math.random() * Math.PI * 2;
      const rz = Math.random() * 0.6 - 0.3;
      g.add(part(geo, mat, x, y, z, rx, ry, rz));
    }
    return g;
  };

  return PROPS;
})();
