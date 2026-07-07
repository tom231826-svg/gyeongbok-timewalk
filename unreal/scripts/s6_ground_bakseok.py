# -*- coding: utf-8 -*-
# 실행법 (에디터 콘솔 Python 모드):
#   exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s6_ground_bakseok.py').read())
#
# s6_ground_bakseok.py — G1: 박석 마당 바닥
#   make_ground_textures.py 로 생성한 박석/어도/마사토 텍스처를 임포트하고,
#   월드좌표 기반 UV 마스터 머티리얼 1개 + 인스턴스 3개를 만들어 바닥 3장을 깐다:
#     · Ground_Bakseok — 마당(회랑 안쪽 126×132m), 박석
#     · Ground_Eodo    — 어도(임금 길, 폭 7m), 살짝 돋움
#     · Ground_Masato  — 바깥 흙바닥 600×600m (기존 Ground_Temp 대체)
#   월드좌표 UV 라 평면 크기와 무관하게 무늬 크기가 일정하고 이음매가 없다.
#   재실행 안전: 바닥 액터는 지우고 다시 깔고, 텍스처·머티리얼은 재사용.

import os

try:
    import unreal
except ImportError:
    unreal = None


TEX_DIR = "/Users/junkim/projects/gyeongbok-timewalk/unreal/textures"
GROUND_ROOT = "/Game/Gyeongbok/Ground"
MASTER_PATH = GROUND_ROOT + "/M_GroundWS"

# (이름, 디퓨즈, 노멀, 타일 실물크기 cm, 매크로 얼룩 강도, 러프니스)
SURFACES = {
    "Bakseok": ("bakseok_D.jpg", "bakseok_N.png", 600.0, 0.35, 0.85),
    "Eodo":    ("eodo_D.jpg",    "eodo_N.png",    400.0, 0.25, 0.75),
    "Masato":  ("masato_D.jpg",  "masato_N.png",  900.0, 0.40, 0.95),
}

# 바닥 액터: (라벨, 표면, UE위치 cm, 스케일 m) — layout 좌표계: UE.X=-z*100, UE.Y=x*100
PLANES = [
    ("Ground_Bakseok", "Bakseok", (29400.0, 0.0, 0.0), (132.0, 126.0)),
    ("Ground_Eodo",    "Eodo",    (29400.0, 0.0, 4.0), (128.0, 7.0)),
    ("Ground_Masato",  "Masato",  (29400.0, 0.0, -2.0), (600.0, 600.0)),
]
OLD_LABELS = ["Ground_Temp"]   # s3 임시 바닥 — 발견 시 제거


def log(msg):
    (unreal.log if unreal else print)("[Gyeongbok/s6] " + msg)


def log_warn(msg):
    (unreal.log_warning if unreal else print)("[Gyeongbok/s6][WARN] " + msg)


def import_tex(fname, is_normal):
    src = os.path.join(TEX_DIR, fname)
    if not os.path.isfile(src):
        log_warn("텍스처 파일 없음: %s (make_ground_textures.py 먼저 실행)" % src)
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
            # 노멀은 OpenGL(초록=위) 방식으로 생성됨 — 요철이 반대로 보이면 아래를 True 로
            tex.set_editor_property("flip_green_channel", False)
            unreal.EditorAssetLibrary.save_asset(dest)
        except Exception as e:
            log_warn("노멀 텍스처 설정 스킵(%s): %s" % (name, e))
    return tex


def ensure_master():
    """월드좌표 UV 마스터: BaseTex·NormalTex·TileSize·MacroStrength·Roughness 파라미터."""
    m = unreal.EditorAssetLibrary.load_asset(MASTER_PATH)
    if m:
        return m
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_GroundWS", GROUND_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary

    wp = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -1200, 0)
    mask = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -1000, 0)
    mask.set_editor_property("r", True)
    mask.set_editor_property("g", True)
    mask.set_editor_property("b", False)
    mask.set_editor_property("a", False)
    tsize = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -1000, 200)
    tsize.set_editor_property("parameter_name", "TileSize")
    tsize.set_editor_property("default_value", 600.0)
    div = mel.create_material_expression(m, unreal.MaterialExpressionDivide, -800, 0)

    base = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, -150)
    base.set_editor_property("parameter_name", "BaseTex")
    norm = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 450)
    norm.set_editor_property("parameter_name", "NormalTex")
    try:
        norm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    except Exception as e:
        log_warn("노멀 샘플러 타입 스킵: %s" % e)

    # 매크로 얼룩: 같은 텍스처를 넓게(x0.07) 한 번 더 샘플 → 무채색 → 밝기 변조
    mscale = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -800, 200)
    mscale.set_editor_property("r", 0.07)
    mdiv = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -700, 150)
    msamp = mel.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 150)
    msamp.set_editor_property("parameter_name", "BaseTex")   # 같은 파라미터 공유
    mdesat = mel.create_material_expression(m, unreal.MaterialExpressionDesaturation, -400, 150)
    dfrac = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -500, 300)
    dfrac.set_editor_property("r", 1.0)
    mstr = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 300)
    mstr.set_editor_property("parameter_name", "MacroStrength")
    mstr.set_editor_property("default_value", 0.35)
    mul1 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -250, 150)
    two = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 420)
    two.set_editor_property("r", 2.0)
    mul2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -150, 200)
    onem = mel.create_material_expression(m, unreal.MaterialExpressionOneMinus, -250, 300)
    add1 = mel.create_material_expression(m, unreal.MaterialExpressionAdd, -50, 150)
    final = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, 50, -50)

    rough = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -150, 500)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.85)

    mel.connect_material_expressions(wp, "", mask, "")
    mel.connect_material_expressions(mask, "", div, "A")
    mel.connect_material_expressions(tsize, "", div, "B")
    mel.connect_material_expressions(div, "", base, "UVs")
    mel.connect_material_expressions(div, "", norm, "UVs")
    mel.connect_material_expressions(div, "", mdiv, "A")
    mel.connect_material_expressions(mscale, "", mdiv, "B")
    mel.connect_material_expressions(mdiv, "", msamp, "UVs")
    mel.connect_material_expressions(msamp, "RGB", mdesat, "")
    mel.connect_material_expressions(dfrac, "", mdesat, "Fraction")
    mel.connect_material_expressions(mdesat, "", mul1, "A")
    mel.connect_material_expressions(mstr, "", mul1, "B")
    mel.connect_material_expressions(mul1, "", mul2, "A")
    mel.connect_material_expressions(two, "", mul2, "B")
    mel.connect_material_expressions(mstr, "", onem, "")
    mel.connect_material_expressions(mul2, "", add1, "A")
    mel.connect_material_expressions(onem, "", add1, "B")
    mel.connect_material_expressions(base, "RGB", final, "A")
    mel.connect_material_expressions(add1, "", final, "B")

    mel.connect_material_property(final, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(norm, "", unreal.MaterialProperty.MP_NORMAL)

    mel.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(MASTER_PATH)
    log("M_GroundWS 마스터 머티리얼 생성")
    return m


def ensure_instance(master, key):
    d_file, n_file, tile, macro, roughv = SURFACES[key]
    path = "%s/MI_Ground_%s" % (GROUND_ROOT, key)
    mic = unreal.EditorAssetLibrary.load_asset(path)
    if mic is None:
        at = unreal.AssetToolsHelpers.get_asset_tools()
        mic = at.create_asset("MI_Ground_%s" % key, GROUND_ROOT,
                              unreal.MaterialInstanceConstant,
                              unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(mic, master)
    mel = unreal.MaterialEditingLibrary
    d_tex = import_tex(d_file, is_normal=False)
    n_tex = import_tex(n_file, is_normal=True)
    if d_tex:
        mel.set_material_instance_texture_parameter_value(mic, "BaseTex", d_tex)
    if n_tex:
        mel.set_material_instance_texture_parameter_value(mic, "NormalTex", n_tex)
    mel.set_material_instance_scalar_parameter_value(mic, "TileSize", tile)
    mel.set_material_instance_scalar_parameter_value(mic, "MacroStrength", macro)
    mel.set_material_instance_scalar_parameter_value(mic, "Roughness", roughv)
    unreal.EditorAssetLibrary.save_asset(path)
    return mic


def main():
    if unreal is None:
        print("[Gyeongbok/s6] unreal 모듈 없음 — UE 에디터에서 실행하세요.")
        return
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # 기존 바닥(우리 것 + s3 임시) 제거
    doomed = set(OLD_LABELS + [p[0] for p in PLANES])
    removed = 0
    for a in subsystem.get_all_level_actors():
        try:
            if a.get_actor_label() in doomed:
                subsystem.destroy_actor(a)
                removed += 1
        except Exception:
            continue
    if removed:
        log("기존 바닥 액터 %d 개 제거" % removed)

    master = ensure_master()
    plane_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    if plane_mesh is None:
        log_warn("기본 Plane 메시를 못 찾음 — 중단")
        return

    for label, key, pos, scale in PLANES:
        mic = ensure_instance(master, key)
        actor = subsystem.spawn_actor_from_object(plane_mesh, unreal.Vector(*pos))
        actor.set_actor_label(label)
        actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], 1.0))
        try:
            actor.static_mesh_component.set_material(0, mic)
        except Exception as e:
            log_warn("%s 머티리얼 배정 실패: %s" % (label, e))
        log("%s 깔림 (%s, %.0fx%.0fm)" % (label, key, scale[0], scale[1]))

    log("바닥 완료 — 마당=박석, 중앙 어도, 바깥=마사토. 레벨 저장(Cmd+S) 잊지 말 것.")


if __name__ == "__main__":
    main()
else:
    main()
