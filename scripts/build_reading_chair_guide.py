"""构建可编辑的阅读椅结构引导，不覆盖正式模型或现有参考。"""

from pathlib import Path
import math

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stages" / "S003" / "reading-chair-guide"


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*color, 1)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.7
    return mat


def box(name, center, size, mat, bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("柔化边缘", "BEVEL")
    mod.width = bevel
    mod.segments = 3
    obj.modifiers.new("平滑法线", "WEIGHTED_NORMAL")
    return obj


def beam(name, start, end, width, depth, mat):
    a, b = Vector(start), Vector(end)
    obj = box(name, (a + b) / 2, (width, depth, (b - a).length), mat)
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    wood = material("木框示意", (0.47, 0.26, 0.12))
    cushion = material("软垫示意", (0.66, 0.60, 0.49))
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    # 此处尺寸是设计选择，背部与座面下的结构不是实物证据。
    for side in (-1, 1):
        x = side * 0.35
        box(f"前腿_{side}", (x, -0.34, 0.29), (0.06, 0.06, 0.58), wood)
        box(f"后腿_{side}", (x, 0.30, 0.18), (0.06, 0.06, 0.36), wood)
        beam(f"背部立柱_{side}", (x, 0.30, 0.33), (x, 0.37, 0.73), 0.05, 0.055, wood)
        beam(f"扶手_{side}", (x, -0.34, 0.57), (x, 0.34, 0.59), 0.06, 0.045, wood)
        box(f"侧座框_{side}", (x, -0.02, 0.30), (0.05, 0.64, 0.08), wood)
    for y, name in ((-0.34, "前座框"), (0.30, "后座框")):
        box(name, (0, y, 0.30), (0.66, 0.05, 0.08), wood)
    for y in (-0.23, -0.09, 0.05, 0.19):
        box(f"座面承托_{y}", (0, y, 0.342), (0.65, 0.07, 0.025), wood)
    for y, z in ((0.33, 0.52), (0.36, 0.68)):
        box(f"背部横梁_{z}", (0, y, z), (0.67, 0.045, 0.055), wood)
    box("坐垫示意", (0, -0.035, 0.385), (0.64, 0.69, 0.10), cushion, 0.035)
    back = box("靠垫示意", (0, 0.27, 0.58), (0.64, 0.12, 0.38), cushion, 0.035)
    back.rotation_euler.x = math.radians(-10)

    bpy.context.view_layer.update()
    parts = [obj for obj in scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
    depth = max(point.y for point in points) - min(point.y for point in points)
    depth_scale = Matrix.Diagonal((1, 0.82 / depth, 1, 1))
    for obj in parts:
        obj.matrix_world = depth_scale @ obj.matrix_world

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.world = bpy.data.worlds.new("检查背景")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    bpy.ops.object.light_add(type="AREA", location=(1.5, -2, 3))
    bpy.context.object.data.energy = 300
    bpy.context.object.data.size = 3
    bpy.context.object.rotation_euler = (Vector((0, 0, 0.35)) - bpy.context.object.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.05
    scene.camera = camera
    target = Vector((0, 0, 0.39))
    views = {"front": (0, -3, 0.39), "back": (0, 3, 0.39),
             "left": (-3, 0, 0.39), "right": (3, 0, 0.39),
             "top": (0, 0, 3), "three-quarter": (2, -3, 1.8)}
    for name, location in views.items():
        camera.location = location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = 1.4 if name == "three-quarter" else 1.05
        scene.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    scene["status"] = "结构示意；非正式资产，尺寸和接头待验证"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "guide.blend"))
    print("结构引导已保存：", OUT)


if __name__ == "__main__":
    main()
