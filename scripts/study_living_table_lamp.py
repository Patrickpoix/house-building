"""将台灯原稿按设计尺度试放到起居室；桌子仅供位置检查。"""
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "stages/S003/bookshelf-geometry/house-bookshelf-refinement.blend"
LAMP = ROOT / "tripo/outputs/living-table-lamp/tripo-original.glb"
OUT = ROOT / "stages/S003/table-lamp-study"

OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
# 保存新工程前打包既有相对路径贴图，避免路径随工程目录变化失效。
bpy.ops.file.pack_all()
bpy.ops.import_scene.gltf(filepath=str(LAMP))
lamp = next(obj for obj in bpy.context.selected_objects if obj.type == "MESH")
lamp.name = "STUDY_table_lamp_original"
points = [lamp.matrix_world @ Vector(p) for p in lamp.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
scale = 0.52 / (high.z - low.z)
lamp.scale *= scale
bpy.context.view_layer.update()
points = [lamp.matrix_world @ Vector(p) for p in lamp.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
lamp.location += Vector((1.52 - (low.x + high.x) / 2,
                         7.95 - (low.y + high.y) / 2, 0.54 - low.z))

# 简单桌体仅支撑比例试放，不能作为正式家具。
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.52, 7.95, 0.27))
table = bpy.context.object
table.name = "STUDY_temporary_lamp_support"
table.dimensions = (0.48, 0.48, 0.54)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
scene = bpy.context.scene
camera = scene.camera
scene.render.resolution_x, scene.render.resolution_y = 1200, 800
scene.cycles.samples = 48
scene.cycles.use_denoising = True
for name, position, target, lens in (
    ("living", (5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
    ("lamp-close", (3.05, 6.35, 1.45), (1.52, 7.95, 0.83), 55),
):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-table-lamp-study.blend"))
print("台灯试放完成；临时桌体、结构及照明均未验收。")
