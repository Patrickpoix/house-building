"""构建 S001 空间白模；单位为米，输出为阶段工程和空间检查图。"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S001"
HEIGHT = 3.0
OUTER_THICKNESS = 0.20
INNER_THICKNESS = 0.12

# 开口以墙轴方向坐标给出；门洞以地面为零，窗洞包含窗台与顶部标高。
WALLS = [
    ("south", "x", 0.1, 0.0, 10.0, OUTER_THICKNESS,
     [(0.75, 2.50, 0.90, 2.35), (4.75, 5.55, 1.55, 2.35), (8.20, 9.15, 0.0, 2.20)]),
    ("north", "x", 9.9, 0.0, 10.0, OUTER_THICKNESS,
     [(0.85, 3.25, 0.65, 2.45), (5.00, 8.60, 0.85, 2.45)]),
    ("west", "y", 0.1, 0.2, 9.8, OUTER_THICKNESS,
     [(1.05, 2.60, 0.90, 2.35), (5.25, 8.35, 0.65, 2.45)]),
    ("east", "y", 9.9, 0.2, 9.8, OUTER_THICKNESS,
     [(5.25, 7.25, 0.85, 2.45)]),
    ("bedroom_east", "y", 4.0, 0.2, 4.06, INNER_THICKNESS, []),
    ("bath_east", "y", 7.0, 0.2, 4.06, INNER_THICKNESS,
     [(0.55, 1.55, 0.0, 2.15)]),
    ("bedroom_north", "x", 4.0, 0.2, 3.94, INNER_THICKNESS,
     [(1.10, 2.10, 0.0, 2.15)]),
    ("utility_north", "x", 4.0, 4.06, 6.94, INNER_THICKNESS,
     [(5.10, 6.10, 0.0, 2.15)]),
    ("bath_north", "x", 2.5, 4.06, 6.94, INNER_THICKNESS, []),
]


def material(name, color, roughness=0.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


def box(name, center, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def wall(name, axis, fixed, start, end, thickness, openings, mat):
    points = sorted({start, end, *(v for a, b, _, _ in openings for v in (a, b))})
    if any(a < start or b > end or a >= b or z0 < 0 or z1 > HEIGHT or z0 >= z1
           for a, b, z0, z1 in openings):
        raise ValueError(f"非法墙洞：{name}")
    for left, right in zip(points, points[1:]):
        active = [o for o in openings if o[0] <= left and right <= o[1]]
        if len(active) > 1:
            raise ValueError(f"墙洞重叠：{name}")
        intervals = [(0.0, HEIGHT)]
        if active:
            _, _, z0, z1 = active[0]
            intervals = [(0.0, z0), (z1, HEIGHT)]
        for bottom, top in intervals:
            if top - bottom < 0.001:
                continue
            along = (left + right) / 2
            center = (along, fixed, (bottom + top) / 2) if axis == "x" else (fixed, along, (bottom + top) / 2)
            size = (right - left, thickness, top - bottom) if axis == "x" else (thickness, right - left, top - bottom)
            box(f"wall_{name}", center, size, mat)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    wall_mat = material("whitebox_wall", (0.73, 0.76, 0.72))
    floor_mat = material("whitebox_floor", (0.84, 0.83, 0.77))
    roof_mat = material("whitebox_ceiling", (0.79, 0.81, 0.77))
    ground_mat = material("whitebox_ground", (0.46, 0.51, 0.45))
    box("building_slab_10x10m", (5, 5, -0.10), (10, 10, 0.20), floor_mat)
    for data in WALLS:
        wall(*data, wall_mat)
    roof = box("ceiling_hidden_for_inspection", (5, 5, HEIGHT + 0.06), (10, 10, 0.12), roof_mat)
    roof.hide_render = True
    roof.hide_viewport = True
    box("ground", (5, 5, -0.25), (200, 200, 0.10), ground_mat)

    bpy.ops.object.light_add(type="AREA", location=(1, -2, 12))
    light = bpy.context.object
    light.data.energy = 3000
    light.data.shape = "DISK"
    light.data.size = 10
    aim(light, (5, 5, 0))
    scene.world = bpy.data.worlds.new("whitebox_world")
    scene.world.color = (0.45, 0.45, 0.45)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    bpy.ops.object.camera_add(location=(5, 5, 25))
    camera = bpy.context.object
    camera.name = "camera_plan"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 11.3
    camera.data.clip_start = 23.8
    camera.rotation_euler = (0, 0, 0)
    scene.camera = camera
    scene.render.filepath = str(OUTPUT / "plan.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "whitebox.blend"))
    bpy.ops.render.render(write_still=True)

    camera.location = (18, -15, 25)
    camera.data.clip_start = 0.1
    aim(camera, (5, 5, 0))
    camera.data.ortho_scale = 15.0
    scene.render.filepath = str(OUTPUT / "axonometric.png")
    bpy.ops.render.render(write_still=True)
    print(f"S001 写入 {OUTPUT}")


if __name__ == "__main__":
    main()
