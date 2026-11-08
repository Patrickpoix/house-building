"""声明式布局组装器：把 144 个高质量 PBR 资产像积木一样拼成任意房屋。

设计意图
--------
`build_house.py` 把房型、隔墙、家具摆设写死在代码里，只能生成一栋固定住宅。
本脚本把「房屋」变成一份可读、可改、可版本化的 JSON：改面积、改房间分区、
改隔墙、换资产清单，就得到一栋不同的房屋，全程不碰任何建模代码。

资产一律从母库 `asset_library.blend` 以 Collection Instance 引用，
沿用完整的 4K / 8 通道 PBR 贴图，不降级、不重建、不复制几何。
建筑壳体（地面 / 墙 / 天花 / 门窗洞）用同一套共享 4K 贴图 + BOX 世界投影生成。

用法（blpython = 装了 bpy 的解释器）
--------------------------------
  blpython src/02_scene/assemble.py -- --list-categories        # 看 36 类
  blpython src/02_scene/assemble.py -- --pick 03                # 看某类 4 个资产 + 尺寸
  blpython src/02_scene/assemble.py -- scene/layouts/studio_45.json
  blpython src/02_scene/assemble.py -- scene/layouts/studio_45.json --render
  blpython src/02_scene/assemble.py -- --all --render           # 生成全部示例房屋

布局 JSON 详见 docs/09_任意组装指南.md。零硬编码，全部路径走 config.py。
"""
import sys
import pathlib

sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents
                           if (p / "config.py").is_file())))
import config as C

import bpy
import json
import csv
import math
import os
from mathutils import Vector

# ---------------------------------------------------------------- 集合
STRUCT = None
FURN = None
LIGHTS = None
CAMS = None
SCENE = None


def coll(name):
    c = bpy.data.collections.new(name)
    SCENE.collection.children.link(c)
    return c


def link_to(ob, collection):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection.objects.link(ob)


# ---------------------------------------------------------------- 基础几何
def box(name, size, pos, mat, collection, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = size
    ob.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat is not None:
        ob.data.materials.append(mat)
    link_to(ob, collection)
    return ob


def lerp_point(p0, p1, t):
    return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)


def add_wall(name, p0, p1, height, thick, openings, mat):
    """带洞口的墙。openings 为沿 p0→p1 方向的局部米制 (a, b, z0, z1)。"""
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    ang = math.atan2(y1 - y0, x1 - x0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    cuts = sorted([(max(0.0, a), min(L, b), z0, z1) for a, b, z0, z1 in openings])
    segs, cur = [], 0.0
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
    out = []
    for i, (a, b, z0, z1) in enumerate(segs):
        if b - a < 1e-4 or z1 - z0 < 1e-4:
            continue
        mid = (a + b) / 2
        px, py = x0 + ux * mid, y0 + uy * mid
        out.append(box(f"{name}_s{i}", (b - a, thick, z1 - z0),
                       (px, py, (z0 + z1) / 2), mat, STRUCT, rot=(0, 0, ang)))
    return out


# ---------------------------------------------------------------- 材质（共享 4K / 8 通道 PBR）
_MAT_CACHE = {}


def pbr_mat(name, tex, base, rough=0.7, metal=0.0, tex_scale=1.4,
            use_normal=True, transmission=0.0):
    """建筑表面材质：与 build_house.py 同一套 8 通道贴图 + BOX 世界投影。"""
    key = (name, tex, tex_scale, use_normal, transmission)
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (1000, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bs.location = (700, 0)
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    bs.inputs['Base Color'].default_value = base
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if transmission:
        bs.inputs['Transmission Weight'].default_value = transmission
        bs.inputs['IOR'].default_value = 1.45

    if tex and C.tex(tex, "basecolor").exists():
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        geo.location = (-1200, 0)
        mp = nt.nodes.new('ShaderNodeVectorMath')
        mp.operation = 'SCALE'
        mp.inputs[3].default_value = tex_scale
        mp.location = (-1000, 0)
        nt.links.new(geo.outputs['Position'], mp.inputs[0])

        def T(suffix, colorspace, y):
            pth = C.tex(tex, suffix)
            n = nt.nodes.new('ShaderNodeTexImage')
            n.location = (-760, y)
            n.label = suffix
            n.projection = 'BOX'
            n.projection_blend = 0.12
            if pth.exists():
                img = bpy.data.images.load(str(pth), check_existing=True)
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

        mul = nt.nodes.new('ShaderNodeMixRGB')
        mul.blend_type = 'MULTIPLY'
        mul.location = (-260, 420)
        mul.inputs[0].default_value = 0.72
        nt.links.new(bc.outputs['Color'], mul.inputs[1])
        nt.links.new(ao.outputs['Color'], mul.inputs[2])
        nt.links.new(mul.outputs['Color'], bs.inputs['Base Color'])
        nt.links.new(rgh.outputs['Color'], bs.inputs['Roughness'])
        nt.links.new(mtl.outputs['Color'], bs.inputs['Metallic'])
        nt.links.new(spc.outputs['Color'], bs.inputs['Specular IOR Level'])
        if use_normal:
            bump = nt.nodes.new('ShaderNodeBump')
            bump.location = (300, -260)
            bump.inputs['Strength'].default_value = 0.15
            bump.inputs['Distance'].default_value = 0.005
            nt.links.new(hgt.outputs['Color'], bump.inputs['Height'])
            nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
            try:
                m.displacement_method = 'BUMP'
            except (AttributeError, TypeError):
                pass
            dn = nt.nodes.new('ShaderNodeDisplacement')
            dn.location = (300, -560)
            dn.inputs['Scale'].default_value = 0.008
            nt.links.new(dsp.outputs['Color'], dn.inputs['Height'])
            nt.links.new(dn.outputs['Displacement'], out.inputs['Displacement'])
    m.diffuse_color = base
    _MAT_CACHE[key] = m
    return m


def solid_mat(name, base, rough=0.7, metal=0.0, transmission=0.0, emission=0.0):
    key = (name, tuple(base), rough, metal, transmission, emission)
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    m = bpy.data.materials.new(name)
    m.diffuse_color = base
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs['Base Color'].default_value = base
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if transmission:
        bs.inputs['Transmission Weight'].default_value = transmission
        bs.inputs['IOR'].default_value = 1.45
    if emission:
        bs.inputs['Emission Color'].default_value = base
        bs.inputs['Emission Strength'].default_value = emission
    _MAT_CACHE[key] = m
    return m


# ---------------------------------------------------------------- 壳体
def build_shell(L):
    sh = L["shell"]
    x0, x1 = sh["x0"], sh["x1"]
    y0, y1 = sh["y0"], sh["y1"]
    H = sh.get("height", 2.8)
    te = sh.get("wall_thick_ext", 0.24)
    ti = sh.get("wall_thick_int", 0.16)
    floor_tex = sh.get("floor_tex", "oak_wood")
    wall_tex = sh.get("wall_tex", "wall_paint")

    M_WALL = pbr_mat("asm_wall", wall_tex, (0.90, 0.87, 0.81, 1), 0.9, tex_scale=1.4,
                     use_normal=False)
    M_FLOOR = {}
    M_SUB = solid_mat("asm_subfloor", (0.085, 0.062, 0.045, 1), 0.92)
    M_CEIL = solid_mat("asm_ceiling", (0.95, 0.94, 0.92, 1), 0.92)
    M_TRIM = pbr_mat("asm_trim", floor_tex, (0.62, 0.42, 0.26, 1), 0.55)
    M_GLASS = solid_mat("asm_glass", (0.90, 0.95, 0.98, 1), 0.05,
                        transmission=0.95)
    M_DOOR = pbr_mat("asm_door", floor_tex, (0.60, 0.40, 0.25, 1), 0.5)
    M_SKY = solid_mat("asm_sky", (0.52, 0.68, 0.82, 1), 1.0, emission=0.35)

    def floor_mat(tex):
        if tex not in M_FLOOR:
            base = (0.66, 0.45, 0.28, 1) if tex in ("oak_wood", "walnut_wood") \
                else (0.76, 0.74, 0.70, 1)
            M_FLOOR[tex] = pbr_mat(f"asm_floor_{tex}", tex, base, 0.5,
                                   tex_scale=1.2,
                                   use_normal=tex not in ("floor_tile", "concrete_floor"))
        return M_FLOOR[tex]

    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    W, D = x1 - x0, y1 - y0
    # 基层（深色，仅作为地板之下的兜底）
    box("asm_slab", (W, D, 0.12), (cx, cy, -0.06), M_SUB, STRUCT)
    # 先铺满一整块默认地板：无论布局的 rooms 是否覆盖完整，都不会露出深色基层。
    # rooms 的分块地板随后盖在其上（z 更高 0.006，避免 z-fighting）。
    box("asm_floor_base", (W - 0.02, D - 0.02, 0.004), (cx, cy, 0.0),
        floor_mat(floor_tex), STRUCT)
    rooms = L.get("rooms", [])
    for i, r in enumerate(rooms):
        rw, rd = r["x1"] - r["x0"], r["y1"] - r["y0"]
        box(f"asm_floor_{r.get('name', i)}", (rw - 0.02, rd - 0.02, 0.008),
            ((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2, 0.006),
            floor_mat(r.get("floor_tex", floor_tex)), STRUCT)

    if sh.get("ceiling", True):
        # 天花板完整保存在 .blend 里；方案俯视图渲染时由 render_preview()
        # 临时隐藏（连同天空板），「打开屋顶」看室内，渲染后恢复。
        box("asm_ceiling", (W, D, 0.10), (cx, cy, H + 0.05), M_CEIL, STRUCT)

    # 四面外墙：把 windows 的 (side, from, to) 换算成沿墙的局部洞口
    sides = {
        "south": ((x0, y0), (x1, y0)),
        "north": ((x1, y1), (x0, y1)),
        "east": ((x1, y0), (x1, y1)),
        "west": ((x0, y1), (x0, y0)),
    }
    wins = L.get("windows", [])
    for side, (p0, p1) in sides.items():
        seg_L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ops = []
        for w in [w for w in wins if w["side"] == side]:
            a, b = w["from"] * seg_L, w["to"] * seg_L
            ops.append((a, b, w.get("z0", 0.6), w.get("z1", 2.3)))
        add_wall(f"asm_wall_{side}", p0, p1, H, te, ops, M_WALL)
        # 玻璃 + 窗框（与洞口严格对齐）
        for w in [w for w in wins if w["side"] == side]:
            g0 = lerp_point(p0, p1, w["from"])
            g1 = lerp_point(p0, p1, w["to"])
            z0, z1 = w.get("z0", 0.6), w.get("z1", 2.3)
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            gL = math.hypot(g1[0] - g0[0], g1[1] - g0[1])
            gx, gy = (g0[0] + g1[0]) / 2, (g0[1] + g1[1]) / 2
            box("asm_glass", (gL, 0.012, z1 - z0), (gx, gy, (z0 + z1) / 2),
                M_GLASS, STRUCT, rot=(0, 0, ang))
            for z in (z0, z1):
                box("asm_win_h", (gL, 0.09, 0.06), (gx, gy, z),
                    M_TRIM, STRUCT, rot=(0, 0, ang))
            ux, uy = (p1[0] - p0[0]) / seg_L, (p1[1] - p0[1]) / seg_L
            for t in (0.0, 0.5, 1.0):
                px, py = g0[0] + ux * gL * t, g0[1] + uy * gL * t
                box("asm_win_v", (0.055, 0.09, z1 - z0), (px, py, (z0 + z1) / 2),
                    M_TRIM, STRUCT, rot=(0, 0, ang))

    # 内隔墙（带门洞）
    for i, pt in enumerate(L.get("partitions", [])):
        p0, p1 = pt["p0"], pt["p1"]
        seg_L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ops = []
        if "door_at" in pt:
            w = pt.get("door_w", 0.9)
            c = pt["door_at"] * seg_L
            ops.append((max(0.0, c - w / 2), min(seg_L, c + w / 2), 0.0, 2.1))
        add_wall(f"asm_part_{i}", p0, p1, H, ti, ops, M_WALL)
        if "door_at" in pt:
            w = pt.get("door_w", 0.9)
            c = pt["door_at"] * seg_L
            dp = lerp_point(p0, p1, min(1.0, max(0.0, c / seg_L)))
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            box(f"asm_door_{i}", (w, 0.045, 2.1), (dp[0], dp[1], 1.05),
                M_DOOR, STRUCT, rot=(0, 0, ang))

    # 踢脚线
    for p0, p1 in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                   ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        seg_L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        box("asm_skirting", (seg_L, 0.03, 0.09),
            ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, 0.045),
            M_TRIM, STRUCT, rot=(0, 0, ang))

    # 窗外天空背景（避免窗外纯白）。放在南侧窗外但对「俯视相机」不可见，
    # 否则会像一堵白墙挡在斜俯视机位与房子之间。
    box("asm_sky_s", (W * 1.6, 0.02, H * 2.2), (cx, y0 - 6.0, H * 0.9),
        M_SKY, STRUCT)      # 室内视角的窗外背景；俯视预览时临时隐藏
    return H


# ---------------------------------------------------------------- 资产实例化
def place_assets(L):
    wanted = [a["asset"] for a in L["assets"]]
    wanted_set = set(wanted)
    with bpy.data.libraries.load(str(C.LIBRARY_BLEND), link=False) as (src, dst):
        names = [n for n in src.collections if n in wanted_set]
        dst.collections = list(names)
    assets = {c.name: c for c in dst.collections if c}
    placed, missing = 0, []
    for i, a in enumerate(L["assets"]):
        c = assets.get(a["asset"])
        if c is None:
            missing.append(a["asset"])
            continue
        pos = a["pos"]
        xyz = (pos[0], pos[1], pos[2] if len(pos) > 2 else 0.0)
        s = a.get("scale", 1.0)
        e = bpy.data.objects.new(f"INST_{a['asset']}_{i}", None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = c
        e.location = xyz
        e.rotation_euler = (0, 0, a.get("rot_z", 0.0))
        e.scale = (s, s, s)
        e["label"] = a.get("label", a["asset"])
        link_to(e, FURN)
        placed += 1
    return placed, missing


# ---------------------------------------------------------------- 灯光 / 相机 / 渲染
def setup_world(exposure=-0.35):
    w = bpy.data.worlds.new("asm_world")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs['Color'].default_value = (0.55, 0.62, 0.70, 1)
    bg.inputs['Strength'].default_value = 0.6
    SCENE.world = w
    try:
        SCENE.view_settings.view_transform = 'AgX'
    except Exception:
        pass
    SCENE.view_settings.exposure = exposure


def add_light(name, ltype, pos, energy, size=None, color=(1, 1, 1), target=None):
    ld = bpy.data.lights.new(name, ltype)
    ld.energy = energy
    ld.color = color
    if size and ltype == 'AREA':
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    link_to(ob, LIGHTS)
    ob.location = pos
    if target:
        ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    return ob


def setup_lighting(L):
    sh = L["shell"]
    cx = (sh["x0"] + sh["x1"]) / 2
    cy = (sh["y0"] + sh["y1"]) / 2
    target = (cx, cy, 0.8)
    add_light("asm_sun", 'SUN', (cx - 3, cy - 6, 8), L.get("lighting", {}).get("sun", 2.2),
              target=target)
    add_light("asm_key", 'AREA', (cx - 2, cy - 1, sh.get("height", 2.8) - 0.3), 600,
              size=4.0, color=(1.0, 0.93, 0.84), target=target)
    add_light("asm_fill", 'AREA', (cx + 3, cy + 2, sh.get("height", 2.8) - 0.3), 350,
              size=5.0, color=(0.82, 0.88, 1.0), target=target)


def setup_camera(L):
    cam = L.get("camera", {})
    pos = cam.get("pos")
    target = cam.get("target")
    if not pos or not target:
        sh = L["shell"]
        pos = [sh["x1"] + 4, sh["y0"] - 6, sh.get("height", 2.8) + 3.5]
        target = [(sh["x0"] + sh["x1"]) / 2, (sh["y0"] + sh["y1"]) / 2, 1.2]
    cd = bpy.data.cameras.new("asm_camera")
    cd.lens = cam.get("lens", 24)
    ob = bpy.data.objects.new("asm_camera", cd)
    link_to(ob, CAMS)
    ob.location = pos
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    SCENE.camera = ob


def relink_textures(out_blend):
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        tgt = C.tex_by_name(base)
        if tgt and tgt.exists():
            im.filepath = C.rel(tgt, out_blend)
            try:
                im.reload()
            except Exception:
                pass


def render_preview(L, out_png):
    r = L.get("render", {})
    w, h = r.get("resolution", [1280, 720])
    SCENE.render.engine = 'CYCLES'
    SCENE.cycles.device = 'CPU'
    SCENE.cycles.samples = r.get("samples", 24)
    SCENE.cycles.use_denoising = True
    SCENE.render.resolution_x = w
    SCENE.render.resolution_y = h
    SCENE.render.resolution_percentage = 100
    SCENE.render.image_settings.file_format = 'PNG'
    SCENE.render.filepath = str(out_png)

    # 方案俯视图要「打开屋顶」：临时隐藏天花板与窗外天空板，否则相机被挡、
    # 或天花板虽对相机不可见却仍挡住太阳光，在室内留下大片黑影。
    # 这两步只影响渲染，不写回 .blend（保存发生在渲染之前）。
    hidden = []
    for nm in ("asm_ceiling", "asm_sky_s"):
        ob = bpy.data.objects.get(nm)
        if ob is not None:
            hidden.append((ob, ob.hide_render))
            ob.hide_render = True
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        for ob, prev in hidden:
            ob.hide_render = prev


# ---------------------------------------------------------------- 主流程
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    global STRUCT, FURN, LIGHTS, CAMS, SCENE, _MAT_CACHE
    SCENE = bpy.context.scene
    STRUCT = coll("ASM_Structure")
    FURN = coll("ASM_Furniture_Instances")
    LIGHTS = coll("ASM_Lighting")
    CAMS = coll("ASM_Cameras")
    _MAT_CACHE = {}


def assemble(layout_path, do_render):
    layout_path = pathlib.Path(layout_path)
    if not layout_path.is_absolute():
        layout_path = C.ROOT / layout_path
    L = json.loads(layout_path.read_text(encoding="utf-8"))
    ident = L["id"]
    print(f"\n=== 组装 {ident} · {L['name']} ===")
    reset_scene()
    build_shell(L)
    placed, missing = place_assets(L)
    setup_world(L.get("render", {}).get("exposure", -0.35))
    setup_lighting(L)
    setup_camera(L)
    C.ASSEMBLED.mkdir(parents=True, exist_ok=True)
    out_blend = C.ASSEMBLED / f"{ident}.blend"
    relink_textures(out_blend)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"  资产实例 {placed}/{len(L['assets'])}  缺失 {len(missing)}")
    if missing:
        print("  MISSING:", ", ".join(missing[:8]))
    print(f"  输出 {out_blend.relative_to(C.ROOT)}")
    if do_render:
        out_png = C.ASSEMBLED / f"{ident}.png"
        render_preview(L, out_png)
        print(f"  预览 {out_png.relative_to(C.ROOT)}")
    return placed, missing


def catalog_rows():
    with open(C.CATALOG_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def list_categories():
    rows = catalog_rows()
    seen = {}
    for r in rows:
        seen[r["category_no"]] = r["category"]
    print(f"共 {len(seen)} 类 / {len(rows)} 个资产（完整 4K · 8 通道 PBR）")
    for no, cn in seen.items():
        print(f"  {no} {cn}")


def pick(no):
    rows = [r for r in catalog_rows() if r["category_no"] == no]
    if not rows:
        print(f"无类别 {no}")
        return
    print(f"类别 {no} · {rows[0]['category']}")
    for r in rows:
        print(f"  {r['id']:<28} {r['dimensions_m']:<18} {r['materials']}")


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    C.ensure_dirs()
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--list-categories":
        list_categories()
        return
    if args[0] == "--pick" and len(args) > 1:
        pick(args[1])
        return
    do_render = "--render" in args
    targets = [a for a in args if a != "--render" and not a.startswith("--")]
    if args[0] == "--all":
        targets = sorted(str(p) for p in C.LAYOUTS.glob("*.json"))
    total = 0
    for t in targets:
        p, _ = assemble(t, do_render)
        total += p
    print(f"\n=== 完成，共实例化 {total} 个资产 ===")


if __name__ == "__main__":
    main()
