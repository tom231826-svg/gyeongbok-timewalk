"""Blender 헤드리스 스크립트: 실측 FBX → 통계 출력 + 데시메이션 + GLB(Draco) + 미리보기 렌더.
사용: blender -b -P convert_fbx.py -- <fbx경로> <출력폴더> <이름> [목표삼각형수]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
FBX, OUT, NAME = argv[0], argv[1], argv[2]
TARGET = int(argv[3]) if len(argv) > 3 else 200_000

# 기본 씬 비우기 (팩토리 리셋은 5.1 헤드리스에서 불안정)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.wm.fbx_import(filepath=FBX)   # 5.x 신형 임포터 (구형은 이 파일에서 크래시)

# 웹용: 8K 텍스처를 2K로 축소
for img in bpy.data.images:
    if img.size[0] > 2048:
        print(f"[TEX] {img.name} {tuple(img.size)} -> 2048")
        img.scale(2048, 2048)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tv = sum(len(o.data.vertices) for o in meshes)
tf = sum(len(o.data.polygons) for o in meshes)
imgs = [(i.name, tuple(i.size), i.packed_file is not None) for i in bpy.data.images]
print(f"[STATS] objects={len(meshes)} verts={tv} faces={tf}")
print(f"[STATS] images={imgs}")

# 전체 바운딩박스
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
size = mx - mn; center = (mn + mx) / 2
print(f"[STATS] bbox_size={tuple(round(v,2) for v in size)} center={tuple(round(v,2) for v in center)}")

# 데시메이션
if tf > TARGET:
    ratio = TARGET / tf
    print(f"[DECIMATE] ratio={ratio:.4f}")
    for o in meshes:
        if len(o.data.polygons) > 2000:
            m = o.modifiers.new("dec", "DECIMATE")
            m.ratio = ratio

# GLB 내보내기 (Draco 압축)
os.makedirs(OUT, exist_ok=True)
glb = os.path.join(OUT, NAME + ".glb")
try:
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True,
                              export_draco_mesh_compression_enable=True)
except TypeError:
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)
print(f"[GLB] {glb} {os.path.getsize(glb)//1024}KB")

# 미리보기 렌더 (Workbench 텍스처 모드 — 헤드리스 안전)
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "TEXTURE"
scn.render.resolution_x, scn.render.resolution_y = 1280, 800

cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam); scn.camera = cam
r = max(size) * 1.1
cam.location = center + Vector((r * 0.8, -r, r * 0.45))
d = center - cam.location
cam.rotation_euler = (math.atan2(math.hypot(d.x, d.y), -d.z) , 0, math.atan2(d.x, -d.y) * -1 + math.pi)
# 간단히: track-to 컨스트레인트로 확실히 조준
empty = bpy.data.objects.new("t", None); empty.location = center
scn.collection.objects.link(empty)
tr = cam.constraints.new("TRACK_TO"); tr.target = empty
tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
cam_data.clip_end = r * 10

png = os.path.join(OUT, NAME + "_preview.png")
scn.render.filepath = png
bpy.ops.render.render(write_still=True)
print(f"[PNG] {png}")
