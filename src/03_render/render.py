"""03 渲染出图（Cycles CPU，无 GPU）。

从 scene/house.blend 渲染 6 个机位（整体 + 各空间），并渲染资产库总览与 5 张资产特写。
低采样 + OIDN 降噪控制耗时；分辨率按机位重要性分级。
"""
import bpy, os, sys, csv, random, math
from mathutils import Vector

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

HOUSE = str(C.HOUSE_BLEND)
RENDERS = str(C.RENDERS)

# 机位 -> (相机名, 分辨率, 采样数)
SHOTS = [
    ("living",   "CAM_living",   1280, 840, 48),
    ("kitchen",  "CAM_kitchen",  1280, 840, 48),
    ("bedroom",  "CAM_bedroom",  1100, 740, 40),
    ("study",    "CAM_study",    1100, 740, 40),
    ("bath",     "CAM_bath",     1000, 680, 32),
    ("overview", "CAM_overview", 1100, 1100, 28),
]



def relink_textures():
    """4K 贴图以 //../_textures/ 相对路径存于 asset_library.blend；
    通过 libraries.load 载入到未保存的临时场景时相对基准会失效，这里按文件名重定位。"""
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        tgt = C.tex_by_name(base)
        if tgt and tgt.exists() and os.path.abspath(im.filepath) != str(tgt):
            im.filepath = str(tgt)
            try:
                im.reload()
            except Exception:
                pass


def render_shots(only=None):
    """only 为机位 key 集合时只渲染指定机位（用于局部修补后补图，避免全量重渲）。"""
    bpy.ops.wm.open_mainfile(filepath=HOUSE)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 24
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
        # 白色软包 / 织物在高光下易过曝丢细节，整体压 0.35 档
        sc.view_settings.exposure = -0.35
    except Exception:
        pass
    results = []
    for key, camname, w, h, samples in SHOTS:
        if only and key not in only:
            continue
        cam = bpy.data.objects.get(camname)
        if not cam:
            print("NO_CAM", camname); continue
        # 俯视机位需要临时移除天花板，否则看不到室内
        ceilings = [o for o in bpy.data.objects if o.name.startswith("ceiling")]
        for o in ceilings:
            o.hide_render = (key == "overview")
        sc.camera = cam
        sc.render.resolution_x = w; sc.render.resolution_y = h
        sc.render.resolution_percentage = 100
        sc.cycles.samples = samples
        sc.render.filepath = str(C.R_SHOTS / f"house_{key}.png")
        bpy.ops.render.render(write_still=True)
        p = sc.render.filepath
        print("SHOT", key, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0, flush=True)
        results.append((key, os.path.getsize(p) if os.path.exists(p) else 0))
    return results


def render_asset_closeups():
    """Q10：随机抽 5 个资产，单独摆到小展台上做近景渲染，验证细节经得起放大。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    LIB = str(C.LIBRARY_BLEND)
    rows = list(csv.DictReader(open(C.CATALOG_CSV)))
    random.seed(20261107)
    picks = random.sample(rows, 5)

    with bpy.data.libraries.load(LIB, link=False) as (src, dst):
        names = [p["id"] for p in picks]
        dst.collections = list(names)
    cols = {c.name: c for c in dst.collections if c}

    for i, p in enumerate(picks):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        with bpy.data.libraries.load(LIB, link=False) as (src, dst):
            dst.collections = [p["id"]]
        c = [x for x in dst.collections if x][0]
        relink_textures()
        e = bpy.data.objects.new("asset", None)
        e.instance_type = 'COLLECTION'; e.instance_collection = c
        bpy.context.scene.collection.objects.link(e)

        # 依据 manifest 的包围盒尺寸自适应机位（正交取景，让资产占画面主体）
        dims = [float(x) for x in p["dimensions_m"].split("x")]
        maxdim = max(dims) if dims else 0.5
        maxdim = max(maxdim, 0.12)
        height = dims[2] if len(dims) > 2 else maxdim
        target = Vector((0, 0, height * 0.45))

        # 中性亮世界，避免背景上半部发黑
        w = bpy.data.worlds.new("studio_world")
        bpy.context.scene.world = w
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs['Color'].default_value = (0.30, 0.32, 0.35, 1)
        w.node_tree.nodes["Background"].inputs['Strength'].default_value = 0.45

        floor = bpy.data.materials.new("studio_floor"); floor.use_nodes = True
        floor.node_tree.nodes.get("Principled BSDF").inputs['Base Color'].default_value = (0.24, 0.25, 0.27, 1)
        floor.node_tree.nodes.get("Principled BSDF").inputs['Roughness'].default_value = 0.9
        bpy.ops.mesh.primitive_plane_add(size=40)
        fl = bpy.context.object; fl.data.materials.append(floor); fl.location.z = -0.01

        def area(nm, energy, loc, sz):
            ld = bpy.data.lights.new(nm, 'AREA')
            ld.energy = energy; ld.shape = 'DISK'; ld.size = sz
            lo = bpy.data.objects.new(nm, ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = loc
            lo.rotation_euler = (target - lo.location).to_track_quat('-Z', 'Y').to_euler()
            return lo

        # 固定距离布光：不随资产尺寸缩放，避免小资产因灯距过近而过曝
        area("key", 260, (1.6, -1.8, 2.6), 2.4)
        area("fill", 130, (-2.0, -0.5, 1.5), 2.4)
        area("rim", 100, (-0.5, 1.8, 2.0), 2.0)

        cam = bpy.data.cameras.new("cam")
        cam.type = 'ORTHO'
        cam.ortho_scale = maxdim * 1.75
        co = bpy.data.objects.new("cam", cam)
        bpy.context.scene.collection.objects.link(co)
        # 固定机位角度（正交取景大小只由 ortho_scale 决定），略俯视以看清扁平资产
        co.location = Vector((1.5, -1.9, 1.9)) + target
        co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()

        sc = bpy.context.scene
        sc.camera = co
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
        sc.cycles.samples = 40; sc.cycles.use_denoising = True
        sc.render.resolution_x = 800; sc.render.resolution_y = 800
        sc.render.image_settings.file_format = 'PNG'
        sc.render.threads_mode = 'FIXED'; sc.render.threads = 24
        try:
            sc.view_settings.view_transform = 'AgX'
            sc.view_settings.look = 'AgX - Medium High Contrast'
            sc.view_settings.exposure = -0.20
        except Exception:
            pass
        out = str(C.R_CLOSEUPS / f"asset_closeup_{i+1}_{p['id']}.png")
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print("CLOSEUP", i + 1, p["id"], p["category"], os.path.getsize(out) if os.path.exists(out) else 0, flush=True)

    with open(C.R_CLOSEUPS / "closeup_picks.md", "w") as f:
        f.write("# Q10 资产特写抽查（随机 5 个，seed=20261107）\n\n")
        f.write("| # | 资产 ID | 类别 | 尺寸 (m) | 部件数 | 材质 |\n| --- | --- | --- | --- | --- | --- |\n")
        for i, p in enumerate(picks):
            f.write(f"| {i+1} | {p['id']} | {p['category']} | {p['dimensions_m']} | "
                    f"{p['parts']} | {p['materials']} |\n")
    return [p["id"] for p in picks]


def render_hero_4k():
    """真 4K 主图（3840×2160）：分 2×2 区块渲染再无损拼接。

    单进程直接渲染 4K 时内存峰值约 4.3 GB，会触发容器上限，进程在保存前被杀；
    改为 4 个 1920×1080 区块分别渲染（相机 / 灯光 / 色彩管理完全一致），每块
    内存显著低于上限，最后用 PIL 拼接。每个像素仍由 Cycles 真实渲染，不是放大。
    """
    from PIL import Image
    bpy.ops.wm.open_mainfile(filepath=HOUSE)
    sc = bpy.context.scene
    cam = bpy.data.objects.get("CAM_living")
    if not cam:
        print("NO_HERO_CAM")
        return None
    sc.camera = cam
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.cycles.samples = 12
    sc.render.image_settings.file_format = 'PNG'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 16
    sc.render.use_persistent_data = False
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
        sc.view_settings.exposure = -0.35
    except Exception:
        pass
    sc.render.resolution_x = 3840; sc.render.resolution_y = 2160
    sc.render.resolution_percentage = 100
    sc.render.use_border = True
    sc.render.use_crop_to_border = True

    # (border_min_x, min_y, max_x, max_y) -> 拼到最终图的左上角坐标
    quads = [
        (0.0, 0.0, 0.5, 0.5, (0, 1080)),      # 左下
        (0.5, 0.0, 1.0, 0.5, (1920, 1080)),   # 右下
        (0.0, 0.5, 0.5, 1.0, (0, 0)),         # 左上
        (0.5, 0.5, 1.0, 1.0, (1920, 0)),      # 右上
    ]
    tiles = []
    for i, (x0, y0, x1, y1, pos) in enumerate(quads):
        sc.render.border_min_x, sc.render.border_max_x = x0, x1
        sc.render.border_min_y, sc.render.border_max_y = y0, y1
        p = str(C.R_HERO / f"_hero_tile_{i}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        if not os.path.exists(p):
            print("HERO_TILE_MISSING", i, flush=True)
            return None
        tiles.append((p, pos))
        print("HERO_TILE", i, os.path.getsize(p), flush=True)

    out = Image.new('RGB', (3840, 2160))
    for p, pos in tiles:
        im = Image.open(p).convert('RGB')
        if im.size != (1920, 1080):
            im = im.resize((1920, 1080), Image.LANCZOS)
        out.paste(im, pos)
    hero = str(C.R_HERO / "hero_4k.png")
    out.save(hero, optimize=True)
    for p, _ in tiles:
        try:
            os.remove(p)
        except OSError:
            pass
    print("HERO_4K", os.path.exists(hero), os.path.getsize(hero), flush=True)
    return hero


def main():
    mode = sys.argv[-1] if len(sys.argv) > 1 else "all"
    if mode.startswith("house:"):
        keys = {k for k in mode.split(":", 1)[1].split(",") if k}
        print("HOUSE_SHOTS", render_shots(only=keys), flush=True)
    elif mode in ("all", "house"):
        print("HOUSE_SHOTS", render_shots(), flush=True)
    if mode in ("all", "closeup"):
        print("CLOSEUPS", render_asset_closeups(), flush=True)
    if mode in ("all", "hero"):
        render_hero_4k()
    print("RENDER_DONE", flush=True)


if __name__ == "__main__":
    main()
