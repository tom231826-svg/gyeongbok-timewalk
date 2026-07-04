#!/usr/bin/env python3
"""경복궁 타임워크 시제품 — 시대별 360° 파노라마(equirectangular) 플레이스홀더 생성.

6장 생성: (광화문 앞 / 근정전 앞마당) x (1888 고종 중건기 / 1929 일제강점기 / 2026 현재)
스타일: 미니멀 실루엣 일러스트. 고증 렌더가 아닌 UX 시연용 시안.
출력: ../assets/pano_{node}_{era}.jpg (2048x1024, 4096x2048에서 다운샘플로 안티앨리어싱)
"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter

W, H = 4096, 2048          # 작업 해상도 (최종 1/2 축소)
HORIZON = H // 2
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")


def deg_x(az):
    """방위각(도, 0=북=화면중앙) → x픽셀. 반환값은 wrap 안 된 실수."""
    return W / 2 + az / 360.0 * W


def deg_w(deg):
    return deg / 360.0 * W


def alt_y(alt):
    """고도각(도) → y픽셀 (양수 alt = 지평선 위)."""
    return HORIZON - alt / 180.0 * H


def vgrad(img, y0, y1, c0, c1):
    d = ImageDraw.Draw(img)
    n = max(1, y1 - y0)
    for i in range(n):
        t = i / n
        c = tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
        d.line([(0, y0 + i), (W, y0 + i)], fill=c)


def wrapped(fn):
    """중앙 cx 기준으로 그리는 함수를 좌우 wrap 포함 3회 호출."""
    def inner(d, cx, *a, **kw):
        for off in (-W, 0, W):
            fn(d, cx + off, *a, **kw)
    return inner


@wrapped
def roof(d, cx, y_eave, w_eave, w_ridge, h, color, lift=None):
    """한식 지붕 실루엣: 처마 곡선(양끝 들림) + 용마루."""
    if lift is None:
        lift = h * 0.28
    pts = []
    n = 24
    for i in range(n + 1):
        t = i / n
        x = cx - w_eave / 2 + w_eave * t
        y = y_eave - lift * (2 * t - 1) ** 2
        pts.append((x, y))
    pts.append((cx + w_ridge / 2, y_eave - h))
    pts.append((cx - w_ridge / 2, y_eave - h))
    d.polygon(pts, fill=color)


@wrapped
def rect(d, cx, y_top, w, h, color):
    d.rectangle([cx - w / 2, y_top, cx + w / 2, y_top + h], fill=color)


@wrapped
def trapezoid(d, cx, y_top, w_top, w_bot, h, color):
    d.polygon([(cx - w_top / 2, y_top), (cx + w_top / 2, y_top),
               (cx + w_bot / 2, y_top + h), (cx - w_bot / 2, y_top + h)], fill=color)


@wrapped
def arch(d, cx, y_bot, w, h, color):
    d.rectangle([cx - w / 2, y_bot - h + w / 2, cx + w / 2, y_bot], fill=color)
    d.ellipse([cx - w / 2, y_bot - h, cx + w / 2, y_bot - h + w], fill=color)


@wrapped
def dome(d, cx, y_base, w, h, color):
    d.ellipse([cx - w / 2, y_base - h, cx + w / 2, y_base + h * 0.2], fill=color)
    d.rectangle([cx - w * 0.05, y_base - h - w * 0.12, cx + w * 0.05, y_base - h], fill=color)


@wrapped
def haetae(d, cx, y_base, s, color):
    """해태상 약식 실루엣: 대좌 + 몸통 + 머리."""
    d.rectangle([cx - s * 0.7, y_base - s * 0.35, cx + s * 0.7, y_base], fill=color)
    d.ellipse([cx - s * 0.55, y_base - s * 1.05, cx + s * 0.45, y_base - s * 0.25], fill=color)
    d.ellipse([cx + s * 0.1, y_base - s * 1.35, cx + s * 0.65, y_base - s * 0.75], fill=color)


@wrapped
def lamp(d, cx, y_base, s, color):
    d.line([(cx, y_base), (cx, y_base - s)], fill=color, width=max(2, int(s * 0.06)))
    d.ellipse([cx - s * 0.1, y_base - s * 1.12, cx + s * 0.1, y_base - s * 0.92], fill=color)


@wrapped
def banner(d, cx, y_top, w, h, color):
    d.rectangle([cx - w / 2, y_top, cx + w / 2, y_top + h], fill=color)


def sun(img, az, alt, r, color, glow):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    x, y = deg_x(az) % W, alt_y(alt)
    for gr, ga in ((r * 5, 25), (r * 3, 45), (r * 1.8, 80)):
        d.ellipse([x - gr, y - gr, x + gr, y + gr], fill=glow + (ga,))
    d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))
    ov = ov.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(ov)


def clouds(img, seedpts, color, alpha):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for (az, alt, w, h) in seedpts:
        x, y = deg_x(az) % W, alt_y(alt)
        d.ellipse([x - w, y - h, x + w, y + h], fill=color + (alpha,))
        d.ellipse([x - w * 0.6, y - h * 1.5, x + w * 0.7, y - h * 0.2], fill=color + (alpha,))
    img.alpha_composite(ov.filter(ImageFilter.GaussianBlur(30)))


def mountains(d, az0, az1, base_alt, peak_alt, color, peaks):
    """능선 폴리곤. peaks = [(az, alt), ...] 좌→우."""
    pts = [(deg_x(az0), alt_y(base_alt))]
    for az, alt in peaks:
        pts.append((deg_x(az), alt_y(alt)))
    pts.append((deg_x(az1), alt_y(base_alt)))
    pts.append((deg_x(az1), HORIZON + 40))
    pts.append((deg_x(az0), HORIZON + 40))
    d.polygon(pts, fill=color)


def corridor(d, sil, gap_az=None, y_base=None, wall_h=90, roof_h=70):
    """회랑: 전방위 띠. gap_az 구간은 문(더 큰 지붕)으로 비움."""
    y_base = y_base or (HORIZON + 100)
    d.rectangle([0, y_base - wall_h, W, y_base], fill=sil)
    # 회랑 지붕: 살짝 위로 띠
    d.rectangle([0, y_base - wall_h - roof_h * 0.45, W, y_base - wall_h], fill=sil)
    # 기둥 리듬(밝은 틈)
    return y_base


def hanok_row(d, az_from, az_to, y_base, sil, n=7, scale=1.0):
    """멀리 보이는 저층 한옥 지붕 행렬 (육조거리 등)."""
    for i in range(n):
        t = i / max(1, n - 1)
        az = az_from + (az_to - az_from) * t
        w = deg_w(9 * scale)
        roof(d, deg_x(az), y_base, w, w * 0.45, deg_w(1.6 * scale), sil)
        rect(d, deg_x(az), y_base, w * 0.8, 40 * scale, sil)


# ──────────────────────────── 시대 팔레트 ────────────────────────────
ERAS = {
    "1888": dict(
        sky_top=(18, 26, 52), sky_hor=(212, 142, 84), ground_top=(56, 44, 40),
        ground_bot=(30, 24, 22), sil=(38, 27, 36), sil2=(52, 38, 46),
        mount=(30, 24, 40), sun_az=105, sun_alt=9, sun_r=26,
        sun_c=(255, 214, 150), sun_glow=(255, 170, 90),
    ),
    "1929": dict(
        sky_top=(196, 186, 166), sky_hor=(234, 222, 198), ground_top=(168, 155, 130),
        ground_bot=(120, 110, 92), sil=(74, 64, 51), sil2=(96, 87, 72),
        mount=(150, 139, 118), sun_az=-25, sun_alt=38, sun_r=20,
        sun_c=(246, 240, 224), sun_glow=(238, 228, 204),
    ),
    "2026": dict(
        sky_top=(56, 118, 196), sky_hor=(206, 230, 246), ground_top=(198, 192, 182),
        ground_bot=(150, 144, 134), sil=(44, 41, 38), sil2=(122, 66, 54),
        mount=(72, 100, 76), sun_az=-60, sun_alt=52, sun_r=16,
        sun_c=(255, 255, 240), sun_glow=(255, 250, 220),
        stone=(196, 188, 172), wall=(150, 82, 62),
    ),
}


def base_canvas(p):
    img = Image.new("RGBA", (W, H))
    vgrad(img, 0, HORIZON, p["sky_top"], p["sky_hor"])
    vgrad(img, HORIZON, H, p["ground_top"], p["ground_bot"])
    return img


def finish(img, era, name):
    if era == "1929":
        noise = Image.effect_noise((W, H), 22).convert("L")
        img = Image.composite(img.convert("RGB"), Image.new("RGB", (W, H), (110, 100, 84)),
                              noise.point(lambda v: 255 - min(60, (255 - v) // 3)))
        # 비네트
        vig = Image.new("L", (W, H), 0)
        dv = ImageDraw.Draw(vig)
        dv.ellipse([-W * 0.25, -H * 0.55, W * 1.25, H * 1.55], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(220))
        img = Image.composite(img, Image.new("RGB", (W, H), (72, 64, 50)), vig)
    else:
        img = img.convert("RGB")
    img = img.resize((W // 2, H // 2), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    img.save(path, "JPEG", quality=80, optimize=True)
    print(name, os.path.getsize(path) // 1024, "KB")


# ──────────────────────────── 광화문 앞 ────────────────────────────
def gwanghwamun(era):
    p = ERAS[era]
    img = base_canvas(p)
    sun(img, p["sun_az"], p["sun_alt"], p["sun_r"], p["sun_c"], p["sun_glow"])
    if era == "2026":
        clouds(img, [(-130, 34, 340, 60), (55, 44, 260, 50), (160, 28, 300, 55)], (255, 255, 255), 150)
    if era == "1929":
        clouds(img, [(-90, 30, 420, 70), (120, 36, 380, 66)], (222, 212, 190), 120)
    d = ImageDraw.Draw(img)
    sil, sil2, mnt = p["sil"], p["sil2"], p["mount"]

    # 북악산 (성문 뒤)
    mountains(d, -75, 85, 2, 13, mnt,
              [(-48, 6), (-25, 9), (2, 13), (18, 10.5), (40, 7), (62, 5)])

    y_base = HORIZON + 130
    if era in ("1888", "2026"):
        # 궁장(담) 좌우로 길게
        wall_c = sil if era == "1888" else p["wall"]
        stone_c = sil if era == "1888" else p["stone"]
        d.rectangle([deg_x(-88), y_base - 95, deg_x(88), y_base], fill=wall_c)
        d.rectangle([deg_x(-88), y_base - 118, deg_x(88), y_base - 95], fill=sil)  # 담 기와
        # 광화문: 석축 + 홍예 3 + 2층 지붕
        gx = deg_x(0)
        stone_w, stone_h = deg_w(46), 270
        rect(d, gx, y_base - stone_h, stone_w, stone_h, stone_c)
        for ax, aw in ((-10, 9), (0, 11), (10, 9)):
            arch(d, deg_x(ax), y_base, deg_w(aw) * 0.55, 170, (14, 10, 12) if era == "1888" else (40, 32, 30))
        rect(d, gx, y_base - stone_h - 66, deg_w(38), 66, wall_c if era == "2026" else sil2)
        roof(d, gx, y_base - stone_h - 60, deg_w(44), deg_w(10), 120, sil)
        rect(d, gx, y_base - stone_h - 178, deg_w(30), 58, wall_c if era == "2026" else sil2)
        roof(d, gx, y_base - stone_h - 172, deg_w(36), deg_w(7), 130, sil)
        haetae(d, deg_x(-21), y_base + 55, 70, sil)
        haetae(d, deg_x(21), y_base + 55, 70, sil)
        if era == "2026":
            # 월대(광장 쪽으로 넓어지는 단)
            trapezoid(d, gx, y_base, deg_w(24), deg_w(40), 130, p["stone"])
            lamp(d, deg_x(150), HORIZON + 260, 220, sil)
            lamp(d, deg_x(-150), HORIZON + 260, 220, sil)
            # 남쪽 현대 스카이라인 (낮게, 옅게)
            sky_blk = tuple(min(255, c + 70) for c in p["sil"])
            for az, bw, bh in ((140, 14, 120), (156, 10, 170), (172, 12, 140),
                               (-172, 11, 150), (-156, 13, 120), (-140, 9, 180)):
                x = deg_x(az if az > 0 else 360 + az)
                rect(d, x, HORIZON + 60 - bh, deg_w(bw) * 0.5, bh, sky_blk)
        else:
            # 1888 육조거리 관아 지붕 행렬 (남쪽)
            hanok_row(d, 118, 168, HORIZON + 210, sil2, n=5, scale=1.5)
            hanok_row(d, -168, -118, HORIZON + 210, sil2, n=5, scale=1.5)
    else:
        # 1929: 광화문 부재 — 총독부 청사 + 가림막 + 배너
        d.rectangle([deg_x(-62), y_base - 60, deg_x(62), y_base], fill=sil2)  # 판장 울타리
        fx = deg_x(0)
        rect(d, fx, y_base - 330, deg_w(64), 330, sil2)          # 본관 매스
        rect(d, fx, y_base - 380, deg_w(26), 60, sil2)           # 중앙부
        dome(d, fx, y_base - 372, deg_w(14), 150, sil)           # 돔
        for c in range(-5, 6):
            d.rectangle([fx + deg_w(4.6 * c) - 14, y_base - 300, fx + deg_w(4.6 * c) + 14, y_base - 70],
                        fill=sil)                                 # 열주 리듬
        for baz in (-48, -40, 40, 48):
            lamp(d, deg_x(baz), y_base + 30, 260, sil)
            banner(d, deg_x(baz), alt_y(0) - 210, deg_w(2.2), 190, sil)
        hanok_row(d, 118, 168, HORIZON + 210, sil2, n=5, scale=1.4)
        hanok_row(d, -168, -118, HORIZON + 210, sil2, n=5, scale=1.4)

    finish(img, era, f"pano_g_{era}.jpg")


# ──────────────────────────── 근정전 앞마당 ────────────────────────────
def geunjeongjeon(era):
    p = ERAS[era]
    img = base_canvas(p)
    sun(img, p["sun_az"], p["sun_alt"], p["sun_r"], p["sun_c"], p["sun_glow"])
    if era == "2026":
        clouds(img, [(-110, 40, 320, 56), (70, 36, 280, 52)], (255, 255, 255), 150)
    if era == "1929":
        clouds(img, [(-70, 34, 400, 70), (140, 30, 360, 60)], (222, 212, 190), 120)
    d = ImageDraw.Draw(img)
    sil, sil2 = p["sil"], p["sil2"]
    wall_c = p.get("wall", sil2)
    stone_c = p.get("stone", sil2)

    # 북악산: 근정전 지붕 뒤로 살짝
    mountains(d, -50, 60, 1, 10, p["mount"], [(-20, 6), (6, 10), (30, 7)])

    # 회랑 (전방위)
    y_cor = HORIZON + 105
    cor_wall = wall_c if era == "2026" else sil2
    d.rectangle([0, y_cor - 85, W, y_cor], fill=cor_wall)
    d.rectangle([0, y_cor - 130, W, y_cor - 85], fill=sil)
    # 근정문 (남쪽 az180, 회랑보다 크게)
    for gaz in (180,):
        roof(d, deg_x(gaz) - W, y_cor - 195, deg_w(30), deg_w(7), 95, sil)   # wrap 좌
        roof(d, deg_x(gaz), y_cor - 195, deg_w(30), deg_w(7), 95, sil)
        rect(d, deg_x(gaz), y_cor - 200, deg_w(24), 200, sil2)
        roof(d, deg_x(gaz), y_cor - 305, deg_w(24), deg_w(5), 85, sil)

    # 근정전 (북쪽 az0): 2단 월대 + 몸체 + 겹지붕
    gx = deg_x(0)
    y0 = HORIZON + 170
    trapezoid(d, gx, y0 - 120, deg_w(70), deg_w(88), 120, stone_c)   # 하월대
    trapezoid(d, gx, y0 - 200, deg_w(56), deg_w(66), 80, stone_c)    # 상월대
    rect(d, gx, y0 - 480, deg_w(44), 280, wall_c)                    # 몸체(기둥열)
    if era == "2026":
        for c in range(-4, 5):
            d.rectangle([gx + deg_w(4.6 * c) - 12, y0 - 470, gx + deg_w(4.6 * c) + 12, y0 - 205], fill=sil)
    roof(d, gx, y0 - 465, deg_w(58), deg_w(14), 150, sil)            # 아래 지붕
    rect(d, gx, y0 - 660, deg_w(34), 70, wall_c)                     # 상층 벽
    roof(d, gx, y0 - 648, deg_w(46), deg_w(9), 160, sil)             # 위 지붕
    # 계단 어도
    trapezoid(d, gx, y0 - 120, deg_w(9), deg_w(13), 120, sil)

    # 품계석: 남쪽(근정문 방향) 어도 양측 2열
    for saz, ss in ((168, 34), (172, 26), (176, 20), (-168, 34), (-172, 26), (-176, 20)):
        x = deg_x(saz if saz > 0 else 360 + saz)
        y = HORIZON + 420 - ss * 4
        rect(d, x, y - ss, deg_w(0.9), ss, sil)

    if era == "1929":
        # 박람회: 근정전 기둥 사이 현수막 + 마당 가설 부스 + 남쪽 하늘 위 총독부 돔
        for c in (-2, 0, 2):
            banner(d, gx + deg_w(5.5 * c), y0 - 455, deg_w(2.4), 230, sil)
        for baz in (-55, -80, -105, 55, 80, 105):
            x = deg_x(baz if baz > 0 else 360 + baz)
            trapezoid(d, x, y_cor - 175, deg_w(4), deg_w(12), 45, sil2)   # 천막 지붕
            rect(d, x, y_cor - 130, deg_w(10), 130, sil2)
        dome(d, deg_x(180), y_cor - 300, deg_w(10), 110, sil2)
        dome(d, deg_x(-180), y_cor - 300, deg_w(10), 110, sil2)

    finish(img, era, f"pano_j_{era}.jpg")


if __name__ == "__main__":
    for era in ("1888", "1929", "2026"):
        gwanghwamun(era)
        geunjeongjeon(era)
    print("done")
