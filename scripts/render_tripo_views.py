"""将单个 Tripo GLB 渲染为四向和近景，不修改源文件。

用法：blender -b --python scripts/render_tripo_views.py -- 输入.glb 输出目录
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
if len(args) != 2:
    raise SystemExit("用法：-- 输入.glb 输出目录")
source, output = map(Path, args)
output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not objects:
    raise RuntimeError("模型没有网格")
points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
center = (minimum + maximum) / 2
extent = max(maximum - minimum)
if extent <= 0:
    raise RuntimeError("模型包围盒为空")
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.world = bpy.data.worlds.new("inspection world")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
bpy.ops.object.light_add(type="AREA")
light = bpy.context.object
light.data.energy = 400 * extent * extent
light.data.size = 4 * extent
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
scene.camera = camera

for name, direction, scale in (
    ("front", (0, -1, 0.08), 1.25),
    ("back", (0, 1, 0.08), 1.25),
    ("left", (-1, 0, 0.08), 1.25),
    ("right", (1, 0, 0.08), 1.25),
    ("close", (0.35, -1, 0.2), 0.65),
):
    camera.location = center + Vector(direction).normalized() * extent * 3
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = extent * scale
    light.location = center + Vector(direction).normalized() * extent * 2 + Vector((0, 0, extent * 2))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str((output / f"{name}.png").resolve())
    bpy.ops.render.render(write_still=True)
print(f"五向检查图已保存：{output}")
