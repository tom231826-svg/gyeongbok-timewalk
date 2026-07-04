#!/usr/bin/env python3
"""template.html의 %%토큰%%에 assets 이미지를 base64 데이터 URI로 삽입 → ../index.html 생성."""
import base64
import os

SRC = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(SRC, "..", "assets")
OUT = os.path.join(SRC, "..", "index.html")

TOKENS = {
    "%%PANO_g_1888%%": "pano_g_1888.jpg", "%%PANO_g_1929%%": "pano_g_1929.jpg",
    "%%PANO_g_2026%%": "pano_g_2026.jpg", "%%PANO_j_1888%%": "pano_j_1888.jpg",
    "%%PANO_j_1929%%": "pano_j_1929.jpg", "%%PANO_j_2026%%": "pano_j_2026.jpg",
    "%%CARD_g_1888%%": "card_g_1888.jpg", "%%CARD_g_1929%%": "card_g_1929.jpg",
    "%%CARD_j_1888%%": "card_j_1888.jpg", "%%CARD_j_1929%%": "card_j_1929.jpg",
}

with open(os.path.join(SRC, "template.html"), encoding="utf-8") as f:
    html = f.read()

missing = [t for t in TOKENS if t not in html]
if missing:
    raise SystemExit(f"템플릿에 없는 토큰: {missing}")

for token, fname in TOKENS.items():
    with open(os.path.join(ASSETS, fname), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    html = html.replace(token, "data:image/jpeg;base64," + b64)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"index.html {os.path.getsize(OUT) / 1024 / 1024:.1f} MB")

# 아티팩트용: 호스팅 측이 doctype/html/head/body 골격을 씌우므로 wrapper 제거본 생성
artifact = html
artifact = artifact.replace(
    '<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, '
    'maximum-scale=1, user-scalable=no">\n', "")
artifact = artifact.replace("</head>\n<body>\n", "")
artifact = artifact.replace("\n</body>\n</html>", "")
ART = os.path.join(SRC, "..", "artifact.html")
with open(ART, "w", encoding="utf-8") as f:
    f.write(artifact)
assert "<!DOCTYPE" not in artifact and "</html>" not in artifact, "wrapper 제거 실패"
print(f"artifact.html {os.path.getsize(ART) / 1024 / 1024:.1f} MB")
