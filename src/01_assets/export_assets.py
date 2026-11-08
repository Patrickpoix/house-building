"""把 36 类 / 144 个 PBR 资产从母库拆成独立、可迁移的文件。

每个资产目录（assets/by_category/<类别>/<资产ID>/）产出三件套：
  model.blend   — 独立 Blender 文件，贴图以 // 相对路径引用共享 4K 贴图库
  preview.png   — Cycles 真实材质预览（摄影棚灯光 / 正交机位）
  meta.json     — 尺寸、材质、部件数、顶点数、依赖贴图、来源等元数据

每个类别目录另产出：
  README.md     — 本类 4 个变体的对照说明
  preview.png   — 4 变体拼图

不默认生成内嵌缩略贴图的 glTF 副本（几何与 model.blend 完全重复，
144 份合计约 500 MiB）。需要跨软件复用时，用
src/04_tools/export_glb.py 按需为指定资产导出自包含 GLB。

不修改母库 asset_library.blend。可重复运行（覆盖式幂等）。
用法：
    blender -b -P src/01_assets/export_assets.py            # 全量 144 个
    blender -b -P src/01_assets/export_assets.py -- 01      # 只导第 01 类
"""
from __future__ import annotations
import bpy, os, sys, json, csv, math, gc
from pathlib import Path
from mathutils import Vector

# --- 路径自举 ---
import pathlib as _pathlib
sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

from PIL import Image, ImageDraw, ImageFont

PREVIEW_PX = 360

# 关闭 .blend1 备份，避免每个资产多出一个副本
try:
    bpy.context.preferences.filepaths.save_version = 0
except Exception:
    pass


def log(*a):
    print("[EXPORT]", *a, flush=True)


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


# ---------------------------------------------------------------- 元数据
def load_catalog():
    with open(C.CATALOG_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bounds_of(objs):
    """世界包围盒尺寸与中心（用于相机自动取景）。"""
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        for corner in o.bound_box:
            pts.append(o.matrix_world @ Vector(corner))
    if not pts:
        return (1.0, 1.0, 1.0), Vector((0, 0, 0.5))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return tuple(hi[i] - lo[i] for i in range(3)), (lo + hi) / 2


def set_material_display_colors():
    """把每种材质的 viewport 固有色设成该材质 albedo 平均色。

    程序化材质的 diffuse_color 默认是灰 (0.6)，会让 Workbench / 实体视图
    里所有资产看起来像灰模。这里按 4K basecolor 取平均色写回，
    使任何显示模式下颜色都与真实 PBR 贴图一致。
    """
    import numpy as np
    for m in bpy.data.materials:
        if m.name not in C.MATERIALS:
            continue
        p = C.tex(m.name, "basecolor")
        if not p.exists():
            continue
        try:
            a = np.asarray(Image.open(p).resize((32, 32)).convert('RGB'),
                           dtype=float) / 255.0
            m.diffuse_color = (*a.reshape(-1, 3).mean(0), 1.0)
        except Exception:
            pass


def setup_preview(center: Vector, size):
    """Cycles 低采样摄影棚预览：真实 PBR 贴图 + 浅灰背景 + 柔和灯光。

    12 采样 + OIDN 降噪单张约 3 秒，144 张仍在可接受范围，且能真实呈现
    木纹 / 织物 / 金属 / 陶瓷的材质差异，而非灰模。
    """
    sc = bpy.context.scene

    # 浅灰渐变背景（世界）
    world = bpy.data.worlds.new("PREVIEW_WORLD")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.80, 0.82, 0.85, 1.0)
    bg.inputs[1].default_value = 0.75

    # 正交相机
    cam_data = bpy.data.cameras.new("PREVIEW_CAM")
    cam = bpy.data.objects.new("PREVIEW_CAM", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(max(size) * 2.4, 0.35)
    dist = max(max(size) * 3.0, 1.2)
    direction = Vector((1.0, -1.25, 0.85)).normalized()
    cam.location = center + direction * dist
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()

    # 主光 + 补光
    ld = bpy.data.lights.new("PREVIEW_KEY", 'AREA')
    ld.energy = 220
    ld.shape = 'DISK'
    ld.size = max(max(size) * 3.0, 2.0)
    key = bpy.data.objects.new("PREVIEW_KEY", ld)
    sc.collection.objects.link(key)
    key.location = center + Vector((1.5, -2.0, 3.0))
    key.rotation_euler = (center - key.location).to_track_quat('-Z', 'Y').to_euler()
    fill_data = bpy.data.lights.new("PREVIEW_FILL", 'AREA')
    fill_data.energy = 90
    fill_data.shape = 'DISK'
    fill_data.size = max(max(size) * 3.0, 2.0)
    fill = bpy.data.objects.new("PREVIEW_FILL", fill_data)
    sc.collection.objects.link(fill)
    fill.location = center + Vector((-2.0, 1.2, 1.8))
    fill.rotation_euler = (center - fill.location).to_track_quat('-Z', 'Y').to_euler()

    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 12
    sc.cycles.use_denoising = True
    sc.render.resolution_x = PREVIEW_PX
    sc.render.resolution_y = PREVIEW_PX
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 8
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    return cam


def make_preview(out_path: Path):
    sc = bpy.context.scene
    sc.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)


def relink_images(blend_path: Path):
    """把 .blend 内贴图改成相对该文件自身的 // 路径（可迁移的关键）。"""
    fixed, missing = 0, []
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        target = C.tex_by_name(base)
        if target is None or not target.exists():
            missing.append(base)
            continue
        im.filepath = C.rel(target, blend_path)
        try:
            im.reload()
        except RuntimeError:
            pass
        fixed += 1
    return fixed, missing


def used_textures():
    names = []
    for im in bpy.data.images:
        if im.source == 'FILE' and im.filepath:
            t = C.tex_by_name(os.path.basename(im.filepath.replace('\\', '/')))
            if t:
                names.append(str(t.relative_to(C.ROOT)).replace("\\", "/"))
    return sorted(set(names))


# ---------------------------------------------------------------- 单资产导出
def export_one(coll_name: str, row: dict, no: str, cn: str, en: str):
    adir = C.asset_dir(no, cn, en, coll_name)
    adir.mkdir(parents=True, exist_ok=True)

    # 1) 用 libraries.write 从母库抽出该 collection（不污染母库）
    blend_path = adir / "model.blend"
    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        log("MISS_COLLECTION", coll_name)
        return None
    bpy.data.libraries.write(str(blend_path), {coll})

    # 2) 打开独立 .blend，链入 view layer，修贴图路径，保存
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    sc = bpy.context.scene
    for c in list(bpy.data.collections):
        if c.name not in sc.collection.children:
            try:
                sc.collection.children.link(c)
            except RuntimeError:
                pass
    bpy.context.view_layer.update()

    fixed, missing = relink_images(blend_path)
    set_material_display_colors()
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    verts = sum(len(o.data.vertices) for o in meshes)
    faces = sum(len(o.data.polygons) for o in meshes)
    size, center = bounds_of(meshes)
    mats = sorted({o.active_material.name for o in meshes if o.active_material})
    textures = used_textures()

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    # 3) 预览渲染
    setup_preview(center, size)
    make_preview(adir / "preview.png")

    # 4) 元数据
    meta = dict(
        id=coll_name,
        category_no=no, category_cn=cn, category_en=en,
        name=row.get("name", ""), variant=row.get("variant", ""),
        builder=row.get("builder", ""),
        dimensions_m=row.get("dimensions_m", ""),
        materials_csv=row.get("materials", ""),
        materials_in_blend=mats,
        parts=len(meshes), vertices=verts, faces=faces,
        bounds_m=[round(float(v), 4) for v in size],
        textures=textures,
        texture_count=len(textures),
        relinked_textures=fixed, missing_textures=missing,
        files=dict(blend="model.blend", preview="preview.png", meta="meta.json"),
        portable="BLEND 以 // 相对路径引用 assets/_textures/；保持项目目录结构即可整体搬走复用",
    )
    with open(adir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


# ---------------------------------------------------------------- 类别产出
def category_outputs(no, cn, en, metas):
    cdir = C.category_dir(no, cn, en)
    cdir.mkdir(parents=True, exist_ok=True)
    # 4 变体拼图
    ims = []
    for m in metas:
        p = C.asset_dir(no, cn, en, m["id"]) / "preview.png"
        if p.exists():
            ims.append((m, Image.open(p).convert('RGB')))
    if ims:
        cell = PREVIEW_PX
        cols = 2
        rows = (len(ims) + 1) // 2
        sh = Image.new('RGB', (cols * cell, rows * (cell + 28)), (246, 246, 246))
        d = ImageDraw.Draw(sh)
        for i, (m, im) in enumerate(ims):
            x, y = (i % cols) * cell, (i // cols) * (cell + 28)
            sh.paste(im.resize((cell, cell), Image.LANCZOS), (x, y))
            d.text((x + 6, y + cell + 5), f'{m["variant"]}  {m["parts"]}p / {m["vertices"]}v',
                   fill=(20, 20, 20), font=font(14))
        sh.save(cdir / "preview.png")

    lines = [
        f"# {no} · {cn} {en}",
        "",
        f"本类共 **{len(metas)}** 个 PBR 资产变体，均带 4K / 8 通道 PBR 材质与几何细节。",
        "",
        "| 变体 | 资产 ID | 尺寸 (m) | 部件 | 顶点 | 材质 | 资产目录 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in metas:
        lines.append(
            f'| {m["variant"]} | `{m["id"]}` | {m["dimensions_m"]} | {m["parts"]} | '
            f'{m["vertices"]} | {m["materials_csv"]} | '
            f'[打开](./{m["id"]}/) |')
    # 取用说明集中在 assets/README.md 与 docs/08_迁移指南.md，
    # 不在 36 个类别 README 里逐字复制同一段。
    lines += [
        "",
        "取用与迁移见 [`assets/README.md`](../../README.md) 与",
        "[`docs/08_迁移指南.md`](../../../docs/08_迁移指南.md)。",
        "",
        "预览图见本目录 `preview.png`（4 变体拼图）与各资产目录内 `preview.png`。",
        "",
    ]
    with open(cdir / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------- 主流程
def main():
    only = None
    if "--" in sys.argv:
        tail = sys.argv[sys.argv.index("--") + 1:]
        if tail:
            only = set(tail)
    rows = load_catalog()
    by_id = {r["id"]: r for r in rows}

    # 母库只读打开一次，之后每个资产再打开自己的 .blend
    bpy.ops.wm.open_mainfile(filepath=str(C.LIBRARY_BLEND))
    all_cols = sorted(c.name for c in bpy.data.collections if c.name.startswith("AST_"))
    log("母库资产数", len(all_cols))

    done, failed = 0, []
    for no, cn, en in C.CATEGORIES:
        if only and no not in only:
            continue
        metas = []
        for cid in [c for c in all_cols if c.split("_")[1] == no]:
            try:
                m = export_one(cid, by_id.get(cid, {}), no, cn, en)
                if m:
                    metas.append(m)
                    done += 1
            except Exception as e:
                failed.append((cid, repr(e)[:160]))
                log("FAIL", cid, repr(e)[:160])
            # 每个资产结束后回到母库，保证下一个 collection 可取
            bpy.ops.wm.open_mainfile(filepath=str(C.LIBRARY_BLEND))
            if done % 24 == 0:
                gc.collect()
        if metas:
            category_outputs(no, cn, en, metas)
            log("CATEGORY", no, cn, len(metas), "完成，累计", done)

    # 顶层索引
    write_index(rows)
    log("DONE", done, "失败", len(failed))
    for f in failed[:20]:
        log("  FAILED", f)


def write_index(rows):
    lines = [
        "# PBR 资产库 · 36 类 / 144 个",
        "",
        "按类别分目录，每个资产独立成包（`model.blend` + `preview.png` + `meta.json`）。",
        "",
        "| 类别 | 中文 | 英文 | 数量 | 目录 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for no, cn, en in C.CATEGORIES:
        n = sum(1 for r in rows if r["category_no"] == no)
        lines.append(f"| {no} | {cn} | {en} | {n} | [{no}_{en}_{cn}](./{no}_{en}_{cn}/) |")
    lines += [
        "",
        f"合计 **{len(C.CATEGORIES)} 类 / {len(rows)} 个资产**。",
        "",
        "贴图库见 `../_textures/`（16 材质 × 8 通道 × 4096²）；母库见 `../_library/asset_library.blend`。",
        "迁移与复现见 `../../docs/08_迁移指南.md`。",
        "",
    ]
    with open(C.BY_CATEGORY / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
