"""00 4K 全通道 PBR 贴图生成管线。

实现约束（这些做法会引入可见伪影，改动时不要退回）：
  1. 程序化噪声用「非镜像周期值噪声」。mirror tile 会让每种材质带左右 /
     上下镜像对称，4K 放大后呈万花筒感。
  2. AI 木纹 / 藤编原图自带的镜像 V 形纹，用逐行低频水平剪切 + 非对称
     低频明暗调制打散：纹理内容不做插值、相邻行偏移连续、无接缝断层。
  3. 不用规则 sin(linspace) 条带（刷漆木年轮 / 织物经纬 / 藤编网格），
     改用多频 fbm 相位调制。规则正弦在 BOX 投影下会变成波浪纹与摩尔纹。
  4. 偏平材质（黑钢 / 拉丝钢 / 混凝土 / 乳胶漆 / 釉面 / 羊毛）补中尺度
     结构：骨料、滚筒痕、橘皮、氧化斑、绒面斑驳，而非「纯色 + 白噪」。
  5. 地砖在 albedo 层加入可见砖缝与板间色差（只在 height 里有缝肉眼不可见）。
  6. 高度场以平滑宏观结构为主；normal 用细节层降采样梯度，AO/roughness/
     displacement 用平滑层，避免碎噪与位移失控。

通道：basecolor(RGB) / normal(RGB) / roughness / metallic / ao / height /
      displacement / specular（后 6 为灰度）；全部 4096x4096，
     16 材质 x 8 通道 = 128 张。
用法： python src/00_textures/make_ai_textures.py [材质名]   # 不传则全量 16 种
"""
import numpy as np
from PIL import Image, ImageFilter
import os, sys, gc

SIZE = 4096
# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()
SRC = str(C.AI_SOURCE)


def T(name, channel):
    """该材质该通道的输出路径（自动建目录）。"""
    return str(C.tex(name, channel))

# ------------------------------------------------------------------ 材质规格
# src: AI 原图名（None = 程序化生成）; kind: 形貌类型; tint: 基础色; rough/metal: PBR 基线
SPECS = {
    "oak_wood":          dict(src="oak_wood",       kind="wood",   rough=0.48, metal=0.00, tint=(0.72, 0.52, 0.33)),
    "walnut_wood":       dict(src="walnut_wood",    kind="wood",   rough=0.44, metal=0.00, tint=(0.32, 0.20, 0.13)),
    "marble":            dict(src="marble",         kind="stone",  rough=0.20, metal=0.00, tint=(0.90, 0.89, 0.87)),
    "linen_fabric":      dict(src="linen_fabric",   kind="fabric", rough=0.82, metal=0.00, tint=(0.76, 0.71, 0.61)),
    "leather":           dict(src="leather",        kind="leather",rough=0.58, metal=0.00, tint=(0.52, 0.33, 0.22)),
    "brass":             dict(src="brass",          kind="metal",  rough=0.32, metal=0.92, tint=(0.72, 0.55, 0.24)),
    "white_ceramic":     dict(src="white_ceramic",  kind="glaze",  rough=0.13, metal=0.00, tint=(0.93, 0.92, 0.90)),
    "rattan":            dict(src="rattan",         kind="weave",  rough=0.72, metal=0.00, tint=(0.74, 0.58, 0.36)),
    # 以下 8 种由程序化 4K 生成（材质名与 house.blend 的依赖保持一致）
    "brushed_steel":     dict(src=None, kind="metal",  rough=0.30, metal=0.95, tint=(0.62, 0.64, 0.66)),
    "black_steel":       dict(src=None, kind="metal",  rough=0.40, metal=0.88, tint=(0.14, 0.15, 0.16)),
    "concrete_floor":    dict(src=None, kind="stone",  rough=0.76, metal=0.00, tint=(0.55, 0.55, 0.53)),
    "floor_tile":        dict(src=None, kind="tile",   rough=0.38, metal=0.00, tint=(0.74, 0.73, 0.70)),
    "glazed_terracotta": dict(src=None, kind="glaze",  rough=0.26, metal=0.00, tint=(0.68, 0.38, 0.27)),
    "painted_wood":      dict(src=None, kind="wood",   rough=0.52, metal=0.00, tint=(0.87, 0.84, 0.78)),
    "wall_paint":        dict(src=None, kind="paint",  rough=0.88, metal=0.00, tint=(0.91, 0.89, 0.85)),
    "wool_fabric":       dict(src=None, kind="fabric", rough=0.90, metal=0.00, tint=(0.70, 0.68, 0.63)),
}

# ------------------------------------------------------------------ 基础工具
def edge_blend(a, feather=0.05):
    """四边交叉渐变做无缝：首尾 C0 连续，且不引入镜像对称。

    镜像 tile 虽无缝，但对有方向性的纹理（木纹、拉丝）会产生强烈
    万花筒对称；这里只把右/下边缘窄带向对侧渐变靠拢，主体纹理保持原样。
    """
    a = a.copy()
    s = a.shape[0]
    f = max(6, int(s * feather))
    for i in range(f):
        t = (i + 1) / (f + 1)
        a[:, s - f + i] = a[:, s - f + i] * (1 - t) + a[:, i] * t
    for i in range(f):
        t = (i + 1) / (f + 1)
        a[s - f + i, :] = a[s - f + i, :] * (1 - t) + a[i, :] * t
    return a


def _noise(cells, seed, size):
    """非镜像的周期值噪声：随机格点双三次放大 + 四边羽化，首尾 C0 连续。

    与 mirror tile 不同，这里不会引入任何轴对称。
    """
    cells = max(2, int(cells))
    rng = np.random.default_rng(seed)
    g = rng.random((cells, cells)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8), 'L').resize((size, size), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32) / 255.0
    return edge_blend(a, 0.035)


def fbm(size, seed, octaves=6, base_cells=4, gain=0.5):
    out = np.zeros((size, size), np.float32)
    amp, tot, cells = 1.0, 0.0, base_cells
    for i in range(octaves):
        out += _noise(cells, seed + i * 131, size) * amp
        tot += amp
        amp *= gain
        cells = min(cells * 2, size // 2)
    return out / tot


def highfreq(size, seed):
    """真 4K 高频细节：多尺度周期噪声的高通部分 + 细颗粒。"""
    a = fbm(size, seed, octaves=4, base_cells=64, gain=0.62)
    b = fbm(size, seed + 7717, octaves=3, base_cells=256, gain=0.55)
    grain = _noise(size // 2, seed + 313, size)
    return 0.45 * (a - 0.5) + 0.35 * (b - 0.5) + 0.20 * (grain - 0.5)


def blur(arr, radius):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), 'L')
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


def save_gray(arr, path):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), 'L').save(path, optimize=True)


def save_rgb(arr, path):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), 'RGB').save(path, optimize=True)


def normal_from_height(h, strength):
    gy, gx = np.gradient(h.astype(np.float32))
    nx, ny = -gx * strength, -gy * strength
    nz = np.ones_like(h)
    n = np.stack([nx, ny, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


# ------------------------------------------------------------------ albedo 源
def desymmetrize(rgb, kind, seed):
    """打破 AI 原图常见的左右镜像 V 形木纹（万花筒）。

    逐行施加低频、平滑、首尾一致的水平剪切：相邻行偏移量连续，因此不产生
    断层；用 np.roll 做整数平移，纹理内容不被插值破坏。再叠加一层非对称
    低频明暗调制，进一步消除镜像带来的成对明暗块。
    """
    if kind not in ("wood", "weave"):
        return rgb
    s = rgb.shape[0]
    rng = np.random.default_rng(seed + 4242)
    yy = np.linspace(0, 2 * np.pi, s, dtype=np.float32)
    dx = np.zeros(s, np.float32)
    for freq, amp in ((1, 165), (2, 82), (3, 43), (5, 21), (8, 10)):
        dx += amp * np.sin(freq * yy + rng.uniform(0, 2 * np.pi))
    dx = np.rint(dx).astype(np.int32)
    for y in range(s):
        rgb[y] = np.roll(rgb[y], int(dx[y]), axis=0)
    mod = fbm(s, seed + 8181, 4, 3)
    rgb *= (1.0 + 0.16 * (mod - 0.5))[..., None]
    del mod
    return np.clip(rgb, 0, 1).astype(np.float32)


def load_ai(name, kind, seed):
    """读 AI 材质图 -> 中心方裁（去水印）-> 4096 -> 去镜像 -> 边缘羽化无缝。"""
    im = Image.open(C.AI_SOURCE / f"src_{name}.png").convert('RGB')
    a = np.asarray(im, dtype=np.float32) / 255.0
    h, w = a.shape[:2]
    pad = int(min(h, w) * 0.06)                 # 去掉 AI 水印 / 边缘伪影
    a = a[pad:h - pad, pad:w - pad]
    h, w = a.shape[:2]
    s = min(h, w)
    a = a[(h - s) // 2:(h - s) // 2 + s, (w - s) // 2:(w - s) // 2 + s]
    rgb = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGB')
                     .resize((SIZE, SIZE), Image.LANCZOS), dtype=np.float32) / 255.0
    rgb = desymmetrize(rgb, kind, seed)
    del a
    return edge_blend(rgb, 0.05)


def procedural_rgb(name, spec, seed):
    """无 AI 原图的 8 种材质：4K 程序化彩色 albedo。

    所有规则 sin(linspace) 条带都被多频 fbm 相位调制替代；
    大幅补入中尺度结构，避免「死平纯色 + 白噪」的塑料感。
    """
    S = SIZE
    tint = np.array(spec["tint"], np.float32)[None, None, :]
    kind = spec["kind"]
    f1 = fbm(S, seed, 5, 4)          # 宏观起伏
    f2 = fbm(S, seed + 91, 6, 22)    # 中频
    f3 = fbm(S, seed + 611, 5, 9)    # 中尺度斑驳 / 相位扰动源
    f4 = fbm(S, seed + 733, 4, 48)   # 细斑 / 橘皮
    hf = highfreq(S, seed + 400)
    ph = 30.0 * (f3 - 0.5)          # 非对称相位扰动，打散规则织纹

    if kind == "metal":
        # 拉丝：沿 y 压扁噪声形成方向性细丝 + 轻微氧化斑
        strip = blur(_noise(S // 64, seed + 55, S), 1.0)
        v = 0.78 + 0.22 * strip + 0.12 * (f3 - 0.5) + 0.08 * (f2 - 0.5) + 0.16 * hf
        del strip
    elif kind == "stone":
        # 混凝土：骨料斑驳 + 细孔，而非均匀灰
        agg = blur(fbm(S, seed + 151, 5, 34), 1.2)
        v = 0.80 + 0.16 * (f1 - 0.5) + 0.18 * (agg - 0.5) + 0.10 * (f2 - 0.5) + 0.18 * hf
        del agg
    elif kind == "tile":
        # 大板砖：albedo 层可见砖缝 + 板间色差（缝只在 height 里则肉眼不可见）
        gx = np.linspace(0, 4 * np.pi, S, dtype=np.float32)[None, :]
        gy = np.linspace(0, 4 * np.pi, S, dtype=np.float32)[:, None]
        seam = np.clip(1.0 - np.minimum(np.abs(np.sin(gx)), np.abs(np.sin(gy))) / 0.045, 0, 1)
        bx = np.floor(np.linspace(0, 4, S, dtype=np.float32))[None, :]
        by = np.floor(np.linspace(0, 4, S, dtype=np.float32))[:, None]
        shade = 0.965 + 0.012 * ((bx * 3 + by * 5) % 4)
        v = ((0.88 + 0.10 * (f1 - 0.5) + 0.08 * (f3 - 0.5)
              + 0.07 * (f2 - 0.5) + 0.14 * hf) * shade - 0.26 * seam)
        del gx, gy, seam, bx, by, shade
    elif kind == "glaze":
        # 釉面：整体平滑 + 极轻橘皮 + 少量色差，避免点阵
        v = 0.90 + 0.07 * (f1 - 0.5) + 0.05 * (f4 - 0.5) + 0.035 * (f2 - 0.5) + 0.07 * hf
    elif kind == "paint":
        # 乳胶漆：滚筒痕 + 中尺度斑驳，不能是纯色 + 白噪
        v = 0.90 + 0.11 * (f1 - 0.5) + 0.10 * (f3 - 0.5) + 0.06 * (f4 - 0.5) + 0.05 * (f2 - 0.5) + 0.10 * hf
    elif kind == "wood":
        # 刷漆木：极淡多频木纹 + 漆膜橘皮（规则正弦条带已移除）
        yy = np.linspace(0, 9, S, dtype=np.float32)[:, None]
        phase = yy + 2.8 * f1 + 1.0 * f2
        grain = (0.5 + 0.5 * np.sin(phase * np.pi)) * \
                (0.55 + 0.45 * (0.5 + 0.5 * np.sin(phase * 0.41 * np.pi + 0.8)))
        v = 0.85 + 0.055 * grain + 0.055 * (f4 - 0.5) + 0.05 * (f2 - 0.5) + 0.11 * hf
        del yy, phase, grain
    elif kind == "fabric":
        # 羊毛/织物：非规则绒面斑驳 + 相位扰动的经纬起伏
        xx = np.linspace(0, 150, S, dtype=np.float32)[None, :]
        yy = np.linspace(0, 150, S, dtype=np.float32)[:, None]
        weave = 0.5 + 0.5 * np.sin((xx + 0.8 * ph) * np.pi) * np.sin((yy + 0.7 * ph) * np.pi)
        v = 0.80 + 0.11 * (weave - 0.5) + 0.10 * (f3 - 0.5) + 0.08 * (f4 - 0.5) + 0.16 * hf
        del xx, yy, weave
    else:
        v = 0.85 + 0.12 * (f1 - 0.5) + 0.20 * hf

    v = np.clip(v, 0, 1)[..., None]
    rgb = np.clip(tint * (0.72 + 0.46 * v) + 0.035 * hf[..., None], 0, 1)
    del f1, f2, f3, f4, ph, v
    return rgb.astype(np.float32)


# ------------------------------------------------------------------ 高度场
def build_height(rgb, spec, seed):
    """高度场：以 albedo 结构与材质形貌为主，高频只做受控微起伏。"""
    S = SIZE
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    kind = spec["kind"]
    lum_s = blur(lum, 5.0)
    f_mid = blur(fbm(S, seed + 1201, 4, 12), 6.0)
    hf = blur(0.5 + 0.5 * highfreq(S, seed + 2202), 6.0)
    ph = 30.0 * (f_mid - 0.5)        # 非对称相位扰动，复用 f_mid 不额外占内存

    if kind == "wood":
        h = 0.72 * (1.0 - lum_s) + 0.20 * f_mid + 0.08 * hf
    elif kind in ("stone", "tile", "glaze", "paint"):
        h = 0.52 * lum_s + 0.38 * f_mid + 0.10 * hf
        if kind == "tile":
            gx = np.linspace(0, 4 * np.pi, S, dtype=np.float32)[None, :]
            gy = np.linspace(0, 4 * np.pi, S, dtype=np.float32)[:, None]
            seam = np.minimum(np.abs(np.sin(gx)), np.abs(np.sin(gy)))
            seam = np.clip(1.0 - seam / 0.06, 0, 1)
            h = h - 0.34 * seam
            del gx, gy, seam
    elif kind == "fabric":
        # 降低规则 weave 权重，织纹主要由 albedo 结构 + 相位扰动呈现
        xx = np.linspace(0, 150, S, dtype=np.float32)[None, :]
        yy = np.linspace(0, 150, S, dtype=np.float32)[:, None]
        weave = 0.5 + 0.5 * np.sin((xx + 0.8 * ph) * np.pi) * np.sin((yy + 0.7 * ph) * np.pi)
        h = 0.50 * lum_s + 0.26 * weave + 0.18 * f_mid + 0.06 * hf
        del xx, yy, weave
    elif kind == "leather":
        pebble = blur(fbm(S, seed + 3303, 4, 96), 2.0)
        h = 0.34 * lum_s + 0.52 * pebble + 0.14 * hf
        del pebble
    elif kind == "metal":
        h = 0.62 * lum_s + 0.30 * f_mid + 0.08 * hf
    else:  # weave / rattan
        xx = np.linspace(0, 46, S, dtype=np.float32)[None, :]
        yy = np.linspace(0, 46, S, dtype=np.float32)[:, None]
        over = 0.5 + 0.5 * np.sin((xx + 0.5 * ph) * np.pi) * np.sin((yy + 0.4 * ph) * np.pi)
        h = 0.34 * lum_s + 0.52 * over + 0.14 * hf
        del xx, yy, over

    mn, mx = float(h.min()), float(h.max())
    out = np.clip((h - mn) / max(mx - mn, 1e-6), 0, 1).astype(np.float32)
    del lum, lum_s, f_mid, hf, ph, h
    return out


def normal_from_height_ds(h, strength):
    """降采样算梯度再放大：让 4K 图的梯度尺度与结构匹配，避免白噪主导法线。"""
    DS = 1024
    small = np.asarray(Image.fromarray((np.clip(h, 0, 1) * 255).astype(np.uint8), 'L')
                       .resize((DS, DS), Image.LANCZOS), dtype=np.float32) / 255.0
    gy, gx = np.gradient(small)
    nx, ny = -gx * strength, -gy * strength
    nz = np.ones_like(small)
    n = np.stack([nx, ny, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgb = n * 0.5 + 0.5
    up = np.asarray(Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), 'RGB')
                    .resize((SIZE, SIZE), Image.LANCZOS), dtype=np.float32) / 255.0
    return up


# ------------------------------------------------------------------ 主流程
def build_one(name, spec, idx):
    seed = 9000 + idx * 977
    print(f"[{idx+1}/{len(SPECS)}] {name}  src={'AI' if spec['src'] else 'proc'}", flush=True)

    rgb = load_ai(spec["src"], spec["kind"], seed) if spec["src"] else procedural_rgb(name, spec, seed)
    hf = highfreq(SIZE, seed + 5555)
    amp = 0.018 if spec["kind"] in ("glaze", "metal", "paint") else 0.032
    rgb = np.clip(rgb + amp * hf[..., None], 0, 1).astype(np.float32)
    del hf
    gc.collect()

    h_raw = build_height(rgb, spec, seed)
    h_detail = np.clip(blur(h_raw, 1.2), 0, 1)
    h = np.clip(blur(h_raw, 6.0), 0, 1)
    h = np.clip(0.5 + (h - 0.5) * 0.58, 0, 1).astype(np.float32)
    del h_raw
    gc.collect()

    # 色偏校准：把 albedo 均值拉向规格 tint，避免 AI 图偏色破坏场景配色
    target = np.array(spec["tint"], np.float32)
    cur = rgb.reshape(-1, 3).mean(0)
    gain = np.clip(target / np.maximum(cur, 1e-3), 0.55, 1.55)
    base = np.clip(rgb * gain[None, None, :], 0, 1)
    gray = base.mean(axis=2, keepdims=True)
    base = np.clip(gray + (base - gray) * 0.88, 0, 1)

    h_low = blur(h, 56)
    h_mid = blur(h, 14)

    cavity = np.clip(h_low - h_mid, 0, 1)
    ao = np.clip(1.0 - 1.2 * cavity, 0.80, 1.0)

    grime = np.clip(blur(fbm(SIZE, seed + 808, 4, 6), 20) - 0.48, 0, 1)
    micro = blur(0.5 + 0.5 * highfreq(SIZE, seed + 909), 1.5) - 0.5
    rough = (spec["rough"] + 0.13 * grime - 0.11 * (h_mid - 0.5) + 0.055 * micro)
    if spec["kind"] in ("glaze", "metal"):
        rough = spec["rough"] + 0.06 * grime + 0.022 * micro
    rough = np.clip(rough, 0.03, 0.98)

    if spec["metal"] > 0:
        metal = np.clip(spec["metal"] - 0.08 * grime + 0.015 * micro, 0, 1)
    else:
        metal = np.full((SIZE, SIZE), 0.008, np.float32)

    specu = np.clip(np.full((SIZE, SIZE), 0.5 if spec["metal"] == 0 else 0.12, np.float32)
                    - 0.05 * grime, 0, 1)

    strength = {"glaze": 2.6, "metal": 4.2, "stone": 5.0, "paint": 2.4,
                "tile": 5.2, "wood": 6.5, "fabric": 7.5, "leather": 7.0,
                "weave": 7.0}.get(spec["kind"], 5.0)
    nrm = normal_from_height_ds(h_detail, strength)

    height_out = h
    disp = np.clip(blur(h, 18), 0, 1)

    save_rgb(base, T(name, "basecolor"))
    save_rgb(nrm, T(name, "normal"))
    save_gray(rough, T(name, "roughness"))
    save_gray(metal, T(name, "metallic"))
    save_gray(ao, T(name, "ao"))
    save_gray(height_out, T(name, "height"))
    save_gray(disp, T(name, "displacement"))
    save_gray(specu, T(name, "specular"))
    print(f"    done  {name}  8ch @ {SIZE}", flush=True)

    del rgb, h, h_detail, height_out, base, ao, rough, metal, specu, nrm, disp
    del h_low, h_mid, cavity, grime, micro, gray, gain
    gc.collect()


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    items = [(n, s) for n, s in SPECS.items() if not only or n == only]
    if not items:
        print("UNKNOWN_MATERIAL", only); sys.exit(1)
    for i, (n, s) in enumerate(items):
        build_one(n, s, list(SPECS).index(n))
    print("TEXTURES_DONE", len(items), flush=True)
