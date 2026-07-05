# -*- coding: utf-8 -*-
# 실행법 (3가지 중 택1):
#   에디터 콘솔(Python 모드):  exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s2_layout_level.py').read())
#   에디터 콘솔(Cmd 모드):     py "/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s2_layout_level.py"
#   헤드리스 CLI:              <UE>/UnrealEditor-Cmd <프로젝트>.uproject -run=pythonscript -script="/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s2_layout_level.py"
#
# s2_layout_level.py
#   /Game/Gyeongbok/Scans/<name> 의 StaticMesh 를 현재 레벨에 StaticMeshActor 로 배치한다.
#   - JSON 좌표 [x,z](m) -> UE 좌표: UE.X = -z*100, UE.Y = x*100  (x=동, z=남; UE +X=북,+Y=동,+Z=up)
#   - 바운딩박스 긴 축(수평)을 targetLenM 에 맞춰 균일 스케일
#   - 바운딩박스 최저점 Z 가 0, 수평 중심이 목표 좌표에 오도록 배치(원점 제각각 대비)
#   - yawDeg 적용, 액터 라벨 = name
#   - 재실행 시 같은 라벨 액터 삭제 후 재스폰(중복 방지)

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


def log(msg):
    if unreal:
        unreal.log("[Gyeongbok/s2] " + msg)
    else:
        print("[Gyeongbok/s2] " + msg)


def log_warn(msg):
    if unreal:
        unreal.log_warning("[Gyeongbok/s2] " + msg)
    else:
        print("[Gyeongbok/s2][WARN] " + msg)


def log_error(msg):
    if unreal:
        unreal.log_error("[Gyeongbok/s2] " + msg)
    else:
        print("[Gyeongbok/s2][ERROR] " + msg)


# ---------------------------------------------------------------------------
# layout 로드 + 검증
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
        pos = b.get("pos")
        if not name or not isinstance(pos, (list, tuple)) or len(pos) != 2:
            log_warn("buildings[%d] name/pos 형식 오류 → 스킵" % i)
            continue
        valid.append({
            "name": name,
            "pos": [float(pos[0]), float(pos[1])],
            "yawDeg": float(b.get("yawDeg", 0.0)),
            "targetLenM": float(b.get("targetLenM", 0.0)),
        })
    return valid


# ---------------------------------------------------------------------------
# 좌표 변환 / 에디터 서브시스템 / 에셋 디스커버리
# ---------------------------------------------------------------------------
def to_ue_location(pos_xz):
    """[x(동,m), z(남,m)] -> unreal.Vector(cm).  UE.X=-z*100, UE.Y=x*100."""
    x, z = pos_xz[0], pos_xz[1]
    return unreal.Vector(-z * 100.0, x * 100.0, 0.0)


def get_actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def find_static_mesh(folder):
    try:
        if not unreal.EditorAssetLibrary.does_directory_exist(folder):
            return None
        for a in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
            obj = unreal.EditorAssetLibrary.load_asset(a)
            if isinstance(obj, unreal.StaticMesh):
                return obj
    except Exception as e:
        log_warn("find_static_mesh(%s) 실패: %s" % (folder, e))
    return None


def get_bounds(actor):
    """(origin, box_extent) 반환. 버전별 시그니처 방어."""
    try:
        return actor.get_actor_bounds(False)
    except Exception:
        return actor.get_actor_bounds(False, False)


def delete_actors_by_labels(subsystem, labels):
    label_set = set(labels)
    removed = 0
    for a in subsystem.get_all_level_actors():
        try:
            if a.get_actor_label() in label_set:
                subsystem.destroy_actor(a)
                removed += 1
        except Exception as e:
            log_warn("액터 삭제 중 예외: %s" % e)
    if removed:
        log("재실행: 기존 액터 %d 개 삭제" % removed)


# ---------------------------------------------------------------------------
# 배치
# ---------------------------------------------------------------------------
def place_building(subsystem, b):
    name = b["name"]
    folder = "%s/%s" % (DEST_ROOT, name)
    mesh = find_static_mesh(folder)
    if mesh is None:
        log_error("[스킵] '%s' StaticMesh 없음 (%s) — s1 먼저 실행?" % (name, folder))
        return False

    target = to_ue_location(b["pos"])
    yaw = b["yawDeg"]
    rotation = unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw)

    # 1) 원점에 회전 적용해 스폰
    actor = subsystem.spawn_actor_from_object(mesh, unreal.Vector(0.0, 0.0, 0.0), rotation)
    if actor is None:
        log_error("[실패] '%s' 스폰 실패" % name)
        return False
    actor.set_actor_label(name)

    # 2) 회전 반영된 바운딩박스로 긴 축(수평) 측정 -> 균일 스케일
    _, extent = get_bounds(actor)
    full_x = extent.x * 2.0
    full_y = extent.y * 2.0
    long_axis = max(full_x, full_y)
    target_len_cm = b["targetLenM"] * 100.0
    if long_axis > 1e-3 and target_len_cm > 1e-3:
        scale = target_len_cm / long_axis
    else:
        scale = 1.0
        log_warn("'%s' 스케일 계산 불가(long=%.3f, target=%.3f) — 1.0 사용"
                 % (name, long_axis, target_len_cm))
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))

    # 3) 스케일 반영된 바운딩박스로 재배치: 수평중심=목표, 바닥 Z=0
    origin, extent = get_bounds(actor)
    delta_x = target.x - origin.x
    delta_y = target.y - origin.y
    delta_z = extent.z - origin.z  # 최저점(origin.z - extent.z) 을 0 으로
    actor.set_actor_location(unreal.Vector(delta_x, delta_y, delta_z), False, True)

    log("[배치] '%s'  loc=(%.0f, %.0f) scale=%.4f yaw=%.1f  (긴축 %.2fm→%.2fm)"
        % (name, target.x, target.y, scale, yaw, long_axis / 100.0, b["targetLenM"]))
    return True


def main():
    if unreal is None:
        print("[Gyeongbok/s2] unreal 모듈 없음 — UE 에디터/헤드리스에서 실행하세요.")
        return

    buildings = load_buildings(LAYOUT_JSON)
    log("배치 대상 %d 개 (layout=%s)" % (len(buildings), LAYOUT_JSON))

    subsystem = get_actor_subsystem()

    # 재실행 안전: 같은 라벨 먼저 제거
    delete_actors_by_labels(subsystem, [b["name"] for b in buildings])

    placed = 0
    for b in buildings:
        try:
            if place_building(subsystem, b):
                placed += 1
        except Exception as e:
            log_error("[예외] '%s' 배치 실패: %s" % (b["name"], e))

    log("요약: 배치 %d / %d" % (placed, len(buildings)))
    log("레벨 저장은 수동으로: File > Save Current Level")


if __name__ == "__main__":
    main()
else:
    main()
