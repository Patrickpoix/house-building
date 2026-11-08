"""02 100 ㎡ 住宅搭建（Blender 4.5 / bpy headless）。

设计：温暖日光 · 现代自然风（橡木 + 亚麻 + 白墙 + 绿植 + 黄铜点睛），
与参考视频的雨夜暗调厨房明确区分。

平面：10.0m × 10.0m = 100 ㎡ 建筑面积，层高 2.8m。
家具全部以 asset_library.blend 里的 Collection 实例引用（Q13），不重造模型。

输出：scene/house.blend、docs/06_平面布局.md、scene/placement.json
"""
import bpy, math, os, json, csv, random
from mathutils import Vector

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

LIB = str(C.LIBRARY_BLEND)
MANIFEST = str(C.CATALOG_CSV)
OUT_BLEND = str(C.HOUSE_BLEND)

H = 2.80           # 层高
WALL_T = 0.16      # 内墙厚
WALL_T_EXT = 0.24  # 外墙厚
EXT = 5.0          # 半边长 -> 10m

# ---------------------------------------------------------------- 场景清理
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != "Collection" and not c.objects and not c.children:
        bpy.data.collections.remove(c)

scene = bpy.context.scene


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


STRUCT = coll("HOUSE_Structure")
FURN = coll("HOUSE_Furniture_Instances")
LIGHTS = coll("HOUSE_Lighting")
CAMS = coll("HOUSE_Cameras")
DECO = coll("HOUSE_Decor")


def link_to(ob, collection):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- 材质（4K 8 通道 PBR）
def relink_textures():
    """跨 .blend append 后，相对路径基准会变成当前文件所在目录而断链。

    这里按文件名把所有贴图重定位到 TEX 绝对路径，保证 house.blend 渲染不丢贴图。
    （仓库内另提供 scripts/relink_textures.py 供换机后改回相对路径。）
    """
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        tgt = C.tex_by_name(base)
        if tgt and tgt.exists():
            # 统一写成相对 house.blend 的路径 —— 整个文件夹搬走后依然有效
            im.filepath = C.rel(tgt, C.HOUSE_BLEND)
            try:
                im.reload()
            except Exception:
                pass


def make_mat(name, base, rough=0.7, metal=0.0, tex=None, transmission=0.0,
             emission=0.0, use_normal=True, tex_scale=3.0):
    """建筑表面使用 4K 8 通道 PBR 贴图 + BOX 世界投影。

    用世界坐标 Position 驱动 BOX 三平面投影：墙段任意切分纹理都连续、
    不会拉伸成条纹；也避免用程序噪声直接当 Base Color 造成的大面积塑料感。
    """
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (1000, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.location = (700, 0)
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    bs.inputs['Base Color'].default_value = base
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if transmission:
        bs.inputs['Transmission Weight'].default_value = transmission
        bs.inputs['IOR'].default_value = 1.45
    if emission:
        bs.inputs['Emission Color'].default_value = base
        bs.inputs['Emission Strength'].default_value = emission

    if tex and C.tex(tex, "basecolor").exists():
        geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.location = (-1200, 0)
        mp = nt.nodes.new('ShaderNodeVectorMath'); mp.operation = 'SCALE'
        mp.inputs[3].default_value = tex_scale; mp.location = (-1000, 0)
        nt.links.new(geo.outputs['Position'], mp.inputs[0])

        def T(suffix, colorspace, y):
            pth = C.tex(tex, suffix)
            n = nt.nodes.new('ShaderNodeTexImage'); n.location = (-760, y)
            n.label = suffix
            n.projection = 'BOX'                 # 三平面投影，无 UV 也不拉伸
            n.projection_blend = 0.12
            if os.path.exists(pth):
                img = bpy.data.images.load(pth, check_existing=True)
                img.colorspace_settings.name = colorspace
                n.image = img
            nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
            return n

        bc = T('basecolor', 'sRGB', 460)
        ao = T('ao', 'Non-Color', 230)
        rgh = T('roughness', 'Non-Color', 0)
        mtl = T('metallic', 'Non-Color', -230)
        spc = T('specular', 'Non-Color', -460)
        hgt = T('height', 'Non-Color', -690)
        dsp = T('displacement', 'Non-Color', -920)

        # BaseColor x AO（凹陷积灰），保留贴图真实颜色与纹理
        mul = nt.nodes.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'
        mul.location = (-260, 420); mul.inputs[0].default_value = 0.72
        nt.links.new(bc.outputs['Color'], mul.inputs[1])
        nt.links.new(ao.outputs['Color'], mul.inputs[2])
        nt.links.new(mul.outputs['Color'], bs.inputs['Base Color'])
        nt.links.new(rgh.outputs['Color'], bs.inputs['Roughness'])
        nt.links.new(mtl.outputs['Color'], bs.inputs['Metallic'])
        nt.links.new(spc.outputs['Color'], bs.inputs['Specular IOR Level'])

        if use_normal:
            bump = nt.nodes.new('ShaderNodeBump'); bump.location = (300, -260)
            bump.inputs['Strength'].default_value = 0.15
            bump.inputs['Distance'].default_value = 0.005
            nt.links.new(hgt.outputs['Color'], bump.inputs['Height'])
            nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
            try:
                m.displacement_method = 'BUMP'
            except (AttributeError, TypeError):
                pass
            dn = nt.nodes.new('ShaderNodeDisplacement'); dn.location = (300, -560)
            dn.inputs['Scale'].default_value = 0.008
            nt.links.new(dsp.outputs['Color'], dn.inputs['Height'])
            nt.links.new(dn.outputs['Displacement'], out.inputs['Displacement'])
    m.diffuse_color = base
    return m


M_WALL = make_mat("wall_warm_white", (0.90, 0.87, 0.81, 1), 0.9,
                  tex="wall_paint", use_normal=False, tex_scale=1.4)
M_FLOOR = make_mat("floor_oak", (0.66, 0.45, 0.28, 1), 0.5, tex="oak_wood", tex_scale=1.2)
M_FLOOR_TILE = make_mat("floor_tile_wet", (0.76, 0.74, 0.70, 1), 0.3,
                        tex="floor_tile", use_normal=False, tex_scale=1.0)
M_CEIL = make_mat("ceiling_white", (0.95, 0.94, 0.92, 1), 0.92)
M_TRIM = make_mat("trim_oak", (0.62, 0.42, 0.26, 1), 0.55, tex="oak_wood")
M_GLASS = make_mat("window_glass", (0.90, 0.95, 0.98, 1), 0.05, transmission=0.95)
M_DOOR = make_mat("door_oak", (0.60, 0.40, 0.25, 1), 0.5, tex="oak_wood")
M_METAL = make_mat("brass_trim", (0.78, 0.60, 0.28, 1), 0.32, 0.9, tex="brass")
M_RUG = make_mat("rug_linen", (0.82, 0.78, 0.69, 1), 0.85, tex="linen_fabric")
M_SKY = make_mat("sky_backdrop", (0.52, 0.68, 0.82, 1), 1.0, emission=0.35)
M_SUBFLOOR = make_mat("subfloor_dark", (0.085, 0.062, 0.045, 1), 0.92)
M_CURTAIN = make_mat("curtain_linen", (0.86, 0.83, 0.76, 1), 0.88,
                     tex="linen_fabric", tex_scale=1.6)
M_SWITCH = make_mat("switch_plate", (0.93, 0.92, 0.89, 1), 0.45)
M_EMIT = make_mat("downlight_lens", (1.0, 0.94, 0.84, 1), 0.30, emission=2.2)
M_VENT = make_mat("vent_slat", (0.72, 0.71, 0.69, 1), 0.55, 0.35,
                  tex="brushed_steel", tex_scale=2.0)


# ---------------------------------------------------------------- 真实木地板板条
def plank_material(i, tex="oak_wood"):
    """每条板条独立的贴图采样偏移 + 板间色差。

    全屋共用一张 4K 木纹做 BOX 世界投影会让俯视下平铺重复明显。
    这里在 Position 之后插入随机 ADD 偏移，让每条板采样贴图不同区域；
    8 张 4K 贴图由 images.load(check_existing=True) 复用同一 datablock，
    12 个材质变体不会让内存翻 12 倍。
    """
    rng = random.Random(9100 + i * 37)
    off = (rng.uniform(-9, 9), rng.uniform(-9, 9), rng.uniform(-9, 9))
    tint = 0.88 + 0.22 * rng.random()
    m = make_mat(f"plank_{tex}_{i:02d}", (0.66, 0.45, 0.28, 1), 0.5,
                 tex=tex, tex_scale=1.2)
    nt = m.node_tree
    geo = next((n for n in nt.nodes if n.type == 'NEW_GEOMETRY'), None)
    scale = next((n for n in nt.nodes if n.type == 'VECT_MATH'
                  and n.operation == 'SCALE'), None)
    if geo and scale:
        add = nt.nodes.new('ShaderNodeVectorMath')
        add.operation = 'ADD'
        add.inputs[1].default_value = off
        add.location = (-1100, 160)
        for l in list(nt.links):
            if l.from_node == geo and l.to_node == scale:
                nt.links.remove(l)
        nt.links.new(geo.outputs['Position'], add.inputs[0])
        nt.links.new(add.outputs['Vector'], scale.inputs[0])
    bs = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs:
        tc = nt.nodes.new('ShaderNodeMixRGB')
        tc.blend_type = 'MULTIPLY'
        tc.inputs[0].default_value = 1.0
        tc.inputs[2].default_value = (tint, tint * 0.985, tint * 0.965, 1.0)
        tc.location = (120, 420)
        for l in list(nt.links):
            if l.to_node == bs and l.to_socket.name == 'Base Color':
                src = l.from_socket
                nt.links.remove(l)
                nt.links.new(src, tc.inputs[1])
                nt.links.new(tc.outputs['Color'], bs.inputs['Base Color'])
                break
    return m


PLANK_MATS = [plank_material(i) for i in range(12)]


def plank_floor(name, x0, x1, y0, y1, z, seed):
    """逐条板条几何：错缝、板间缝、随机长度与宽度、逐板贴图偏移。

    板缝是真实几何（露出下方深色基层），不是贴图上画的假缝。
    全部板条合并进一个 mesh 对象，用 material_index 循环 12 个变体。
    """
    rng = random.Random(int(seed * 1000) + 17)
    verts, faces, midx = [], [], []
    gap, thick, pw0 = 0.0022, 0.008, 0.135
    y = y0
    while y < y1 - 1e-4:
        pw = pw0 * (0.86 + 0.28 * rng.random())
        yh = min(y + pw, y1)
        x = x0 - (0.15 + 1.45 * rng.random())       # 每行错缝起点
        while x < x1 - 1e-4:
            xe = min(x + 0.70 + 1.45 * rng.random(), x1)
            ax, bx = max(x, x0) + gap, xe - gap
            ay, by = y + gap, yh - gap
            if bx - ax > 0.10 and by - ay > 0.02:
                b = len(verts)
                verts.extend([
                    (ax, ay, z + thick), (bx, ay, z + thick),
                    (bx, by, z + thick), (ax, by, z + thick),
                    (ax, ay, z), (bx, ay, z), (bx, by, z), (ax, by, z),
                ])
                mi = rng.randrange(len(PLANK_MATS))
                faces.extend([
                    (b, b + 1, b + 2, b + 3),          # 顶面
                    (b + 4, b + 7, b + 6, b + 5),      # 底面
                    (b, b + 4, b + 5, b + 1),
                    (b + 1, b + 5, b + 6, b + 2),
                    (b + 2, b + 6, b + 7, b + 3),
                    (b + 3, b + 7, b + 4, b),
                ])
                midx.extend([mi] * 6)
            x = xe
        y = yh
    me = bpy.data.meshes.new(name + "_planks_mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    for mm in PLANK_MATS:
        me.materials.append(mm)
    for poly, mi in zip(me.polygons, midx):
        poly.material_index = mi
    ob = bpy.data.objects.new(name + "_planks", me)
    link_to(ob, STRUCT)
    return ob


# ---------------------------------------------------------------- 几何工具
def box(name, size, pos, mat, collection=STRUCT, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.location = pos; ob.rotation_euler = rot
    ob.data.materials.append(mat)
    link_to(ob, collection)
    if parent:
        ob.parent = parent
    return ob


def cylinder(name, r, depth, pos, mat, collection=DECO, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth)
    ob = bpy.context.object; ob.name = name
    ob.location = pos; ob.rotation_euler = rot
    ob.data.materials.append(mat)
    link_to(ob, collection)
    return ob


# ---------------------------------------------------------------- 平面尺寸表
# 坐标 x∈[-5,5], y∈[-5,5]；南侧 y=-5 为采光面（客厅/餐厨），北侧为卧室/卫浴/书房
ROOMS = [
    # name, x0, x1, y0, y1, floor_mat
    ("玄关 Entry",      -5.0, -2.6, -5.0, -3.0, M_FLOOR),
    ("客厅 Living",     -2.6,  1.4, -5.0, -0.4, M_FLOOR),
    ("餐厨 KitchenDining", 1.4, 5.0, -5.0, -0.4, M_FLOOR_TILE),
    ("走廊 Hall",       -2.6,  1.4, -0.4,  0.6, M_FLOOR),
    ("主卧 Bedroom",    -5.0, -1.2,  0.6,  5.0, M_FLOOR),
    ("卫浴 Bath",       -1.2,  1.6,  0.6,  3.0, M_FLOOR_TILE),
    ("书房 Study",       1.6,  5.0, -0.4,  2.2, M_FLOOR),
    ("阳台 Balcony",     1.6,  5.0,  2.2,  5.0, M_FLOOR_TILE),
]


def build_floor():
    # 深色基层：板条之间露出的是真实几何缝，不是贴图假缝
    box("floor_slab", (10.0, 10.0, 0.12), (0, 0, -0.06), M_SUBFLOOR)
    for i, (name, x0, x1, y0, y1, fm) in enumerate(ROOMS):
        if fm is M_FLOOR:
            plank_floor("floor_" + name.split()[0], x0, x1, y0, y1, 0.004, seed=i + 1)
        else:
            w, d = x1 - x0, y1 - y0
            box("floor_" + name.split()[0], (w - 0.02, d - 0.02, 0.006),
                ((x0 + x1) / 2, (y0 + y1) / 2, 0.004), fm)
    # 天花（分块，留出灯槽感）
    box("ceiling", (10.0, 10.0, 0.10), (0, 0, H + 0.05), M_CEIL)
    # 踢脚线
    for (x0, y0, x1, y1) in [(-EXT, -EXT, EXT, -EXT), (EXT, -EXT, EXT, EXT),
                              (EXT, EXT, -EXT, EXT), (-EXT, EXT, -EXT, -EXT)]:
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        box("skirting", (L, 0.03, 0.09), ((x0 + x1) / 2, (y0 + y1) / 2, 0.045),
            M_TRIM, rot=(0, 0, ang))


def wall(name, p0, p1, height=H, thick=WALL_T, openings=(), mat=M_WALL):
    """生成带门窗洞的墙：沿 p0->p1 方向切段，跳过洞口。"""
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    ang = math.atan2(y1 - y0, x1 - x0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    cuts = sorted([(max(0.0, a), min(L, b), z0, z1) for a, b, z0, z1 in openings])
    segs = []
    cur = 0.0
    for a, b, z0, z1 in cuts:
        if a > cur:
            segs.append((cur, a, 0.0, height))
        if z0 > 0:
            segs.append((a, b, 0.0, z0))
        if z1 < height:
            segs.append((a, b, z1, height))
        cur = max(cur, b)
    if cur < L:
        segs.append((cur, L, 0.0, height))
    made = []
    for i, (a, b, z0, z1) in enumerate(segs):
        if b - a < 1e-4 or z1 - z0 < 1e-4:
            continue
        mid = (a + b) / 2
        px, py = x0 + ux * mid, y0 + uy * mid
        ob = box(f"{name}_s{i}", (b - a, thick, z1 - z0), (px, py, (z0 + z1) / 2), mat,
                 rot=(0, 0, ang))
        made.append(ob)
    return made


def add_glass(name, p0, p1, z0, z1, thick=0.012):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0); ang = math.atan2(y1 - y0, x1 - x0)
    box(name, (L, thick, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
        M_GLASS, rot=(0, 0, ang))


def add_window_frame(name, p0, p1, z0, z1):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0); ang = math.atan2(y1 - y0, x1 - x0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    for z in (z0, z1):
        box(f"{name}_h{z:.1f}", (L, 0.09, 0.06), (cx, cy, z), M_TRIM, rot=(0, 0, ang))
    for t in (0.0, 0.5, 1.0):
        px, py = x0 + ux * L * t, y0 + uy * L * t
        box(f"{name}_v{t:.1f}", (0.055, 0.09, z1 - z0), (px, py, (z0 + z1) / 2),
            M_TRIM, rot=(0, 0, ang))


def build_walls():
    # ---- 四面外墙。wall() 的 openings 用「沿 p0->p1 方向的局部长度」计，下面逐面换算标注。
    # 南墙 p0=(-5,-5)->(5,-5)，方向 +x，local = x + 5
    wall("wall_south", (-EXT, -EXT), (EXT, -EXT), thick=WALL_T_EXT,
         openings=[(2.0, 4.4, 0.5, 2.35),    # 客厅大窗 x∈[-3.0,-0.6]
                   (6.9, 9.3, 0.5, 2.35)])   # 餐厨大窗 x∈[1.9,4.3]
    # 北墙 p0=(5,5)->(-5,5)，方向 -x，local = 5 - x
    wall("wall_north", (EXT, EXT), (-EXT, EXT), thick=WALL_T_EXT,
         openings=[(0.6, 3.0, 0.6, 2.4),     # 阳台/书房窗 x∈[2.0,4.4]
                   (7.0, 9.2, 0.9, 2.3)])   # 主卧窗 x∈[-4.2,-2.0]
    # 西墙 p0=(-5,5)->(-5,-5)，方向 -y，local = 5 - y
    wall("wall_west", (-EXT, EXT), (-EXT, -EXT), thick=WALL_T_EXT,
         openings=[(1.8, 4.0, 0.9, 2.3)])   # 主卧侧窗 y∈[1.0,3.2]
    # 东墙 p0=(5,-5)->(5,5)，方向 +y，local = y + 5
    wall("wall_east", (EXT, -EXT), (EXT, EXT), thick=WALL_T_EXT,
         openings=[(4.8, 6.8, 0.6, 2.35),   # 书房窗 y∈[-0.2,1.8]
                   (8.0, 9.8, 0.5, 2.4)])   # 阳台窗 y∈[3.0,4.8]

    # ---- 玻璃 + 窗框（与上方洞口严格对齐）
    for nm, a, b, z0, z1 in [
        ("living", (-3.0, -EXT), (-0.6, -EXT), 0.5, 2.35),
        ("dining", (1.9, -EXT), (4.3, -EXT), 0.5, 2.35),
        ("bedroom_n", (-4.2, EXT), (-2.0, EXT), 0.9, 2.3),
        ("balcony_n", (2.0, EXT), (4.4, EXT), 0.6, 2.4),
        ("bedroom_w", (-EXT, 3.2), (-EXT, 1.0), 0.9, 2.3),
        ("study_e", (EXT, -0.2), (EXT, 1.8), 0.6, 2.35),
        ("balcony_e", (EXT, 3.0), (EXT, 4.8), 0.5, 2.4),
    ]:
        add_glass("glass_" + nm, a, b, z0, z1)
        add_window_frame("win_" + nm, a, b, z0, z1)

    # ---- 内隔墙（门洞 z0=0 / z1=2.1，保留上过梁）
    # 玄关 / 客厅：x=-2.6, y∈[-5,-3.0], local = y + 5
    wall("wall_entry_living", (-2.6, -5.0), (-2.6, -3.0), openings=[(0.7, 1.7, 0, 2.1)])
    # 客厅 / 餐厨：x=1.4, y∈[-5,-0.4]
    wall("wall_living_kitchen", (1.4, -5.0), (1.4, -0.4),
         openings=[(0.5, 1.6, 0, 2.15), (3.0, 4.1, 0, 2.15)])
    # 主卧南墙：y=0.6, x∈[-5,-1.2], local = x + 5
    wall("wall_bedroom_south", (-5.0, 0.6), (-1.2, 0.6), openings=[(1.4, 2.4, 0, 2.1)])
    # 主卧东墙：x=-1.2, y∈[0.6,5.0], local = y - 0.6
    wall("wall_bedroom_east", (-1.2, 0.6), (-1.2, 5.0), openings=[(0.9, 1.8, 0, 2.1)])
    # 卫浴南墙 / 北墙 / 东墙
    wall("wall_bath_south", (-1.2, 0.6), (1.6, 0.6))
    wall("wall_bath_north", (-1.2, 3.0), (1.6, 3.0), openings=[(1.0, 1.9, 0, 2.1)])
    wall("wall_bath_east", (1.6, 0.6), (1.6, 3.0))
    # 书房 / 阳台分隔（同一面墙只建一次）：y=2.2, x∈[1.6,5.0], local = x - 1.6
    wall("wall_study_balcony", (1.6, 2.2), (5.0, 2.2), openings=[(1.2, 2.1, 0, 2.1)])
    # 书房西墙：x=1.6, y∈[-0.4,0.6]
    wall("wall_study_west", (1.6, -0.4), (1.6, 0.6))

    # ---- 门扇：若干半开，制造生活感（Q11）
    doors = [
        ("door_bedroom", (-3.1, 0.6), 0.95, 0.0),
        ("door_bath", (-1.2, 1.95), 0.85, math.radians(28)),
        ("door_study", (3.15, 2.2), 0.9, math.radians(-18)),
        ("door_entry", (-2.6, -3.8), 0.9, 0.0),
    ]
    for nm, (x, y), w, ang in doors:
        box(nm, (w, 0.045, 2.1), (x, y, 1.05), M_DOOR, rot=(0, 0, ang))
        cylinder(nm + "_handle", 0.022, 0.05, (x + w * 0.36, y + 0.045, 1.02),
                 M_METAL, rot=(math.pi / 2, 0, 0))


# ---------------------------------------------------------------- 资产实例化
def load_asset_collections():
    """从 asset_library.blend 载入全部资产 Collection（不链接到场景，仅作实例源）。

    注意：bpy 会原地替换赋给 dst.collections 的列表对象，因此不能用原 names 列表
    去 zip；必须按加载后 Collection 自身的 .name 建立映射。
    """
    with bpy.data.libraries.load(LIB, link=False) as (src, dst):
        names = [n for n in src.collections if n.startswith("AST_")]
        dst.collections = list(names)          # 传副本，避免 names 被原地改写
    loaded = [c for c in dst.collections if c]
    return {c.name: c for c in loaded}


ASSETS = {}
PLACEMENTS = []


def place(asset_id, pos, rot_z=0.0, scale=1.0, label=None):
    """以 Collection Instance 引用资产库资产。pos 允许 (x, y) 或 (x, y, z)。"""
    c = ASSETS.get(asset_id)
    if c is None:
        print("MISSING_ASSET", asset_id)
        return None
    xyz = (pos[0], pos[1], pos[2] if len(pos) > 2 else 0.0)
    e = bpy.data.objects.new(f"INST_{asset_id}", None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = c
    e.location = xyz
    e.rotation_euler = (0, 0, rot_z)
    e.scale = (scale, scale, scale)
    link_to(e, FURN)
    PLACEMENTS.append(dict(asset=asset_id, pos=[round(v, 3) for v in xyz],
                           rot_z=round(rot_z, 4), scale=scale, label=label or asset_id))
    return e


def read_manifest():
    with open(MANIFEST) as f:
        return list(csv.DictReader(f))


def pick(rows, cat_no, variant="A"):
    for r in rows:
        if r["category_no"] == cat_no and r["variant"] == variant:
            return r["id"]
    for r in rows:
        if r["category_no"] == cat_no:
            return r["id"]
    return None


def furnish(rows):
    P = lambda no, v="A": pick(rows, no, v)

    # ---- 客厅：沙发 + 茶几 + 地毯 + 单椅 + 落地灯 + 绿植 + 电视 + 边柜 + 挂画
    place(P("03", "A"), (-0.7, -3.7), rot_z=0.0, label="客厅沙发")
    place(P("02", "C"), (-0.7, -2.5), label="客厅茶几")
    place(P("23", "A"), (-0.7, -3.1), scale=0.95, label="客厅地毯")
    place(P("01", "B"), (-2.0, -2.2), rot_z=math.radians(35), label="休闲单椅")
    place(P("07", "B"), (-2.2, -4.3), label="落地灯")
    place(P("19", "B"), (0.9, -4.3), label="客厅绿植")
    place(P("18", "A"), (1.25, -3.0), rot_z=math.radians(-90), label="电视")
    place(P("04", "A"), (1.25, -4.2), rot_z=math.radians(-90), label="电视边柜")
    place(P("25", "A"), (-1.35, -3.75), rot_z=math.radians(12), scale=0.9, label="沙发靠垫")
    place(P("25", "B"), (-0.15, -3.72), rot_z=math.radians(-8), scale=0.9, label="沙发靠垫2")
    place(P("06", "A"), (0.55, -2.0), label="收纳篮")
    place(P("20", "A"), (-0.7, -2.5), label="茶几上的书")

    # ---- 餐厨：餐桌 + 4 椅 + 吊灯 + 灶台/烤箱 + 水槽 + 锅具 + 餐具 + 瓶罐
    place(P("02", "A"), (3.2, -2.7), label="餐桌")
    for i, (dx, dy, a) in enumerate([(-0.9, 0, 90), (0.9, 0, -90), (0, -0.9, 0), (0, 0.9, 180)]):
        place(P("01", "A" if i % 2 == 0 else "C"), (3.2 + dx, -2.7 + dy),
              rot_z=math.radians(a), label=f"餐椅{i+1}")
    place(P("07", "A"), (3.2, -2.7), label="餐桌吊灯")
    place(P("08", "A"), (4.5, -4.2), rot_z=math.radians(-90), label="嵌入式烤箱")
    place(P("08", "B"), (2.2, -4.2), rot_z=math.radians(-90), label="冰箱")
    place(P("13", "A"), (3.5, -4.4), rot_z=0, label="水槽龙头")
    place(P("09", "A"), (3.2, -2.7), label="餐桌上的锅")
    place(P("10", "A"), (2.8, -2.7), scale=0.8, label="餐盘")
    place(P("11", "A"), (3.6, -2.35), scale=0.9, label="咖啡杯")
    place(P("12", "C"), (4.55, -2.0), label="玻璃瓶")
    place(P("28", "A"), (4.3, -4.1), label="调味瓶")
    place(P("36", "B"), (2.0, -4.1), label="收纳罐")
    place(P("27", "A"), (3.7, -3.1), label="餐具")
    place(P("30", "B"), (4.4, -3.3), label="木质厨具")
    place(P("35", "A"), (3.2, -2.35), label="果盘（生活化细节）")

    # ---- 玄关：边柜 + 收纳 + 绿植
    place(P("04", "C"), (-4.4, -4.2), rot_z=math.radians(90), label="玄关柜")
    place(P("06", "B"), (-3.4, -4.3), label="玄关收纳盒")
    place(P("21", "A"), (-4.4, -4.2), label="玄关摆件")
    place(P("22", "A"), (-3.8, -3.0), rot_z=math.radians(90), label="玄关挂画")

    # ---- 主卧：床 + 床头柜 + 落地灯 + 地毯 + 挂画 + 绿植
    place(P("05", "A"), (-3.2, 3.0), rot_z=math.radians(180), label="双人床")
    place(P("04", "B"), (-4.5, 2.0), label="床头柜")
    place(P("07", "C"), (-4.5, 2.0), label="床头台灯")
    place(P("23", "C"), (-3.2, 2.0), scale=0.9, label="卧室地毯")
    place(P("19", "D"), (-1.6, 4.3), scale=0.85, label="卧室绿植")
    place(P("22", "C"), (-3.2, 0.72), scale=0.8, label="卧室挂画")
    place(P("26", "A"), (-2.0, 3.6), scale=0.8, label="随手搭放的毛巾（Q11）")

    # ---- 卫浴：洁具 + 台盆 + 五金 + 毛巾
    place(P("14", "A"), (0.2, 1.4), label="洗手盆")
    place(P("13", "C"), (-0.5, 2.6), label="台盆")
    place(P("33", "A"), (-1.05, 2.2), rot_z=math.radians(90), label="卫浴五金")
    place(P("26", "B"), (-0.9, 2.7), scale=0.7, label="浴巾")
    place(P("12", "A"), (-0.45, 2.6), scale=0.6, label="卫浴瓶器")

    # ---- 书房：书桌 + 办公椅 + 书 + 台灯 + 绿植
    place(P("32", "A"), (3.3, 0.9), rot_z=math.radians(180), label="书桌")
    place(P("01", "D"), (3.3, 0.1), label="办公椅")
    place(P("20", "C"), (3.9, 0.9), label="书桌上的书")
    place(P("07", "D"), (2.1, 0.9), label="书房落地灯")
    place(P("19", "C"), (4.6, 1.8), scale=0.8, label="书房绿植")
    place(P("22", "D"), (1.72, 0.9), rot_z=math.radians(90), scale=0.8, label="书房挂画")

    # ---- 阳台：户外椅 + 户外桌 + 绿植
    place(P("31", "A"), (2.6, 3.6), rot_z=math.radians(20), label="阳台椅")
    place(P("31", "C"), (4.2, 3.9), rot_z=math.radians(-15), scale=0.85, label="阳台椅2")
    place(P("19", "A"), (3.4, 4.5), scale=1.1, label="阳台绿植")
    place(P("19", "B"), (4.6, 4.5), scale=0.9, label="阳台绿植2")

    # ---- 走廊：装饰 + 收纳
    place(P("06", "D"), (-1.9, 0.1), label="走廊收纳")
    place(P("21", "C"), (-1.9, 0.1), scale=0.7, label="走廊摆件")


# ---------------------------------------------------------------- 额外陈设细节（Q11）
def extra_details():
    # 窗台、台面上的小物用资产实例补充
    rows = read_manifest()
    P = lambda no, v="A": pick(rows, no, v)
    # 厨房台面（沿南墙的台面体）
    box("kitchen_counter", (3.4, 0.62, 0.86), (3.3, -4.65, 0.43),
        make_mat("counter_marble", (0.90, 0.89, 0.86, 1), 0.2, tex="marble"))
    box("kitchen_counter_top", (3.5, 0.66, 0.04), (3.3, -4.65, 0.88),
        make_mat("counter_top", (0.88, 0.87, 0.84, 1), 0.18, tex="marble"))
    for i, x in enumerate([2.0, 2.7, 4.05, 4.7]):
        place(P("36", "A" if i % 2 == 0 else "C"), (x, -4.62),
              scale=0.55, label=f"台面罐{i+1}")
    place(P("09", "C"), (2.45, -4.55), scale=0.8, label="台面上的陶锅")
    place(P("35", "C"), (3.3, -4.5), scale=0.8, label="台面果盘")
    # 窗台绿植
    place(P("19", "C"), (-2.7, -4.78), scale=0.5, label="客厅窗台小盆栽")
    place(P("19", "D"), (2.2, -4.78), scale=0.5, label="餐厨窗台小盆栽")
    # 地毯上的随意书本 / 半开的抽屉感
    place(P("20", "B"), (-1.5, -2.9), rot_z=math.radians(24), scale=0.8,
          label="随手放的书（Q11）")
    place(P("35", "B"), (0.2, -3.9), scale=0.9, label="茶几果盘")
    # 吊灯悬挂点
    place(P("07", "A"), (3.2, -2.7), scale=0.85, label="餐吊灯（低位重复形成层次）")

    # ---- 软装密度补强（全部引用资产库，不重造几何）
    # 顶部阴角线 + 挂镜线：沿四面外墙内侧，增加建筑层次
    for (x0, y0, x1, y1) in [(-EXT, -EXT, EXT, -EXT), (EXT, -EXT, EXT, EXT),
                              (EXT, EXT, -EXT, EXT), (-EXT, EXT, -EXT, -EXT)]:
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        box("crown_molding", (L, 0.045, 0.055), (cx, cy, H - 0.055),
            M_TRIM, rot=(0, 0, ang))
        box("picture_rail", (L, 0.018, 0.018), (cx, cy, 2.24),
            M_TRIM, rot=(0, 0, ang))
    # 窗台板（南侧两扇大窗）
    for cx, w in ((-1.8, 2.4), (3.1, 2.4)):
        box("window_sill", (w + 0.14, 0.26, 0.035), (cx, -EXT + 0.16, 0.49), M_TRIM)

    # 客厅茶几陈设（桌面 z≈0.78）
    place(P("21", "C"), (-1.05, -2.42, 0.79), scale=0.62, label="茶几花瓶")
    place(P("11", "B"), (-0.55, -2.28, 0.79), scale=0.8, label="茶几咖啡杯")
    place(P("35", "D"), (-0.42, -2.70, 0.79), scale=0.62, label="茶几果盘")
    place(P("20", "D"), (-0.85, -2.62, 0.79), rot_z=math.radians(18), scale=0.72,
          label="茶几书堆")
    # 沙发搭毯与靠垫组（放到坐垫高度）
    place(P("26", "C"), (-1.55, -3.62, 0.46), rot_z=math.radians(-12), scale=0.85,
          label="沙发扶手上搭的毯")
    place(P("25", "C"), (-1.05, -3.78, 0.50), rot_z=math.radians(16), scale=0.78,
          label="沙发靠垫3")
    place(P("25", "D"), (-0.32, -3.76, 0.50), rot_z=math.radians(-14), scale=0.78,
          label="沙发靠垫4")
    # 边柜 / 电视柜上的层叠陈设
    place(P("21", "B"), (1.25, -4.20, 0.87), scale=0.68, label="电视柜摆件")
    place(P("19", "C"), (1.25, -4.45, 0.87), scale=0.58, label="电视柜小盆栽")
    place(P("20", "B"), (1.05, -3.95, 0.87), rot_z=math.radians(10), scale=0.7,
          label="电视柜上的书")
    # 客厅角落大株绿植 + 落地灯旁小几
    place(P("19", "D"), (1.0, -4.55), scale=1.15, label="客厅角落大绿植")
    place(P("01", "C"), (0.95, -1.55), rot_z=math.radians(-28), scale=0.9,
          label="客厅边椅")
    # 餐桌陈设（桌面 z≈0.78）
    place(P("21", "D"), (3.2, -3.05, 0.79), scale=0.7, label="餐桌中央花器")
    place(P("10", "C"), (2.5, -2.70, 0.79), scale=0.72, label="餐盘2")
    place(P("10", "D"), (3.9, -2.70, 0.79), scale=0.72, label="餐盘3")
    place(P("11", "C"), (2.55, -2.30, 0.79), scale=0.85, label="玻璃杯")
    place(P("11", "D"), (3.85, -2.30, 0.79), scale=0.85, label="玻璃杯2")
    place(P("12", "B"), (3.55, -3.25, 0.79), scale=0.72, label="餐桌陶瓶")
    place(P("27", "C"), (2.75, -2.30, 0.79), rot_z=math.radians(8), label="餐具叉")
    # 卧室床头与床尾
    place(P("25", "B"), (-3.85, 2.05, 0.64), rot_z=math.radians(10), scale=0.85,
          label="床上靠枕")
    place(P("25", "A"), (-2.6, 2.05, 0.64), rot_z=math.radians(-8), scale=0.85,
          label="床上靠枕2")
    place(P("26", "B"), (-2.3, 3.7, 0.58), rot_z=math.radians(14), scale=0.8,
          label="床尾搭毯")
    place(P("21", "A"), (-4.5, 2.0, 0.87), scale=0.5, label="床头柜摆件")
    place(P("11", "A"), (-4.35, 1.9, 0.87), scale=0.7, label="床头柜水杯")
    # 书房桌面
    place(P("20", "B"), (2.85, 0.85, 0.78), rot_z=math.radians(-12), scale=0.8,
          label="书桌书堆")
    place(P("35", "A"), (3.75, 0.65, 0.78), scale=0.55, label="书桌笔筒")
    place(P("11", "B"), (3.55, 1.15, 0.78), scale=0.7, label="书桌咖啡杯")
    # 卫浴台面
    place(P("12", "C"), (-0.65, 2.55, 0.90), scale=0.55, label="卫浴瓶")
    place(P("26", "C"), (-0.95, 2.45, 0.90), scale=0.55, label="折叠毛巾")
    # 玄关与走廊
    place(P("19", "A"), (-4.55, -3.35), scale=0.7, label="玄关绿植")
    place(P("35", "B"), (-4.4, -4.2, 0.87), scale=0.62, label="玄关托盘")
    place(P("22", "B"), (-1.9, 0.52, 1.35), scale=0.75, label="走廊挂画")
    place(P("21", "D"), (-1.9, 0.1, 0.34), scale=0.6, label="走廊端景摆件")
    # 阳台
    place(P("35", "C"), (3.4, 3.9, 0.46), scale=0.6, label="阳台小桌果盘")
    place(P("19", "D"), (2.0, 4.5, 0.0), scale=0.75, label="阳台角落绿植")

    # 挂画补正高度（避免全部落在地面）
    for aid, xyz, ang, sc in [
        (P("22", "A"), (-3.8, -3.0, 1.30), 90, 0.9),
        (P("22", "C"), (-3.2, 0.72, 1.35), 0, 0.8),
        (P("22", "D"), (1.72, 0.9, 1.32), 90, 0.8),
    ]:
        place(aid, xyz, rot_z=math.radians(ang), scale=sc, label="墙面挂画")

    architectural_finishes()


def curtain_panel(name, cx, width, y, z0, z1, seed=0.0, nx=16, nz=12):
    """真实褶皱窗帘布：竖向折褶 + 非周期扰动 + 底部外扩，Solidify 给厚度。"""
    verts, faces = [], []
    for i in range(nx + 1):
        u = i / nx
        x = cx - width / 2 + width * u
        for j in range(nz + 1):
            t = j / nz
            z = z1 - (z1 - z0) * t
            fold = 0.026 * math.sin(u * math.pi * 7.0 + seed) * (1 - 0.18 * t)
            wob = 0.004 * math.sin(u * 11.0 + seed * 1.7 + t * 3.0)
            yv = y + fold + wob + 0.020 * t * t
            verts.append((x, yv, z))
    for i in range(nx):
        for j in range(nz):
            a = i * (nz + 1) + j
            faces.append((a, a + (nz + 1), a + (nz + 1) + 1, a + 1))
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    link_to(ob, DECO)
    ob.data.materials.append(M_CURTAIN)
    sol = ob.modifiers.new("curtain_thickness", 'SOLIDIFY')
    sol.thickness = 0.006
    return ob


def architectural_finishes():
    """建筑收口：门套线、开关插座、筒灯、出风口、窗帘、帘杆。

    墙 / 地 / 家具之外，还需要这些「房子完工」的收口件，
    视觉上仍像毛坯 + 摆家具。这里全部用几何补齐。
    """
    # 门套线（门洞两侧竖框 + 顶部横框）
    casings = [
        ("bd", -3.1, 0.6, 0.95, 'x'),
        ("bath", -1.2, 1.95, 0.85, 'y'),
        ("study", 3.15, 2.2, 0.90, 'x'),
        ("entry", -2.6, -3.8, 0.90, 'y'),
    ]
    t = WALL_T + 0.02
    for nm, x, y, w, axis in casings:
        for s in (-1, 1):
            if axis == 'x':
                box(f"casing_{nm}_{s}", (0.038, t, 2.12),
                    (x + s * (w / 2 + 0.019), y, 1.06), M_TRIM)
            else:
                box(f"casing_{nm}_{s}", (t, 0.038, 2.12),
                    (x, y + s * (w / 2 + 0.019), 1.06), M_TRIM)
        if axis == 'x':
            box(f"casing_{nm}_head", (w + 0.076, t, 0.038), (x, y, 2.12), M_TRIM)
        else:
            box(f"casing_{nm}_head", (t, w + 0.076, 0.038), (x, y, 2.12), M_TRIM)
    # 开关 / 插座面板 + 按键
    for i, (px, py, ang, h) in enumerate([
        (-2.42, -3.05, math.pi / 2, 1.15), (1.52, -2.10, math.pi / 2, 1.15),
        (-1.32, 1.20, 0, 1.15), (-4.75, 0.72, 0, 1.15), (3.05, 2.32, 0, 1.15),
        (-2.42, -3.05, math.pi / 2, 0.32), (1.52, -2.10, math.pi / 2, 0.32),
    ]):
        box(f"switch_{i}", (0.082, 0.010, 0.082), (px, py, h), M_SWITCH,
            rot=(0, 0, ang))
        box(f"switch_btn_{i}", (0.028, 0.012, 0.030), (px, py, h), M_VENT,
            rot=(0, 0, ang))
    # 顶面筒灯（金属圈 + 发光镜片）
    for i, (lx, ly) in enumerate([
        (-1.6, -3.4), (0.2, -3.4), (-1.6, -1.2),
        (3.2, -2.8), (3.2, -1.2), (-3.2, 2.8),
        (-2.0, 2.8), (3.3, 0.9), (-0.2, 1.8),
    ]):
        cylinder(f"downlight_rim_{i}", 0.052, 0.006, (lx, ly, H - 0.006), M_METAL)
        cylinder(f"downlight_lens_{i}", 0.044, 0.004, (lx, ly, H - 0.012), M_EMIT)
    # 空调出风口（框 + 百叶）
    for i, (vx, vy, vw) in enumerate([(0.0, -4.86, 0.9), (3.1, 4.86, 0.9)]):
        box(f"vent_frame_{i}", (vw, 0.012, 0.14), (vx, vy, H - 0.32), M_VENT)
        for k in range(7):
            box(f"vent_slat_{i}_{k}", (vw - 0.06, 0.014, 0.008),
                (vx, vy - 0.008, H - 0.375 + k * 0.018), M_VENT)
    # 窗帘（南侧两扇大窗 + 主卧北窗）
    for i, (cx, ww) in enumerate([(-1.8, 2.4), (3.1, 2.4), (-3.1, 2.2)]):
        yc = -EXT + 0.14 if i < 2 else EXT - 0.14
        z0, z1 = 0.42, H - 0.10
        cylinder(f"curtain_rod_{i}", 0.012, ww + 0.30,
                 (cx, yc, z1 + 0.03), M_METAL, rot=(0, math.pi / 2, 0))
        for s in (-1, 1):
            curtain_panel(f"curtain_{i}_{s}", cx + s * (ww / 2 - 0.24), 0.48,
                          yc + (0.02 if i < 2 else -0.02), z0, z1,
                          seed=i * 3.1 + s)


def outdoor_backdrop():
    """南窗外远景：竖直天空渐变，替代窗外纯白过曝（Q8-7）。"""
    m = bpy.data.materials.new("sky_gradient")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 0.72
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.78, 0.83, 0.87, 1)   # 近地平线浅灰蓝
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.30, 0.48, 0.68, 1)   # 天顶蓝
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    box("sky_backdrop_plane", (26.0, 0.02, 9.0), (0, -8.0, 3.2), m,
        collection=DECO)


# ---------------------------------------------------------------- 灯光与相机
def add_area(name, pos, energy, size, color=(1, 1, 1), target=None, shape='DISK'):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy; ld.shape = shape; ld.size = size; ld.color = color
    ob = bpy.data.objects.new(name, ld); link_to(ob, LIGHTS)
    ob.location = pos
    if name.startswith("sun_"):
        # 窗外主日光只负责照明。若不关掉 transmission / glossy 可见性，
        # 透过玻璃（transmission ray）看到的是这块高亮面光本身，
        # 窗口呈现一片纯白，把 outdoor_backdrop() 的天空渐变完全遮住。
        # 关掉后相机 / 玻璃看到的是天空平面，漫反射与阴影照明不受影响。
        ob.visible_camera = False
        ob.visible_transmission = False
        ob.visible_glossy = False
    if target:
        ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    else:
        ob.rotation_euler = (0, 0, 0)
    return ob


def lighting():
    # 温暖日光世界（低强度，避免与室内灯叠加过曝）
    world = bpy.data.worlds.new("warm_daylight") if not scene.world else scene.world
    scene.world = world; world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs['Color'].default_value = (0.52, 0.63, 0.78, 1)
    bg.inputs['Strength'].default_value = 0.22
    # 南向主日光（两扇大窗各一）：强度降到约一半，配合窗外渐变天空消除纯白过曝
    add_area("sun_living", (-1.7, -5.6, 2.6), 205, 5.0, (1.0, 0.91, 0.78),
             target=(-1.0, -1.5, 0.8))
    add_area("sun_dining", (3.0, -5.6, 2.6), 175, 4.5, (1.0, 0.92, 0.80),
             target=(2.8, -1.5, 0.8))
    # 西向卧室侧光
    add_area("sun_bedroom", (-5.6, 1.8, 2.4), 150, 3.5, (1.0, 0.90, 0.78),
             target=(-2.5, 2.0, 0.8))
    # 窗外远景：玻璃后面不再是一片纯白
    outdoor_backdrop()
    # 室内暖光（低调补光，不再与主日光叠加过曝）
    for nm, pos, en in [("ceil_living", (-0.7, -3.0, 2.72), 90),
                        ("ceil_dining", (3.2, -2.7, 2.72), 80),
                        ("ceil_bedroom", (-3.2, 3.0, 2.72), 65),
                        ("ceil_study", (3.3, 0.9, 2.72), 60),
                        ("ceil_hall", (-0.6, 0.1, 2.72), 45),
                        ("ceil_bath", (0.2, 1.8, 2.72), 45)]:
        add_area(nm, pos, en, 1.2, (1.0, 0.86, 0.68))


def camera(name, pos, target, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    ob = bpy.data.objects.new(name, cd); link_to(ob, CAMS)
    ob.location = pos
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    return ob


def cameras():
    # 所有机位都放在对应房间内部，避免被内隔墙挡住；俯视机位渲染时临时隐藏天花板
    return {
        "living": camera("CAM_living", (1.1, -4.7, 1.62), (-1.9, -1.7, 1.0), 22),
        "kitchen": camera("CAM_kitchen", (1.9, -1.0, 1.66), (4.0, -4.1, 1.0), 22),
        "bedroom": camera("CAM_bedroom", (-1.5, 0.95, 1.62), (-3.7, 3.9, 0.9), 24),
        "study": camera("CAM_study", (2.0, -0.1, 1.62), (4.3, 1.7, 1.0), 24),
        "bath": camera("CAM_bath", (-0.9, 0.9, 1.62), (0.4, 2.6, 1.0), 24),
        "overview": camera("CAM_overview", (0, -0.2, 9.6), (0, 0, 0), 35),
    }


def render_settings():
    sc = scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 32
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1100; sc.render.resolution_y = 720
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = 'AgX'
    except Exception:
        pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 24


# ---------------------------------------------------------------- 文档输出
def write_docs():
    with open(C.DOCS / "06_平面布局.md", "w") as f:
        f.write("# 平面尺寸表 — 温暖日光 · 现代自然风住宅\n\n")
        f.write("**建筑面积：10.00 m × 10.00 m = 100.00 ㎡**；层高 2.80 m；"
                "外墙 0.24 m，内墙 0.16 m。南侧（y = −5）为主要采光面。\n\n")
        f.write("| 空间 | x 范围 (m) | y 范围 (m) | 面积 (㎡) | 地面材质 |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for name, x0, x1, y0, y1, fm in ROOMS:
            f.write(f"| {name} | {x0:.2f} ~ {x1:.2f} | {y0:.2f} ~ {y1:.2f} | "
                    f"{(x1-x0)*(y1-y0):.2f} | {fm.name} |\n")
        f.write("\n## 设计说明\n\n")
        f.write("- 风格：温暖日光 · 现代自然风（橡木地板 / 暖白墙 / 亚麻软装 / 黄铜五金 / 绿植），"
                "与参考视频的雨夜暗调厨房明确区分。\n")
        f.write("- 南侧客厅与餐厨连续大窗引入主日光；主卧设西侧窗；东侧书房、阳台开窗。\n")
        f.write("- 内墙开门洞形成玄关→走廊→各房间的动线；卫浴与书房独立分隔。\n")
        f.write("- 家具全部以 `asset_library.blend` 的 Collection 实例引用，不重造几何。\n")
        f.write("- 生活化不规则细节：半开的卫浴门与书房门、随手搭放的毛巾与书本、"
                "台面错落摆放的罐与锅、窗台小盆栽（Q11）。\n")
    with open(C.PLACEMENT_JSON, "w") as f:
        json.dump(dict(instance_count=len(PLACEMENTS), placements=PLACEMENTS), f,
                  ensure_ascii=False, indent=2)


def main():
    rows = read_manifest()
    build_floor()
    build_walls()
    global ASSETS
    ASSETS = load_asset_collections()
    print("LOADED_ASSETS", len(ASSETS))
    furnish(rows)
    extra_details()
    lighting()
    cams = cameras()
    render_settings()
    scene.camera = cams["living"]

    # 4K 贴图不打包（约 1.6GB）：重定位为相对 scene/house.blend 的 //../assets/_textures/ 路径
    relink_textures()
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    write_docs()
    print("INSTANCES", len(PLACEMENTS))
    print("OBJECTS", len(bpy.data.objects))
    print("HOUSE_DONE")


if __name__ == "__main__":
    main()
