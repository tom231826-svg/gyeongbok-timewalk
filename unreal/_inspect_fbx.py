"""
Headless Blender FBX inspector.
Run as: blender --background --factory-startup --python _inspect_fbx.py -- <fbx_path> <out_json_path> <asset_name>

Read-only: never saves the .blend, never modifies the source FBX.
Uses the new bpy.ops.wm.fbx_import operator (the legacy import_scene.fbx
operator crashes headless on some of these large scan files).
"""
import bpy
import sys
import json
import traceback
from mathutils import Vector

argv = sys.argv
idx = argv.index("--")
fbx_path = argv[idx + 1]
out_path = argv[idx + 2]
asset_name = argv[idx + 3]


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block_collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(block_collection):
            if block.users == 0:
                block_collection.remove(block)


def write_result(result):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


clear_scene()

try:
    bpy.ops.wm.fbx_import(filepath=fbx_path)
except Exception as e:
    write_result(
        {
            "name": asset_name,
            "fbx": fbx_path,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }
    )
    sys.exit(0)

mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]

total_tris = 0
materials = set()
min_co = [float("inf")] * 3
max_co = [float("-inf")] * 3

for obj in mesh_objs:
    mesh = obj.data
    mesh.calc_loop_triangles()
    total_tris += len(mesh.loop_triangles)

    for slot in obj.material_slots:
        if slot.material:
            materials.add(slot.material.name)

    mat = obj.matrix_world
    for corner in obj.bound_box:
        world_co = mat @ Vector(corner)
        for i in range(3):
            if world_co[i] < min_co[i]:
                min_co[i] = world_co[i]
            if world_co[i] > max_co[i]:
                max_co[i] = world_co[i]

if mesh_objs:
    bbox_size = [max_co[i] - min_co[i] for i in range(3)]
    long_axis = max(bbox_size)
    bbox_min_out = min_co
    bbox_max_out = max_co
else:
    bbox_size = [0, 0, 0]
    long_axis = 0
    bbox_min_out = [0, 0, 0]
    bbox_max_out = [0, 0, 0]

textures = []
for img in bpy.data.images:
    if img.name in ("Render Result", "Viewer Node"):
        continue
    try:
        w, h = int(img.size[0]), int(img.size[1])
    except Exception:
        w, h = 0, 0
    textures.append(
        {
            "name": img.name,
            "size": [w, h],
            "packed": bool(img.packed_file),
            "source": img.source,
            "filepath": img.filepath,
        }
    )

result = {
    "name": asset_name,
    "fbx": fbx_path,
    "meshes": len(mesh_objs),
    "objects_total": len(bpy.data.objects),
    "triangles": total_tris,
    "textures": textures,
    "materials": sorted(materials),
    "bbox": bbox_size,
    "bboxMin": bbox_min_out,
    "bboxMax": bbox_max_out,
    "lowestPoint": bbox_min_out[2],
    "longAxisLen": long_axis,
}

write_result(result)
print(f"OK {asset_name}: meshes={len(mesh_objs)} tris={total_tris} bbox={bbox_size}")
