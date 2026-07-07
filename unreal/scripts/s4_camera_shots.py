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

    # 근정전 부재(승인 대기) 기준 구도 — 마당·회랑·사정문·배경 산세가 주인공.
    # 좌표는 layout 고정값: 마당 중심 UE(29400,0), 사정문 (36200,0), 행각 (29400,±6300).
    subsystem = get_actor_subsystem()
    delete_actors_by_labels(subsystem, CAM_LABELS)

    # ① 동행각 로우앵글 — 노을(서쪽 광원)을 정면으로 받는 회랑의 원근
    pos1 = unreal.Vector(23500.0, -1500.0, 1.7 * M)
    tgt1 = unreal.Vector(32000.0, 6300.0, 6.0 * M)
    spawn_camera(subsystem, "Cam_SW_LowAngle", pos1, tgt1, focal_mm=32.0, aperture=5.6)

    # ② 어도 축선 아이레벨 — 어도를 따라 북쪽 사정문(+배경 북악산)으로
    pos2 = unreal.Vector(22900.0, 0.0, 1.6 * M)
    tgt2 = unreal.Vector(36200.0, 0.0, 5.0 * M)
    spawn_camera(subsystem, "Cam_Eodo_Eye", pos2, tgt2, focal_mm=40.0, aperture=8.0)

    # ③ 남서 상공 부감 — 박석 마당 전체 + 회랑 사각 + 경회루·산세
    pos3 = unreal.Vector(24000.0, -7500.0, 18.0 * M)
    tgt3 = unreal.Vector(30000.0, 500.0, 0.0)
    spawn_camera(subsystem, "Cam_Woldae_High", pos3, tgt3, focal_mm=24.0, aperture=8.0)

    log("카메라 3대 배치 완료(마당 기준 구도). 근정전 도착 후엔 구도 재조준 예정.")
    log("촬영: 카메라 선택 → 뷰포트 우클릭 'xx로 파일럿' → 콘솔(Cmd모드) HighResShot 3840x2160")


if __name__ == "__main__":
    main()
else:
    main()
