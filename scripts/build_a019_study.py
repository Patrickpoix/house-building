"""重建 A019 电饭煲结构研究稿；不是已通过 PBR 验收的最终资产。"""

from math import pi
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S002" / "A019-study"
GUIDE = ROOT / "stages" / "S002" / "experiments" / "A019-generated-shape.glb"


def make_material(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return mat


def rounded_box(name, position, size, radius, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("edge_radius", "BEVEL")
    bevel.width = radius
    bevel.segments = 5
    bevel.affect = "EDGES"
    obj.modifiers.new("weighted_normals", "WEIGHTED_NORMAL")
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def cylinder(name, position, radius, depth, material, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=position, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    bevel = obj.modifiers.new("edge_radius", "BEVEL")
    bevel.width = min(radius * 0.18, depth * 0.22)
    bevel.segments = 3
    obj.modifiers.new("weighted_normals", "WEIGHTED_NORMAL")
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def recess(target, position, size, radius=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    cutter = bpy.context.object
    cutter.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if radius:
        bevel = cutter.modifiers.new("cutter_radius", "BEVEL")
        bevel.width = radius
        bevel.segments = 5
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    cutter.select_set(False)
    cut = target.modifiers.new("recess", "BOOLEAN")
    cut.operation = "DIFFERENCE"
    cut.solver = "EXACT"
    cut.object = cutter
    while target.modifiers.find(cut.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=cut.name)
    bpy.ops.object.modifier_apply(modifier=cut.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def cylindrical_recess(target, position, radius, depth):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=depth, location=position)
    cutter = bpy.context.object
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    cutter.select_set(False)
    cut = target.modifiers.new("pot_interior", "BOOLEAN")
    cut.operation = "DIFFERENCE"
    cut.solver = "EXACT"
    cut.object = cutter
    while target.modifiers.find(cut.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=cut.name)
    bpy.ops.object.modifier_apply(modifier=cut.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def apply_outer_bevel(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="edge_radius")


def unwrap_after_cuts(obj):
    # 倒角与布尔运算后的新面需要重新展开，避免沿用立方体的拉伸 UV。
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.015)
    bpy.ops.object.mode_set(mode="OBJECT")


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    if not GUIDE.is_file():
        raise FileNotFoundError(f"缺少几何参照 {GUIDE}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    bpy.ops.import_scene.gltf(filepath=str(GUIDE))
    guide = next(obj for obj in scene.objects if obj.type == "MESH")
    guide.name = "guide_generated_geometry_not_final"
    guide.dimensions = (0.28, 0.32, 0.25)
    bpy.context.view_layer.update()
    bounds = [guide.matrix_world @ Vector(point) for point in guide.bound_box]
    guide.location.x -= (min(p.x for p in bounds) + max(p.x for p in bounds)) / 2
    guide.location.y -= (min(p.y for p in bounds) + max(p.y for p in bounds)) / 2
    guide.location.z -= min(p.z for p in bounds)
    guide.hide_render = True
    guide.hide_set(True)

    ivory = make_material("study_ivory_enamel", (0.72, 0.69, 0.61), 0.0, 0.30)
    stainless = make_material("study_brushed_steel", (0.56, 0.57, 0.55), 0.95, 0.27)
    dark = make_material("study_graphite_polymer", (0.06, 0.065, 0.065), 0.0, 0.40)
    rubber = make_material("study_rubber", (0.035, 0.038, 0.036), 0.0, 0.65)

    body = rounded_box("A019_body", (0, 0, 0.1065), (0.280, 0.296, 0.185), 0.026, ivory)
    rounded_box("A019_lower_band", (0, 0, 0.023), (0.258, 0.282, 0.019), 0.008, dark)
    collar = rounded_box("A019_lid_collar", (0, 0, 0.202), (0.278, 0.294, 0.019), 0.008, ivory)
    lid = rounded_box("A019_lid", (0, 0, 0.228), (0.276, 0.292, 0.043), 0.019, stainless)
    apply_outer_bevel(body)
    apply_outer_bevel(collar)
    apply_outer_bevel(lid)
    recess(body, (0, 0, 0.125), (0.238, 0.254, 0.180), radius=0.015)
    recess(collar, (0, 0, 0.202), (0.238, 0.254, 0.05), radius=0.015)
    pot = cylinder("A019_inner_pot", (0, 0, 0.112), 0.110, 0.145, dark)
    apply_outer_bevel(pot)
    cylindrical_recess(pot, (0, 0, 0.119), 0.106, 0.140)
    seat = rounded_box("A019_pot_seat", (0, 0, 0.190), (0.236, 0.252, 0.008), 0.004, ivory)
    apply_outer_bevel(seat)
    cylindrical_recess(seat, (0, 0, 0.190), 0.111, 0.020)
    rounded_box("A019_latch_frame", (0, -0.150, 0.194), (0.068, 0.013, 0.056), 0.006, dark)
    rounded_box("A019_latch_button", (0, -0.158, 0.191), (0.052, 0.008, 0.042), 0.004, rubber)
    rounded_box("A019_controls_panel", (0, -0.149, 0.074), (0.104, 0.004, 0.038), 0.0018, ivory)
    for x in (-0.035, 0.035):
        cylinder("A019_round_button", (x, -0.153, 0.073), 0.008, 0.006, ivory, (pi / 2, 0, 0))
    rounded_box("A019_centre_button", (0, -0.154, 0.073), (0.025, 0.006, 0.013), 0.002, dark)
    for x in (-0.035, 0, 0.035):
        cylinder("A019_status_light", (x, -0.152, 0.087), 0.0015, 0.004, dark, (pi / 2, 0, 0))
    for x in (-0.065, 0.065):
        for y in (-0.104, 0.104):
            cylinder("A019_foot", (x, y, 0.010), 0.013, 0.020, rubber)
    for x in (-0.032, 0.032):
        rounded_box("A019_hinge_mount", (x, 0.147, 0.218), (0.026, 0.016, 0.038), 0.004, ivory)
    cylinder("A019_hinge_pin", (0, 0.155, 0.232), 0.005, 0.092, stainless, (0, pi / 2, 0))
    lid_parts = [lid]
    for x in (-0.009, 0.0, 0.009):
        recess(lid, (x, 0.006, 0.250), (0.004, 0.016, 0.008))
        lid_parts.append(rounded_box("A019_steam_vent", (x, 0.006, 0.2465), (0.0035, 0.0155, 0.001), 0.0003, dark))
    for y in (0.025, 0.034, 0.043, 0.052):
        recess(body, (0.140, y, 0.075), (0.012, 0.0035, 0.016))
        rounded_box("A019_side_vent", (0.1345, y, 0.075), (0.001, 0.003, 0.015), 0.0003, dark)
    unwrap_after_cuts(lid)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0.150, 0.215))
    hinge = bpy.context.object
    hinge.name = "A019_lid_hinge_pivot"
    for obj in lid_parts:
        world = obj.matrix_world.copy()
        obj.parent = hinge
        obj.matrix_world = world

    bpy.ops.object.camera_add(location=(0.58, -0.72, 0.49))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.48
    aim(camera, (0, 0, 0.12))
    scene.camera = camera
    for position, energy, size in [((0.3, -0.45, 0.8), 18, 0.65), ((-0.5, 0.15, 0.55), 9, 0.45)]:
        bpy.ops.object.light_add(type="AREA", location=position)
        lamp = bpy.context.object
        lamp.data.energy = energy
        lamp.data.size = size
        aim(lamp, (0, 0, 0.12))
    scene.world = bpy.data.worlds.new("study_world")
    scene.world.color = (0.55, 0.55, 0.55)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT / "preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "study.blend"))
    bpy.ops.render.render(write_still=True)
    hinge.rotation_euler.x = -75 * pi / 180
    camera.data.ortho_scale = 0.76
    aim(camera, (0, 0.02, 0.22))
    scene.render.filepath = str(OUTPUT / "open-preview.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
