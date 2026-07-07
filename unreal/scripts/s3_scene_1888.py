# -*- coding: utf-8 -*-
# 실행법 (3가지 중 택1):
#   에디터 콘솔(Python 모드):  exec(open('/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s3_scene_1888.py').read())
#   에디터 콘솔(Cmd 모드):     py "/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s3_scene_1888.py"
#   헤드리스 CLI:              <UE>/UnrealEditor-Cmd <프로젝트>.uproject -run=pythonscript -script="/Users/junkim/projects/gyeongbok-timewalk/unreal/scripts/s3_scene_1888.py"
#
# s3_scene_1888.py
#   1888년 늦은 오후(노을) 분위기 셋업: DirectionalLight(서쪽 저녁 태양), SkyAtmosphere,
#   SkyLight(리얼타임 캡처), ExponentialHeightFog(옅은 주황 헤이즈), PostProcessVolume(무한),
#   그리고 임시 바닥 Plane(600m×600m, 마당 중심).
#   템플릿 맵 정리: 맵에 딸려온 기본 태양·하늘·안개는 삭제(태양 2개 방지),
#   사막 Landscape 는 숨김(삭제 아님 — 되돌리기 가능).
#   재실행 안전: 아래 SCENE_LABELS 라벨의 기존 액터를 삭제 후 재생성.
#
# ── 파이썬으로 자동화 못 하는 것(수동 체크리스트) ────────────────────────────────
#   [ ] Project Settings > Rendering > Global Illumination = Lumen  (PPV 로도 걸지만 프로젝트 기본값 권장)
#   [ ] Project Settings > Rendering > Reflections = Lumen
#   [ ] Project Settings > Rendering > Shadow Maps = Virtual Shadow Maps (Nanite 그림자 품질)
#   [ ] Project Settings > Rendering > Generate Mesh Distance Fields = ON  (Lumen/AO)
#   [ ] Project Settings > Rendering > Dynamic Global Illumination "Software/Hardware Ray Tracing" 선택
#   [ ] Project Settings > Rendering > Nanite = 지원 확인, "Support Nanite" 활성
#   [ ] (선택) Post Process 에서 Auto Exposure 를 Manual 로 두면 노을 노출이 더 안정적

import os

try:
    import unreal
except ImportError:
    unreal = None


SCENE_LABELS = [
    "Sun_1888",
    "SkyAtmosphere_1888",
    "SkyLight_1888",
    "HeightFog_1888",
    "PostProcess_1888",
    "Ground_Temp",
]


def log(msg):
    if unreal:
        unreal.log("[Gyeongbok/s3] " + msg)
    else:
        print("[Gyeongbok/s3] " + msg)


def log_warn(msg):
    if unreal:
        unreal.log_warning("[Gyeongbok/s3] " + msg)
    else:
        print("[Gyeongbok/s3][WARN] " + msg)


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
            log_warn("액터 삭제 예외: %s" % e)
    if removed:
        log("재실행: 기존 씬 액터 %d 개 삭제" % removed)


def set_prop(obj, name, value):
    """존재하지 않는(버전차) 프로퍼티는 로그만 남기고 넘어감."""
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as e:
        log_warn("프로퍼티 '%s' 설정 스킵: %s" % (name, e))
        return False


def set_movable(actor):
    try:
        actor.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception as e:
        log_warn("mobility=Movable 설정 스킵: %s" % e)


def clean_template_scene(subsystem):
    """템플릿 맵에 딸려온 조명·하늘·안개는 삭제(태양 중복 방지), Landscape 는 숨긴다."""
    doomed_classes = tuple(
        c for c in (
            getattr(unreal, "DirectionalLight", None),
            getattr(unreal, "SkyLight", None),
            getattr(unreal, "SkyAtmosphere", None),
            getattr(unreal, "ExponentialHeightFog", None),
        ) if c is not None
    )
    landscape_cls = getattr(unreal, "LandscapeProxy", None)
    label_set = set(SCENE_LABELS)
    removed, hidden = 0, 0
    for a in subsystem.get_all_level_actors():
        try:
            if a.get_actor_label() in label_set:
                continue
            if isinstance(a, doomed_classes):
                subsystem.destroy_actor(a)
                removed += 1
            elif landscape_cls and isinstance(a, landscape_cls):
                a.set_is_temporarily_hidden_in_editor(True)
                a.set_actor_hidden_in_game(True)
                hidden += 1
        except Exception as e:
            log_warn("템플릿 정리 예외: %s" % e)
    log("템플릿 정리: 기본 조명·하늘 %d 개 삭제, 랜드스케이프 %d 개 숨김" % (removed, hidden))


# ---------------------------------------------------------------------------
# 개별 액터 생성
# ---------------------------------------------------------------------------
def spawn_sun(subsystem):
    # 서쪽 저녁 태양: forward(빛 진행방향)가 +Y(동)+아래를 향하면 광원은 서쪽에 위치.
    # yaw=95 -> 대략 동남동으로 진행(광원=서북서), pitch=-8 -> 지평선 직전(골든아워, 긴 그림자).
    rotation = unreal.Rotator(roll=0.0, pitch=-8.0, yaw=95.0)
    sun = subsystem.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1500), rotation)
    sun.set_actor_label("Sun_1888")
    set_movable(sun)

    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    if comp:
        set_prop(comp, "intensity", 4.0)          # lux, 저녁이라 약하게
        set_prop(comp, "use_temperature", True)
        set_prop(comp, "temperature", 3900.0)     # 진한 노을 색온도(주황)
        set_prop(comp, "atmosphere_sun_light", True)      # SkyAtmosphere 태양으로 사용
        set_prop(comp, "atmosphere_sun_light_index", 0)
        set_prop(comp, "cast_shadows", True)
        try:
            comp.set_light_color(unreal.LinearColor(1.0, 0.9, 0.75, 1.0))
        except Exception as e:
            log_warn("sun set_light_color 스킵: %s" % e)
    log("Sun_1888 생성 (pitch=-14, yaw=95, 4700K)")
    return sun


def spawn_sky_atmosphere(subsystem):
    sky = subsystem.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky.set_actor_label("SkyAtmosphere_1888")
    # 기본값이 지구 대기라 노을은 태양 각도로 자연스럽게 형성됨.
    log("SkyAtmosphere_1888 생성")
    return sky


def spawn_sky_light(subsystem):
    sl = subsystem.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1500))
    sl.set_actor_label("SkyLight_1888")
    set_movable(sl)
    comp = sl.get_component_by_class(unreal.SkyLightComponent)
    if comp:
        set_prop(comp, "real_time_capture", True)
        try:
            set_prop(comp, "source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
        except Exception as e:
            log_warn("skylight source_type 스킵: %s" % e)
        try:
            comp.recapture_sky()
        except Exception:
            pass
    log("SkyLight_1888 생성 (real-time capture)")
    return sl


def spawn_height_fog(subsystem):
    fog = subsystem.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    fog.set_actor_label("HeightFog_1888")
    comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if comp:
        set_prop(comp, "fog_density", 0.018)          # 옅은 저녁 헤이즈
        set_prop(comp, "fog_height_falloff", 0.2)
        set_prop(comp, "start_distance", 500.0)       # 5m 부터
        # 옅은 주황 헤이즈
        try:
            set_prop(comp, "fog_inscattering_color", unreal.LinearColor(0.95, 0.55, 0.30, 1.0))
        except Exception as e:
            log_warn("fog color 스킵: %s" % e)
    log("HeightFog_1888 생성 (옅은 주황)")
    return fog


def spawn_post_process(subsystem):
    ppv = subsystem.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    ppv.set_actor_label("PostProcess_1888")
    set_prop(ppv, "unbound", True)  # 무한 범위(레벨 전체)

    settings = ppv.get_editor_property("settings")

    def pp(override_name, value_name, value):
        try:
            settings.set_editor_property(override_name, True)
            settings.set_editor_property(value_name, value)
        except Exception as e:
            log_warn("PP '%s' 스킵: %s" % (value_name, e))

    # 웜 화이트밸런스 — 주의: white_temp 는 "높일수록" 화면이 따뜻해짐 (기본 6500).
    # (이전 5200 은 방향이 반대라 오히려 낮처럼 차갑게 나왔음 — 07-07 수정)
    pp("override_white_temp", "white_temp", 7200.0)
    # 노출을 살짝 어둡게 — 자동 노출이 노을의 어스름을 밝은 낮처럼 끌어올리는 것 방지
    pp("override_auto_exposure_bias", "auto_exposure_bias", -0.5)
    # 블룸 약하게 (기본 0.675 -> 0.35)
    pp("override_bloom_intensity", "bloom_intensity", 0.35)
    # AO 강하게 (기본 0.5 -> 0.75)
    pp("override_ambient_occlusion_intensity", "ambient_occlusion_intensity", 0.75)
    pp("override_ambient_occlusion_radius", "ambient_occlusion_radius", 200.0)
    # Lumen (프로젝트 기본이 아니어도 여기서 강제; 미지원 버전이면 스킵 로그)
    try:
        pp("override_dynamic_global_illumination_method", "dynamic_global_illumination_method",
           unreal.DynamicGlobalIlluminationMethod.LUMEN)
        pp("override_reflection_method", "reflection_method",
           unreal.ReflectionMethod.LUMEN)
    except Exception as e:
        log_warn("Lumen PPV 설정 스킵(프로젝트 세팅에서 처리): %s" % e)
    # ACES 톤: UE 기본 톤매퍼가 ACES 계열(Filmic). 필요시 film_ 커브로 조정.

    ppv.set_editor_property("settings", settings)
    log("PostProcess_1888 생성 (unbound, warm WB, bloom↓, AO↑, Lumen)")
    return ppv


def spawn_ground(subsystem):
    plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    if plane is None:
        log_warn("기본 Plane 메시를 못 찾음 — 바닥 생략")
        return None
    # 마당 중심: layout courtyard center (0,-294)m → UE (29400, 0) cm. Z=-2cm(건물 바닥과 z-파이팅 방지)
    floor = subsystem.spawn_actor_from_object(plane, unreal.Vector(29400.0, 0.0, -2.0))
    floor.set_actor_label("Ground_Temp")
    # 기본 Plane = 1m x 1m -> 600m x 600m (마당+주변, 긴 노을 그림자 수용)
    floor.set_actor_scale3d(unreal.Vector(600.0, 600.0, 1.0))
    try:
        comp = floor.static_mesh_component
        mat = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
        if mat:
            comp.set_material(0, mat)
    except Exception as e:
        log_warn("바닥 임시 머티리얼 스킵: %s" % e)
    log("Ground_Temp 생성 (400m x 400m 임시 바닥)")
    return floor


def main():
    if unreal is None:
        print("[Gyeongbok/s3] unreal 모듈 없음 — UE 에디터/헤드리스에서 실행하세요.")
        return

    subsystem = get_actor_subsystem()
    delete_actors_by_labels(subsystem, SCENE_LABELS)
    clean_template_scene(subsystem)

    spawn_ground(subsystem)
    spawn_sky_atmosphere(subsystem)
    spawn_sun(subsystem)
    spawn_sky_light(subsystem)
    spawn_height_fog(subsystem)
    spawn_post_process(subsystem)

    log("씬 셋업 완료. 상단 주석의 프로젝트 세팅 체크리스트(Lumen/VSM/Distance Fields)를 확인하세요.")
    log("레벨 저장은 수동: File > Save Current Level")


if __name__ == "__main__":
    main()
else:
    main()
