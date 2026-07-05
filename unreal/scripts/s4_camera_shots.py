# -*- coding: utf-8 -*-
# 실행법 (3가지 중 택1):
#   에디터 콘솔(Python 모드):  exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s4_camera_shots.py').read())
#   에디터 콘솔(Cmd 모드):     py "/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s4_camera_shots.py"
#   헤드리스 CLI:              <UE>/UnrealEditor-Cmd <프로젝트>.uproject -run=pythonscript -script="/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s4_camera_shots.py"
#
# s4_camera_shots.py
#   시네마틱 스틸용 CineCameraActor 3대 배치. 위치는 layout 좌표계 기준으로 계산.
#   방위(convention): UE +X=북, +Y=동, +Z=up  →  북=+X, 남=-X, 동=+Y, 서=-Y.
#   경복궁 근정전은 남향, 마당은 근정전 남쪽에 펼쳐진다는 배치를 전제로 카메라를 잡는다.
#     ① Cam_SW_LowAngle : 마당 남서 모서리, 로우앵글, 근정전(북쪽) 방향
#     ② Cam_Eodo_Eye    : 어도(중앙축) 정면, 아이레벨(1.6m), 근정전 정면
#     ③ Cam_Woldae_High : 월대(근정전 앞 기단) 위에서 마당 부감(내려다봄)
#   재실행 안전: 아래 CAM_LABELS 라벨 기존 카메라 삭제 후 재배치.
#
# ── 파이썬으로 자동화 못 하는 것(수동) ──────────────────────────────────────────
#   [ ] 실제 촬영: 각 카메라 선택 → 뷰포트에서 우클릭 "Pilot" 또는 오른쪽 상단 카메라 아이콘으로 시점 진입
#   [ ] High Resolution Screenshot: 뷰포트 좌상단 메뉴 ▸ High Resolution Screenshot (배율 2~4x)
#       또는 콘솔 명령:  HighResShot 3840x2160
#   [ ] 노출/포커스 미세조정은 카메라 디테일 패널에서 눈으로 확인하며 조정

import json
import math
import os

try:
    import unreal
except ImportError:
    unreal = None


LAYOUT_JSON = os.environ.get(
    "GYEONGBOK_LAYOUT",
    "/Users/junkim/projects/gyeongbok-timewalk/unreal/layout_1888.json",
)
CAM_LABELS = ["Cam_SW_LowAngle", "Cam_Eodo_Eye", "Cam_Woldae_High"]
M = 100.0  # 미터 -> cm


def log(msg):
    if unreal:
        unreal.log("[Gyeongbok/s4] " + msg)
    else:
        print("[Gyeongbok/s4] " + msg)


def log_warn(msg):
    if unreal:
        unreal.log_warning("[Gyeongbok/s4] " + msg)
    else:
        print("[Gyeongbok/s4][WARN] " + msg)


def log_error(msg):
    if unreal:
        unreal.log_error("[Gyeongbok/s4] " + msg)
    else:
        print("[Gyeongbok/s4][ERROR] " + msg)


# ---------------------------------------------------------------------------
# layout 로드 + 좌표 변환
# ---------------------------------------------------------------------------
def load_buildings(path):
    if not os.path.isfile(path):
        raise IOError("layout JSON 을 찾을 수 없음: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    buildings = data.get("buildings")
    if not isinstance(buildings, list) or not buildings:
        raise ValueError("layout JSON 에 'buildings' 가 비어있음")

    valid = []
    for i, b in enumerate(buildings):
        pos = b.get("pos")
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            log_warn("buildings[%d] pos 형식 오류 → 스킵" % i)
            continue
        # UE 좌표(cm): X=-z*100(북+), Y=x*100(동+)
        ue_x = -float(pos[1]) * M
        ue_y = float(pos[0]) * M
        valid.append({
            "name": b.get("name", "b%d" % i),
            "ue_x": ue_x,
            "ue_y": ue_y,
            "targetLenM": float(b.get("targetLenM", 0.0)),
        })
    if not valid:
        raise ValueError("유효한 building 이 없음")
    return valid


# ---------------------------------------------------------------------------
# 수학 헬퍼 (unreal 유틸 우선, 실패 시 순수 파이썬 폴백)
# ---------------------------------------------------------------------------
def look_at_rotation(cam_pos, target):
    try:
        return unreal.MathLibrary.find_look_at_rotation(cam_pos, target)
    except Exception:
        dx = target.x - cam_pos.x
        dy = target.y - cam_pos.y
        dz = target.z - cam_pos.z
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
        return unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def distance_cm(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def get_actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def delete_actors_by_labels(subsystem, labels):
    label_set = set(labels)
    removed = 0
    for a in subsystem.get_all_level_actors():
        try:
            if a.get_actor_label() in label_set:
                subsystem.destroy_actor(a)
                removed += 1
        except Exception as e:
            log_warn("카메라 삭제 예외: %s" % e)
    if removed:
        log("재실행: 기존 카메라 %d 개 삭제" % removed)


# ---------------------------------------------------------------------------
# 마당 지오메트리 추정
# ---------------------------------------------------------------------------
def compute_geometry(buildings):
    # hero = 긴 축(targetLenM) 최대 건물 = 근정전으로 가정. 전부 0이면 최북단(max ue_x).
    hero = max(buildings, key=lambda b: (b["targetLenM"], b["ue_x"]))
    xs_min = min(b["ue_x"] for b in buildings)  # 최남단(작을수록 남쪽)
    ys_min = min(b["ue_y"] for b in buildings)  # 최서단
    ys_max = max(b["ue_y"] for b in buildings)  # 최동단

    hero_x, hero_y = hero["ue_x"], hero["ue_y"]
    hero_half = max(hero["targetLenM"] * M * 0.5, 10.0 * M)  # 근정전 반폭(footprint 근사)

    # 마당 깊이: 건물 남북 퍼짐 vs 최소 120m
    spread_south = hero_x - xs_min
    depth = max(spread_south, 120.0 * M)
    south_edge_x = hero_x - depth

    # 마당 폭: 건물 동서 퍼짐 vs 최소 100m
    spread_ew = ys_max - ys_min
    half_width = max(spread_ew * 0.5, 50.0 * M)

    axis_y = hero_y                      # 중앙축(어도) = 근정전 중심 Y
    hero_south_face_x = hero_x - hero_half

    return {
        "hero": hero,
        "hero_x": hero_x,
        "hero_y": hero_y,
        "hero_half": hero_half,
        "hero_south_face_x": hero_south_face_x,
        "south_edge_x": south_edge_x,
        "depth": depth,
        "axis_y": axis_y,
        "west_edge_y": axis_y - half_width,
    }


# ---------------------------------------------------------------------------
# 카메라 생성
# ---------------------------------------------------------------------------
def spawn_camera(subsystem, label, pos, target, focal_mm, aperture=8.0):
    rotation = look_at_rotation(pos, target)
    cam = subsystem.spawn_actor_from_class(unreal.CineCameraActor, pos, rotation)
    cam.set_actor_label(label)

    try:
        comp = cam.get_cine_camera_component()
    except Exception:
        comp = cam.get_component_by_class(unreal.CineCameraComponent)

    if comp:
        try:
            comp.set_editor_property("current_focal_length", float(focal_mm))
            comp.set_editor_property("current_aperture", float(aperture))
        except Exception as e:
            log_warn("%s 렌즈 프로퍼티 스킵: %s" % (label, e))
        # 매뉴얼 포커스 = 타깃까지 거리
        try:
            focus = comp.get_editor_property("focus_settings")
            focus.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
            focus.set_editor_property("manual_focus_distance", distance_cm(pos, target))
            comp.set_editor_property("focus_settings", focus)
        except Exception as e:
            log_warn("%s 포커스 설정 스킵: %s" % (label, e))

    log("%s  pos=(%.0f,%.0f,%.0f)  %.0fmm f/%.1f" %
        (label, pos.x, pos.y, pos.z, focal_mm, aperture))
    return cam


def main():
    if unreal is None:
        print("[Gyeongbok/s4] unreal 모듈 없음 — UE 에디터/헤드리스에서 실행하세요.")
        return

    buildings = load_buildings(LAYOUT_JSON)
    g = compute_geometry(buildings)
    log("hero(근정전 추정)='%s'  south_edge_x=%.0f  axis_y=%.0f  depth=%.0fm"
        % (g["hero"]["name"], g["south_edge_x"], g["axis_y"], g["depth"] / M))

    subsystem = get_actor_subsystem()
    delete_actors_by_labels(subsystem, CAM_LABELS)

    # ① 남서 모서리, 로우앵글, 근정전 방향
    pos1 = unreal.Vector(g["south_edge_x"] + 5 * M, g["west_edge_y"], 2.0 * M)
    tgt1 = unreal.Vector(g["hero_x"], g["hero_y"], 8.0 * M)
    spawn_camera(subsystem, "Cam_SW_LowAngle", pos1, tgt1, focal_mm=24.0, aperture=8.0)

    # ② 어도 정면, 아이레벨, 근정전 정면
    pos2 = unreal.Vector(g["south_edge_x"] + 10 * M, g["axis_y"], 1.6 * M)
    tgt2 = unreal.Vector(g["hero_south_face_x"], g["axis_y"], 6.0 * M)
    spawn_camera(subsystem, "Cam_Eodo_Eye", pos2, tgt2, focal_mm=35.0, aperture=8.0)

    # ③ 월대(근정전 앞 기단) 위에서 마당 부감
    pos3 = unreal.Vector(g["hero_south_face_x"] - 8 * M, g["axis_y"], 4.0 * M)
    tgt3 = unreal.Vector(g["south_edge_x"] + g["depth"] * 0.45, g["axis_y"], 0.0)
    spawn_camera(subsystem, "Cam_Woldae_High", pos3, tgt3, focal_mm=28.0, aperture=8.0)

    log("카메라 3대 배치 완료. 촬영은 수동(상단 주석: Pilot + HighResShot 3840x2160).")


if __name__ == "__main__":
    main()
else:
    main()
