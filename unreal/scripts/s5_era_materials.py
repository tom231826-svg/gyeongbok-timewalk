# -*- coding: utf-8 -*-
# 실행법:
#   에디터 콘솔(Python 모드):  exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s5_era_materials.py').read())
#     → 실행되면 기본 1888로 적용됨. 이후 콘솔에서 시대만 바꿔 재적용:  set_era(1929)   set_era(2026)   set_era(1888)
#
# s5_era_materials.py  —  "시대 전환" 드라이런
#   s1/s2 로 임포트·배치된 실측 스캔 메시의 표면 텍스처를 시대별 파생본으로 교체한다.
#   2026=FBX 임포트 원본 머티리얼 복원(8K, 낡음) / 1888=선명(갓 칠한 단청) / 1929=퇴색.
#   1888/1929 텍스처는 웹 작업 때 이미 만들어 둔 것 재사용:
#     1888  : ~/projects/gyeongbok-timewalk/prototype/assets/scans_csp/era1888/<file>.jpg
#     1929  : .../scans_csp/era1929/<file>.jpg
#   (2026 은 파일 임포트 없음 — 스캔 폴더의 원본 머티리얼로 되돌림. 원본을 못 찾을 때만 웹 2K 로 폴백)
#
#   방식: 파라미터화된 마스터 머티리얼 M_EraScan(Base 텍스처 파라미터) 1개를 만들고,
#         건물·시대별 MaterialInstanceConstant 를 만들어 메시 슬롯에 배정.
#         imported FBX 머티리얼을 직접 건드리지 않아 안전하고, 시대 스왑이 파라미터 교체로 끝난다.
#
#   ⚠ 첫 실행에서 오류가 나면 Output Log 를 캡처해서 보내면 API 를 맞춰 고칠 수 있음
#      (UE 버전별로 머티리얼 그래프 API 시그니처가 조금 다름).

import os

try:
    import unreal
except ImportError:
    unreal = None

SCANS_ROOT = "/Game/Gyeongbok/Scans"
MAT_ROOT = "/Game/Gyeongbok/Mat"
TEX_ROOT = "/Game/Gyeongbok/EraTex"
FS_TEX = "/Users/junkim/projects/gyeongbok-timewalk/prototype/assets/scans_csp"

# 건물 → { 머티리얼슬롯이름에 포함된 키 : 텍스처파일명 }  (근거: build_v2.py 의 [MAT] 로그)
MATS = {
    "seowollang":    {"GJM_W_WR": "seowollang_tex0.jpg"},
    "dongwollang":   {"GJM_E_WR": "dongwollang_tex0.jpg"},
    "donghaenggak":  {"GJM_E_HG_in1": "donghaenggak_tex1.jpg", "GJM_E_HG": "donghaenggak_tex0.jpg"},
    "seohaenggak":   {"GJM_W_HG": "seohaenggak_tex0.jpg", "서행각": "seohaenggak_tex1.jpg"},
    "heung_e":       {"HRM_E_HG": "heung_e_tex0.jpg"},
    "heung_w":       {"HRM_W_HG": "heung_w_tex0.jpg"},
    "sajeongmun":    {"SJM": "sajeongmun_tex0.jpg"},
    "gyeonghoeru":   {"GHR_L": "gyeonghoeru_tex0.jpg"},
    "gangnyeongjeon": {"GNJ_in": "gangnyeongjeon_tex1.jpg", "원본": "gangnyeongjeon_tex0.jpg"},
}


def log(msg):
    (unreal.log if unreal else print)("[Gyeongbok/s5] " + msg)


def log_warn(msg):
    (unreal.log_warning if unreal else print)("[Gyeongbok/s5][WARN] " + msg)


def era_dir(era):
    return {"1888": "era1888", "1929": "era1929", "2026": ""}[str(era)]


def era_fs_path(era, fname):
    d = era_dir(era)
    return os.path.join(FS_TEX, d, fname) if d else os.path.join(FS_TEX, fname)


# ─────────────────────────── 텍스처 임포트 ───────────────────────────
def import_texture(era, fname):
    """디스크의 시대 텍스처를 /Game/Gyeongbok/EraTex/E<era>/<name> 로 임포트(있으면 재사용)."""
    src = era_fs_path(era, fname)
    if not os.path.isfile(src):
        log_warn("텍스처 없음: %s" % src)
        return None
    asset_name = os.path.splitext(fname)[0] + "_E" + str(era)
    dest_dir = "%s/E%s" % (TEX_ROOT, era)
    dest = "%s/%s" % (dest_dir, asset_name)
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        return unreal.EditorAssetLibrary.load_asset(dest)
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = dest_dir
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    except Exception as e:
        log_warn("텍스처 임포트 실패 %s: %s" % (fname, e))
        return None
    return unreal.EditorAssetLibrary.load_asset(dest) if unreal.EditorAssetLibrary.does_asset_exist(dest) else None


# ─────────────────────────── 마스터 머티리얼 ───────────────────────────
def ensure_master():
    """Base 텍스처 파라미터를 BaseColor 에 연결한 마스터 머티리얼 1개(있으면 재사용)."""
    path = "%s/M_EraScan" % MAT_ROOT
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset("M_EraScan", MAT_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    try:
        mel = unreal.MaterialEditingLibrary
        base = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -400, 0)
        base.set_editor_property("parameter_name", "Base")
        mel.connect_material_property(base, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -400, 250)
        rough.set_editor_property("parameter_name", "Roughness")
        rough.set_editor_property("default_value", 0.85)
        mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
        mel.recompile_material(mat)
    except Exception as e:
        log_warn("마스터 머티리얼 그래프 구성 실패(수동 확인 필요): %s" % e)
    unreal.EditorAssetLibrary.save_asset(path)
    log("마스터 머티리얼 생성: %s" % path)
    return mat


def ensure_instance(master, bldg, era, key, tex):
    """건물·시대·슬롯별 MaterialInstanceConstant (있으면 파라미터만 갱신)."""
    name = "MI_%s_%s_E%s" % (bldg, key.replace(" ", ""), era)
    dest_dir = "%s/Inst" % MAT_ROOT
    dest = "%s/%s" % (dest_dir, name)
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        mic = unreal.EditorAssetLibrary.load_asset(dest)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mic = tools.create_asset(name, dest_dir, unreal.MaterialInstanceConstant,
                                 unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(mic, master)
    if tex:
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mic, "Base", tex)
    unreal.EditorAssetLibrary.save_asset(dest)
    return mic


# ─────────────────────────── 메시·원본 머티리얼 검색 ───────────────────────────
def find_static_mesh(folder):
    if not unreal.EditorAssetLibrary.does_directory_exist(folder):
        return None
    for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
        obj = unreal.EditorAssetLibrary.load_asset(a)
        if isinstance(obj, unreal.StaticMesh):
            return obj
    return None


def find_original_material(folder, key):
    """스캔 폴더 안의 FBX 임포트 원본 머티리얼(이름에 key 포함). 우리가 만든 MI_/M_Era 는 제외.
    key 매칭 실패 시 폴더의 아무 원본 머티리얼(단일 재질 건물용)로 폴백."""
    if not unreal.EditorAssetLibrary.does_directory_exist(folder):
        return None
    fallback = None
    for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
        obj = unreal.EditorAssetLibrary.load_asset(a)
        if not isinstance(obj, unreal.MaterialInterface):
            continue
        nm = obj.get_name()
        if nm.startswith("MI_") or nm.startswith("M_Era"):
            continue
        if key in nm:
            return obj
        if fallback is None:
            fallback = obj
    return fallback


def assign_to_mesh(mesh, slot_key, mic, claimed):
    """머티리얼 슬롯 이름에 slot_key 가 포함된 슬롯에 mic 배정. 매칭 슬롯 수 반환.
    claimed: 이번 시대 적용에서 이미 배정된 슬롯 인덱스 집합 — 키 이름이 겹칠 때
    (예: 'GJM_E_HG' ⊂ 'GJM_E_HG_in1') 먼저 배정된 슬롯을 덮어쓰지 않게 함."""
    n = 0
    try:
        slots = mesh.get_editor_property("static_materials")
        for i, sm in enumerate(slots):
            if i in claimed:
                continue
            sname = str(sm.material_slot_name)
            iname = ""
            try:
                iname = sm.material_interface.get_name() if sm.material_interface else ""
            except Exception:
                pass
            if slot_key in sname or slot_key in iname:
                try:
                    mesh.set_material(i, mic)   # UE5 StaticMesh.set_material(index, material)
                except Exception:
                    sm.material_interface = mic
                claimed.add(i)
                n += 1
        if n == 0 and len(slots) == 1 and 0 not in claimed:   # 슬롯 이름 매칭 실패 + 슬롯 1개면 그냥 배정
            try:
                mesh.set_material(0, mic)
            except Exception:
                slots[0].material_interface = mic
            claimed.add(0)
            n = 1
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    except Exception as e:
        log_warn("메시 머티리얼 배정 실패: %s" % e)
    return n


# ─────────────────────────── 메인 ───────────────────────────
def set_era(era):
    """era = 1888 | 1929 | 2026 . 전 스캔 표면을 그 시대로 교체."""
    if unreal is None:
        print("[Gyeongbok/s5] unreal 모듈 없음 — UE 에디터에서 실행하세요.")
        return
    era = str(era)
    if era not in ("1888", "1929", "2026"):
        log_warn("era 는 1888/1929/2026 중 하나. 받은 값: %s" % era)
        return
    master = ensure_master()
    applied = 0
    for bldg, keymap in MATS.items():
        folder = "%s/%s" % (SCANS_ROOT, bldg)
        mesh = find_static_mesh(folder)
        if mesh is None:
            continue   # 이 빌드/드라이런에 임포트 안 된 건물은 조용히 스킵
        claimed = set()
        # 키 이름이 겹칠 수 있어 긴 키부터 배정 (예: GJM_E_HG_in1 → GJM_E_HG 순)
        for key in sorted(keymap, key=len, reverse=True):
            fname = keymap[key]
            if era == "2026":
                orig = find_original_material(folder, key)
                if orig is not None:
                    applied += assign_to_mesh(mesh, key, orig, claimed)
                    continue
                log_warn("'%s' 원본 머티리얼 못 찾음 → 웹 2K 텍스처로 폴백" % bldg)
            tex = import_texture(era, fname)
            if tex is None:
                continue
            mic = ensure_instance(master, bldg, era, key, tex)
            applied += assign_to_mesh(mesh, key, mic, claimed)
    log("시대 %s 적용 완료 — 머티리얼 슬롯 %d 개 교체" % (era, applied))
    log("다른 시대로 바꾸려면 콘솔에서:  set_era(1929)   set_era(2026)   set_era(1888)")


# 실행 시 기본 1888 (환경변수 GYEONGBOK_ERA 로 덮어쓰기 가능)
if unreal is not None:
    set_era(os.environ.get("GYEONGBOK_ERA", "1888"))
