"""按需把指定资产导出为自包含 GLB（跨软件复用，可选工具）。

默认流水线不产出 GLB：它会内嵌一份 1K 缩略贴图、几何与 model.blend 完全重复，
144 份合计约 500 MiB。只有当你需要把某几个资产拿到别的 3D 软件 / 网页里用时，
才用本工具临时导出，用完可随时删除，不影响工程本体。

用法（blpython = 装了 bpy 的解释器）：
    blpython src/04_tools/export_glb.py -- AST_01_001_餐椅_A       # 单个资产
    blpython src/04_tools/export_glb.py -- 01 03 07                  # 按类别号
    blpython src/04_tools/export_glb.py -- all                       # 144 个全量

参数可以是：完整资产 ID、两位类别号、或 all。可混用多个。
产物写到各资产目录下的 model.glb；model.blend 始终保留 4K 相对路径引用，
本工具只改内存里的图片路径，不回存 .blend。
"""
from __future__ import annotations
import bpy, os, sys, csv, tempfile
from pathlib import Path

# --- 路径自举：项目可任意改名 / 搬家 ---
import pathlib as _pathlib
sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C

from PIL import Image

GLB_TEX_PX = 1024          # 内嵌贴图边长：4K→1K，单文件约 2–4 MB
_TMP: Path | None = None
_CACHE: dict[str, str] = {}


def log(*a):
    print("[GLB]", *a, flush=True)


def small_texture(src: Path) -> str | None:
    """把 4K 贴图降采样成 1K 临时 PNG（带缓存）。"""
    global _TMP
    if not src.exists():
        return None
    key = str(src)
    if key in _CACHE:
        return _CACHE[key]
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="house_glb_tex_"))
    out = _TMP / (src.stem + ".png")
    try:
        im = Image.open(src)
        im.thumbnail((GLB_TEX_PX, GLB_TEX_PX), Image.LANCZOS)
        im.convert(im.mode if im.mode in ('L', 'RGB') else 'RGB').save(out, optimize=True)
    except Exception:
        return None
    _CACHE[key] = str(out)
    return str(out)


def switch_images():
    """把内存里的图片临时指向 1K 降采样版（磁盘 .blend 不变）。"""
    n = 0
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        target = C.tex_by_name(base)
        if target is None:
            continue
        small = small_texture(target)
        if small is None:
            continue
        im.filepath = small
        try:
            im.reload()
        except RuntimeError:
            pass
        n += 1
    return n


def resolve_targets(args: list[str]) -> list[Path]:
    """把参数（资产 ID / 类别号 / all）解析成资产目录列表。

    类别中英文名从 config.CATEGORIES 反查，不依赖 catalog.csv 的列名约定。
    """
    rows = list(csv.DictReader(open(C.CATALOG_CSV, encoding="utf-8")))
    cat_map = {no: (cn, en) for no, cn, en in C.CATEGORIES}
    wanted = set(args)
    all_mode = 'all' in wanted
    dirs: list[Path] = []
    for r in rows:
        no = r["category_no"]
        aid = r["id"]
        if all_mode or aid in wanted or no in wanted:
            cn, en = cat_map[no]
            dirs.append(C.asset_dir(no, cn, en, aid))
    # 去重并保持顺序
    seen, out = set(), []
    for d in dirs:
        if str(d) not in seen:
            seen.add(str(d))
            out.append(d)
    return out


def export_one(adir: Path) -> bool:
    blend = adir / "model.blend"
    if not blend.exists():
        log("SKIP 缺 model.blend", adir.name)
        return False
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    sc = bpy.context.scene
    for c in list(bpy.data.collections):
        if c.name not in sc.collection.children:
            try:
                sc.collection.children.link(c)
            except RuntimeError:
                pass
    bpy.context.view_layer.update()

    switch_images()
    for o in list(bpy.context.view_layer.objects):
        o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = next(
        (o for o in bpy.context.view_layer.objects if o.type == 'MESH'), None)

    out = adir / "model.glb"
    try:
        bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB',
                                  use_selection=True, export_apply=True,
                                  export_yup=True)
        log("OK", adir.name, f"{out.stat().st_size / 1048576:.2f} MiB")
        return True
    except Exception as e:
        log("FAIL", adir.name, repr(e)[:140])
        return False


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print(__doc__)
        return
    targets = resolve_targets(args)
    if not targets:
        log("没有匹配到任何资产，参数应为资产 ID / 类别号 / all")
        return
    log("待导出", len(targets), "个资产")
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    ok = sum(export_one(d) for d in targets)
    log("DONE", ok, "/", len(targets))


if __name__ == "__main__":
    main()
