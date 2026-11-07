"""渲染 A030 原件四向、近景及横向形变对照；不修改原 GLB。"""
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tripo" / "outputs" / "A030" / "comparison"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "tripo" / "outputs" / "A030" / "tripo-original.glb"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.world = bpy.data.worlds.new("A030 comparison world")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
bpy.ops.object.light_add(type="AREA", location=(2, -3, 4))
light = bpy.context.object
light.data.energy = 400
light.data.size = 4
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
scene.camera = camera
center = sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8


def render(name, direction, scale, target):
    camera.location = target + Vector(direction).normalized() * 3
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    light.location = target + Vector(direction).normalized() * 2 + Vector((0, 0, 2))
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


for name, direction in (("front", (0, -1, 0.12)), ("back", (0, 1, 0.12)),
                        ("left", (-1, 0, 0.12)), ("right", (1, 0, 0.12))):
    render(name, direction, 1.35, center)
render("original-close", (0.35, -1, 0.25), 0.65, center + Vector((0, 0, -0.15)))
# 不重投影 UV：观察小幅横向形变是否暴露纹理拉伸或接缝。
obj.scale.x *= 1.12
render("stretched-close", (0.35, -1, 0.25), 0.65, center + Vector((0, 0, -0.15)))
print(f"A030 原件和横向1.12倍对照渲染完成：{OUT}")
