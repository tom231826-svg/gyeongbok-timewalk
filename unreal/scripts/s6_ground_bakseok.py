# -*- coding: utf-8 -*-
# 실행법 (에디터 콘솔 Python 모드):
#   exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s6_ground_bakseok.py').read())
#
# s6_ground_bakseok.py (v2) — G1: 실제 근정전 권역 바닥 구성
#   실제 구성 재현(화질보다 구성 우선):
#     · 박석 마당 — 회랑 안쪽 전면(126×132m) + 근정문 남쪽 전정(영제교까지 52m)
#     · 삼도(三道) — 중앙 어도(폭4.6m, +8cm) + 좌우 신하길(폭2.6m, +4cm), 남북 관통
#     · 품계석 2열×12 — 어도 양옆(임시 돌기둥 프록시, 스케치팹 도착 시 교체)
#     · 마사토 — 회랑 바깥 600×600m
#   v1 실패 교훈: 월드좌표 UV 등 복잡한 머티리얼 그래프 API가 버전차로 깨짐
#   → v2 는 검증된 노드만 사용(TexCoord 타일링 + TextureSample). 평면마다 전용 머티리얼.
#   재실행 안전: 라벨 삭제 후 재생성, 텍스처·머티리얼 재사용.

import os

try:
    import unreal
except ImportError:
    unreal = None


TEX_DIR = "/Users/junkim/projects/gyeongbok-timewalk/unreal/textures"
GROUND_ROOT = "/Game/Gyeongbok/Ground"

# 표면: (디퓨즈, 노멀, 타일 실물 m)
SURF = {
    "bakseok": ("bakseok_D.jpg", "bakseok_N.png", 6.0),
    "eodo":    ("eodo_D.jpg",    "eodo_N.png",    4.0),
    "masato":  ("masato_D.jpg",  "masato_N.png",  9.0),
}

# 바닥 평면: (라벨, 표면, UE위치 cm, 크기 m(x북남,y동서))
PLANES = [
    ("Ground_Bakseok_Main",  "bakseok", (29400.0, 0.0, 0.0),  (132.0, 126.0)),
    ("Ground_Bakseok_South", "bakseok", (20200.0, 0.0, 0.0),  (52.0, 126.0)),
    ("Samdo_Center",         "eodo",    (28400.0, 0.0, 8.0),  (152.0, 4.6)),
    ("Samdo_E",              "eodo",    (28400.0, 360.0, 4.0), (152.0, 2.6)),
    ("Samdo_W",              "eodo",    (28400.0, -360.0, 4.0), (152.0, 2.6)),
    ("Ground_Masato",        "masato",  (29400.0, 0.0, -2.0), (600.0, 600.0)),
]

# 품계석 프록시: 어도 양옆 2열×12 (실물 위치 근사 — 마당 남반부)
PUM_Y = 550.0            # 어도에서 5.5m
PUM_X0, PUM_STEP, PUM_N = 25000.0, 500.0, 12

OLD_LABELS = ["Ground_Temp", "Ground_Bakseok", "Ground_Eodo"]   # v1·s3 잔재


def log(msg):
    (unreal.log if unreal else print)("[Gyeongbok/s6] " + msg)


def log_warn(msg):
    (unreal.log_warning if unreal else print)("[Gyeongbok/s6][WARN] " + msg)


def import_tex(fname, is_normal):
    src = os.path.join(TEX_DIR, fname)
    if not os.path.isfile(src):
        log_warn("텍스처 파일 없음: %s" % src)
        return None
    name = os.path.splitext(fname)[0]
    dest = "%s/%s" % (GROUND_ROOT, name)
    if not unreal.EditorAssetLibrary.does_asset_exist(dest):
        task = unreal.AssetImportTask()
        task.filename = src
        task.destination_path = GROUND_ROOT
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.EditorAssetLibrary.load_asset(dest)
    if tex and is_normal:
        try:
            tex.set_editor_property("compression_settings",
                                    unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("srgb", False)
            unreal.EditorAssetLibrary.save_asset(dest)
        except Exception as e:
            log_warn("노멀 설정 스킵(%s): %s" % (name, e))
    return tex


def ensure_plane_material(label, surf_key, size_m):
    """평면 전용 머티리얼: TexCoord 타일링 → 텍스처. 검증된 노드만 사용."""
    d_file, n_file, tile_m = SURF[surf_key]
    path = "%s/M_%s" % (GROUND_ROOT, label)
    m = unreal.EditorAssetLibrary.load_asset(path)
    if m:
        return m
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_%s" % label, GROUND_ROOT, unreal.Material,
                        unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary

    uv = mel.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -500, 0)
    try:
        uv.set_editor_property("u_tiling", size_m[0] / tile_m)
        uv.set_editor_property("v_tiling", size_m[1] / tile_m)
    except Exception as e:
        log_warn("%s 타일링 스킵: %s" % (label, e))

    d_tex = import_tex(d_file, is_normal=False)
    base = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -250, -100)
    if d_tex:
        try:
            base.set_editor_property("texture", d_tex)
        except Exception as e:
            log_warn("%s 디퓨즈 지정 실패: %s" % (label, e))
    mel.connect_material_expressions(uv, "", base, "UVs")
    mel.connect_material_property(base, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -250, 150)
    rough.set_editor_property("r", 0.9)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    n_tex = import_tex(n_file, is_normal=True)
    if n_tex:
        norm = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -250, 300)
        try:
            norm.set_editor_property("texture", n_tex)
            norm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            mel.connect_material_expressions(uv, "", norm, "UVs")
            mel.connect_material_property(norm, "", unreal.MaterialProperty.MP_NORMAL)
        except Exception as e:
            log_warn("%s 노멀 연결 스킵(디퓨즈만 사용): %s" % (label, e))

    mel.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(path)
    log("M_%s 생성" % label)
    return m


def ensure_stone_material():
    path = "%s/M_StoneProxy" % GROUND_ROOT
    m = unreal.EditorAssetLibrary.load_asset(path)
    if m:
        return m
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_StoneProxy", GROUND_ROOT, unreal.Material,
                        unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    col = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    try:
        col.set_editor_property("constant", unreal.LinearColor(0.32, 0.31, 0.29, 1.0))
    except Exception as e:
        log_warn("품계석 색 스킵: %s" % e)
    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 0.85)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(path)
    return m


def main():
    if unreal is None:
        print("[Gyeongbok/s6] unreal 모듈 없음 — UE 에디터에서 실행하세요.")
        return
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    doomed = set(OLD_LABELS + [p[0] for p in PLANES])
    doomed |= {"Pum_%s_%02d" % (s, i) for s in ("E", "W") for i in range(PUM_N)}
    removed = 0
    for a in subsystem.get_all_level_actors():
        try:
            if a.get_actor_label() in doomed:
                subsystem.destroy_actor(a)
                removed += 1
        except Exception:
            continue
    if removed:
        log("기존 바닥·품계석 %d 개 제거" % removed)

    plane_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
    if plane_mesh is None:
        log_warn("기본 Plane 메시 없음 — 중단")
        return

    for label, surf, pos, size in PLANES:
        mat = ensure_plane_material(label, surf, size)
        actor = subsystem.spawn_actor_from_object(plane_mesh, unreal.Vector(*pos))
        actor.set_actor_label(label)
        actor.set_actor_scale3d(unreal.Vector(size[0], size[1], 1.0))
        try:
            actor.static_mesh_component.set_material(0, mat)
        except Exception as e:
            log_warn("%s 머티리얼 배정 실패: %s" % (label, e))
        log("%s (%.0fx%.0fm)" % (label, size[0], size[1]))

    if cube_mesh:
        stone = ensure_stone_material()
        for side, ysign in (("E", 1.0), ("W", -1.0)):
            for i in range(PUM_N):
                pos = unreal.Vector(PUM_X0 + i * PUM_STEP, ysign * PUM_Y, 45.0)
                a = subsystem.spawn_actor_from_object(cube_mesh, pos)
                a.set_actor_label("Pum_%s_%02d" % (side, i))
                a.set_actor_scale3d(unreal.Vector(0.45, 0.30, 0.90))
                try:
                    a.static_mesh_component.set_material(0, stone)
                except Exception:
                    pass
        log("품계석 프록시 2열×%d 배치 (스케치팹 도착 시 교체)" % PUM_N)

    log("바닥 v2 완료 — 박석 마당+남쪽 전정, 삼도, 품계석, 마사토. Cmd+S 저장.")


if __name__ == "__main__":
    main()
else:
    main()
