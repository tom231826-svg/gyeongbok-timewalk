#!/usr/bin/env python3
"""경복궁 타임워크 - 시대별 텍스처 파생 스크립트.

scans_csp/*_tex*.jpg (2020년대 실측 스캔, 다소 낡은 상태)를 입력으로 받아
- era1888/  : 고종 중건 직후 새 궁궐 느낌 (채도up, 밝기up, 그림자 완화, 단청색 선택 부스트)
- era1929/  : 1888 결과물 기반 퇴락 진행 (채도down, 밝기down, 웜그레이 페이드)
두 파생 세트를 생성한다.

원본 파일은 읽기 전용으로만 사용하며 절대 덮어쓰지 않는다.
재실행해도 안전 (출력 파일은 매번 새로 계산되어 덮어써짐).
"""
from __future__ import annotations

import glob
import os

import numpy as np
from PIL import Image
from matplotlib.colors import hsv_to_rgb, rgb_to_hsv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
SCANS_DIR = "/Users/junkim/projects/gyeongbok-timewalk/prototype/assets/scans_csp"
ERA1888_DIR = os.path.join(SCANS_DIR, "era1888")
ERA1929_DIR = os.path.join(SCANS_DIR, "era1929")
INPUT_GLOB = os.path.join(SCANS_DIR, "*_tex*.jpg")

LONG_SIDE = 1024
JPEG_QUALITY = 80

# ---------------------------------------------------------------------------
# 1888년 파라미터 (고종 중건 직후 - 갓 칠한 단청 느낌)
# ---------------------------------------------------------------------------
SAT_SCALE_1888 = 1.25          # 채도 +25%
BRIGHT_ADD_1888 = 0.07         # 밝기 +7%
SHADOW_GAMMA_1888 = 0.85       # <1 → 어두운 영역일수록 더 크게 리프트 (얼룩 완화)

# 단청 선택 부스트 (hue는 0-360도 기준)
DANCHEONG_TEAL_CENTER = 175.0      # 청록/뇌록 계열 중심 (약 150~200도 대역)
DANCHEONG_TEAL_HALF = 25.0
DANCHEONG_VERMILLION_CENTER = 0.0  # 주홍/석간주 계열 중심 (약 0~25, 350~360도 대역)
DANCHEONG_VERMILLION_HALF = 22.0
DANCHEONG_HUE_SOFTNESS = 15.0      # hue 경계 바깥으로 부드럽게 사라지는 폭(도)

DANCHEONG_SAT_GATE_LO = 0.15   # 이 채도 미만은 단청이 아닌 얼룩/무채색으로 간주 → 부스트 제외
DANCHEONG_SAT_GATE_HI = 0.30   # 이 채도 이상이면 게이트 완전히 열림
DANCHEONG_EXTRA_BOOST = 0.18   # 게이트 통과 픽셀에 추가되는 채도 부스트 강도 (점근적 적용)

# ---------------------------------------------------------------------------
# 1929년 파라미터 (일제강점기 - 1888 결과물 기반 퇴락)
# ---------------------------------------------------------------------------
SAT_SCALE_1929 = 0.75          # 채도 -25%
BRIGHT_ADD_1929 = -0.04        # 밝기 -4%
SEPIA_BLEND_ALPHA_1929 = 0.10  # 웜그레이와 블렌드 비율
SEPIA_WARM_GRAY = np.array([0.58, 0.52, 0.44])  # 살짝 갈색조 웜그레이 (0-1 RGB)


def _smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _angular_dist(hue_deg: np.ndarray, center: float) -> np.ndarray:
    d = np.abs(hue_deg - center) % 360.0
    return np.minimum(d, 360.0 - d)


def _hue_band_mask(hue_deg: np.ndarray, center: float, half: float, softness: float) -> np.ndarray:
    """center±half 안쪽은 1, 그 바깥으로 softness 폭에 걸쳐 부드럽게 0으로 감쇠."""
    d = _angular_dist(hue_deg, center)
    t = (d - half) / softness
    return 1.0 - _smoothstep(t)


def load_resized_float(path: str, long_side: int = LONG_SIDE) -> np.ndarray:
    """이미지를 열어 긴 변 기준 long_side로 축소하고 float [0,1] RGB 배열로 반환."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    scale = long_side / max(w, h)
    if scale < 1.0:  # 확대는 하지 않음 (원본이 이미 작으면 그대로)
        new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
        im = im.resize((new_w, new_h), Image.LANCZOS)
    arr = np.asarray(im, dtype=np.float32) / 255.0
    return arr


def apply_dancheong_boost(hsv: np.ndarray) -> np.ndarray:
    """hsv 배열(H:0-1, S:0-1, V:0-1)에서 단청 색 픽셀만 선택적으로 추가 채도 부스트."""
    h_deg = hsv[..., 0] * 360.0
    s = hsv[..., 1]

    teal_mask = _hue_band_mask(h_deg, DANCHEONG_TEAL_CENTER, DANCHEONG_TEAL_HALF, DANCHEONG_HUE_SOFTNESS)
    verm_mask = _hue_band_mask(h_deg, DANCHEONG_VERMILLION_CENTER, DANCHEONG_VERMILLION_HALF, DANCHEONG_HUE_SOFTNESS)
    hue_mask = np.maximum(teal_mask, verm_mask)

    sat_gate_t = (s - DANCHEONG_SAT_GATE_LO) / (DANCHEONG_SAT_GATE_HI - DANCHEONG_SAT_GATE_LO)
    sat_gate = _smoothstep(sat_gate_t)

    mask = hue_mask * sat_gate
    # 점근적 적용: 이미 채도가 높은 픽셀은 덜 부스트되어 클리핑(만화 느낌) 방지
    s_new = s + mask * DANCHEONG_EXTRA_BOOST * (1.0 - s)

    out = hsv.copy()
    out[..., 1] = np.clip(s_new, 0.0, 1.0)
    return out


def make_1888(rgb: np.ndarray) -> np.ndarray:
    hsv = rgb_to_hsv(rgb)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    # 그림자 리프트 (어두운 얼룩 완화): gamma < 1 → 어두운 값일수록 크게 밝아짐
    v_lifted = np.power(np.clip(v, 0.0, 1.0), SHADOW_GAMMA_1888)
    v_new = np.clip(v_lifted + BRIGHT_ADD_1888, 0.0, 1.0)

    s_new = np.clip(s * SAT_SCALE_1888, 0.0, 1.0)

    hsv_new = np.stack([h, s_new, v_new], axis=-1)
    hsv_new = apply_dancheong_boost(hsv_new)

    rgb_new = hsv_to_rgb(np.clip(hsv_new, 0.0, 1.0))
    return np.clip(rgb_new, 0.0, 1.0)


def make_1929(rgb_1888: np.ndarray) -> np.ndarray:
    hsv = rgb_to_hsv(rgb_1888)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    s_new = np.clip(s * SAT_SCALE_1929, 0.0, 1.0)
    v_new = np.clip(v + BRIGHT_ADD_1929, 0.0, 1.0)

    hsv_new = np.stack([h, s_new, v_new], axis=-1)
    rgb_new = hsv_to_rgb(np.clip(hsv_new, 0.0, 1.0))
    rgb_new = np.clip(rgb_new, 0.0, 1.0)

    # 살짝 갈색조 웜그레이 페이드
    rgb_faded = rgb_new * (1.0 - SEPIA_BLEND_ALPHA_1929) + SEPIA_WARM_GRAY * SEPIA_BLEND_ALPHA_1929
    return np.clip(rgb_faded, 0.0, 1.0)


def save_float_rgb(arr: np.ndarray, path: str) -> int:
    """float [0,1] RGB 배열을 JPEG로 저장하고 저장된 파일 크기(bytes)를 반환."""
    im = Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8))
    im.save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return os.path.getsize(path)


def human_size(num_bytes: int) -> str:
    kb = num_bytes / 1024.0
    if kb < 1024:
        return f"{kb:.1f}KB"
    return f"{kb / 1024.0:.2f}MB"


def process_all() -> None:
    os.makedirs(ERA1888_DIR, exist_ok=True)
    os.makedirs(ERA1929_DIR, exist_ok=True)

    src_paths = sorted(glob.glob(INPUT_GLOB))
    if not src_paths:
        print(f"입력 파일을 찾지 못했습니다: {INPUT_GLOB}")
        return

    total_1888 = 0
    total_1929 = 0
    print(f"{len(src_paths)}개 원본 텍스처 처리 시작 (긴 변 {LONG_SIDE}px, JPEG q={JPEG_QUALITY})\n")

    for src_path in src_paths:
        fname = os.path.basename(src_path)
        rgb = load_resized_float(src_path)

        rgb_1888 = make_1888(rgb)
        rgb_1929 = make_1929(rgb_1888)

        out_1888 = os.path.join(ERA1888_DIR, fname)
        out_1929 = os.path.join(ERA1929_DIR, fname)

        size_1888 = save_float_rgb(rgb_1888, out_1888)
        size_1929 = save_float_rgb(rgb_1929, out_1929)

        total_1888 += size_1888
        total_1929 += size_1929

        print(f"  {fname:32s}  1888: {human_size(size_1888):>8s}   1929: {human_size(size_1929):>8s}")

    print()
    print(f"era1888 총 용량: {human_size(total_1888)} ({total_1888} bytes)")
    print(f"era1929 총 용량: {human_size(total_1929)} ({total_1929} bytes)")


def make_preview(base_name: str = "seowollang_tex0.jpg", panel_long_side: int = 512) -> str:
    """원본 / 1888 / 1929 세 이미지를 나란히 붙인 비교 이미지를 생성."""
    from PIL import ImageDraw, ImageFont

    src_path = os.path.join(SCANS_DIR, base_name)
    path_1888 = os.path.join(ERA1888_DIR, base_name)
    path_1929 = os.path.join(ERA1929_DIR, base_name)

    def load_panel(path: str) -> Image.Image:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        scale = panel_long_side / max(w, h)
        new_w, new_h = round(w * scale), round(h * scale)
        return im.resize((new_w, new_h), Image.LANCZOS)

    panels = [load_panel(src_path), load_panel(path_1888), load_panel(path_1929)]
    labels = ["2020s (scan)", "1888", "1929"]

    gap = 6
    label_h = 28
    w = panels[0].width
    h = panels[0].height
    total_w = w * 3 + gap * 2
    total_h = h + label_h

    canvas = Image.new("RGB", (total_w, total_h), color=(20, 20, 20))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()

    x = 0
    for panel, label in zip(panels, labels):
        canvas.paste(panel, (x, label_h))
        draw.text((x + 8, 4), label, fill=(255, 255, 255), font=font)
        x += w + gap

    out_path = os.path.join(SCANS_DIR, "era_preview.jpg")
    canvas.save(out_path, format="JPEG", quality=90)
    return out_path


if __name__ == "__main__":
    process_all()
    preview_path = make_preview()
    print(f"\n비교 이미지 생성: {preview_path}")
