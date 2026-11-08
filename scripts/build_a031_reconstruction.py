"""重建 A031 单层围裙研究稿；原始 Tripo 网格保留为隐藏参照。"""
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stages" / "S002" / "A031-study"
sys.path.insert(0, str(ROOT / "scripts"))
from build_a030_study import mesh_grid, seam

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = "METRIC"

# 这些贴图是项目已有的织物研究贴图；需继续接受实际近景检查。
library = ROOT / "stages" / "S002" / "A030-study" / "study-textured.blend"
names = ["study_flax_canvas", "study_olive_webbing", "study_natural_thread"]
with bpy.data.libraries.load(str(library), link=False) as (src, dst):
    dst.materials = list(names)
for image in bpy.data.images:
    if image.source == "FILE" and not image.packed_file:
        image.filepath = str(ROOT / "stages" / "S002" / "A030-study" / "textures" / Path(image.filepath).name)
        image.reload()
        image.pack()
canvas, webbing, thread = dst.materials


def half_width(z):
    # 下摆至腰部近直线，胸片两侧平滑收窄。
    if z <= 0.48:
        return 0.35 - 0.015 * z / 0.48
    t = min(1.0, (z - 0.48) / 0.37)
    return 0.145 + 0.19 * (1 - t) ** 2


def surface(x, z):
    u = x / max(half_width(z), 0.001)
    top = min(1.0, z / 0.85)
    drape = 0.010 * math.sin(5.0 * u + 1.4 * top) * (1 - 0.55 * top)
    left_fold = 0.020 * math.exp(-((u + 0.63 - 0.18 * top) / 0.17) ** 2) * (1 - top) ** 0.7
    right_fold = -0.014 * math.exp(-((u - 0.56 + 0.18 * top) / 0.19) ** 2) * (1 - top) ** 0.8
    return drape + left_fold + right_fold


def panel(u, v):
    z = 0.85 * v
    x = (2 * u - 1) * half_width(z)
    return x, surface(x, z), z


mesh_grid("A031_body", 120, 144, panel, canvas, 0.0018)


def pocket(u, v):
    x = (u - 0.5) * 0.48
    z = 0.27 + 0.23 * v
    # 上缘稍向外张开，底边及两侧保持贴合。
    opening = 0.010 * v ** 5 * math.sin(math.pi * u) ** 0.5
    return x, surface(x, z) - 0.0025 - opening, z


mesh_grid("A031_patch_pocket", 80, 48, pocket, canvas, 0.0015)
paths = {
    "pocket_edge": [pocket(0.012, 1 - i / 48) for i in range(49)]
    + [pocket(i / 80, 0.012) for i in range(1, 80)]
    + [pocket(0.988, i / 48) for i in range(49)],
    "pocket_divider": [pocket(0.5, i / 48) for i in range(49)],
    "pocket_top": [pocket(i / 80, 0.97) for i in range(81)],
}
for name, path in paths.items():
    seam("A031_" + name, [(x, y - 0.001, z) for x, y, z in path], thread, 0.00022)

# 腰侧与下摆的细线沿布面变化，避免飘离褶皱。
hem = [panel(0.012, 1 - i / 144) for i in range(145)]
hem += [panel(i / 120, 0.01) for i in range(1, 120)]
hem += [panel(0.988, i / 144) for i in range(145)]
seam("A031_body_hem", [(x, y - 0.0012, z) for x, y, z in hem], thread, 0.00022)


def neck(u, v):
    t = v
    x = -0.145 + 0.29 * t
    z = 0.85 + 0.245 * math.sin(math.pi * t)
    dx, dz = 0.29, 0.245 * math.pi * math.cos(math.pi * t)
    length = math.hypot(dx, dz)
    offset = (u - 0.5) * 0.026
    x += -dz / length * offset
    z += dx / length * offset
    return x, surface(x, min(z, 0.85)) - 0.001, z


mesh_grid("A031_neck_strap", 6, 96, neck, webbing, 0.0018)
for side in (-1, 1):
    def waist(u, v, side=side):
        t = v
        x = side * (0.326 + 0.17 * math.sin(math.pi * t / 2))
        z = 0.48 - 0.29 * t * t
        dx = side * 0.17 * math.pi / 2 * math.cos(math.pi * t / 2)
        dz = -0.58 * t
        length = math.hypot(dx, dz)
        offset = (u - 0.5) * 0.027
        x -= dz / length * offset
        z += dx / length * offset
        y = surface(side * 0.326, 0.48) - 0.002 - 0.018 * t
        return x, y, z
    mesh_grid(f"A031_waist_strap_{side}", 6, 64, waist, webbing, 0.0018)

# 保留 Tripo 原件以便对照，不参与导出和渲染。
bpy.ops.import_scene.gltf(filepath=str(ROOT / "tripo" / "outputs" / "A031" / "tripo-original.glb"))
guide = bpy.context.selected_objects[0]
guide.name = "A031_tripo_guide"
guide.hide_render = True
guide.hide_set(True)
guide.hide_viewport = True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "reconstructed-v2.blend"))
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.scene.objects:
    if obj.name.startswith("A031_") and obj != guide:
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / "reconstructed-v2.glb"), export_format="GLB", use_selection=True)
print("A031 单层重建研究已保存；仍须外观和结构验收。")
