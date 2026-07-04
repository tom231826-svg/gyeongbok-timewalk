"""CSP 안전판: FBX → GLB(지오메트리만, Draco 없음) + 텍스처 JPG 별도 저장.
아티팩트 호스팅의 보안정책이 blob URL(fetch/worker)을 막으므로:
- Draco 압축 제거 (wasm/worker 불필요)
- 이미지 제외 GLB (텍스처는 data URI로 앱에서 직접 주입)
사용: blender -b -P convert_csp.py -- <fbx> <출력폴더> <이름> <목표삼각형수>
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
FBX, OUT, NAME, TARGET = argv[0], argv[1], argv[2], int(argv[3])
TEXSIZE = int(argv[4]) if len(argv) > 4 else 2048

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.wm.fbx_import(filepath=FBX)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tf = sum(len(o.data.polygons) for o in meshes)
print(f"[STATS] meshes={len(meshes)} faces={tf}")

# 재질 → 텍스처 매핑 출력 + 텍스처 JPG 저장 (2048)
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 78
saved = {}
for o in meshes:
    for slot in o.material_slots:
        mat = slot.material
        if not mat or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                img = node.image
                if img.size[0] > TEXSIZE:
                    img.scale(TEXSIZE, TEXSIZE)
                if img.name not in saved:
                    fn = f"{NAME}_tex{len(saved)}.jpg"
                    img.save_render(os.path.join(OUT, fn))
                    saved[img.name] = fn
                print(f"[MAT] mesh={o.name} material={mat.name} image={img.name} file={saved[img.name]}")

if tf > TARGET:
    ratio = TARGET / tf
    print(f"[DECIMATE] ratio={ratio:.4f}")
    for o in meshes:
        if len(o.data.polygons) > 2000:
            m = o.modifiers.new("dec", "DECIMATE")
            m.ratio = ratio

glb = os.path.join(OUT, NAME + ".glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True,
                          export_image_format="NONE")
print(f"[GLB] {glb} {os.path.getsize(glb)//1024}KB")
