"""将单个 Tripo GLB 渲染为四向和近景，不修改源文件。

用法：blender -b --python scripts/render_tripo_views.py -- 输入.glb 输出目录 [material-diagnostic]
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
if len(args) not in (2, 3) or (len(args) == 3 and args[2] != "material-diagnostic"):
    raise SystemExit("用法：-- 输入.glb 输出目录 [material-diagnostic]")
source, output = map(Path, args[:2])
diagnostic = len(args) == 3
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

views = (
    ("front", (0, -1, 0.08), 1.25),
    ("back", (0, 1, 0.08), 1.25),
    ("left", (-1, 0, 0.08), 1.25),
    ("right", (1, 0, 0.08), 1.25),
    ("close", (0.35, -1, 0.2), 0.65),
)
if diagnostic:
    views = (("original", (0.35, -1, 0.2), 0.65),)

def render_view(name, direction, scale):
    camera.location = center + Vector(direction).normalized() * extent * 3
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = extent * scale
    light.location = center + Vector(direction).normalized() * extent * 2 + Vector((0, 0, extent * 2))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str((output / f"{name}.png").resolve())
    bpy.ops.render.render(write_still=True)

for name, direction, scale in views:
    render_view(name, direction, scale)

if diagnostic:
    shaders = [node for mat in bpy.data.materials if mat.use_nodes
               for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
    if not shaders:
        raise RuntimeError("没有可检查的 Principled 材质")
    for shader in shaders:
        socket = shader.inputs["Normal"]
        for link in list(socket.links):
            shader.id_data.links.remove(link)
    render_view("without-normal", (0.35, -1, 0.2), 0.65)
    for shader in shaders:
        socket = shader.inputs["Base Color"]
        for link in list(socket.links):
            shader.id_data.links.remove(link)
        socket.default_value = (0.5, 0.5, 0.5, 1)
    render_view("neutral-color-without-normal", (0.35, -1, 0.2), 0.65)
print(f"检查图已保存：{output}")
