# -*- coding: utf-8 -*-
# 실행법 (에디터 콘솔 Python 모드):
#   exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s7_backdrop.py').read())
#
# s7_backdrop.py — G2+G3: 배경 산세 + 마당 북쪽 회랑 메우기
#   G2: 북악산·인왕산 능선 — 원거리에 넓적한 콘(원뿔) 산체 6기 배치.
#       1.5~2.5km 거리 + 저녁 안개의 대기 원근이 실루엣으로 만들어줌 (웹 능선 레이어의 UE판).
#   G3: 마당 북측 회랑 — 이미 임포트된 서월랑·동월랑 스캔을 복제해 북변(z=-360)에 배치.
#       사정문 스캔(중앙)과 함께 마당 사각을 닫는다. 고증상 '대체 표현'(레지스트리 C 표기).
#   재실행 안전: Backdrop_/North_ 라벨 삭제 후 재생성.

try:
    import unreal
except ImportError:
    unreal = None


GROUND_ROOT = "/Game/Gyeongbok/Ground"
SCANS_ROOT = "/Game/Gyeongbok/Scans"
RIDGE_MAT_PATH = GROUND_ROOT + "/M_Ridge"

# (라벨, UE위치 cm(x=북,y=동), 스케일 m(가로,세로,높이)) — 산 기슭이 멀리 북·서를 두름
MOUNTAINS = [
    ("Backdrop_Bukak_Main", (200000.0, -20000.0), (1800.0, 1400.0, 360.0)),
    ("Backdrop_Bukak_E",    (215000.0,  70000.0), (1500.0, 1200.0, 260.0)),
    ("Backdrop_Bukak_W",    (190000.0, -95000.0), (1400.0, 1100.0, 240.0)),
    ("Backdrop_NE_Far",     (240000.0, 140000.0), (1700.0, 1300.0, 280.0)),
    ("Backdrop_Inwang",     (80000.0, -220000.0), (2200.0, 1600.0, 300.0)),
    ("Backdrop_Inwang_S",   (20000.0, -235000.0), (1600.0, 1200.0, 220.0)),
]

# 북회랑 대체: (라벨, 원본 스캔 폴더, UE위치 cm) — 월랑 52m 를 북변 좌우에
NORTH_FILL = [
    ("North_Wollang_W", "seowollang",  (36000.0, -3300.0, 0.0)),
    ("North_Wollang_E", "dongwollang", (36000.0,  3300.0, 0.0)),
]


def log(msg):
    (unreal.log if unreal else print)("[Gyeongbok/s7] " + msg)


def log_warn(msg):
    (unreal.log_warning if unreal else print)("[Gyeongbok/s7][WARN] " + msg)


def ensure_ridge_material():
    m = unreal.EditorAssetLibrary.load_asset(RIDGE_MAT_PATH)
    if m:
        return m
    at = unreal.AssetToolsHelpers.get_asset_tools()
    m = at.create_asset("M_Ridge", GROUND_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    col = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    try:
        col.set_editor_property("constant", unreal.LinearColor(0.10, 0.13, 0.09, 1.0))  # 짙은 산림
    except Exception as e:
        log_warn("능선 색 설정 스킵: %s" % e)
    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 1.0)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(RIDGE_MAT_PATH)
    log("M_Ridge 생성")
    return m


def first_static_mesh(folder):
    if not unreal.EditorAssetLibrary.does_directory_exist(folder):
        return None
    for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
        obj = unreal.EditorAssetLibrary.load_asset(a)
        if isinstance(obj, unreal.StaticMesh):
            return obj
    return None


def main():
    if unreal is None:
        print("[Gyeongbok/s7] unreal 모듈 없음 — UE 에디터에서 실행하세요.")
        return
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    doomed = set(l for l, _, _ in MOUNTAINS) | set(l for l, _, _ in NORTH_FILL)
    removed = 0
    for a in subsystem.get_all_level_actors():
        try:
            if a.get_actor_label() in doomed:
                subsystem.destroy_actor(a)
                removed += 1
        except Exception:
            continue
    if removed:
        log("재실행: 기존 배경 액터 %d 개 삭제" % removed)

    # ── G2: 산세 ──
    cone = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cone")
    ridge_mat = ensure_ridge_material()
    if cone is None:
        log_warn("기본 Cone 메시 없음 — 산세 생략")
    else:
        for label, (px, py), (sx, sy, sz) in MOUNTAINS:
            # 엔진 Cone 피벗=중앙 → 바닥이 Z=0 에 닿게 높이 절반만큼 올림
            actor = subsystem.spawn_actor_from_object(
                cone, unreal.Vector(px, py, sz * 100.0 / 2.0))
            actor.set_actor_label(label)
            actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
            try:
                actor.static_mesh_component.set_material(0, ridge_mat)
            except Exception as e:
                log_warn("%s 머티리얼 스킵: %s" % (label, e))
            log("%s 배치 (%.0fm 폭, %.0fm 높이)" % (label, sx, sz))

    # ── G3: 북회랑 대체 ──
    for label, folder_name, (px, py, pz) in NORTH_FILL:
        mesh = first_static_mesh("%s/%s" % (SCANS_ROOT, folder_name))
        if mesh is None:
            log_warn("%s: 스캔 '%s' 없음 → 스킵 (s1 먼저)" % (label, folder_name))
            continue
        actor = subsystem.spawn_actor_from_object(mesh, unreal.Vector(px, py, pz))
        actor.set_actor_label(label)
        actor.set_actor_scale3d(unreal.Vector(100.0, 100.0, 100.0))  # 스캔 1:100 → 균일 ×100
        log("%s 배치 (북변 회랑 대체)" % label)

    log("배경 완료 — 노을 안개 속 산세 + 닫힌 마당. 레벨 저장(Cmd+S).")


if __name__ == "__main__":
    main()
else:
    main()
