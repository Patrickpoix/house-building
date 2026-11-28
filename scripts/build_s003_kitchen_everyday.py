"""餐厨墙挂炊具、备料器物以及两种实际使用状态的布巾。"""

import argparse
from math import cos, hypot, pi, radians, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_props import lathe, rod
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material, textile
from build_s003_utility import FLOOR_TOP

RAIL, LADLE, TURNER, STRAINER, KNIFE, TOWEL, RAG, JAR, PRESS = (f"A{i}" for i in range(137, 146))
VIEWS = {
    "kitchen-utensil-rail": ((8.36, 8.63, 1.60), (9.22, 9.73, 1.50), 42),
    "kitchen-counter-linen": ((6.79, 8.82, 1.35), (7.39, 9.22, 0.90), 45),
    "kitchen-everyday": ((6.64, 7.13, 1.62), (8.75, 9.38, 1.34), 25),
    "utility-cleaning-cloth": ((5.09, 3.73, 0.82), (5.86, 3.40, 0.09), 36),
}
RAIL_Y = -0.056
HOOK_Y = -0.088
HOOK_Z = -0.060
HOOK_X = (-0.217, -0.005, 0.216)


def tube(name, points, radius, material, sides=12):
    centers = [Vector(point) for point in points]
    vertices = []
    last_tangent = first = None
    for row, center in enumerate(centers):
        tangent = (centers[min(row + 1, len(centers) - 1)] - centers[max(0, row - 1)]).normalized()
        if last_tangent is None:
            reference = Vector((1, 0, 0)) if abs(tangent.x) < 0.92 else Vector((0, 0, 1))
            first = tangent.cross(reference).normalized()
        else:
            # 延续上一截面的方向，避免弯道突然切换参考轴产生折痕。
            first = last_tangent.rotation_difference(tangent) @ first
        second = tangent.cross(first)
        vertices.extend(center + radius * (cos(tau * i / sides) * first + sin(tau * i / sides) * second)
                        for i in range(sides))
        last_tangent = tangent
    faces = [tuple(reversed(range(sides)))]
    for row in range(len(centers) - 1):
        for i in range(sides):
            a = row * sides + i
            b = row * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    part = mesh_object(name, vertices, faces, [material])
    uv = part.data.uv_layers.new(name="金属沿程")
    for face in part.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        for index in face.loop_indices:
            row, side = divmod(part.data.loops[index].vertex_index, sides)
            if side == 0 and any(v % sides == sides - 1 for v in face.vertices):
                side = sides
            uv.data[index].uv = (side / sides, row / (len(centers) - 1))
    return part


def utensil_rail(metal):
    brackets = []
    for x in (-0.275, 0.275):
        brackets.extend((
            rounded_box("厨具挂杆_贴墙安装座", (x, -0.007, 0), (0.040, 0.014, 0.062), 0.005, metal),
            rod("厨具挂杆_支臂", (x, -0.011, 0), (x, RAIL_Y, 0), 0.008, metal),
        ))
        for z in (-0.019, 0.019):
            brackets.append(rod("厨具挂杆_安装螺钉", (x, -0.016, z), (x, -0.012, z), 0.003, metal))
    rail = rod("厨具挂杆_圆杆", (-0.303, RAIL_Y, 0), (0.303, RAIL_Y, 0), 0.009, metal)
    for x in HOOK_X:
        upper = [(x, RAIL_Y + 0.013 * cos(pi * i / 12), 0.013 * sin(pi * i / 12))
                 for i in range(13)]
        lower = [(x, HOOK_Y + 0.018 * cos(pi * i / 18), -0.041 - 0.018 * sin(pi * i / 18))
                 for i in range(19)]
        brackets.append(tube("厨具挂杆_可取下挂钩", upper + lower, 0.0028, metal))
    return [rail, *brackets]


def handle(metal, name, joint):
    eye = tube(f"{name}_挂眼", [(0.011 * cos(tau * i / 32) + 0.013, 0,
                               -0.011 * sin(tau * i / 32)) for i in range(33)], 0.0028, metal)
    shank = tube(f"{name}_长柄", [(0.013, 0, -0.011), (0.013, 0, joint + 0.025),
                                (0.013, 0.009, joint)], 0.0040, metal)
    return [eye, shank]


def ladle(metal):
    profile = [(0.006, 0.001), (0.018, 0.004), (0.030, 0.010), (0.038, 0.019),
               (0.043, 0.030), (0.043, 0.033), (0.041, 0.034), (0.039, 0.032),
               (0.038, 0.023), (0.032, 0.015), (0.022, 0.008), (0.005, 0.004)]
    bowl = lathe("汤勺_冲压深圆勺", metal, profile, 0.001, 0.004)
    bowl.rotation_euler.x = pi / 2
    bowl.location = (0.013, 0.027, -0.249)
    neck = tube("汤勺_勺柄焊脚", [(0.013, 0.009, -0.207), (0.013, 0.008, -0.217),
                                (0.013, 0.0065, -0.223)], 0.0039, metal)
    return [*handle(metal, "汤勺", -0.208), neck, bowl]


def turner(metal):
    wood, _ = white_oak_material("锅铲_长纹白橡握柄", "WoodUV")
    grip = board("锅铲_白橡握柄", (0.013, 0, -0.085), (0.020, 0.015, 0.130), wood, 2, 0.27)
    grip.modifiers[0].width = 0.005
    blade = rounded_box("锅铲_薄铲面", (0.013, 0.010, -0.243), (0.077, 0.004, 0.083), 0.002, metal)
    # 铲面是实体，三条透孔供油液流回锅中。
    for x in (-0.008, 0.013, 0.034):
        cutter = rounded_box("锅铲_槽加工工具", (x, 0.01, -0.246), (0.007, 0.016, 0.042), 0.003, metal)
        bpy.context.view_layer.objects.active = cutter
        for modifier in list(cutter.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        cut = blade.modifiers.new("铲面贯通槽", "BOOLEAN")
        cut.object = cutter
        bpy.context.view_layer.objects.active = blade
        bpy.ops.object.modifier_apply(modifier=cut.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    return [*handle(metal, "锅铲", -0.211), grip, blade]


def strainer(metal):
    radius = 0.052
    ring = tube("漏勺_压合边圈", [(0.013 + radius * cos(tau * i / 96), 0.010,
                                  -0.236 + radius * sin(tau * i / 96)) for i in range(97)], 0.003, metal)
    wires = []
    for step in range(-9, 10):
        offset = step * 0.0054
        half = (radius ** 2 - offset ** 2) ** 0.5
        for axis in range(2):
            points = []
            for i in range(13):
                distance = half * (2 * i / 12 - 1)
                depth = 0.011 * (1 - (distance ** 2 + offset ** 2) / radius ** 2)
                x, z = (distance, offset) if axis == 0 else (offset, distance)
                points.append((0.013 + x, 0.010 + depth + axis * 0.0007, -0.236 + z))
            wires.append(tube("漏勺_经纬金属丝", points, 0.00042, metal, 6))
    return [*handle(metal, "漏勺", -0.185), ring, *wires]


def kitchen_knife(metal):
    wood, _ = white_oak_material("厨刀_两片白橡柄", "WoodUV")
    outline = [(-0.035, -0.016), (0.058, -0.022), (0.122, -0.009), (0.166, 0.014),
               (0.121, 0.021), (-0.037, 0.020)]
    vertices = [(x, y, z) for z in (0.0045, 0.0074) for x, y in outline]
    count = len(outline)
    blade = mesh_object("厨刀_连续钢片与刀根", vertices,
                        [tuple(reversed(range(count))), tuple(range(count, 2 * count)),
                         *((i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count))],
                        [metal])
    uv = blade.data.uv_layers.new(name="钢片UV")
    for loop in blade.data.loops:
        x, y, _ = vertices[loop.vertex_index]
        uv.data[loop.index].uv = ((x + 0.037) / 0.203, (y + 0.022) / 0.043)
    bevel = blade.modifiers.new("薄刃和背边", "BEVEL")
    bevel.width = 0.0012
    bevel.segments = 4
    blade.modifiers.new("刀面法线", "WEIGHTED_NORMAL")
    parts = [blade]
    for z in (0.0023, 0.0097):
        slab = board("厨刀_橡木柄片", (-0.083, 0.003, z), (0.109, 0.024, 0.0046), wood, 0, 0.17)
        slab.modifiers[0].width = 0.0016
        parts.append(slab)
    for x in (-0.119, -0.083, -0.047):
        parts.append(cylinder("厨刀_三颗贯通铆钉", (x, 0.003, 0.006), 0.0028, 0.012, metal))
    return parts


def sewn_sheet(name, cloth, binding, width, length, point):
    columns, rows = 48, 64
    vertices, faces = [], []
    for row in range(rows + 1):
        v = row / rows
        vertices.extend(point(column / columns, v) for column in range(columns + 1))
    stride = columns + 1
    for row in range(rows):
        for column in range(columns):
            a = row * stride + column
            faces.append((a, a + 1, a + 1 + stride, a + stride))
    obj = mesh_object(name, vertices, faces, [cloth, binding])
    uv = obj.data.uv_layers.new(name="原裁片经纬")
    for face in obj.data.polygons:
        row, col = divmod(face.index, columns)
        face.use_smooth = True
        face.material_index = int(col in (0, columns - 1) or row in (0, rows - 1))
        for index in face.loop_indices:
            v, u = divmod(obj.data.loops[index].vertex_index, stride)
            uv.data[index].uv = (u / columns * width / 0.085, v / rows * length / 0.085)
    solid = obj.modifiers.new("包边布的厚度", "SOLIDIFY")
    solid.thickness = 0.0015
    solid.offset = 0
    return obj


def countertop_towel():
    width, upper, hang = 0.235, 0.181, 0.152
    cloth = textile("搭布_斜纹麦灰亚麻", (0.53, 0.41, 0.25))
    binding = textile("搭布_深色窄包边", (0.27, 0.18, 0.10))

    def point(u, v):
        distance = v * (upper + hang)
        wave = sin(tau * (2.47 * u + 0.13 * v)) + 0.36 * sin(tau * (4.8 * u - 0.57 * v))
        x = width * (u - 0.5) + 0.007 * sin(pi * v) * sin(tau * u)
        radius = 0.011
        if distance < upper - radius:
            return x, upper - radius - distance + 0.005 * sin(pi * u) * (1 - v), radius + 0.0017
        arc = distance - upper + radius
        angle = min(arc / radius, pi / 2)
        drop = max(0, arc - radius * pi / 2)
        return x, -(radius + 0.010 * v**3 * wave) * sin(angle), 0.0017 + radius * cos(angle) - drop

    return sewn_sheet("亚麻搭布_越过圆边的垂片", cloth, binding, width, upper + hang, point)


def floor_rag():
    cloth = textile("家政抹布_褪色青灰旧棉", (0.24, 0.31, 0.30))
    binding = textile("家政抹布_双折边深线", (0.13, 0.20, 0.20))
    width, length = 0.294, 0.246

    def point(u, v):
        x = width * (u - 0.5) + 0.027 * sin(pi * v) * (0.45 - u)
        y = length * (v - 0.5) + 0.042 * sin(tau * u) * (0.1 + 0.9 * v)
        ridge = max(0, cos(tau * (u * 1.78 + 0.52 * v + 0.16 * sin(pi * v)))) ** 3
        z = 0.0008 + 0.028 * ridge * sin(pi * u) ** 1.4 * sin(pi * v) ** 0.7
        return x, y, z

    return sewn_sheet("家政抹布_落地折皱与窄边", cloth, binding, width, length, point)


def spice_jar(metal):
    glaze = room_material("调味罐_温灰釉", (0.53, 0.50, 0.38), 0.34)
    wood, _ = white_oak_material("调味罐_白橡防潮盖", "WoodUV")
    profile = [(0.036, 0), (0.044, 0), (0.047, 0.005), (0.048, 0.010),
               (0.050, 0.070), (0.049, 0.081), (0.044, 0.086), (0.044, 0.091),
               (0.041, 0.092), (0.039, 0.087), (0.042, 0.026), (0.040, 0.015), (0.030, 0.008)]
    lid = lathe("调味罐_车旋压盖", wood, [(0.039, 0.083), (0.044, 0.087), (0.049, 0.090),
                (0.049, 0.096), (0.047, 0.101), (0.040, 0.102), (0.010, 0.102)], 0.083, 0.102)
    lid.data.uv_layers.active.name = "WoodUV"
    knob = cylinder("调味罐_盖钮", (0, 0, 0.107), 0.010, 0.010, metal)
    return [lathe("调味罐_有短颈的陶胎", glaze, profile, 0, 0.008), lid, knob]


def grinder(metal):
    wood, _ = white_oak_material("磨胡椒器_白橡车纹", "WoodUV")
    profile = [(0.022, 0), (0.027, 0.002), (0.029, 0.007), (0.028, 0.046),
               (0.024, 0.064), (0.020, 0.088), (0.020, 0.100), (0.026, 0.122),
               (0.026, 0.128), (0.024, 0.129), (0.012, 0.129)]
    body = lathe("磨胡椒器_车削腰形木身", wood, profile, 0, 0.129)
    head = lathe("磨胡椒器_旋转木帽", wood, [(0.019, 0.130), (0.026, 0.131),
                 (0.028, 0.140), (0.027, 0.151), (0.022, 0.158), (0.009, 0.160)], 0.130, 0.160)
    for part in (body, head):
        part.data.uv_layers.active.name = "WoodUV"
    return [body, head, cylinder("磨胡椒器_调节帽", (0, 0, 0.163), 0.009, 0.007, metal),
            cylinder("磨胡椒器_底部磨芯", (0, 0, 0.002), 0.016, 0.004, metal, vertices=24)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "dining-lighting/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "kitchen-everyday/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    metal = satin_steel(RAIL)
    rail_at = Vector((9.191, 9.800, 1.693))
    place_new(RAIL, utensil_rail(metal), rail_at)
    for asset, parts, x, tilt in ((LADLE, ladle, HOOK_X[0], 11), (TURNER, turner, HOOK_X[1], -8),
                                  (STRAINER, strainer, HOOK_X[2], 6)):
        place_new(asset, parts(metal), rail_at + Vector((x, HOOK_Y, HOOK_Z)), radians(tilt))
    cutting = scene.objects["A126"]
    place_new(KNIFE, kitchen_knife(metal), cutting.matrix_world @ Vector((-0.008, -0.022, 0.026)),
              cutting.rotation_euler.z + radians(5))
    counter = scene.objects["餐厨_北侧一体开孔台面"]
    front = min((counter.matrix_world @ Vector(point)).y for point in counter.bound_box)
    top = max((counter.matrix_world @ Vector(point)).z for point in counter.bound_box)
    place_new(TOWEL, [countertop_towel()], (7.280, front, top - 0.0119))
    place_new(RAG, [floor_rag()], (5.89, 3.41, FLOOR_TOP), radians(-28))
    place_new(JAR, spice_jar(metal), (9.66, 8.55, top))
    place_new(PRESS, grinder(metal), (9.67, 8.69, top))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-everyday"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in args.views:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
