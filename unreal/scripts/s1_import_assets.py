# -*- coding: utf-8 -*-
# 실행법 (3가지 중 택1):
#   에디터 콘솔(Python 모드):  exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s1_import_assets.py').read())
#   에디터 콘솔(Cmd 모드):     py "/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s1_import_assets.py"
#   헤드리스 CLI:              <UE>/UnrealEditor-Cmd <프로젝트>.uproject -run=pythonscript -script="/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s1_import_assets.py"
#
# s1_import_assets.py
#   layout_1888.json 의 각 FBX 를 /Game/Gyeongbok/Scans/<name> 폴더로 임포트한다.
#   - Nanite 활성(build_nanite=True), 라이트맵 UV 생성 OFF, 머티리얼+임베디드 텍스처 임포트, combine_meshes=True
#   - 이미 임포트된 건물은 스킵(재실행 안전). 진행 로그 출력.
#
#   참고: AssetImportTask + FbxImportUI 경로는 UE 5.6 에서도 동작하는 레거시 FBX 임포터를 강제한다.
#         (Interchange 기본 경로보다 스크립트 제어가 예측 가능하다.) 임베디드 텍스처는 이 경로로 함께 들어온다.

import json
import os

try:
    import unreal
except ImportError:
    unreal = None


LAYOUT_JSON = os.environ.get(
    "GYEONGBOK_LAYOUT",
    "/Users/junkim/projects/gyeongbok-timewalk/unreal/layout_1888.json",
)
DEST_ROOT = "/Game/Gyeongbok/Scans"


# ---------------------------------------------------------------------------
# 로깅 (unreal 없을 때도 안전)
# ---------------------------------------------------------------------------
def log(msg):
    if unreal:
        unreal.log("[Gyeongbok/s1] " + msg)
    else:
        print("[Gyeongbok/s1] " + msg)


def log_warn(msg):
    if unreal:
        unreal.log_warning("[Gyeongbok/s1] " + msg)
    else:
        print("[Gyeongbok/s1][WARN] " + msg)


def log_error(msg):
    if unreal:
        unreal.log_error("[Gyeongbok/s1] " + msg)
    else:
        print("[Gyeongbok/s1][ERROR] " + msg)


# ---------------------------------------------------------------------------
# layout JSON 로드 + 스키마 검증 (경계에서 입력 검증)
# ---------------------------------------------------------------------------
def load_buildings(path):
    if not os.path.isfile(path):
        raise IOError("layout JSON 을 찾을 수 없음: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    buildings = data.get("buildings")
    if not isinstance(buildings, list):
        raise ValueError("layout JSON 에 'buildings' 배열이 없음")

    valid = []
    for i, b in enumerate(buildings):
        name = b.get("name")
        fbx = b.get("fbx")
        if not name or not fbx:
            log_warn("buildings[%d] name/fbx 누락 → 스킵" % i)
            continue
        if not os.path.isfile(fbx):
            log_warn("'%s' FBX 경로 없음 → 스킵: %s" % (name, fbx))
            continue
        valid.append({"name": name, "fbx": fbx})
    return valid


# ---------------------------------------------------------------------------
# 에셋 존재/디스커버리 헬퍼
# ---------------------------------------------------------------------------
def list_static_meshes(folder):
    """folder(패키지경로) 안의 StaticMesh 에셋 경로 목록."""
    found = []
    try:
        if not unreal.EditorAssetLibrary.does_directory_exist(folder):
            return found
        for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
            obj = unreal.EditorAssetLibrary.load_asset(a)
            if isinstance(obj, unreal.StaticMesh):
                found.append(a)
    except Exception as e:
        log_warn("list_static_meshes(%s) 실패: %s" % (folder, e))
    return found


# ---------------------------------------------------------------------------
# FBX 임포트 옵션
# ---------------------------------------------------------------------------
def build_import_options():
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)

    smid = options.get_editor_property("static_mesh_import_data")
    smid.set_editor_property("combine_meshes", True)
    smid.set_editor_property("generate_lightmap_u_vs", False)
    # 스캔 원본의 자잘한 트랜스폼을 흡수(원점 제각각 대비)
    try:
        smid.set_editor_property("import_translation", unreal.Vector(0.0, 0.0, 0.0))
        smid.set_editor_property("import_uniform_scale", 1.0)
    except Exception as e:
        log_warn("import transform 프로퍼티 설정 스킵: %s" % e)
    # Nanite: 임포트 단계에서 빌드 (버전에 따라 프로퍼티명이 없을 수 있어 방어)
    try:
        smid.set_editor_property("build_nanite", True)
    except Exception as e:
        log_warn("build_nanite 임포트 옵션 미지원(임포트 후 폴백 사용): %s" % e)
    options.set_editor_property("static_mesh_import_data", smid)
    return options


def make_task(fbx_path, dest_path, options):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx_path)
    task.set_editor_property("destination_path", dest_path)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("automated", True)  # 다이얼로그 없이
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    return task


# ---------------------------------------------------------------------------
# Nanite 폴백: 임포트 옵션이 안 먹은 경우 에셋에서 직접 활성
# ---------------------------------------------------------------------------
def ensure_nanite(mesh_path):
    try:
        mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
        if not isinstance(mesh, unreal.StaticMesh):
            return
        ns = mesh.get_editor_property("nanite_settings")
        if not ns.get_editor_property("enabled"):
            ns.set_editor_property("enabled", True)
            mesh.set_editor_property("nanite_settings", ns)
            unreal.EditorAssetLibrary.save_asset(mesh_path)
            log("  Nanite 폴백 활성: %s" % mesh_path)
    except Exception as e:
        log_warn("  Nanite 폴백 실패(%s): %s" % (mesh_path, e))


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main():
    if unreal is None:
        print("[Gyeongbok/s1] unreal 모듈 없음 — UE 에디터/헤드리스에서 실행하세요.")
        return

    buildings = load_buildings(LAYOUT_JSON)
    log("임포트 대상 %d 개 (layout=%s)" % (len(buildings), LAYOUT_JSON))

    options = build_import_options()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    imported, skipped, failed = 0, 0, 0
    for b in buildings:
        name = b["name"]
        dest = "%s/%s" % (DEST_ROOT, name)

        existing = list_static_meshes(dest)
        if existing:
            log("[스킵] '%s' 이미 존재 (%s)" % (name, existing[0]))
            skipped += 1
            continue

        log("[임포트] '%s'  <-  %s" % (name, b["fbx"]))
        task = make_task(b["fbx"], dest, options)
        try:
            asset_tools.import_asset_tasks([task])
        except Exception as e:
            log_error("[실패] '%s' 임포트 예외: %s" % (name, e))
            failed += 1
            continue

        meshes = list_static_meshes(dest)
        if not meshes:
            log_error("[실패] '%s' 임포트 후 StaticMesh 를 찾지 못함" % name)
            failed += 1
            continue
        for mp in meshes:
            ensure_nanite(mp)
        log("[완료] '%s' -> %s" % (name, meshes[0]))
        imported += 1

    log("요약: 임포트 %d / 스킵 %d / 실패 %d" % (imported, skipped, failed))
    log("다음 단계: s2_layout_level.py 로 레벨에 배치")


if __name__ == "__main__":
    main()
else:
    # 에디터 콘솔에서 exec() 로 불러도 실행되도록
    main()
