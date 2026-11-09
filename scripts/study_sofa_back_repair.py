"""试验去除沙发镜像背面并补壳，原始 GLB 不修改。"""
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tripo/outputs/living-sofa/tripo-original.glb"
OUT = ROOT / "tripo/outputs/living-sofa/back-repair-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
sofa = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
sofa.name = "STUDY_sofa_clipped"
# 前视朝 -Y。剪除 +Y 一侧的重复坐垫；试验稿必须与原稿比较。
bm = bmesh.new()
bm.from_mesh(sofa.data)
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                       dist=0.00001, plane_co=(0, 0.04, 0), plane_no=(0, 1, 0),
                       clear_outer=True, clear_inner=False)
bm.to_mesh(sofa.data)
bm.free()
sofa.data.update()

def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

fabric = material("试验_橄榄织物", (0.24, 0.27, 0.15), 0.83)
wood = material("试验_浅色木脚", (0.52, 0.35, 0.19), 0.48)

def box(name, center, dimensions, mat, radius):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("软边", "BEVEL")
    bevel.width = radius
    bevel.segments = 4
    obj.modifiers.new("平滑法线", "WEIGHTED_NORMAL")
    return obj

# 壳体与后脚只是结构验证，需要真实面料、接缝及连接精修。
box("STUDY_back_shell", (0, 0.10, 0.215), (0.96, 0.13, 0.30), fabric, 0.018)
for x in (-0.462, 0.462):
    box(f"STUDY_arm_extension_{x}", (x, 0.10, 0.205), (0.076, 0.13, 0.27), fabric, 0.012)
    box(f"STUDY_rear_leg_{x}", (x, 0.14, 0.035), (0.024, 0.024, 0.07), wood, 0.004)

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
light.data.energy = 400
light.data.size = 4
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
scene.camera = camera
center = Vector((0, 0, 0.2022))
for name, direction in (("front", (0, -1, 0.08)), ("back", (0, 1, 0.08)),
                        ("left", (-1, 0, 0.08)), ("right", (1, 0, 0.08))):
    direction = Vector(direction).normalized()
    camera.location = center + direction * 3
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 1.25
    light.location = center + direction * 2 + Vector((0, 0, 2))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "sofa-back-repair-study.blend"))
print("背部结构试验已保存，必须核对剪切边和材质。")
