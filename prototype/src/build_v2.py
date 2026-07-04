#!/usr/bin/env python3
"""v0.2 빌드: template_v2 + three.min.js + app.js + 카드 사진 → index.html / artifact.html"""
import base64
import json
import os
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(SRC, "..", "assets")

def read(p, mode="r"):
    with open(p, mode, encoding=None if "b" in mode else "utf-8") as f:
        return f.read()

def b64(fname):
    return "data:image/jpeg;base64," + base64.b64encode(
        read(os.path.join(ASSETS, fname), "rb")).decode("ascii")

def b64raw(path: str) -> str:
    return base64.b64encode(read(path, "rb")).decode("ascii")

VENDOR = os.path.join(SRC, "vendor")
SCANS = os.path.join(ASSETS, "scans_csp")   # CSP 안전판: Draco 없음, 텍스처 별도

# 재질이름(부분일치 키) → 텍스처 파일 매핑. 근거: convert_csp.py 실행 로그의 [MAT] 줄.
# 주의: 한 키가 다른 키를 포함하면(예: GJM_E_HG_in1 ⊃ GJM_E_HG) 구체적인 키를 먼저 적을 것.
MATS = {
    "seowollang":    {"GJM_W_WR": "seowollang_tex0.jpg"},
    "dongwollang":   {"GJM_E_WR": "dongwollang_tex0.jpg"},
    "donghaenggak":  {"GJM_E_HG_in1": "donghaenggak_tex1.jpg", "GJM_E_HG": "donghaenggak_tex0.jpg"},
    "seohaenggak":   {"GJM_W_HG": "seohaenggak_tex0.jpg", "서행각1": "seohaenggak_tex1.jpg"},
    "heung_e":       {"HRM_E_HG": "heung_e_tex0.jpg"},
    "heung_w":       {"HRM_W_HG": "heung_w_tex0.jpg"},
    "sajeongmun":    {"SJM": "sajeongmun_tex0.jpg"},
    "gyeonghoeru":   {"GHR_L": "gyeonghoeru_tex0.jpg"},
    "gangnyeongjeon":{"GNJ_in": "gangnyeongjeon_tex1.jpg", "원본": "gangnyeongjeon_tex0.jpg"},
}
SET_FULL = list(MATS.keys())                                   # 로컬 완전판: 전부
SET_ARTIFACT = ["seowollang", "dongwollang", "sajeongmun"]     # 배포판: 아티팩트 16MB 한도 내 조합

def scan_data_json(names: list) -> str:
    data, total = {}, 0
    for n in names:
        glb = os.path.join(SCANS, "q", n + ".glb")             # 양자화본 우선 (KHR_mesh_quantization, 디코더 불필요)
        if not os.path.exists(glb):
            glb = os.path.join(SCANS, n + ".glb")
        if not os.path.exists(glb):
            print(f"  (스킵: {n} — GLB 없음)")
            continue
        total += os.path.getsize(glb)
        entry = {"glb": "data:model/gltf-binary;base64," + b64raw(glb), "tex": {}}
        for key, fn in MATS.get(n, {}).items():
            p = os.path.join(SCANS, fn)
            if os.path.exists(p):
                total += os.path.getsize(p)
                entry["tex"][key] = "data:image/jpeg;base64," + b64raw(p)
            # 시대 파생 텍스처 (P1-A): era1888/, era1929/ 폴더에 있으면 자동 포함
            for era_dir, field in (("era1888", "tex1888"), ("era1929", "tex1929")):
                pe = os.path.join(SCANS, era_dir, fn)
                if os.path.exists(pe):
                    total += os.path.getsize(pe)
                    entry.setdefault(field, {})[key] = "data:image/jpeg;base64," + b64raw(pe)
        data[n] = entry
    print(f"  스캔 {len(data)}동, 원본 합계 {total/1024/1024:.1f}MB")
    return json.dumps(data, ensure_ascii=False)

POSTFX_FILES = [  # 의존 순서 주의
    "Pass.js", "MaskPass.js", "ShaderPass.js", "RenderPass.js",
    "CopyShader.js", "LuminosityHighPassShader.js", "SSAOShader.js", "SMAAShader.js",
    "SimplexNoise.js", "EffectComposer.js", "UnrealBloomPass.js", "SSAOPass.js", "SMAAPass.js",
]

def build(scan_set: list) -> str:
    html = read(os.path.join(SRC, "template_v2.html"))
    app = read(os.path.join(SRC, "app.js"))
    app = app.replace("%%CARD_1888%%", b64("card_j_1888.jpg"))
    app = app.replace("%%CARD_1929%%", b64("card_j_1929.jpg"))
    app = app.replace("/*__SCAN_DATA__*/{}", scan_data_json(scan_set))
    cards_path = os.path.join(SRC, "building_cards.json")
    if os.path.exists(cards_path):
        app = app.replace("/*__BCARDS__*/[]", read(cards_path))
    tour_path = os.path.join(SRC, "tour_script.json")
    if os.path.exists(tour_path):
        app = app.replace("/*__TOUR__*/null", read(tour_path))
    html = html.replace("%%THREE%%", read(os.path.join(SRC, "three.min.js")))
    loaders = read(os.path.join(VENDOR, "GLTFLoader.js"))
    for f in POSTFX_FILES:
        loaders += "\n" + read(os.path.join(VENDOR, f))
    html = html.replace("%%LOADERS%%", loaders)
    props_path = os.path.join(SRC, "props.js")
    html = html.replace("%%PROPS%%", read(props_path) if os.path.exists(props_path) else "window.PROPS={};")
    figures_path = os.path.join(SRC, "figures.js")
    html = html.replace("%%FIGURES%%", read(figures_path) if os.path.exists(figures_path) else "window.FIGURES=null;")
    return html.replace("%%APP%%", app)

full = build(SET_FULL)
OUT = os.path.join(SRC, "..", "index.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(full)
print(f"index.html(완전판) {os.path.getsize(OUT)/1024/1024:.2f} MB")

artifact = build(SET_ARTIFACT)
artifact = artifact.replace(
    '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, '
    'maximum-scale=1, user-scalable=no">\n', "")
artifact = artifact.replace("</head>\n<body>\n", "")
artifact = artifact.replace("\n</body>\n</html>", "")
assert "<!DOCTYPE" not in artifact and "</html>" not in artifact, "wrapper 제거 실패"
ART = os.path.join(SRC, "..", "artifact.html")
with open(ART, "w", encoding="utf-8") as f:
    f.write(artifact)
print(f"artifact.html(배포판, 월랑 2동) {os.path.getsize(ART)/1024/1024:.2f} MB")
