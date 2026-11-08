"""用可编辑木边几替换灯具试放支撑方块；保存独立房间研究稿。"""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import board

SOURCE = ROOT / "stages/S003/lamp-power-study/house-lamp-power-study.blend"
OUT = ROOT / "stages/S003/side-table-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
placeholder = bpy.data.objects.get("STUDY_temporary_lamp_support")
if placeholder is None:
    raise RuntimeError("未找到原支撑体，停止以避免重复装配")
bpy.data.objects.remove(placeholder, do_unlink=True)
wood = bpy.data.materials["书架_白橡木皮_试验"]

# 台面上表面保持 0.54 m；真实结构的桌腿、围板可单独编辑。
board("STUDY_side_table_top", (1.52, 7.95, 0.526), (0.48, 0.48, 0.028), wood, 1, 0.17)
for x in (1.315, 1.725):
    for y in (7.745, 8.155):
        board(f"STUDY_side_table_leg_{x}_{y}", (x, y, 0.256), (0.038, 0.038, 0.512), wood, 2, x * 0.13 + y * 0.07)
for y in (7.745, 8.155):
    board(f"STUDY_side_table_apron_y_{y}", (1.52, y, 0.475), (0.372, 0.018, 0.075), wood, 0, 0.35)
for x in (1.315, 1.725):
    board(f"STUDY_side_table_apron_x_{x}", (x, 7.95, 0.475), (0.018, 0.372, 0.075), wood, 1, 0.52)

scene = bpy.context.scene
camera = scene.camera
scene.render.resolution_x, scene.render.resolution_y = 1200, 800
scene.cycles.samples = 48
scene.cycles.use_denoising = True
for name, position, target, lens in (
    ("living", (5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
    ("table-close", (3.05, 6.35, 1.35), (1.52, 7.95, 0.55), 48),
):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-side-table-study.blend"))
print("木边几试验已保存；接头、碰撞与正式房间验收待完成。")
