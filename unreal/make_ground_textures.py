# -*- coding: utf-8 -*-
"""바닥 텍스처 생성기 (오프라인 도구 — 맥 파이썬으로 실행, UE 아님).

근정전 마당 박석(불규칙 화강암 판돌)·어도(장방형 판석)·마사토(흙)의
디퓨즈+노멀 타일 텍스처를 절차 생성한다. 전부 주기적(이어붙임 무늬 안 깨짐).

실행:  python3 unreal/make_ground_textures.py
출력:  unreal/textures/{bakseok,eodo,masato}_D.jpg / _N.png

스캔 텍스처는 UV 아틀라스(조각 퍼즐)라 크롭 불가 → 절차 생성 채택.
승인 후 근정전 스캔이 오면 진짜 박석을 베이크해 교체하는 업그레이드 여지 있음.
"""

import os

import numpy as np
from PIL import Image

N = 2048
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
RNG = np.random.default_rng(20260707)


def fbm_noise(sigma):
    """주기적(타일러블) 가우시안 블러 노이즈, 0..1 정규화. FFT라 가장자리가 이어짐."""
    w = RNG.standard_normal((N, N)).astype(np.float32)
    fx = np.fft.fftfreq(N)[:, None]
    fy = np.fft.rfftfreq(N)[None, :]
    gauss = np.exp(-2.0 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2)).astype(np.float32)
    b = np.fft.irfft2(np.fft.rfft2(w) * gauss, s=(N, N))
    b = (b - b.min()) / (b.max() - b.min() + 1e-9)
    return b.astype(np.float32)


def periodic_voronoi(grid):
    """지터 격자 보로노이 (주기적). F1, F2 거리(px)와 셀 ID 반환."""
    s = N / grid
    jit = (RNG.random((grid, grid, 2)).astype(np.float32) - 0.5) * 0.70
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    ci = np.floor(xs / s).astype(np.int32)
    cj = np.floor(ys / s).astype(np.int32)
    f1 = np.full((N, N), 1e9, np.float32)
    f2 = np.full((N, N), 1e9, np.float32)
    cid = np.zeros((N, N), np.int32)
    for di in range(-2, 3):
        for dj in range(-2, 3):
            gi, gj = ci + di, cj + dj
            wi, wj = gi % grid, gj % grid
            px = (gi + 0.5 + jit[wi, wj, 0]) * s
            py = (gj + 0.5 + jit[wi, wj, 1]) * s
            d = np.hypot(xs - px, ys - py)
            idx = wi * grid + wj
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, idx, cid)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid


def normal_from_height(h, strength):
    """주기적 그래디언트로 노멀맵(0..255 RGB) 생성."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * strength
    nz = np.ones_like(h)
    ln = np.sqrt(dx ** 2 + dy ** 2 + nz ** 2)
    nx, ny, nz = -dx / ln, dy / ln, nz / ln
    rgb = np.stack([(nx + 1) * 127.5, (ny + 1) * 127.5, (nz + 1) * 127.5], axis=-1)
    return rgb.clip(0, 255).astype(np.uint8)


def save(name, color, height, nstrength):
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray((color.clip(0, 1) * 255).astype(np.uint8)).save(
        os.path.join(OUT, name + "_D.jpg"), quality=92)
    Image.fromarray(normal_from_height(height, nstrength)).save(
        os.path.join(OUT, name + "_N.png"))
    print("saved", name)


def cell_table(n_cells, lo=0.0, hi=1.0, seed_shift=0):
    r = np.random.default_rng(11 + seed_shift)
    return (lo + r.random(n_cells) * (hi - lo)).astype(np.float32)


def make_bakseok():
    """박석: 불규칙 화강암 판돌(~75cm), 폭 변하는 줄눈, 거친 입자, 틈새 이끼. 타일 = 6m."""
    grid = 8
    f1, f2, cid = periodic_voronoi(grid)
    edge = f2 - f1
    # 줄눈 폭이 곳에 따라 달라짐(좁게 붙은 데 ~ 벌어진 데) + 가장자리 거칠게
    width_var = 6.0 + 10.0 * fbm_noise(30.0)
    wob = (fbm_noise(2.2) - 0.5) * 14.0
    t = np.clip((edge + wob - width_var) / 5.0, 0.0, 1.0)   # 0=줄눈, 1=판돌

    n_cells = grid * grid
    tone = cell_table(n_cells)[cid]                       # 판돌별 밝기
    tan = (cell_table(n_cells, seed_shift=5)[cid] < 0.22)  # 일부 황갈빛 돌
    dark = (cell_table(n_cells, seed_shift=13)[cid] < 0.15)  # 일부 어두운 돌

    v = 0.55 + (tone - 0.5) * 0.22
    v = np.where(dark, v * 0.78, v)
    r = np.where(tan, v * 1.07, v * 1.02)
    g = np.where(tan, v * 1.00, v * 1.00)
    b = np.where(tan, v * 0.88, v * 0.95)

    # 화강암 입자(강하게) + 후추알 + 돌 안 얼룩
    spk = fbm_noise(1.2) * 0.55 + fbm_noise(3.5) * 0.45
    pepper = fbm_noise(0.8)
    mottle = fbm_noise(10.0)
    grain = (0.78 + 0.44 * spk) * (0.94 + 0.12 * pepper) * (0.90 + 0.20 * mottle)
    macro = 0.88 + 0.24 * fbm_noise(60.0)                 # 큰 풍화 얼룩
    r, g, b = r * grain * macro, g * grain * macro, b * grain * macro

    # 돌 가장자리 낀 때(줄눈 인접부 어둡고 채도 죽음)
    rim = 0.82 + 0.18 * np.clip(t * 2.2 - 0.4, 0, 1)
    r, g, b = r * rim, g * rim, b * rim

    # 줄눈: 어두운 흙 + 이끼(강하게)
    jr, jg, jb = 0.26, 0.235, 0.19
    moss = np.clip(fbm_noise(25.0) * 1.9 - 0.6, 0, 1)
    jr = jr * (1 - moss * 0.75) + 0.30 * moss * 0.75
    jg = jg * (1 - moss * 0.75) + 0.42 * moss * 0.75
    jb = jb * (1 - moss * 0.75) + 0.20 * moss * 0.75
    jshade = 0.65 + 0.6 * spk
    color = np.stack([
        jr * jshade * (1 - t) + r * t,
        jg * jshade * (1 - t) + g * t,
        jb * jshade * (1 - t) + b * t,
    ], axis=-1)

    height = t * 1.0 + spk * 0.16 + mottle * 0.10 + (tone - 0.5) * 0.18
    save("bakseok", color, height, 7.0)


def make_eodo():
    """어도: 장방형 판석(벽돌식 어긋쌓기), 박석보다 크고 매끈. 타일 = 4m."""
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    row_h = N / 5.0            # 판 높이 0.8m
    col_w = N / 3.0            # 판 폭 1.33m
    row = np.floor(ys / row_h)
    off = (row % 2) * (col_w / 2.0)
    col = np.floor((xs + off) / col_w)
    wob = (fbm_noise(2.5) - 0.5) * 6.0
    du = np.minimum((xs + off) % col_w, col_w - ((xs + off) % col_w)) + wob
    dv = np.minimum(ys % row_h, row_h - (ys % row_h)) + wob
    t = np.clip((np.minimum(du, dv) - 5.0) / 5.0, 0.0, 1.0)

    n_ids = 64
    cid = (row.astype(np.int32) % 8) * 8 + (col.astype(np.int32) % 8)
    tone = cell_table(n_ids, seed_shift=9)[cid]
    v = 0.66 + (tone - 0.5) * 0.10
    spk = fbm_noise(1.5) * 0.5 + fbm_noise(4.0) * 0.5
    grain = 0.90 + 0.20 * spk
    macro = 0.93 + 0.14 * fbm_noise(55.0)
    r, g, b = v * 1.02 * grain * macro, v * 1.0 * grain * macro, v * 0.95 * grain * macro
    jv = 0.34 + 0.2 * spk
    color = np.stack([
        jv * 0.95 * (1 - t) + r * t,
        jv * 0.90 * (1 - t) + g * t,
        jv * 0.80 * (1 - t) + b * t,
    ], axis=-1)
    height = t * 0.7 + spk * 0.06
    save("eodo", color, height, 5.0)


def make_masato():
    """마사토(마당 밖 흙바닥): 모래+잔자갈 톤. 타일 = 9m."""
    big = fbm_noise(90.0)
    mid = fbm_noise(18.0)
    fine = fbm_noise(1.6)
    v = 0.60 + (big - 0.5) * 0.16 + (mid - 0.5) * 0.10
    grain = 0.90 + 0.20 * fine
    r = v * 1.08 * grain
    g = v * 0.98 * grain
    b = v * 0.82 * grain
    color = np.stack([r, g, b], axis=-1)
    height = big * 0.35 + mid * 0.15 + fine * 0.08
    save("masato", color, height, 3.0)


if __name__ == "__main__":
    make_bakseok()
    make_eodo()
    make_masato()
    print("완료 →", OUT)
