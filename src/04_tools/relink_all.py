"""批量重定位所有 .blend 的贴图路径（搬项目 / 改目录结构后一键修复）。

    blpython src/04_tools/relink_all.py

会遍历：母库、房屋、144 个独立资产的 model.blend，把每个文件内的贴图引用
统一改成相对该文件自身的 // 路径。依赖 config.py，无硬编码。
"""
from __future__ import annotations
import bpy, os, sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C

blends = [C.LIBRARY_BLEND, C.HOUSE_BLEND]
if C.BY_CATEGORY.exists():
    blends += sorted(C.BY_CATEGORY.rglob("model.blend"))
if C.LIBRARY_DIR.exists():
    blends += [p for p in C.LIBRARY_DIR.glob("*.blend") if p not in blends]

total_fixed, total_missing, done = 0, 0, 0
for blend in blends:
    if not blend.exists():
        continue
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    fixed, missing = 0, 0
    for im in bpy.data.images:
        if im.source != 'FILE' or not im.filepath:
            continue
        base = os.path.basename(im.filepath.replace('\\', '/'))
        target = C.tex_by_name(base)
        if target is None or not target.exists():
            missing += 1
            continue
        im.filepath = C.rel(target, blend)
        try:
            im.reload()
        except RuntimeError:
            pass
        fixed += 1
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    total_fixed += fixed
    total_missing += missing
    done += 1
    if done % 30 == 0:
        print(f"RELINK_PROGRESS {done}/{len(blends)}", flush=True)

print(f"RELINK_ALL_DONE blends={done} fixed={total_fixed} missing={total_missing}")
