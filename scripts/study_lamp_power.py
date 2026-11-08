"""为台灯试放稿补充可复核的电线与墙面插座，保留原稿。"""
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "stages/S003/table-lamp-study/house-table-lamp-study.blend"
OUT = ROOT / "stages/S003/lamp-power-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0

def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat

cord_mat = material("台灯电线_暖灰", (0.22, 0.20, 0.17), 0.58)
socket_mat = material("插座面板_暖白", (0.78, 0.76, 0.70), 0.35)
curve = bpy.data.curves.new("台灯电线曲线", "CURVE")
curve.dimensions = "3D"
curve.resolution_u = 16
curve.bevel_depth = 0.0035
curve.bevel_resolution = 4
spline = curve.splines.new("BEZIER")
positions = [(1.48, 8.00, 0.555), (1.44, 8.10, 0.547),
             (1.40, 8.18, 0.545), (1.39, 8.205, 0.51),
             (1.39, 8.21, 0.08), (1.35, 8.21, 0.009),
             (0.85, 8.21, 0.009), (0.45, 8.20, 0.009),
             (0.235, 8.18, 0.08), (0.222, 8.18, 0.27)]
spline.bezier_points.add(len(positions) - 1)
for point, position in zip(spline.bezier_points, positions):
    point.co = position
    point.handle_left_type = point.handle_right_type = "VECTOR"
cord = bpy.data.objects.new("STUDY_lamp_cord", curve)
bpy.context.collection.objects.link(cord)
cord.data.materials.append(cord_mat)

def block(name, center, size, mat, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("圆角", "BEVEL")
    mod.width = bevel
    mod.segments = 3
    return obj

block("STUDY_socket_plate", (0.205, 8.18, 0.27), (0.012, 0.086, 0.086), socket_mat, 0.004)
block("STUDY_lamp_plug", (0.222, 8.18, 0.27), (0.025, 0.030, 0.035), cord_mat, 0.005)

scene = bpy.context.scene
camera = scene.camera
scene.render.resolution_x, scene.render.resolution_y = 1200, 800
scene.cycles.samples = 48
scene.cycles.use_denoising = True
for name, position, target, lens in (
    ("living", (5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
    ("cord-detail", (2.15, 8.55, 1.85), (0.85, 8.12, 0.35), 38),
):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-lamp-power-study.blend"))
print("电线与插座试验已保存；空间通行与最终电气设计待验收。")
