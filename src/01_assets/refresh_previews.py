"""只重刷 144 张资产预览图与 36 张类别拼图，不重导 .blend。

用于调整预览灯光 / 材质显示色后快速更新，避免重跑完整导出。

    blpython src/01_assets/refresh_previews.py
    blpython src/01_assets/refresh_previews.py -- 01 02     # 只刷指定类别
"""
from __future__ import annotations
import bpy, os, sys, csv
from mathutils import Vector

# --- 路径自举 ---
import pathlib as _pathlib
sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C

from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    bpy.context.preferences.filepaths.save_version = 0
except Exception:
    pass

PREVIEW_PX = 360


def font(sz=14):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def bounds_of(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    if not pts:
        return (1, 1, 1), Vector((0, 0, 0.5))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return tuple(hi[i] - lo[i] for i in range(3)), (lo + hi) / 2


def set_display_colors():
    for m in bpy.data.materials:
        if m.name not in C.MATERIALS:
            continue
        p = C.tex(m.name, "basecolor")
        if not p.exists():
            continue
        try:
            a = np.asarray(Image.open(p).resize((32, 32)).convert('RGB'), dtype=float) / 255
            m.diffuse_color = (*a.reshape(-1, 3).mean(0), 1.0)
        except Exception:
            pass


def setup(center, size):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("PREVIEW_WORLD"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.80, 0.82, 0.85, 1.0)
    bg.inputs[1].default_value = 0.75
    cd = bpy.data.cameras.new("PREVIEW_CAM"); cam = bpy.data.objects.new("PREVIEW_CAM", cd)
    sc.collection.objects.link(cam); sc.camera = cam
    cd.type = 'ORTHO'; cd.ortho_scale = max(max(size) * 2.4, 0.35)
    d = Vector((1.0, -1.25, 0.85)).normalized()
    cam.location = center + d * max(max(size) * 3.0, 1.2)
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for name, energy, off in (("KEY", 220, (1.5, -2.0, 3.0)),
                              ("FILL", 90, (-2.0, 1.2, 1.8))):
        ld = bpy.data.lights.new("PREVIEW_" + name, 'AREA')
        ld.energy = energy; ld.shape = 'DISK'; ld.size = max(max(size) * 3.0, 2.0)
        ob = bpy.data.objects.new("PREVIEW_" + name, ld); sc.collection.objects.link(ob)
        ob.location = center + Vector(off)
        ob.rotation_euler = (center - ob.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = 12; sc.cycles.use_denoising = True
    sc.render.resolution_x = PREVIEW_PX; sc.render.resolution_y = PREVIEW_PX
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 8
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass


def relink(blend_path):
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        t = C.tex_by_name(base)
        if t and t.exists():
            im.filepath = C.rel(t, blend_path)
            try:
                im.reload()
            except RuntimeError:
                pass


def category_sheet(no, cn, en, ids):
    cdir = C.category_dir(no, cn, en)
    ims = []
    for aid in ids:
        p = C.asset_dir(no, cn, en, aid) / "preview.png"
        if p.exists():
            ims.append((aid.rsplit("_", 1)[-1], Image.open(p).convert('RGB')))
    if not ims:
        return
    cell, cols = PREVIEW_PX, 2
    rows = (len(ims) + 1) // 2
    sh = Image.new('RGB', (cols * cell, rows * (cell + 28)), (246, 246, 246))
    d = ImageDraw.Draw(sh)
    for i, (variant, im) in enumerate(ims):
        x, y = (i % cols) * cell, (i // cols) * (cell + 28)
        sh.paste(im.resize((cell, cell), Image.LANCZOS), (x, y))
        d.text((x + 6, y + cell + 5), f"variant {variant}", fill=(20, 20, 20), font=font(14))
    sh.save(cdir / "preview.png")


def main():
    only = None
    if "--" in sys.argv:
        tail = sys.argv[sys.argv.index("--") + 1:]
        if tail:
            only = set(tail)
    rows = list(csv.DictReader(open(C.CATALOG_CSV, encoding="utf-8")))
    done = 0
    for no, cn, en in C.CATEGORIES:
        if only and no not in only:
            continue
        ids = [r["id"] for r in rows if r["category_no"] == no]
        for aid in ids:
            blend = C.asset_dir(no, cn, en, aid) / "model.blend"
            if not blend.exists():
                print("MISS", aid, flush=True)
                continue
            bpy.ops.wm.open_mainfile(filepath=str(blend))
            relink(blend)
            set_display_colors()
            meshes = [o for o in bpy.data.objects if o.type == 'MESH']
            size, center = bounds_of(meshes)
            setup(center, size)
            bpy.context.scene.render.filepath = str(
                C.asset_dir(no, cn, en, aid) / "preview.png")
            bpy.ops.render.render(write_still=True)
            done += 1
        category_sheet(no, cn, en, ids)
        print(f"[PREVIEW] {no} {cn} 完成，累计 {done}", flush=True)
    print("PREVIEWS_DONE", done, flush=True)


if __name__ == "__main__":
    main()
