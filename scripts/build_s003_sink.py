"""以连续金属盆、独立龙头及完整开孔重建北侧洗涤台。"""

import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_dining import rounded_rectangle
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material


BASIN, TAP = "A123", "A124"
DRAIN_Y = 0.076
OPENING_WIDTH, OPENING_DEPTH, OPENING_RADIUS = 0.622, 0.376, 0.046
BASIN_OUTLET_BOTTOM = -0.243
VIEWS = {
    "kitchen-washing": ((7.19, 7.40, 1.56), (8.31, 9.48, 1.17), 31),
    "kitchen-sink-detail": ((7.31, 8.74, 1.62), (8.00, 9.48, 0.91), 38),
}


def rolled_basin(steel):
    # 卷边延伸到台面，盆壁和盆底向后置排水孔收坡。
    rings = (
        (0.662, 0.412, 0.001, 0.070, 0),
        (0.664, 0.414, 0.003, 0.071, 0),
        (0.661, 0.411, 0.006, 0.070, 0),
        (0.604, 0.358, 0.006, 0.053, 0),
        (0.594, 0.348, 0.001, 0.049, 0),
        (0.589, 0.344, -0.012, 0.047, 0),
        (0.540, 0.302, -0.158, 0.054, 0.005),
        (0.508, 0.270, -0.176, 0.058, 0.007),
        (0.470, 0.232, -0.182, 0.056, 0.012),
        (0.177, 0.107, -0.188, 0.052, 0.050),
        (0.067, 0.067, -0.193, 0.0334, DRAIN_Y),
        (0.062, 0.062, -0.205, 0.0309, DRAIN_Y),
    )
    steps = 18
    size = 4 * steps
    vertices = [(x, y + shift, z) for width, depth, z, radius, shift in rings
                for x, y, z in rounded_rectangle(width, depth, z, radius, steps)]
    faces = []
    for row in range(len(rings) - 1):
        for column in range(size):
            a, b = row * size + column, row * size + (column + 1) % size
            faces.append((a, b, b + size, a + size))
    body = mesh_object("水槽_一体拉伸不锈钢盆", vertices, faces, [steel])
    uv = body.data.uv_layers.new(name="BasinUV")
    for face in body.data.polygons:
        face.use_smooth = True
        for index in face.loop_indices:
            x, y, z = vertices[body.data.loops[index].vertex_index]
            uv.data[index].uv = (0.5 + x / 0.66, 0.5 + (y + z * 0.26) / 0.42)
    wall = body.modifiers.new("冲压钢板厚度", "SOLIDIFY")
    wall.thickness = 0.0014
    return body


def sink():
    steel = satin_steel(BASIN)
    gasket = room_material("水槽_排水密封橡胶", (0.028, 0.029, 0.027), 0.68)
    parts = [rolled_basin(steel)]
    rings = (
        (0.038, 0.038, -0.194), (0.036, 0.036, -0.190),
        (0.028, 0.028, -0.191), (0.024, 0.024, -0.207),
    )
    sides = 64
    points = [(w * cos(i * tau / sides), DRAIN_Y + d * sin(i * tau / sides), z)
              for w, d, z in rings for i in range(sides)]
    faces = []
    for row in range(len(rings) - 1):
        for i in range(sides):
            a, b = row * sides + i, row * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    collar = mesh_object("水槽_落水环", points, faces, [steel])
    uv = collar.data.uv_layers.new(name="DrainUV")
    for face in collar.data.polygons:
        face.use_smooth = True
        for index in face.loop_indices:
            x, y, _ = points[collar.data.loops[index].vertex_index]
            uv.data[index].uv = (0.5 + x / 0.076, 0.5 + (y - DRAIN_Y) / 0.076)
    parts.append(collar)
    parts.append(cylinder("水槽_下水接头密封", (0, DRAIN_Y, BASIN_OUTLET_BOTTOM + 0.018),
                          0.033, 0.036, gasket))
    parts.append(cylinder("水槽_提篮底边", (0, DRAIN_Y, -0.219), 0.025, 0.006, steel))
    for step in range(7):
        x = (step - 3) * 0.006
        chord = 2 * (0.023 ** 2 - x ** 2) ** 0.5
        parts.append(board("水槽_提篮过水钢条", (x, DRAIN_Y, -0.204),
                           (0.0018, chord, 0.0022), steel, 0, 0))
    return parts


def faucet():
    metal = satin_steel(TAP)
    dark = room_material("龙头_起泡器网芯", (0.060, 0.065, 0.064), 0.47, 0.48)
    radius, shoulder = 0.096, 0.237
    path = [(0, 0.065), (0, shoulder)]
    path += [(-radius + radius * cos(pi * i / 52), shoulder + radius * sin(pi * i / 52))
             for i in range(1, 53)]
    path.append((-2 * radius, 0.214))
    steps = 32
    centers = [Vector((0, y, z)) for y, z in path]
    vertices = []
    lengths = [0.0]
    for row, center in enumerate(centers):
        if row:
            lengths.append(lengths[-1] + (center - centers[row - 1]).length)
        tangent = centers[min(row + 1, len(centers) - 1)] - centers[max(row - 1, 0)]
        axis = tangent.normalized().cross(Vector((1, 0, 0)))
        for i in range(steps):
            a = tau * i / steps
            vertices.append(center + 0.0125 * (axis * cos(a) + Vector((sin(a), 0, 0))))
    faces = [tuple(range(steps))]
    for row in range(len(path) - 1):
        for i in range(steps):
            a, b = row * steps + i, row * steps + (i + 1) % steps
            faces.append((b, a, a + steps, b + steps))
    faces.append(tuple(reversed(range(len(vertices) - steps, len(vertices)))))
    spout = mesh_object("龙头_连续高弯出水管", vertices, faces, [metal])
    uv = spout.data.uv_layers.new(name="SpoutUV")
    for face in spout.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        for index in face.loop_indices:
            row, side = divmod(spout.data.loops[index].vertex_index, steps)
            if face.use_smooth:
                column = 1.0 if side == 0 and max(v % steps for v in face.vertices) == steps - 1 else side / steps
                uv.data[index].uv = (column, lengths[row] / lengths[-1])
            else:
                angle = tau * side / steps
                uv.data[index].uv = (0.5 + 0.5 * cos(angle), 0.5 + 0.5 * sin(angle))
    valve = cylinder("龙头_侧面阀座", (0.027, 0, 0.055), 0.019, 0.024, metal)
    valve.rotation_euler.y = pi / 2
    return [
        spout,
        cylinder("龙头_台面密封套", (0, 0, 0.003), 0.031, 0.006, dark),
        cylinder("龙头_底座", (0, 0, 0.009), 0.029, 0.012, metal),
        cylinder("龙头_混水阀主体", (0, 0, 0.053), 0.023, 0.084, metal),
        valve,
        cylinder("龙头_拨杆", (0.038, 0, 0.076), 0.006, 0.054, metal),
        cylinder("龙头_可拆起泡套", (0, -2 * radius, 0.214), 0.0133, 0.015, metal),
        cylinder("龙头_起泡器网面", (0, -2 * radius, 0.207), 0.010, 0.001, dark),
    ]


def replace_counter(scene):
    sections = [obj for obj in scene.objects if obj.name.startswith("北侧操作台_")]
    vertices = [obj.matrix_world @ Vector(point) for obj in sections for point in obj.bound_box]
    lo = Vector(min(point[i] for point in vertices) for i in range(3))
    hi = Vector(max(point[i] for point in vertices) for i in range(3))
    old_base = scene.objects["龙头底座"]
    origin = Vector((old_base.location.x, scene.objects["水槽内底"].location.y, hi.z))
    clear_height = origin.z + BASIN_OUTLET_BOTTOM - 0.025
    for divider in scene.objects:
        if divider.name.startswith("北柜_隔板") and abs(divider.location.x - origin.x) < OPENING_WIDTH / 2:
            base = divider.location.z - divider.dimensions.z / 2
            divider.dimensions.z = clear_height - base
            divider.location.z = (clear_height + base) / 2
    material = sections[0].active_material
    worktop = board("餐厨_北侧一体开孔台面", (lo + hi) / 2, hi - lo, material, 0, 0)
    steps = 16
    side = 4 * steps
    cut_points = [(x + origin.x, y + origin.y, z)
                  for z in (lo.z - 0.03, hi.z + 0.03)
                  for x, y, z in rounded_rectangle(OPENING_WIDTH, OPENING_DEPTH, z, OPENING_RADIUS, steps)]
    cut_faces = [tuple(reversed(range(side))), tuple(range(side, 2 * side))]
    for i in range(side):
        next_i = (i + 1) % side
        cut_faces.append((i, next_i, next_i + side, i + side))
    cutter = mesh_object("北台开孔加工体", cut_points, cut_faces, [])
    boolean = worktop.modifiers.new("水槽圆角安装孔", "BOOLEAN")
    boolean.object = cutter
    bpy.context.view_layer.objects.active = worktop
    bpy.ops.object.modifier_apply(modifier=boolean.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    for obj in list(scene.objects):
        if obj in sections or obj.name.startswith(("水槽压边_", "水槽内底", "水槽滤盖", "盆壁_", "龙头底座", "龙头弯管")):
            bpy.data.objects.remove(obj, do_unlink=True)
    return origin, Vector((origin.x, origin.y + OPENING_DEPTH / 2 + 0.063, origin.z))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "cooking-station/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "washing-station/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    basin_at, tap_at = replace_counter(scene)
    place_new(BASIN, sink(), basin_at)
    place_new(TAP, faucet(), tap_at)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-washing"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in VIEWS:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
