"""把当前 .blend 内所有贴图引用重定位为相对路径（迁移/搬家用）。

整个项目文件夹被搬到任意位置后，贴图仍以 ``//`` 相对路径引用，通常无需运行
本工具；只有在以下情况才需要：

  * 从别处 append / link 了资产，导致贴图带上了外部绝对路径；
  * 手工改过贴图目录结构；
  * 只想把某个资产目录单独拷出去（此时应配合 migrate_check.py 检查）。

用法（在项目根目录执行）：
    blender -b scene/house.blend -P src/04_tools/relink_textures.py
    blender -b assets/_library/asset_library.blend -P src/04_tools/relink_textures.py

批量修复全部 144 个独立资产：
    python src/04_tools/relink_all.py

路径全部来自 config.py，无硬编码。
"""
import bpy, os

# --- 路径自举 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C

blend_path = bpy.data.filepath
if not blend_path:
    raise RuntimeError("请先打开一个已保存的 .blend 文件再运行本脚本")

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

bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"RELINK_DONE blend={os.path.basename(blend_path)} fixed={fixed} missing={missing}")
