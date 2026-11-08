"""01 程序化 PBR 资产库生成（Blender 4.5 / bpy headless）。

几何不是基础体拼装，而是按部件类型走对应的曲面 / 软体建模：
  - soft  : SDF 圆角盒 + 面中央鼓起 + 低频褶皱（坐垫 / 靠垫 / 软包 / 床垫）
  - cloth : 位移网格布料 + solidify（搭毯 / 毛巾 / 窗帘 / 地毯）
  - leaf  : 参数化叶片（叶尖 / 中脉 / 上卷 / 下垂），替代球体绿植
  - tube  : 沿路径圆管（杯把 / 龙头 / 拉手 / 提梁）
  - lathe : Catmull-Rom 平滑剖面旋转体（真实器型曲线）
  - piping: 沿边滚边缝线
  - 次级细节：铆钉 / 旋钮刻度 / 散热孔阵列 / 铭牌 / 圈足 / 螺纹 / 书脊页口 / 卡纸
  - 倒角 3 段 + WeightedNormal；材质加 Sheen(布艺) / Coat(釉面) / Anisotropic(拉丝) / Bevel 法线柔化

保持 36 类 / 144 个资产 ID 与 CATEGORIES 完全不变（house.blend 依赖）。
输出：assets/_library/asset_library.blend、assets/catalog.csv
"""
import bpy, bmesh, math, csv, os
from mathutils import Vector

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

OUT_BLEND = str(C.LIBRARY_BLEND)
OUT_CSV = str(C.CATALOG_CSV)

# ---------------------------------------------------------------- 清理场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != "Collection":
        bpy.data.collections.remove(c)
for m in list(bpy.data.materials):
    bpy.data.materials.remove(m)

# ---------------------------------------------------------------- 有机不规则工具
# 规则 sin(linspace) 或规则噪声生成的表面起伏轴对称、周期可辨，
# 放大看是「参数化」而非「手工」。这里改用确定性 fBm 值噪声：
# 连续、无镜像对称、无可见周期，且每个部件按 seed 取不同形态。
def _hash3(i, j, k, seed):
    h = (i * 374761393 + j * 668265263 + k * 1442695041
         + int(seed * 1000) * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def _vnoise(x, y, z, seed=0.0):
    """三线性插值值噪声，返回 0..1；格点 hash 无状态、可复现。"""
    i, j, k = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - i, y - j, z - k
    fx *= fx * (3 - 2 * fx); fy *= fy * (3 - 2 * fy); fz *= fz * (3 - 2 * fz)

    def L(a, b, t):
        return a + (b - a) * t

    c = [[[_hash3(i + di, j + dj, k + dk, seed)
           for dk in (0, 1)] for dj in (0, 1)] for di in (0, 1)]
    x00 = L(c[0][0][0], c[1][0][0], fx); x10 = L(c[0][1][0], c[1][1][0], fx)
    x01 = L(c[0][0][1], c[1][0][1], fx); x11 = L(c[0][1][1], c[1][1][1], fx)
    return L(L(x00, x10, fy), L(x01, x11, fy), fz)


def fbm3(x, y, z, seed=0.0, octaves=4):
    """多频 fBm，返回约 -1..1；2.07 倍频避免与格点周期对齐。"""
    s, amp, f = 0.0, 0.5, 1.0
    for o in range(octaves):
        s += amp * (_vnoise(x * f, y * f, z * f, seed + o * 17.31) * 2 - 1)
        amp *= 0.5
        f *= 2.07
    return s


_RELIEF_TEX = None


def micro_relief_texture():
    """共享的程序云纹，供 DISPLACE 修改器做真实顶点位移（非 BUMP / 非法线伪造）。

    用 GLOBAL 坐标：全屋共用同一噪声场，相邻部件不会重复同一块图案，
    且位移在网格上真实存在，导出 glTF / FBX / 其他渲染器都保留几何。
    """
    global _RELIEF_TEX
    if _RELIEF_TEX is None:
        t = bpy.data.textures.new("micro_relief_global", type='CLOUDS')
        t.noise_scale = 0.038
        t.noise_depth = 2
        t.noise_type = 'SOFT_NOISE'
        _RELIEF_TEX = t
    return _RELIEF_TEX


# ---------------------------------------------------------------- 材质系统
FABRIC_MATS = {"linen_fabric", "wool_fabric", "rattan", "leather"}
GLAZE_MATS = {"white_ceramic", "glazed_terracotta", "marble", "painted_wood", "floor_tile"}
METAL_MATS = {"brushed_steel", "brass", "black_steel"}

_mat_cache = {}


def _set(bs, key, val):
    try:
        bs.inputs[key].default_value = val
    except (KeyError, TypeError):
        pass


def pbr(name):
    """完整 8 通道 PBR（4K）。

    BaseColor x AO -> Base Color；Roughness/Metallic/Specular 直连；
    NormalMap(4K normal) -> Bump(4K height) -> BSDF Normal；
    Displacement 通道以 BUMP 方式接入（CPU 渲染不做真实细分位移）。
    不叠加 ShaderNodeTexNoise：4K 贴图已自带真实高频，
    再叠程序噪声只会制造点阵与塑料感。
    """
    if name in _mat_cache:
        return _mat_cache[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (1100, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.location = (760, 0)
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])

    # 改用世界坐标 Position + BOX 三平面投影。
    # Generated 坐标（每个部件各自 0..1）会把 4K 贴图在薄板/软包上
    # 拉伸成规则条纹（沙发上的波浪纹即由此而来），且部件间纹理密度不一致。
    # 世界坐标让全屋共用同一物理尺度的贴图场，薄板不再拉伸、重复感大幅降低。
    geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.location = (-1300, 0)
    mp = nt.nodes.new('ShaderNodeVectorMath'); mp.operation = 'SCALE'
    mp.inputs[3].default_value = 1.8; mp.location = (-1080, 0)
    nt.links.new(geo.outputs['Position'], mp.inputs[0])

    def tex(suffix, colorspace, y):
        pth = str(C.tex(name, suffix))
        n = nt.nodes.new('ShaderNodeTexImage'); n.location = (-820, y)
        n.label = suffix
        n.projection = 'BOX'                 # 三平面投影，无 UV 也不拉伸
        n.projection_blend = 0.15
        if os.path.exists(pth):
            img = bpy.data.images.load(pth, check_existing=True)
            img.colorspace_settings.name = colorspace
            n.image = img
            # 4K 贴图不打包进 .blend：改为相对路径引用，随仓库一起交付
            img.filepath = C.rel(C.tex(name, suffix), C.LIBRARY_BLEND)
        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
        return n

    bc = tex("basecolor", 'sRGB', 520)
    ao = tex("ao", 'Non-Color', 300)
    rgh = tex("roughness", 'Non-Color', 90)
    mtl = tex("metallic", 'Non-Color', -120)
    spc = tex("specular", 'Non-Color', -330)
    nrm = tex("normal", 'Non-Color', -540)
    hgt = tex("height", 'Non-Color', -750)
    dsp = tex("displacement", 'Non-Color', -960)

    glaze = name in GLAZE_MATS
    fabric = name in FABRIC_MATS

    # Base Color *= AO（凹陷积灰），AO 强度由 Mix factor 控制避免过度压暗
    mul = nt.nodes.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'
    mul.location = (-260, 480); mul.inputs[0].default_value = 0.78
    nt.links.new(bc.outputs['Color'], mul.inputs[1])
    nt.links.new(ao.outputs['Color'], mul.inputs[2])
    nt.links.new(mul.outputs['Color'], bs.inputs['Base Color'])

    nt.links.new(rgh.outputs['Color'], bs.inputs['Roughness'])
    nt.links.new(mtl.outputs['Color'], bs.inputs['Metallic'])
    nt.links.new(spc.outputs['Color'], bs.inputs['Specular IOR Level'])

    # 法线链：4K normal -> NormalMap -> Bump(4K height 微起伏) -> BSDF
    nmap = nt.nodes.new('ShaderNodeNormalMap'); nmap.location = (60, -420)
    nmap.inputs['Strength'].default_value = 0.30 if glaze else (0.62 if fabric else 0.52)
    nt.links.new(nrm.outputs['Color'], nmap.inputs['Color'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.location = (300, -420)
    bump.inputs['Strength'].default_value = 0.055 if glaze else 0.14
    bump.inputs['Distance'].default_value = 0.0025
    nt.links.new(hgt.outputs['Color'], bump.inputs['Height'])
    nt.links.new(nmap.outputs['Normal'], bump.inputs['Normal'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])

    # Displacement 通道：BUMP 模式（不做真实细分位移，CPU 可控）
    try:
        m.displacement_method = 'BUMP'
    except (AttributeError, TypeError):
        pass
    dn = nt.nodes.new('ShaderNodeDisplacement'); dn.location = (300, -700)
    dn.inputs['Scale'].default_value = 0.012
    dn.inputs['Midlevel'].default_value = 0.5
    nt.links.new(dsp.outputs['Color'], dn.inputs['Height'])
    nt.links.new(dn.outputs['Displacement'], out.inputs['Displacement'])

    # 分类质感
    if fabric:
        _set(bs, 'Sheen Weight', 0.42)
        _set(bs, 'Sheen Roughness', 0.62)
    if glaze:
        _set(bs, 'Coat Weight', 0.38)
        _set(bs, 'Coat Roughness', 0.12)
    if name in METAL_MATS:
        _set(bs, 'Anisotropic', 0.28)

    m.diffuse_color = (0.6, 0.6, 0.6, 1)
    _mat_cache[name] = m
    return m


SOLID = {}


def solid(name, rgba, rough=0.5, metal=0.0, transmission=0.0, emission=None):
    key = (name, rgba, rough, metal, transmission)
    if key in SOLID:
        return SOLID[key]
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs['Base Color'].default_value = rgba
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if transmission:
        bs.inputs['Transmission Weight'].default_value = transmission
        bs.inputs['IOR'].default_value = 1.45
    if emission:
        bs.inputs['Emission Color'].default_value = rgba
        bs.inputs['Emission Strength'].default_value = emission
    m.diffuse_color = rgba
    SOLID[key] = m
    return m


def _named_material(name, *args, **kwargs):
    """返回带真实材质名的可调用，供 spec['mat'] 引用与清单收集。

    直接用 lambda 时 __name__ 恒为 '<lambda>'，写进 catalog.csv / meta.json
    会变成无意义的占位串；工厂函数把名字挂到 __name__ 上即可根治。
    """
    def factory():
        return solid(name, *args, **kwargs)
    factory.__name__ = name
    return factory


GLASS  = _named_material("glass_clear", (0.92, 0.96, 0.98, 1), 0.06, 0.0, 0.92)
GREEN  = _named_material("plant_green", (0.20, 0.38, 0.16, 1), 0.72)
GREEN2 = _named_material("plant_green_2", (0.31, 0.48, 0.22, 1), 0.72)
GREEN3 = _named_material("plant_green_3", (0.16, 0.30, 0.13, 1), 0.75)
SOIL   = _named_material("soil", (0.16, 0.12, 0.09, 1), 0.95)
ACCENT = _named_material("accent_terracotta", (0.72, 0.36, 0.25, 1), 0.7)
WARM   = _named_material("warm_light", (1.0, 0.85, 0.62, 1), 0.4, emission=3.0)
PAPER  = _named_material("paper", (0.90, 0.87, 0.80, 1), 0.9)
BLACK  = _named_material("matte_black", (0.05, 0.05, 0.055, 1), 0.6)
SCREEN = _named_material("screen_dark", (0.03, 0.05, 0.07, 1), 0.16)


# ---------------------------------------------------------------- 网格生成器
def _recalc(me):
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()


def _mesh_obj(name, verts, faces, smooth=True):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    _recalc(me)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return me


def make_soft_box(name, size, n=8, radius=0.20, bulge=0.0, wrinkle=0.0, seed=0.0):
    """SDF 圆角盒 + 面中央鼓起 + 低频褶皱。用于软包 / 坐垫 / 靠垫 / 床垫。"""
    half = [s / 2 for s in size]
    g = min(half)
    r = max(0.02, min(0.95, radius))
    verts, faces = [], []
    vid = {}

    def addv(p):
        k = tuple(round(c, 5) for c in p)
        if k in vid:
            return vid[k]
        i = len(verts); verts.append(p); vid[k] = i
        return i

    for axis in range(3):
        for sign in (-1, 1):
            others = [a for a in range(3) if a != axis]
            ua, va = others
            grid = []
            for i in range(n + 1):
                u = -1 + 2 * i / n
                row = []
                for j in range(n + 1):
                    v = -1 + 2 * j / n
                    p = [0.0, 0.0, 0.0]
                    p[axis] = float(sign); p[ua] = u; p[va] = v
                    q = [max(-(1 - r), min(1 - r, c)) for c in p]
                    d = [p[k] - q[k] for k in range(3)]
                    L = math.sqrt(sum(c * c for c in d)) or 1.0
                    nv = [c / L for c in d]
                    base = [q[k] + r * nv[k] for k in range(3)]
                    mask = (1 - u * u) * (1 - v * v)
                    amt = g * bulge * mask
                    # 有机起伏：确定性 fBm 值噪声，每个部件按 seed 得到不同形态，
                    # 连续、无镜像对称、无可见周期（不用规则 sin 波）。
                    amt += g * 0.020 * fbm3(u * 1.35 + seed * 0.83,
                                            v * 1.35 - seed * 0.51,
                                            float(sign) * 1.9 + seed * 0.27,
                                            seed=seed, octaves=3) * mask
                    if wrinkle:
                        amt += g * wrinkle * fbm3(u * 3.1 + seed * 0.9,
                                                  v * 3.1 + seed * 1.7,
                                                  float(sign) * 2.6 + seed,
                                                  seed=seed + 5.3, octaves=4) * mask
                    # 重力塌陷：靠边缘略微下坠，打破完美对称
                    edge = max(abs(u), abs(v))
                    amt -= g * 0.014 * (edge ** 4) * mask
                    # 使用压痕：seed 决定位置的局部久坐凹陷
                    pu, pv = 0.22 * math.sin(seed * 2.7), 0.22 * math.cos(seed * 3.9)
                    dent = math.exp(-((u - pu) ** 2 + (v - pv) ** 2) / 0.10)
                    amt -= g * 0.020 * dent * mask
                    # base 是 [-1,1] 相对坐标，鼓起量 amt 为米，沿外法线叠加
                    pos = [base[k] * half[k] + nv[k] * amt for k in range(3)]
                    row.append(addv(pos))
                grid.append(row)
            for i in range(n):
                for j in range(n):
                    faces.append((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    return _mesh_obj(name, verts, faces)


def make_cloth(name, w, d, n=16, amp=0.03, seed=0.0, drape=0.0):
    """位移布料网格（双层起伏），配 solidify 形成有厚度的织物。"""
    verts, faces = [], []
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        for j in range(n + 1):
            y = -d / 2 + d * j / n
            u, v = i / n, j / n
            # 主褶皱保留悬垂方向性，但叠加 fBm 打破可见周期与左右对称
            fold = (math.sin(u * math.pi * 3.2 + seed) * math.cos(v * math.pi * 2.4 + seed * 0.7)
                    + 0.45 * math.sin(u * math.pi * 6.0 + v * math.pi * 3.1 + seed * 1.3))
            organic = fbm3(u * 4.2 + seed * 1.1, v * 4.2 - seed * 0.7, seed * 0.3,
                           seed=seed, octaves=4)
            z = amp * (0.55 * fold + 0.75 * organic)
            # 边缘自然下垂
            z -= drape * (abs(2 * u - 1) ** 2 + abs(2 * v - 1) ** 2)
            verts.append((x, y, z))
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            faces.append((a, a + (n + 1), a + (n + 1) + 1, a + 1))
    return _mesh_obj(name, verts, faces)


def make_leaf(name, length=0.18, width=0.075, curl=0.02, n=10, m=4, seed=0.0):
    """参数化叶片：叶尖收窄 + 中脉隆起 + 叶尖下垂 + 扭转 + fBm 不对称扰动。"""
    verts, faces = [], []
    for i in range(n + 1):
        t = i / n
        w = width * (math.sin(math.pi * t) ** 0.7) * (1 - 0.12 * t) + 1e-5
        for j in range(m + 1):
            s = -1 + 2 * j / m
            x = s * w
            y = t * length
            z = curl * (t ** 2) + 0.014 * (1 - s * s) * math.sin(math.pi * t)
            z -= 0.16 * length * (t ** 3)
            x += 0.012 * length * math.sin(t * math.pi * 1.4) * (1 - s * s)
            # 叶缘/叶面轻微不规则，打破完美双侧对称
            z += 0.0035 * fbm3(s * 2.1, t * 3.7, seed, seed=seed, octaves=3)
            x += 0.0040 * fbm3(s * 3.1 + seed, t * 2.2, 1.7,
                               seed=seed + 2.1, octaves=3) * (1 - abs(s))
            verts.append((x, y, z))
    for i in range(n):
        for j in range(m):
            a = i * (m + 1) + j
            faces.append((a, a + (m + 1), a + (m + 1) + 1, a + 1))
    return _mesh_obj(name, verts, faces)


def make_tube(name, points, radius=0.01, sides=10):
    """沿折线路径生成圆管，用于杯把 / 龙头 / 拉手 / 提梁。"""
    pts = [Vector(p) for p in points]
    verts, faces = [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1))
        if abs(t.dot(up)) > 0.94:
            up = Vector((1, 0, 0))
        u = t.cross(up).normalized(); v = t.cross(u).normalized()
        for s in range(sides):
            a = 2 * math.pi * s / sides
            q = p + radius * (math.cos(a) * u + math.sin(a) * v)
            verts.append(tuple(q))
    for i in range(len(pts) - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            faces.append((i * sides + s, i * sides + s2,
                          (i + 1) * sides + s2, (i + 1) * sides + s))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(pts) - 1) * sides + s for s in range(sides)))
    return _mesh_obj(name, verts, faces)


def catmull_rom(ctrl, sub=5):
    """把稀疏剖面控制点插值成平滑曲线（闭合首尾不插值）。"""
    out = []
    P = [Vector((c[0], c[1])) for c in ctrl]
    for i in range(len(P) - 1):
        p0 = P[max(0, i - 1)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(len(P) - 1, i + 2)]
        for k in range(sub):
            t = k / sub
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t
                       + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append((max(0.0, q.x), q.y))
    out.append(tuple(P[-1]))
    return out


def make_lathe(name, profile, segments=64, smooth_ctrl=True, seed=0.0):
    prof = catmull_rom(profile, 5) if smooth_ctrl and len(profile) >= 3 else profile
    verts, faces = [], []
    n = len(prof)
    for (r, z) in prof:
        for s in range(segments):
            a = 2 * math.pi * s / segments
            # 手工拉坯感：半径随角度/高度微扰，打破完美旋转对称。
            # 用 cos/sin 作噪声坐标可保证 0 与 2π 处连续，旋转体无接缝。
            wobble = 1.0 + 0.010 * fbm3(math.cos(a) * 1.7 + seed,
                                        math.sin(a) * 1.7,
                                        z * 26.0 + seed * 0.3,
                                        seed=seed + 1.3, octaves=3)
            rr = r * wobble
            zz = z + 0.0008 * fbm3(math.cos(a) * 2.3, math.sin(a) * 2.3,
                                   z * 18.0, seed=seed + 7.1, octaves=2)
            verts.append((rr * math.cos(a), rr * math.sin(a), zz))
    for i in range(n - 1):
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append((i * segments + s, i * segments + s2,
                          (i + 1) * segments + s2, (i + 1) * segments + s))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple((n - 1) * segments + s for s in range(segments)))
    return _mesh_obj(name, verts, faces)


def vessel_profile(r, h, t, style="bowl"):
    """闭合旋转剖面控制点：内底 -> 内壁 -> 口沿 -> 外壁 -> 外底。曲线插值后成型。"""
    if style == "plate":
        return [(0, t), (r * 0.42, t * 0.9), (r * 0.72, h * 0.30), (r * 0.92, h * 0.78),
                (r, h), (r + t * 0.7, h * 0.96), (r * 0.86, -t * 0.22), (r * 0.40, -t * 0.30), (0, -t * 0.30)]
    if style == "bottle":
        nr = r * 0.36
        return [(0, t), (r * 0.78, t), (r * 0.96, h * 0.08), (r, h * 0.30), (r * 0.97, h * 0.55),
                (r * 0.72, h * 0.72), (nr, h * 0.82), (nr, h * 0.97),
                (nr + t, h * 1.0), (nr + t, h * 0.82), (r * 0.78, h * 0.70),
                (r + t, h * 0.53), (r + t, h * 0.10), (r * 0.88, 0), (0, 0)]
    if style == "cyl":
        return [(0, t), (r * 0.86, t), (r * 0.95, h * 0.06), (r, h * 0.30), (r, h * 0.82),
                (r * 0.97, h * 0.97), (r + t, h), (r + t, h * 0.28),
                (r * 0.97, h * 0.04), (r * 0.86, 0), (0, 0)]
    if style == "vase":
        return [(0, t), (r * 0.62, t), (r * 0.90, h * 0.10), (r, h * 0.34),
                (r * 0.86, h * 0.62), (r * 0.62, h * 0.84), (r * 0.66, h * 0.97),
                (r * 0.66 + t, h), (r * 0.70 + t, h * 0.84), (r * 0.94, h * 0.62),
                (r + t, h * 0.34), (r * 0.94, h * 0.08), (r * 0.60, 0), (0, 0)]
    return [(0, t), (r * 0.55, t * 0.95), (r * 0.82, h * 0.22), (r * 0.97, h * 0.62),
            (r, h), (r + t, h * 0.96), (r * 0.94, h * 0.40),
            (r * 0.70, -t * 0.18), (0, -t * 0.18)]


def rect_path(w, d, z, inset=0.0):
    a, b = w / 2 - inset, d / 2 - inset
    return [(-a, -b, z), (a, -b, z), (a, b, z), (-a, b, z), (-a, -b, z)]


def P(shape, mat, **kw):
    return dict(shape=shape, mat=mat, **kw)


def build_part(spec, col, prefix, idx):
    shape, mat = spec["shape"], spec["mat"]
    pos = spec.get("pos", (0, 0, 0))
    rot = spec.get("rot", (0, 0, 0))
    bv = spec.get("bevel", 0.008)
    name = f"{prefix}_p{idx:02d}_{shape}"
    smooth_shapes = ("lathe", "cyl", "sph", "torus", "soft", "cloth", "leaf", "tube")

    if shape == "soft":
        me = make_soft_box(name, spec.get("size", (0.2, 0.2, 0.1)),
                           n=spec.get("n", 12), radius=spec.get("radius", 0.24),
                           bulge=spec.get("bulge", 0.12), wrinkle=spec.get("wrinkle", 0.0),
                           seed=spec.get("seed", idx * 1.7))
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    elif shape == "cloth":
        me = make_cloth(name, spec.get("w", 0.4), spec.get("d", 0.3),
                        n=spec.get("n", 16), amp=spec.get("amp", 0.03),
                        seed=spec.get("seed", idx * 2.3), drape=spec.get("drape", 0.0))
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
        sol = ob.modifiers.new("fabric_thickness", 'SOLIDIFY')
        sol.thickness = spec.get("thick", 0.010)
        sol.offset = 0.0
    elif shape == "leaf":
        me = make_leaf(name, spec.get("length", 0.18), spec.get("width", 0.075),
                       curl=spec.get("curl", 0.02), seed=spec.get("seed", idx * 1.7))
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
        sol = ob.modifiers.new("leaf_thickness", 'SOLIDIFY')
        sol.thickness = 0.0022
    elif shape == "tube":
        me = make_tube(name, spec["points"], spec.get("r", 0.010), spec.get("sides", 10))
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    elif shape == "lathe":
        me = make_lathe(name, spec["profile"], spec.get("segments", 64),
                        spec.get("smooth_ctrl", True), seed=spec.get("seed", idx * 1.7))
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    else:
        if shape == "box":
            s = spec.get("size", (0.1, 0.1, 0.1))
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            ob = bpy.context.object
            ob.scale = s
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        elif shape == "cyl":
            bpy.ops.mesh.primitive_cylinder_add(vertices=spec.get("verts", 48),
                                                radius=spec.get("r", 0.05),
                                                depth=spec.get("depth", 0.1))
            ob = bpy.context.object
        elif shape == "cone":
            bpy.ops.mesh.primitive_cone_add(vertices=spec.get("verts", 48),
                                            radius1=spec.get("r1", 0.05),
                                            radius2=spec.get("r2", 0.03),
                                            depth=spec.get("depth", 0.1))
            ob = bpy.context.object
        elif shape == "sph":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=spec.get("verts", 32),
                                                 ring_count=20, radius=spec.get("r", 0.05))
            ob = bpy.context.object
        elif shape == "torus":
            bpy.ops.mesh.primitive_torus_add(major_segments=spec.get("verts", 48),
                                             minor_segments=12,
                                             major_radius=spec.get("r", 0.05),
                                             minor_radius=spec.get("tube", 0.006))
            ob = bpy.context.object
        elif shape == "plane":
            s = spec.get("size", (0.1, 0.1))
            bpy.ops.mesh.primitive_plane_add(size=1.0)
            ob = bpy.context.object
            ob.scale = (s[0], s[1], 1)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        else:
            raise ValueError(shape)
        ob.name = name
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        col.objects.link(ob)

    ob.location = pos
    ob.rotation_euler = rot
    mm = mat() if callable(mat) else pbr(mat) if isinstance(mat, str) else mat
    ob.data.materials.append(mm)

    if bv and shape in ("box", "cyl", "cone"):
        mod = ob.modifiers.new("edge_bevel", 'BEVEL')
        mod.width = min(bv, 0.03); mod.segments = 3
        mod.limit_method = 'ANGLE'
        ob.modifiers.new("weighted_normal", 'WEIGHTED_NORMAL')
    # 真实顶点位移（DISPLACE 修改器），不依赖 Cycles、不是 BUMP / 法线伪造。
    # GLOBAL 坐标让全屋共用同一噪声场，实例摆到不同位置后位移形态自然不同。
    if shape in ("soft", "cloth", "leaf"):
        disp = ob.modifiers.new("micro_relief", 'DISPLACE')
        disp.texture = micro_relief_texture()
        disp.texture_coords = 'GLOBAL'
        disp.strength = 0.0030 if shape == "soft" else (0.0018 if shape == "cloth" else 0.0007)
        disp.mid_level = 0.5
    if spec.get("shade_smooth", True) and shape in smooth_shapes:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


# ---------------------------------------------------------------- 构件生成器
def chair(p):
    m, m2 = p["mat"], p.get("mat2", p["mat"])
    w, h = p.get("w", 0.46), p.get("h", 0.9)
    sh, st = 0.45, 0.042
    parts = [
        P("soft", m, size=(w, w * 0.95, 0.055), pos=(0, 0, sh),
          radius=0.16, bulge=0.10, wrinkle=0.012),
        P("cone", m, r1=st * 0.62, r2=st * 0.44, depth=sh,
          pos=(-w / 2 + st, -w / 2 + st, sh / 2)),
        P("cone", m, r1=st * 0.62, r2=st * 0.44, depth=sh,
          pos=(w / 2 - st, -w / 2 + st, sh / 2)),
        P("cone", m, r1=st * 0.62, r2=st * 0.44, depth=sh,
          pos=(-w / 2 + st, w / 2 - st, sh / 2)),
        P("cone", m, r1=st * 0.62, r2=st * 0.44, depth=sh,
          pos=(w / 2 - st, w / 2 - st, sh / 2)),
        P("box", m2, size=(w - 2 * st, 0.030, h - sh - 0.10),
          pos=(0, -w / 2 + st, sh + (h - sh - 0.10) / 2), bevel=0.012),
        P("soft", m, size=(w - 0.02, 0.045, 0.20), pos=(0, -w / 2 + st, h - 0.14),
          radius=0.30, bulge=0.14),
        P("tube", m2, points=rect_path(w - 0.06, w * 0.95 - 0.06, sh + 0.032, 0.0),
          r=0.0035),
        P("box", m2, size=(w - 2 * st, 0.022, 0.022), pos=(0, 0, sh * 0.28)),
        P("box", m2, size=(0.022, 0.022, w * 0.86), pos=(-w / 2 + st, 0, sh * 0.28)),
    ]
    return parts


def table(p):
    m, m2 = p["mat"], p.get("mat2", "black_steel")
    w, d, h = p.get("w", 1.4), p.get("d", 0.8), p.get("h", 0.75)
    tt, lg = 0.042, 0.046
    parts = [
        P("soft", m, size=(w, d, tt), pos=(0, 0, h), radius=0.035, bulge=0.0),
        P("box", m, size=(w - 0.05, d - 0.05, 0.018), pos=(0, 0, h - tt / 2 - 0.012), bevel=0.006),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(P("cone", m2, r1=lg * 0.62, r2=lg * 0.40, depth=h - tt,
                           pos=(sx * (w / 2 - lg * 1.5), sy * (d / 2 - lg * 1.5), (h - tt) / 2)))
    parts += [
        P("box", m2, size=(w - 3 * lg, 0.020, 0.020), pos=(0, -d / 2 + lg * 1.5, h * 0.30)),
        P("box", m2, size=(w - 3 * lg, 0.020, 0.020), pos=(0, d / 2 - lg * 1.5, h * 0.30)),
        P("tube", m2, points=rect_path(w - 0.02, d - 0.02, h + tt / 2 + 0.001), r=0.003),
    ]
    return parts


def sofa(p):
    """软包沙发：分块坐垫 + 圆角扶手 + 靠背软包 + 滚边缝线 + 锥形木脚 + 靠垫。"""
    m, m2 = p["mat"], p.get("mat2", "oak_wood")
    w, d = p.get("w", 2.1), p.get("d", 0.88)
    parts = [
        P("soft", m, size=(w, d, 0.24), pos=(0, 0, 0.30), radius=0.13, bulge=0.06),
        P("soft", m, size=(w, 0.22, 0.50), pos=(0, -d / 2 + 0.11, 0.60),
          radius=0.19, bulge=0.14, wrinkle=0.010),
        P("soft", m, size=(0.22, d - 0.10, 0.40), pos=(-w / 2 + 0.11, 0, 0.55),
          radius=0.22, bulge=0.14),
        P("soft", m, size=(0.22, d - 0.10, 0.40), pos=(w / 2 - 0.11, 0, 0.55),
          radius=0.22, bulge=0.14),
    ]
    cw = (w - 0.48) / 2
    for i, cx in enumerate((-cw / 2 - 0.02, cw / 2 + 0.02)):
        parts.append(P("soft", p.get("cushion", m),
                       size=(cw - 0.02, d - 0.34, 0.13), pos=(cx, 0.06, 0.47),
                       radius=0.32, bulge=0.20, wrinkle=0.022, seed=i * 3.1))
        parts.append(P("tube", m2,
                       points=rect_path(cw - 0.06, d - 0.40, 0.47, 0.0),
                       r=0.0035))
    for i, cx in enumerate((-cw / 2 - 0.02, cw / 2 + 0.02)):
        parts.append(P("soft", p.get("cushion", m),
                       size=(cw - 0.10, 0.14, 0.38), pos=(cx, -d / 2 + 0.24, 0.68),
                       radius=0.34, bulge=0.22, wrinkle=0.02, seed=7 + i * 2.2,
                       rot=(math.radians(-8), 0, 0)))
    parts.append(P("tube", m2, points=rect_path(w - 0.04, d - 0.04, 0.415), r=0.004))
    # 靠背 channel tufting：竖向缝线分格 + 每格一枚包布纽扣，
    # 让软包从「一块圆角盒」变成有缝制结构的家具。
    yf = -d / 2 - 0.017
    for i in range(1, 6):
        xx = -w / 2 + 0.11 + (w - 0.22) * i / 6
        parts.append(P("tube", m2, points=[(xx, yf, 0.42), (xx, yf, 0.80)], r=0.0026))
        parts.append(P("cyl", m2, r=0.009, depth=0.006,
                       pos=(xx, yf - 0.004, 0.61), rot=(math.pi / 2, 0, 0)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(P("cone", m2, r1=0.032, r2=0.020, depth=0.16,
                           pos=(sx * (w / 2 - 0.14), sy * (d / 2 - 0.14), 0.08)))
    return parts


def cabinet(p):
    m, m2 = p["mat"], p.get("mat2", "brass")
    w, d, h = p.get("w", 1.2), p.get("d", 0.42), p.get("h", 0.85)
    t = 0.024
    parts = [
        P("soft", m, size=(w, d, h), pos=(0, 0, h / 2), radius=0.025, bulge=0.0, n=5),
        P("box", m, size=(w + 0.02, d + 0.02, 0.028), pos=(0, 0, h + 0.008), bevel=0.008),
        P("box", m, size=(w - 2 * t, t, h - 2 * t), pos=(0, -d / 2 + t / 2, h / 2), bevel=0.005),
    ]
    n = p.get("drawers", 2)
    for i in range(n):
        dh = (h - 0.06) / n
        zc = 0.03 + dh * (i + 0.5)
        parts.append(P("soft", p.get("front", m),
                       size=(w - 0.07, 0.022, dh - 0.018), pos=(0, d / 2 + 0.012, zc),
                       radius=0.09, bulge=0.05, n=5))
        # 拉手：弯管 + 两端底座
        hw = min(0.16, w * 0.28)
        pts = [(-hw / 2, d / 2 + 0.020, zc), (-hw / 2, d / 2 + 0.055, zc),
               (hw / 2, d / 2 + 0.055, zc), (hw / 2, d / 2 + 0.020, zc)]
        parts.append(P("tube", m2, points=pts, r=0.0065))
        parts.append(P("cyl", m2, r=0.011, depth=0.010,
                       pos=(-hw / 2, d / 2 + 0.020, zc), rot=(math.pi / 2, 0, 0)))
        parts.append(P("cyl", m2, r=0.011, depth=0.010,
                       pos=(hw / 2, d / 2 + 0.020, zc), rot=(math.pi / 2, 0, 0)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(P("cone", m2, r1=0.024, r2=0.016, depth=0.10,
                           pos=(sx * (w / 2 - 0.09), sy * (d / 2 - 0.08), 0.05)))
    return parts


def bed(p):
    m, fab = p["mat"], p.get("fabric", "linen_fabric")
    w, d = p.get("w", 1.8), p.get("d", 2.0)
    parts = [
        P("soft", m, size=(w, d, 0.28), pos=(0, 0, 0.22), radius=0.07, bulge=0.02),
        P("soft", m, size=(w + 0.10, 0.10, 1.0), pos=(0, -d / 2, 0.62), radius=0.12, bulge=0.06),
        P("box", m, size=(w + 0.10, 0.07, 0.42), pos=(0, d / 2, 0.35), bevel=0.014),
        P("soft", fab, size=(w - 0.08, d - 0.10, 0.20), pos=(0, 0, 0.45),
          radius=0.16, bulge=0.10),
        # 床单参数 z=0.565 / amp=0.035 / drape=0.02 会让最低点约 0.51，
        # 会穿进下面的软包床垫（顶面约 0.56）形成 Z-fighting —— 渲染里表现为
        # 床垫上一块块浅灰绿「污渍」。抬高并收窄起伏，让床单明确浮在床垫之上。
        P("cloth", p.get("sheet", "wall_paint"), w=w - 0.04, d=d * 0.62,
          amp=0.015, drape=0.006, seed=1.2, thick=0.012,
          pos=(0, d * 0.16, 0.588)),
        P("soft", fab, size=(0.66, 0.40, 0.14), pos=(-0.36, -d / 2 + 0.30, 0.64),
          radius=0.40, bulge=0.22, wrinkle=0.014),
        P("soft", fab, size=(0.66, 0.40, 0.14), pos=(0.36, -d / 2 + 0.30, 0.64),
          radius=0.40, bulge=0.22, wrinkle=0.014, seed=3.4),
        P("tube", fab, points=rect_path(w - 0.04, d - 0.06, 0.552), r=0.005),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(P("cone", m, r1=0.035, r2=0.024, depth=0.16,
                           pos=(sx * (w / 2 - 0.04), sy * (d / 2 - 0.04), 0.08)))
    return parts


def storage(p):
    m, m2 = p["mat"], p.get("mat2", "brass")
    w, d, h = p.get("w", 0.44), p.get("d", 0.34), p.get("h", 0.32)
    arc = [(w * 0.24 * math.cos(a), d / 2 + 0.012, h * 0.78 + 0.045 * math.sin(a))
           for a in [math.pi * k / 8 for k in range(9)]]
    parts = [
        P("soft", m, size=(w, d, h), pos=(0, 0, h / 2), radius=0.10, bulge=0.03, n=6),
        P("box", p.get("lid", m), size=(w + 0.018, d + 0.018, 0.026),
          pos=(0, 0, h + 0.006), bevel=0.010),
        P("tube", m2, points=rect_path(w + 0.01, d + 0.01, h + 0.020), r=0.004),
        # 正面编织感横条
        P("box", m2, size=(w * 0.72, 0.008, 0.012), pos=(0, d / 2 + 0.004, h * 0.62)),
        P("box", m2, size=(w * 0.72, 0.008, 0.012), pos=(0, d / 2 + 0.004, h * 0.42)),
        # 皮质提手（弯管 + 两端铆钉）
        P("tube", m2, points=arc, r=0.006),
        P("cyl", m2, r=0.010, depth=0.008,
          pos=(w * 0.24, d / 2 + 0.008, h * 0.78), rot=(math.pi / 2, 0, 0)),
        P("cyl", m2, r=0.010, depth=0.008,
          pos=(-w * 0.24, d / 2 + 0.008, h * 0.78), rot=(math.pi / 2, 0, 0)),
    ]
    return parts


def lamp(p):
    m, shade = p["mat"], p.get("shade", "linen_fabric")
    h = p.get("h", 1.5)
    parts = [
        P("lathe", m, profile=vessel_profile(0.15, 0.038, 0.008, "plate"), pos=(0, 0, 0.0)),
        P("cyl", m, r=0.011, depth=h - 0.30, pos=(0, 0, (h - 0.30) / 2 + 0.03)),
        P("lathe", shade, profile=[(0.075, 0), (0.085, 0.02), (0.16, 0.16), (0.21, 0.30),
                                   (0.21, 0.31), (0.155, 0.17), (0.08, 0.025), (0.07, 0)],
          pos=(0, 0, h - 0.34)),
        P("torus", m, r=0.208, tube=0.005, pos=(0, 0, h - 0.34 + 0.30)),
        P("torus", m, r=0.078, tube=0.004, pos=(0, 0, h - 0.34)),
        P("sph", WARM, r=0.048, pos=(0, 0, h - 0.16)),
        P("cyl", m, r=0.020, depth=0.10, pos=(0, 0, h - 0.02)),
        P("tube", m, points=[(0.02, 0, h - 0.02), (0.05, 0, h - 0.10),
                             (0.05, 0, h - 0.20)], r=0.0025),
    ]
    return parts


def appliance(p):
    """厨电：圆角箱体 + 门缝 + 玻璃视窗 + 旋钮刻度 + 散热孔阵列 + 把手 + 铭牌。"""
    m, m2 = p["mat"], p.get("mat2", "black_steel")
    w, d, h = p.get("w", 0.60), p.get("d", 0.60), p.get("h", 0.60)
    parts = [
        P("soft", m, size=(w, d, h), pos=(0, 0, h / 2), radius=0.045, bulge=0.0, n=6),
        P("box", m2, size=(w - 0.05, 0.014, h * 0.56), pos=(0, d / 2 + 0.010, h * 0.55), bevel=0.006),
        P("box", GLASS, size=(w - 0.13, 0.008, h * 0.34), pos=(0, d / 2 + 0.020, h * 0.56), bevel=0.003),
        P("tube", "brushed_steel", points=rect_path(w - 0.12, h * 0.35, 0, 0), r=0.004,
          rot=(math.pi / 2, 0, 0), pos=(0, d / 2 + 0.024, h * 0.56 + 0.0)),
        P("box", SCREEN, size=(w - 0.14, 0.006, 0.032), pos=(0, d / 2 + 0.023, h * 0.87)),
    ]
    # 把手（横管 + 双支座）
    hy = d / 2 + 0.045
    parts += [
        P("cyl", "brushed_steel", r=0.012, depth=w - 0.16,
          pos=(0, hy, h * 0.34), rot=(0, math.pi / 2, 0)),
        P("cyl", "brushed_steel", r=0.010, depth=0.045,
          pos=(-(w - 0.16) / 2, d / 2 + 0.024, h * 0.34), rot=(math.pi / 2, 0, 0)),
        P("cyl", "brushed_steel", r=0.010, depth=0.045,
          pos=((w - 0.16) / 2, d / 2 + 0.024, h * 0.34), rot=(math.pi / 2, 0, 0)),
    ]
    # 旋钮 + 12 个刻度点
    kx = w / 2 - 0.09
    parts.append(P("cyl", "brushed_steel", r=0.024, depth=0.022,
                   pos=(kx, d / 2 + 0.024, h * 0.30), rot=(math.pi / 2, 0, 0)))
    parts.append(P("cyl", m2, r=0.018, depth=0.026,
                   pos=(kx, d / 2 + 0.030, h * 0.30), rot=(math.pi / 2, 0, 0)))
    for k in range(12):
        a = 2 * math.pi * k / 12
        parts.append(P("cyl", m2, r=0.0018, depth=0.003,
                       pos=(kx + 0.031 * math.cos(a), d / 2 + 0.024, h * 0.30 + 0.031 * math.sin(a)),
                       rot=(math.pi / 2, 0, 0)))
    # 散热孔阵列
    for k in range(7):
        parts.append(P("box", BLACK, size=(w * 0.42, 0.003, 0.0035),
                       pos=(-0.04, d / 2 + 0.024, h * 0.10 + k * 0.011), bevel=0))
    # 铭牌
    parts.append(P("box", "brass", size=(0.075, 0.003, 0.016),
                   pos=(-w / 2 + 0.10, d / 2 + 0.024, h * 0.90), bevel=0.002))
    parts.append(P("box", m2, size=(w, 0.02, 0.03), pos=(0, d / 2 + 0.014, h * 0.42), bevel=0.004))
    return parts


def pot(p):
    m, m2 = p["mat"], p.get("mat2", "brushed_steel")
    r, h = p.get("r", 0.13), p.get("h", 0.12)
    parts = [
        P("lathe", m, profile=vessel_profile(r, h, 0.005, "cyl"), pos=(0, 0, 0)),
        P("torus", m2, r=r + 0.004, tube=0.0055, pos=(0, 0, h * 0.98)),
        P("cyl", m2, r=r * 0.97, depth=0.006, pos=(0, 0, 0.003)),
        P("lathe", p.get("lid", m2), profile=vessel_profile(r + 0.010, 0.030, 0.004, "plate"),
          pos=(0, 0, h + 0.018), rot=(math.pi, 0, 0)),
        P("cyl", m2, r=0.016, depth=0.014, pos=(0, 0, h + 0.052)),
        P("sph", m2, r=0.020, pos=(0, 0, h + 0.066)),
    ]
    # 双侧耳 + 铆钉
    for s in (-1, 1):
        arc = [(s * (r + 0.012 + 0.055 * math.sin(math.pi * k / 8)), 0,
                h * 0.76 + 0.018 * math.cos(math.pi * k / 8)) for k in range(9)]
        parts.append(P("tube", m2, points=arc, r=0.008))
        for k in (0.30, 0.70):
            parts.append(P("sph", m2, r=0.005,
                           pos=(s * (r + 0.006), 0, h * k)))
    return parts


def plate(p):
    m, r = p["mat"], p.get("r", 0.13)
    h = p.get("h", 0.028)
    parts = [
        P("lathe", m, profile=vessel_profile(r, h, 0.005, "plate"), pos=(0, 0, 0)),
        P("torus", p.get("rim", m), r=r * 0.93, tube=0.0032, pos=(0, 0, h * 0.88)),
        P("torus", m, r=r * 0.34, tube=0.0022, pos=(0, 0, -h * 0.26)),
        P("cyl", m, r=r * 0.44, depth=0.003, pos=(0, 0, 0.0015)),
    ]
    return parts


def cup(p):
    m, r, h = p["mat"], p.get("r", 0.042), p.get("h", 0.095)
    R = h * 0.21
    cx, cz = r + R * 0.55, h * 0.53
    arc = [(r * 0.96, 0, h * 0.72)]
    for k in range(9):
        a = -math.pi / 2 + math.pi * k / 8
        arc.append((cx + R * math.cos(a), 0, cz + R * math.sin(a)))
    arc.append((r * 0.96, 0, h * 0.34))
    return [
        P("lathe", m, profile=vessel_profile(r, h, 0.004, "cyl"), pos=(0, 0, 0)),
        P("tube", p.get("handle", m), points=arc, r=0.0065),
        P("cyl", p.get("liquid", "walnut_wood"), r=r * 0.86, depth=0.002, pos=(0, 0, h * 0.70)),
        P("torus", m, r=r * 0.96, tube=0.0028, pos=(0, 0, h * 0.985)),
        P("cyl", m, r=r * 0.72, depth=0.003, pos=(0, 0, -0.001)),
    ]


def bottle(p):
    m, r, h = p["mat"], p.get("r", 0.055), p.get("h", 0.26)
    parts = [
        P("lathe", m, profile=vessel_profile(r, h, 0.004, "bottle"), pos=(0, 0, 0)),
        P("cyl", p.get("cap", "brass"), r=r * 0.40, depth=0.026, pos=(0, 0, h + 0.008)),
        P("torus", p.get("ring", m), r=r * 0.40, tube=0.003, pos=(0, 0, h * 0.96)),
        P("torus", p.get("ring", m), r=r * 0.40, tube=0.0025, pos=(0, 0, h * 0.90)),
        P("box", PAPER, size=(r * 1.25, 0.0015, h * 0.24), pos=(0, r * 0.99, h * 0.34), bevel=0.001),
        P("box", m, size=(r * 0.9, 0.002, 0.008), pos=(0, r * 1.005, h * 0.40), bevel=0),
    ]
    return parts


def sink(p):
    m, m2 = p["mat"], p.get("mat2", "brushed_steel")
    w, d = p.get("w", 0.58), p.get("d", 0.44)
    spout = [(0, -d / 2 + 0.06, 0.86), (0, -d / 2 + 0.06, 1.06),
             (0, -d / 2 + 0.10, 1.12), (0, -d / 2 + 0.16, 1.12),
             (0, -d / 2 + 0.19, 1.08)]
    return [
        P("box", m, size=(w, d, 0.014), pos=(0, 0, 0.86), bevel=0.006),
        P("soft", m2, size=(w - 0.08, d - 0.08, 0.17), pos=(0, 0, 0.775),
          radius=0.10, bulge=0.0, n=6),
        P("box", p.get("inner", m2), size=(w - 0.13, d - 0.13, 0.008),
          pos=(0, 0, 0.700), bevel=0.004),
        P("tube", m2, points=spout, r=0.014),
        P("cyl", m2, r=0.026, depth=0.012, pos=(0, -d / 2 + 0.06, 0.872)),
        P("cyl", m2, r=0.028, depth=0.010, pos=(0, 0, 0.706)),
        P("torus", m2, r=0.020, tube=0.003, pos=(0, 0, 0.712)),
        P("box", m2, size=(0.055, 0.018, 0.012), pos=(0.11, -d / 2 + 0.06, 0.875), bevel=0.003),
    ]


def sanitary(p):
    m, w = p["mat"], p.get("w", 0.55)
    spout = [(0, -w / 2 - 0.02, 0.86), (0, -w / 2 - 0.02, 1.02),
             (0, -w / 2 + 0.02, 1.06), (0, -w / 2 + 0.07, 1.04)]
    return [
        P("lathe", m, profile=vessel_profile(w / 2, 0.17, 0.010, "bowl"), pos=(0, 0, 0.82)),
        P("lathe", m, profile=vessel_profile(0.10, 0.42, 0.010, "cyl"), pos=(0, 0, 0.0)),
        P("cyl", m, r=0.20, depth=0.03, pos=(0, 0, 0.015)),
        P("tube", "brushed_steel", points=spout, r=0.012),
        P("cyl", "brushed_steel", r=0.020, depth=0.010, pos=(0, -w / 2 - 0.02, 0.868)),
        P("cyl", m, r=0.016, depth=0.010, pos=(0, 0, 0.845)),
        P("torus", m, r=w / 2 - 0.008, tube=0.004, pos=(0, 0, 0.985)),
        P("box", "brushed_steel", size=(0.030, 0.085, 0.014),
          pos=(0.10, -w / 2 - 0.05, 1.09), bevel=0.004),
    ]


def door(p):
    m, m2 = p["mat"], p.get("mat2", "brass")
    w, h = p.get("w", 0.90), 2.10
    parts = [
        P("box", m, size=(w, 0.045, h), pos=(0, 0, h / 2), bevel=0.010),
        P("soft", p.get("panel", "wall_paint"),
          size=(w - 0.16, 0.010, h - 0.28), pos=(0, 0.028, h / 2),
          radius=0.06, bulge=0.02, n=5),
        P("tube", m, points=rect_path(w - 0.14, h - 0.26, 0, 0), r=0.004,
          rot=(math.pi / 2, 0, 0), pos=(0, 0.034, h / 2)),
        P("box", m, size=(w + 0.10, 0.09, 0.08), pos=(0, 0, 2.14), bevel=0.008),
        P("box", m, size=(0.08, 0.09, 2.18), pos=(-w / 2 - 0.04, 0, 1.09), bevel=0.008),
        P("box", m, size=(0.08, 0.09, 2.18), pos=(w / 2 + 0.04, 0, 1.09), bevel=0.008),
        P("cyl", m2, r=0.026, depth=0.018, pos=(w / 2 - 0.10, 0.050, 1.02),
          rot=(math.pi / 2, 0, 0)),
        P("tube", m2, points=[(w / 2 - 0.10, 0.060, 1.02),
                              (w / 2 - 0.10, 0.060, 0.96),
                              (w / 2 - 0.10, 0.060, 0.94)], r=0.009),
        P("box", m2, size=(0.030, 0.008, 0.11), pos=(-w / 2 - 0.005, 0.05, 1.65), bevel=0.002),
        P("box", m2, size=(0.030, 0.008, 0.11), pos=(-w / 2 - 0.005, 0.05, 0.45), bevel=0.002),
    ]
    return parts


def window(p):
    m, w, h = p["mat"], p.get("w", 1.6), p.get("h", 1.5)
    t = 0.05
    parts = [
        P("box", m, size=(t, 0.10, h), pos=(-w / 2, 0, h / 2), bevel=0.006),
        P("box", m, size=(t, 0.10, h), pos=(w / 2, 0, h / 2), bevel=0.006),
        P("box", m, size=(w, 0.10, t), pos=(0, 0, 0), bevel=0.006),
        P("box", m, size=(w, 0.10, t), pos=(0, 0, h), bevel=0.006),
        P("box", m, size=(t * 0.6, 0.08, h), pos=(0, 0, h / 2), bevel=0.004),
        P("box", m, size=(w, 0.08, t * 0.6), pos=(0, 0, h / 2), bevel=0.004),
        P("box", GLASS, size=(w - t, 0.006, h - t), pos=(0, 0, h / 2), bevel=0.002),
        P("box", m, size=(w + 0.16, 0.18, 0.04), pos=(0, 0, -0.05), bevel=0.008),
        P("tube", m, points=rect_path(w - t, h - t, 0, 0), r=0.003,
          rot=(math.pi / 2, 0, 0), pos=(0, 0.005, h / 2)),
        P("cyl", "brass", r=0.014, depth=0.02,
          pos=(w / 2 - 0.10, 0.07, h / 2), rot=(math.pi / 2, 0, 0)),
    ]
    return parts


def hardware(p):
    m = p["mat"]
    return [
        P("lathe", m, profile=[(0, 0), (0.020, 0), (0.022, 0.006), (0.016, 0.012),
                               (0.010, 0.024), (0.0, 0.026)], pos=(0, 0, 0),
          rot=(math.pi / 2, 0, 0)),
        P("sph", m, r=0.016, pos=(0, 0.052, 0)),
        P("tube", m, points=[(-0.05, 0.045, 0), (-0.05, 0.062, 0),
                             (0.05, 0.062, 0), (0.05, 0.045, 0)], r=0.0065),
        P("cyl", m, r=0.009, depth=0.006, pos=(-0.05, 0.045, 0), rot=(math.pi / 2, 0, 0)),
        P("cyl", m, r=0.009, depth=0.006, pos=(0.05, 0.045, 0), rot=(math.pi / 2, 0, 0)),
        P("cyl", m, r=0.0022, depth=0.002, pos=(0, 0.068, 0), rot=(math.pi / 2, 0, 0)),
    ]


def electronics(p):
    m = p["mat"]
    w, h = p.get("w", 1.2), p.get("h", 0.70)
    parts = [
        P("soft", m, size=(w, 0.05, h), pos=(0, 0, h / 2 + 0.12),
          radius=0.10, bulge=0.0, n=5),
        P("box", BLACK, size=(w - 0.03, 0.006, h - 0.03),
          pos=(0, 0.029, h / 2 + 0.12), bevel=0.002),
        P("box", SCREEN, size=(w - 0.05, 0.003, h - 0.05),
          pos=(0, 0.033, h / 2 + 0.12), bevel=0.001),
        P("box", m, size=(0.24, 0.16, 0.02), pos=(0, -0.02, 0.13), bevel=0.006),
        P("cyl", m, r=0.012, depth=0.10, pos=(0, 0, 0.06)),
        P("box", m, size=(0.05, 0.16, 0.012), pos=(0, -0.06, 0.01), bevel=0.004),
    ]
    for k in range(4):
        parts.append(P("box", BLACK, size=(0.018, 0.003, 0.006),
                       pos=(-w / 2 + 0.10 + k * 0.024, 0.034, 0.16), bevel=0))
    return parts


def plant(p):
    """绿植：陶盆 lathe + 土 + 弯曲茎 + 参数化叶片 + 侧芽。"""
    m, potm = p["mat"], p.get("pot", "glazed_terracotta")
    r, h = p.get("r", 0.16), p.get("h", 0.60)
    parts = [
        P("lathe", potm, profile=vessel_profile(r, h * 0.42, 0.008, "cyl"), pos=(0, 0, 0)),
        P("torus", potm, r=r + 0.004, tube=0.006, pos=(0, 0, h * 0.42)),
        P("cyl", SOIL, r=r * 0.90, depth=0.012, pos=(0, 0, h * 0.40)),
        P("tube", m, points=[(0, 0, h * 0.40), (0.006, 0, h * 0.55),
                             (0.012, 0.004, h * 0.72), (0.008, 0.008, h * 0.90)],
          r=0.008),
    ]
    leafsets = [
        (0.0, 0.10, h * 0.72, 25, 18, 0.95),
        (1.7, -0.09, h * 0.66, -22, 24, 0.82),
        (3.0, 0.06, h * 0.82, 32, -16, 0.88),
        (4.4, -0.05, h * 0.78, -28, -22, 0.80),
        (5.5, 0.02, h * 0.94, 40, 8, 0.70),
        (0.9, 0.11, h * 0.56, 18, 34, 0.72),
        (2.4, -0.11, h * 0.90, -34, 10, 0.66),
    ]
    for k, (az, tiltx, z, rotz, rotx, sc) in enumerate(leafsets):
        parts.append(P("leaf", GREEN if k % 3 else GREEN2 if k % 3 == 1 else GREEN3,
                       length=h * 0.42 * sc, width=r * 0.62 * sc,
                       curl=0.018 * sc,
                       pos=(0.01, 0.006, z),
                       rot=(math.radians(tiltx * 6), math.radians(rotx), math.radians(az * 57.3))))
    parts.append(P("sph", GREEN3, r=r * 0.22, pos=(0.008, 0.008, h * 0.93)))
    return parts


def books(p):
    m = p["mat"]
    parts = [
        P("soft", m, size=(0.17, 0.245, 0.030), pos=(0, 0, 0.015), radius=0.05, bulge=0.0, n=5),
        P("box", PAPER, size=(0.155, 0.230, 0.022), pos=(0.004, 0.002, 0.016), bevel=0.002),
        P("soft", p.get("m2", "leather"), size=(0.155, 0.225, 0.026),
          pos=(0.008, 0.008, 0.041), radius=0.05, bulge=0.0, n=5),
        P("box", PAPER, size=(0.142, 0.212, 0.019), pos=(0.012, 0.010, 0.042), bevel=0.002),
        P("soft", m, size=(0.175, 0.235, 0.028), pos=(0.005, 0.005, 0.068),
          radius=0.05, bulge=0.0, n=5, rot=(0, 0, 0.10)),
        P("box", PAPER, size=(0.160, 0.220, 0.021), pos=(0.009, 0.007, 0.069),
          bevel=0.002, rot=(0, 0, 0.10)),
        P("box", "brass", size=(0.006, 0.226, 0.002),
          pos=(-0.070, 0.006, 0.030), bevel=0),
        P("box", "brass", size=(0.006, 0.226, 0.002),
          pos=(-0.065, 0.010, 0.083), bevel=0),
        P("box", p.get("m2", "leather"), size=(0.010, 0.22, 0.001),
          pos=(0.055, 0.0, 0.0835), bevel=0, rot=(0, 0, 0.10)),
    ]
    return parts


def decor(p):
    m = p["mat"]
    parts = [
        P("lathe", m, profile=vessel_profile(0.075, 0.20, 0.006, "vase"), pos=(0, 0, 0)),
        P("torus", p.get("m2", "brass"), r=0.050, tube=0.003, pos=(0, 0, 0.155)),
        P("torus", m, r=0.068, tube=0.004, pos=(0, 0, 0.198)),
        P("cyl", m, r=0.086, depth=0.012, pos=(0, 0, -0.004)),
    ]
    for k, (dx, hh, ang) in enumerate([(-0.02, 0.34, -12), (0.025, 0.30, 15), (0.0, 0.38, 2)]):
        parts.append(P("tube", p.get("m2", "brass"),
                       points=[(0, 0, 0.18), (dx * 0.4, 0, 0.24),
                               (dx, 0.004, hh)], r=0.0028))
        parts.append(P("sph", ACCENT, r=0.010, pos=(dx, 0.004, hh)))
    return parts


def frame(p):
    m, w, h = p["mat"], p.get("w", 0.70), p.get("h", 0.90)
    t = 0.035
    parts = [
        P("box", m, size=(t, 0.03, h), pos=(-w / 2, 0, h / 2), bevel=0.004),
        P("box", m, size=(t, 0.03, h), pos=(w / 2, 0, h / 2), bevel=0.004),
        P("box", m, size=(w, 0.03, t), pos=(0, 0, 0), bevel=0.004),
        P("box", m, size=(w, 0.03, t), pos=(0, 0, h), bevel=0.004),
        P("box", PAPER, size=(w - 2 * t, 0.004, h - 2 * t), pos=(0, 0.016, h / 2), bevel=0.001),
        P("box", p.get("art", "wall_paint"),
          size=(w - 2 * t - 0.07, 0.006, h - 2 * t - 0.07), pos=(0, 0.020, h / 2), bevel=0.001),
        P("box", ACCENT, size=(w * 0.34, 0.008, h * 0.28), pos=(0.05, 0.024, h * 0.55), bevel=0.002),
        P("box", "brass", size=(w * 0.16, 0.008, h * 0.10), pos=(-0.09, 0.024, h * 0.34), bevel=0.002),
        P("tube", m, points=rect_path(w - 0.01, h - 0.01, 0, 0), r=0.0025,
          rot=(math.pi / 2, 0, 0), pos=(0, 0.017, h / 2)),
    ]
    return parts


def rug(p):
    m, w, d = p["mat"], p.get("w", 2.0), p.get("d", 1.4)
    parts = [
        P("cloth", m, w=w, d=d, amp=0.012, seed=2.1, thick=0.016, pos=(0, 0, 0.009)),
        P("box", p.get("border", "wool_fabric"), size=(w + 0.02, d + 0.02, 0.005),
          pos=(0, 0, 0.003), bevel=0.002),
        P("box", m, size=(w * 0.58, d * 0.46, 0.003), pos=(0, 0, 0.019), bevel=0.001),
    ]
    for k in range(9):
        x = -w / 2 + 0.05 + k * (w - 0.10) / 8
        parts.append(P("tube", m, points=[(x, -d / 2 - 0.002, 0.008),
                                          (x, -d / 2 - 0.045, 0.006)], r=0.003))
        parts.append(P("tube", m, points=[(x, d / 2 + 0.002, 0.008),
                                          (x, d / 2 + 0.045, 0.006)], r=0.003))
    return parts


def cushion(p):
    m, w = p["mat"], p.get("w", 0.44)
    return [
        P("soft", m, size=(w, w, 0.13), pos=(0, 0, 0.065),
          radius=0.30, bulge=0.24, wrinkle=0.020, seed=1.1),
        P("tube", p.get("m2", m), points=rect_path(w - 0.02, w - 0.02, 0.065), r=0.0045),
        # 顶面双针脚：包边内侧再走一圈细缝线
        P("tube", p.get("m2", m), points=rect_path(w - 0.06, w - 0.06, 0.128), r=0.0018),
        P("cyl", m, r=0.013, depth=0.006, pos=(0, 0, 0.137)),
        P("cyl", m, r=0.013, depth=0.006, pos=(0, 0, -0.004)),
        P("tube", p.get("m2", m),
          points=[(-w * 0.10, -w * 0.10, 0.139), (0, 0, 0.145),
                  (w * 0.10, w * 0.10, 0.139)], r=0.002),
    ]


def towel(p):
    m = p["mat"]
    parts = [
        P("cloth", m, w=0.36, d=0.24, amp=0.030, drape=0.018, seed=3.2,
          thick=0.014, pos=(0, 0, 0.016)),
        P("cloth", m, w=0.34, d=0.075, amp=0.020, seed=5.1,
          thick=0.014, pos=(0.008, 0.10, 0.048)),
        P("box", p.get("stripe", "wool_fabric"), size=(0.36, 0.020, 0.002),
          pos=(0, -0.06, 0.032), bevel=0),
        P("box", p.get("stripe", "wool_fabric"), size=(0.36, 0.010, 0.002),
          pos=(0, -0.085, 0.032), bevel=0),
    ]
    for k in range(7):
        parts.append(P("box", m, size=(0.006, 0.002, 0.010),
                       pos=(-0.15 + k * 0.05, -0.122, 0.014), bevel=0))
    return parts


def utensil(p):
    m = p["mat"]
    return [
        P("soft", m, size=(0.030, 0.055, 0.008), pos=(0, -0.088, 0),
          radius=0.44, bulge=0.18, n=6),
        P("box", m, size=(0.016, 0.16, 0.004), pos=(0, 0.005, 0), bevel=0.002),
        P("soft", m, size=(0.014, 0.035, 0.004), pos=(0, 0.095, 0),
          radius=0.40, bulge=0.10, n=5),
        P("tube", m, points=[(-0.007, 0.085, 0.002), (-0.007, 0.12, 0.002),
                             (0.007, 0.12, 0.002), (0.007, 0.085, 0.002)], r=0.0016),
    ]


def cleaning(p):
    m, m2 = p["mat"], p.get("mat2", "black_steel")
    handle = [(0.10, 0, 0.34), (0.10, 0, 0.60), (0.09, 0, 0.84), (0.08, 0, 0.88)]
    return [
        P("lathe", m, profile=vessel_profile(0.14, 0.32, 0.006, "cyl"), pos=(0, 0, 0)),
        P("torus", m2, r=0.143, tube=0.008, pos=(0, 0, 0.32)),
        P("tube", m2, points=handle, r=0.010),
        P("box", m2, size=(0.20, 0.055, 0.045), pos=(0.08, 0, 0.89), bevel=0.006),
        P("tube", m2, points=[(-0.14, 0, 0.30), (-0.16, 0, 0.38),
                              (0.16, 0, 0.38), (0.14, 0, 0.30)], r=0.006),
        P("cyl", m2, r=0.012, depth=0.006, pos=(0, 0, -0.004)),
        P("box", m2, size=(0.10, 0.006, 0.02), pos=(0, 0.142, 0.20), bevel=0.002),
    ]


def outdoor(p):
    m, m2 = p["mat"], p.get("mat2", "oak_wood")
    parts = [
        P("soft", m2, size=(0.60, 0.58, 0.04), pos=(0, 0, 0.44), radius=0.06, bulge=0.0),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(P("cone", m, r1=0.028, r2=0.020, depth=0.44,
                           pos=(sx * 0.26, sy * 0.25, 0.22)))
    parts += [
        P("soft", m, size=(0.56, 0.045, 0.44), pos=(0, -0.28, 0.68), radius=0.14, bulge=0.06),
        P("soft", p.get("cushion", "linen_fabric"),
          size=(0.50, 0.50, 0.09), pos=(0, 0, 0.50), radius=0.24, bulge=0.16, wrinkle=0.016),
        P("tube", m, points=rect_path(0.50, 0.50, 0.50), r=0.0035),
    ]
    return parts


def office(p):
    m, m2 = p["mat"], p.get("mat2", "black_steel")
    parts = [
        P("soft", m, size=(1.20, 0.60, 0.038), pos=(0, 0, 0.74), radius=0.03, bulge=0.0),
        P("box", m, size=(1.10, 0.006, 0.006), pos=(0, 0, 0.716), bevel=0.001),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(P("cone", m2, r1=0.030, r2=0.022, depth=0.72,
                           pos=(sx * 0.55, sy * 0.25, 0.37)))
    parts += [
        P("soft", m, size=(0.30, 0.40, 0.30), pos=(0.40, 0, 0.92), radius=0.05, bulge=0.0, n=5),
        P("tube", p.get("m3", "brass"),
          points=[(0.40, 0.21, 1.00), (0.40, 0.24, 1.00)], r=0.006),
        P("lathe", p.get("m3", "brass"),
          profile=vessel_profile(0.035, 0.09, 0.004, "cyl"), pos=(-0.42, 0.10, 0.76)),
        P("tube", "brass", points=[(-0.42, 0.10, 0.85), (-0.40, 0.12, 0.95),
                                   (-0.38, 0.13, 1.02)], r=0.0025),
    ]
    return parts


def structural(p):
    m, l = p["mat"], p.get("l", 2.4)
    return [
        P("box", m, size=(l, 0.10, 0.10), pos=(0, 0, 0.05), bevel=0.008),
        P("box", p.get("m2", m), size=(l, 0.02, 0.012), pos=(0, 0.051, 0.085), bevel=0.003),
        P("box", m, size=(0.10, 0.10, 2.60), pos=(-l / 2, 0, 1.30), bevel=0.008),
        P("box", m, size=(0.10, 0.10, 2.60), pos=(l / 2, 0, 1.30), bevel=0.008),
        P("box", p.get("m2", m), size=(l, 0.14, 0.08), pos=(0, 0, 2.56), bevel=0.006),
        P("box", p.get("m2", m), size=(l, 0.03, 0.02), pos=(0, 0.08, 2.50), bevel=0.003),
    ]


def misc(p):
    m = p["mat"]
    parts = [
        P("lathe", m, profile=vessel_profile(0.13, 0.038, 0.006, "plate"), pos=(0, 0, 0)),
        P("torus", m, r=0.126, tube=0.004, pos=(0, 0, 0.036)),
        P("sph", ACCENT, r=0.038, pos=(-0.04, 0.01, 0.055)),
        P("sph", GREEN2, r=0.034, pos=(0.045, -0.02, 0.052)),
        P("sph", ACCENT, r=0.032, pos=(0.02, 0.055, 0.050)),
        P("leaf", GREEN3, length=0.07, width=0.022, curl=0.01,
          pos=(0.02, 0.055, 0.078), rot=(0.3, 0.2, 0.6)),
        P("tube", GREEN, points=[(0.02, 0.055, 0.078), (0.02, 0.058, 0.10)], r=0.002),
    ]
    return parts


def container(p):
    m, m2 = p["mat"], p.get("mat2", "brass")
    r, h = p.get("r", 0.09), p.get("h", 0.20)
    parts = [
        P("lathe", m, profile=vessel_profile(r, h, 0.006, "cyl"), pos=(0, 0, 0)),
        P("torus", m2, r=r + 0.001, tube=0.004, pos=(0, 0, h * 0.96)),
        P("lathe", m2, profile=vessel_profile(r + 0.006, 0.030, 0.005, "plate"),
          pos=(0, 0, h + 0.006), rot=(math.pi, 0, 0)),
        P("sph", m2, r=0.016, pos=(0, 0, h + 0.040)),
        P("torus", m2, r=r + 0.002, tube=0.003, pos=(0, 0, h * 0.30)),
    ]
    for s in (-1, 1):
        parts.append(P("box", m2, size=(0.012, 0.006, 0.030),
                       pos=(s * (r + 0.008), 0, h + 0.004), bevel=0.002))
        parts.append(P("cyl", m2, r=0.003, depth=0.008,
                       pos=(s * (r + 0.008), 0, h * 0.55), rot=(0, math.pi / 2, 0)))
    return parts


BUILDERS = dict(chair=chair, table=table, sofa=sofa, cabinet=cabinet, bed=bed,
                storage=storage, lamp=lamp, appliance=appliance, pot=pot,
                plate=plate, cup=cup, bottle=bottle, sink=sink, sanitary=sanitary,
                door=door, window=window, hardware=hardware, electronics=electronics,
                plant=plant, books=books, decor=decor, frame=frame, rug=rug,
                cushion=cushion, towel=towel, utensil=utensil, cleaning=cleaning,
                outdoor=outdoor, office=office, structural=structural, misc=misc,
                container=container)


# ---------------------------------------------------------------- 36 类定义（每类 4 变体 = 144）
def V(mat, **kw):
    return dict(mat=mat, **kw)


CATEGORIES = [
    ("01", "餐椅 Seating", "chair", [V("oak_wood", mat2="oak_wood"), V("walnut_wood", mat2="walnut_wood"),
                                    V("painted_wood", mat2="painted_wood"), V("rattan", mat2="black_steel", w=0.44)]),
    ("02", "桌案 Tables", "table", [V("oak_wood"), V("walnut_wood", mat2="brass"),
                                    V("marble", mat2="black_steel", w=1.6, d=0.9), V(GLASS, mat2="brushed_steel", w=1.2, d=0.7)]),
    ("03", "沙发 Sofas", "sofa", [V("linen_fabric", cushion="wool_fabric"), V("wool_fabric", cushion="linen_fabric"),
                                  V("leather", mat2="walnut_wood"), V("linen_fabric", mat2="oak_wood", w=1.5)]),
    ("04", "柜体 Cabinets", "cabinet", [V("oak_wood", drawers=2), V("walnut_wood", drawers=3),
                                        V("painted_wood", front="oak_wood"), V("black_steel", front=GLASS, mat2="brass")]),
    ("05", "床具 Beds", "bed", [V("oak_wood", fabric="linen_fabric"), V("walnut_wood", fabric="wool_fabric", w=1.5),
                                V("painted_wood", fabric="linen_fabric", w=1.2), V("leather", fabric="wool_fabric", w=2.0)]),
    ("06", "收纳与布艺 StorageTextile", "storage", [V("rattan", lid="oak_wood"), V("linen_fabric", lid="wool_fabric"),
                                                     V("painted_wood", mat2="brass"), V("wool_fabric", lid="leather", w=0.36, h=0.26)]),
    ("07", "灯具 Lighting", "lamp", [V("brass", shade="linen_fabric", h=1.5), V("black_steel", shade="painted_wood", h=1.7),
                                     V("white_ceramic", shade="linen_fabric", h=0.55), V("rattan", shade="rattan", h=1.4)]),
    ("08", "厨电 Appliances", "appliance", [V("brushed_steel", w=0.60, h=0.60), V("black_steel", w=0.60, h=0.85),
                                            V("painted_wood", w=0.45, h=0.50), V("brushed_steel", mat2="brass", w=0.90, h=0.75)]),
    ("09", "锅具 Cookware", "pot", [V("brushed_steel", lid="brushed_steel"), V("black_steel", lid=GLASS, r=0.15, h=0.10),
                                    V("glazed_terracotta", lid="glazed_terracotta", r=0.12), V("brass", lid="brass", r=0.09, h=0.09)]),
    ("10", "餐具 Tableware", "plate", [V("white_ceramic", r=0.13), V("glazed_terracotta", r=0.11, h=0.045),
                                       V("marble", r=0.16, h=0.022), V("black_steel", rim="brass", r=0.12)]),
    ("11", "杯具 Drinkware", "cup", [V("white_ceramic"), V("glazed_terracotta", handle="walnut_wood"),
                                     V(GLASS, handle=GLASS, liquid=GLASS), V("brushed_steel", r=0.036, h=0.11)]),
    ("12", "瓶器 Vessels", "bottle", [V("white_ceramic", cap="brass"), V("glazed_terracotta", cap="oak_wood", h=0.32),
                                      V(GLASS, cap="brass", r=0.045), V("brass", cap="black_steel", r=0.06, h=0.22)]),
    ("13", "水槽龙头 Sinks", "sink", [V("brushed_steel"), V("black_steel", mat2="brass"),
                                      V("white_ceramic", mat2="brushed_steel", w=0.50), V("brass", mat2="brass", w=0.66)]),
    ("14", "洁具 Sanitary", "sanitary", [V("white_ceramic", w=0.55), V("white_ceramic", w=0.48),
                                         V("marble", w=0.60), V("glazed_terracotta", w=0.52)]),
    ("15", "门 Doors", "door", [V("oak_wood"), V("walnut_wood", mat2="black_steel"),
                                V("painted_wood", panel=GLASS), V("black_steel", panel=GLASS, mat2="brass", w=1.0)]),
    ("16", "窗 Windows", "window", [V("painted_wood", w=1.6, h=1.5), V("black_steel", w=2.0, h=1.8),
                                    V("oak_wood", w=1.2, h=1.2), V("brushed_steel", w=2.4, h=2.1)]),
    ("17", "五金 Hardware", "hardware", [V("brass"), V("black_steel"), V("brushed_steel"), V("white_ceramic")]),
    ("18", "电子 Electronics", "electronics", [V("black_steel", w=1.2), V("black_steel", w=0.9, h=0.5),
                                               V("brushed_steel", w=1.4, h=0.8), V("black_steel", w=0.35, h=0.22)]),
    ("19", "绿植 Plants", "plant", [V(GREEN, pot="glazed_terracotta", h=0.60), V(GREEN, pot="white_ceramic", h=0.85),
                                    V(GREEN, pot="rattan", h=0.45), V(GREEN, pot="concrete_floor", h=1.10)]),
    ("20", "书本 Books", "books", [V("leather", m2="oak_wood"), V("linen_fabric", m2="walnut_wood"),
                                   V("painted_wood", m2="leather"), V("walnut_wood", m2="linen_fabric")]),
    ("21", "装饰摆件 Decor", "decor", [V("white_ceramic"), V("brass", m2="black_steel"),
                                       V("marble", m2="brass"), V(GLASS, m2="brass")]),
    ("22", "挂画 WallArt", "frame", [V("oak_wood", art="linen_fabric"), V("walnut_wood", art="wall_paint"),
                                     V("black_steel", art="marble"), V("brass", art="wool_fabric", w=0.5, h=0.7)]),
    ("23", "地毯 Rugs", "rug", [V("wool_fabric", border="linen_fabric"), V("linen_fabric", border="wool_fabric"),
                                V("leather", border="wool_fabric", w=1.6, d=1.1), V("rattan", border="rattan", w=1.2, d=0.8)]),
    ("24", "窗帘 Curtains", "towel", [V("linen_fabric", stripe="wool_fabric"), V("wool_fabric", stripe="linen_fabric"),
                                      V("painted_wood", stripe="linen_fabric"), V("linen_fabric", stripe="leather")]),
    ("25", "靠垫 Cushions", "cushion", [V("linen_fabric", m2="wool_fabric"), V("wool_fabric", m2="linen_fabric"),
                                        V("leather", m2="linen_fabric"), V("rattan", m2="linen_fabric", w=0.38)]),
    ("26", "毛巾织物 Towels", "towel", [V("linen_fabric"), V("wool_fabric", stripe="leather"),
                                        V("painted_wood", stripe="wool_fabric"), V("linen_fabric", stripe="rattan")]),
    ("27", "餐具小件 Utensils", "utensil", [V("brushed_steel"), V("brass"), V("oak_wood"), V("black_steel")]),
    ("28", "调味容器 Condiments", "bottle", [V(GLASS, cap="oak_wood", r=0.035, h=0.18),
                                             V("white_ceramic", cap="black_steel", r=0.045, h=0.14),
                                             V("brushed_steel", cap="brass", r=0.04, h=0.20),
                                             V("glazed_terracotta", cap="oak_wood", r=0.05, h=0.16)]),
    ("29", "清洁用品 Cleaning", "cleaning", [V("brushed_steel"), V("painted_wood", mat2="black_steel"),
                                             V("rattan", mat2="oak_wood"), V("black_steel", mat2="brass")]),
    ("30", "厨具 KitchenTools", "utensil", [V("brushed_steel"), V("oak_wood"), V("black_steel"),
                                            V("glazed_terracotta")]),
    ("31", "户外阳台 Outdoor", "outdoor", [V("rattan", mat2="oak_wood"), V("oak_wood", mat2="black_steel"),
                                           V("brushed_steel", mat2="brushed_steel"), V("painted_wood", mat2="oak_wood")]),
    ("32", "办公 Office", "office", [V("oak_wood"), V("black_steel", m3="brass"),
                                     V("leather", m3="brass"), V("painted_wood", m3="black_steel")]),
    ("33", "卫浴配件 BathAcc", "hardware", [V("brass"), V("brushed_steel"), V("black_steel"), V("white_ceramic")]),
    ("34", "结构件 Structural", "structural", [V("painted_wood", l=2.4), V("oak_wood", l=3.0),
                                               V("concrete_floor", l=2.4), V("walnut_wood", l=1.8)]),
    ("35", "生活杂项 Misc", "misc", [V("white_ceramic"), V("oak_wood"), V(GLASS), V("brass")]),
    ("36", "收纳容器 Containers", "container", [V("rattan", mat2="oak_wood"), V("painted_wood", mat2="brass"),
                                                V("brushed_steel", mat2="black_steel"), V("glazed_terracotta", mat2="brass")]),
]

VARIANT_NAMES = ["A", "B", "C", "D"]


def bbox_of(objs):
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            mn = Vector((min(mn[i], w[i]) for i in range(3)))
            mx = Vector((max(mx[i], w[i]) for i in range(3)))
    return tuple(round(mx[i] - mn[i], 3) for i in range(3))


def main():
    scene = bpy.context.scene
    root = bpy.data.collections.new("ASTRA_PBR_ASSET_LIBRARY")
    scene.collection.children.link(root)
    rows = []
    total_parts = 0
    total_verts = 0

    for no, cname, builder_name, variants in CATEGORIES:
        cat = bpy.data.collections.new(f"CAT_{no}_{cname.split()[0]}")
        root.children.link(cat)
        for vi, vpar in enumerate(variants, start=1):
            name_en = cname.split()[0]
            aid = f"AST_{no}_{vi:03d}_{name_en}_{VARIANT_NAMES[vi-1]}"
            acol = bpy.data.collections.new(aid)
            cat.children.link(acol)
            specs = BUILDERS[builder_name](vpar)
            objs = [build_part(s, acol, aid, i) for i, s in enumerate(specs)]
            bpy.context.view_layer.update()
            dims = bbox_of(objs)
            total_verts += sum(len(o.data.vertices) for o in objs)
            mats = sorted({(s["mat"] if isinstance(s["mat"], str) else
                            (s["mat"].__name__ if callable(s["mat"]) else "material"))
                           for s in specs})
            rows.append(dict(id=aid, category_no=no, category=cname, name=name_en,
                             variant=VARIANT_NAMES[vi - 1], builder=builder_name,
                             dimensions_m="x".join(str(d) for d in dims),
                             materials="|".join(mats), parts=len(specs), collection=aid))
            total_parts += len(specs)

    # 4K x 8 通道共 128 张贴图（约 1.6GB），不打包进 .blend：
    # 贴图以 //../_textures/<材质>/ 相对路径引用，与 assets/_textures/ 一并交付，工程保持轻量。
    for im in bpy.data.images:
        if im.source == 'FILE' and im.filepath:
            tgt = C.tex_by_name(os.path.basename(im.filepath))
            if tgt and tgt.exists():
                im.filepath = C.rel(tgt, C.LIBRARY_BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print("ASSETS", len(rows), "CATEGORIES", len(CATEGORIES), "PARTS", total_parts)
    print("MIN_PARTS", min(r["parts"] for r in rows))
    print("AVG_PARTS", round(total_parts / len(rows), 2))
    print("TOTAL_VERTS", total_verts)
    print("BLEND_SIZE_MB", round(os.path.getsize(OUT_BLEND) / 1e6, 2))
    print("ASSET_LIBRARY_DONE")


if __name__ == "__main__":
    main()
