"""制作独立的洗漱、卫浴与家政日用资产，并用 S003 复核尺度。"""

import argparse
from math import cos, pi, radians, sin, tau
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bathroom_vanity import TOP
from build_s003_bedroom import STAGES
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_dining import rounded_rectangle
from build_s003_kitchen_everyday import sewn_sheet, tube
from build_s003_kitchen_props import rod
from build_s003_living import LIBRARY, RENDERS, mesh_object, place_new, room_material, textile
from build_s003_utility import FLOOR_TOP
import texture_a019_study as maps

BRUSH, SOAP, TOWEL, PAPER, HAMPER = (f"A{i}" for i in range(156, 161))
VIEWS = {
    "bathroom-wash-items": ((5.19, 1.59, 1.26), (4.31, 1.95, 0.89), 39),
    "bathroom-drying-items": ((5.48, 1.43, 1.48), (6.58, 2.39, 1.08), 29),
    "utility-laundry-hamper": ((6.13, 3.53, 1.04), (6.07, 2.82, 0.25), 38),
}


def toothbrush():
    body = room_material("牙刷_雾蓝聚丙烯", (0.14, 0.28, 0.32), 0.37)
    grip = room_material("牙刷_细粒深灰握片", (0.062, 0.105, 0.111), 0.72)
    bristle = room_material("牙刷_半透米白尼龙", (0.72, 0.71, 0.64), 0.36)
    points = [(0, y, z) for y, z in ((-0.082, 0.006), (-0.060, 0.0065), (-0.020, 0.007),
                                    (0.026, 0.006), (0.043, 0.006), (0.058, 0.009))]
    handle = tube("牙刷_带偏置颈的细柄", points, 0.0047, body, sides=20)
    for vertex in handle.data.vertices:
        vertex.co.x *= 1.28 if vertex.co.y < -0.02 else 0.73
    head = rounded_box("牙刷_含牙刷孔的刷头", (0, 0.067, 0.009), (0.0128, 0.026, 0.007), 0.0028, body)
    friction = rounded_box("牙刷_握柄防滑带", (0, -0.044, 0.0102), (0.0063, 0.054, 0.0019), 0.0008, grip)
    vertices, faces = [], []
    for row in range(7):
        for col in range(-1, 2):
            xc, yc = col * 0.0031, 0.057 + row * 0.0033
            for fiber in range(7):
                tx = xc + 0.00058 * cos(tau * fiber / 7)
                ty = yc + 0.00058 * sin(tau * fiber / 7)
                start = len(vertices)
                height = 0.0215 + 0.0007 * cos(row * pi / 3)
                for z, scale in ((0.012, 1), (height, 0.65)):
                    vertices.extend((tx + scale * 0.00016 * cos(tau * i / 5),
                                     ty + scale * 0.00016 * sin(tau * i / 5), z) for i in range(5))
                for i in range(5):
                    a, b = start + i, start + (i + 1) % 5
                    faces.append((a, b, b + 5, a + 5))
                faces.append(tuple(range(start + 5, start + 10)))
    tuft = mesh_object("牙刷_独立尼龙丝束", vertices, faces, [bristle])
    uv = tuft.data.uv_layers.new(name="尼龙丝束UV")
    for loop in tuft.data.loops:
        corner = loop.vertex_index % 5
        uv.data[loop.index].uv = (corner / 4, int(loop.vertex_index % 10 >= 5))
    parts = [handle, head, friction, tuft]
    for part in parts:
        part.location.z -= 0.00130
    return parts


def soap_bar():
    soap = room_material("皂块_柔白冷制皂", (0.74, 0.675, 0.47), 0.57)
    shader = soap.node_tree.nodes["Principled BSDF"]
    shader.inputs["Subsurface Weight"].default_value = 0.15
    clay = room_material("皂座_青灰浅釉", (0.26, 0.36, 0.35), 0.48)
    pebble = rounded_box("手工皂_缓圆边皂体", (0, 0, 0.025), (0.065, 0.045, 0.026), 0.014, soap)
    drain = rounded_box("皂座_有导水筋浅碟", (0, 0, 0.005), (0.093, 0.066, 0.010), 0.0045, clay)
    pieces = [pebble, drain]
    for x in (-0.022, 0, 0.022):
        pieces.append(rounded_box("皂座_下部架空导水筋", (x, 0, 0.0105), (0.005, 0.046, 0.003), 0.0013, clay))
    return pieces


def hand_towel(metal):
    cloth = textile("浴巾_浅麦棉绒", (0.61, 0.54, 0.37))
    rim = textile("浴巾_苔灰织边", (0.29, 0.32, 0.24))
    center_y, radius = -0.091, 0.012
    back, front = 0.205, 0.301
    arc = pi * radius
    width, length = 0.395, back + front + arc

    def around_rail(u, v):
        x = width * (u - 0.5)
        distance = length * v
        if distance < back:
            drop = back - distance
            ripple = sin(tau * (u * 2.89 + drop)) + 0.21 * sin(tau * (5.1 * u - drop))
            return x, center_y + radius + 0.04 * drop * ripple, -drop
        if distance < back + arc:
            angle = (distance - back) / radius
            return x, center_y + radius * cos(angle), radius * sin(angle)
        drop = distance - back - arc
        ripple = sin(tau * (u * 2.89 + drop)) + 0.21 * sin(tau * (5.1 * u - drop))
        return x + 0.007 * drop * sin(tau * u), center_y - radius + 0.048 * drop * ripple, -drop

    towel = sewn_sheet("浴巾_跨杆双面自然落垂", cloth, rim, width, length, around_rail)
    hardware = [rod("浴巾_水平承托杆", (-0.242, center_y, 0), (0.242, center_y, 0), 0.0112, metal)]
    for x in (-0.233, 0.233):
        hardware.append(rod("浴巾_贴墙支座", (x, -0.001, 0), (x, -0.087, 0), 0.013, metal))
    return [towel, *hardware]


def paper_holder(metal):
    paper = textile("卷纸_本白细纹纸面", (0.83, 0.80, 0.73))
    core = room_material("卷纸_浅灰瓦楞芯", (0.41, 0.33, 0.24), 0.85)
    ring_y, roll_length = -0.084, 0.105
    a, b = -roll_length / 2, roll_length / 2
    contour = [(a, 0.021), (a, 0.053), (a + 0.002, 0.054), (b - 0.002, 0.054), (b, 0.053), (b, 0.021)]
    steps = 80
    vertices = [(x, ring_y + radius * cos(tau * i / steps), radius * sin(tau * i / steps))
                for x, radius in contour for i in range(steps)]
    faces = []
    for row in range(len(contour)):
        for col in range(steps):
            a, b = row * steps + col, row * steps + (col + 1) % steps
            faces.append((a, b, (b + steps) % len(vertices), (a + steps) % len(vertices)))
    roll = mesh_object("卷纸_贯通纸芯与可换纸卷", vertices, faces, [paper, core])
    # 纸卷受重力下垂，纸芯内缘接触穿芯横杆的上缘。
    roll.location.z = -(0.021 - 0.008)
    uv = roll.data.uv_layers.new(name="卷纸UV")
    for face in roll.data.polygons:
        row = face.index // steps
        face.material_index = int(row == len(contour) - 1)
        face.use_smooth = row not in (0, 4)
        for index in face.loop_indices:
            vertex = roll.data.loops[index].vertex_index
            ring, col = divmod(vertex, steps)
            uv.data[index].uv = (col / steps, ring / (len(contour) - 1))
    def free_end(u, v):
        spin = 0.41 - min(1, v * 2.0) * 0.79
        drop = max(0, 2 * v - 1) * 0.045
        x = (u - 0.5) * (roll_length - 0.003)
        y = ring_y - 0.0548 * cos(spin) + 0.008 * (drop / 0.045) ** 2
        z = roll.location.z + 0.0548 * sin(spin) - drop
        return x, y, z

    tail = sewn_sheet("卷纸_外层自然垂尾", paper, paper, roll_length, 0.087, free_end)
    tail.modifiers[0].thickness = 0.00025
    return [roll, tail, rounded_box("纸卷架_贴墙安装板", (-0.077, -0.007, 0), (0.045, 0.014, 0.058), 0.007, metal),
            rod("纸卷架_悬臂", (-0.077, -0.012, 0), (-0.077, ring_y, 0), 0.007, metal),
            rod("纸卷架_过芯横杆", (-0.078, ring_y, 0), (0.072, ring_y, 0), 0.008, metal)]


def hamper():
    canvas = textile("衣物篓_暖灰结构帆布", (0.42, 0.36, 0.27))
    seam = textile("衣物篓_深麻翻折包边", (0.23, 0.184, 0.124))
    source = bpy.data.images.load(str(LIBRARY / "materials/terlenka/terlenka_diff_2k.jpg"), check_existing=True)
    width, height = source.size
    pixels = np.empty(len(source.pixels), dtype=np.float32)
    source.pixels.foreach_get(pixels)
    inset_x, inset_y = (width - maps.RESOLUTION) // 2, (height - maps.RESOLUTION) // 2
    color_sample = pixels.reshape(height, width, 4)[
        inset_y:inset_y + maps.RESOLUTION, inset_x:inset_x + maps.RESOLUTION, :3
    ]
    shade = color_sample.mean(axis=2)
    shade = np.clip(1 + 1.6 * (shade - shade.mean()), 0.56, 1.18)
    maps.OUTPUT = LIBRARY / HAMPER
    diffuse = maps.save_image("hamper_canvas_BaseColor", shade[:, :, None] * (0.53, 0.45, 0.33), False)
    diffuse.filepath = str(maps.OUTPUT / "textures/hamper_canvas_BaseColor.png")
    diffuse.pack()
    tree = canvas.node_tree
    yarn = tree.nodes.new("ShaderNodeTexImage")
    yarn.image = diffuse
    shader = tree.nodes["Principled BSDF"]
    shader.inputs["Normal"].links[0].from_node.inputs["Strength"].default_value = 0.62
    tree.links.new(yarn.outputs["Color"], shader.inputs["Base Color"])
    corners = 16
    rows = [
        (0.30, 0.284, 0.000, 0.064), (0.329, 0.312, 0.011, 0.066),
        (0.347, 0.319, 0.036, 0.067), (0.370, 0.340, 0.371, 0.075),
        (0.376, 0.349, 0.408, 0.078), (0.370, 0.344, 0.421, 0.075),
        (0.352, 0.327, 0.421, 0.070), (0.347, 0.323, 0.405, 0.068),
        (0.330, 0.306, 0.034, 0.060), (0.309, 0.285, 0.026, 0.058),
    ]
    vertices = [point for shape in rows for point in rounded_rectangle(*shape, corners)]
    size = corners * 4
    faces = [tuple(reversed(range(size)))]
    for row in range(len(rows) - 1):
        for col in range(size):
            a, b = row * size + col, row * size + (col + 1) % size
            faces.append((a, b, b + size, a + size))
    faces.append(tuple(range(len(vertices) - size, len(vertices))))
    basket = mesh_object("衣物篓_连续内胆与独立承托底", vertices, faces, [canvas, seam])
    uv = basket.data.uv_layers.new(name="帆布沿篓口排纹")
    for face in basket.data.polygons:
        row = (face.index - 1) // size
        face.material_index = int(3 <= row <= 6)
        face.use_smooth = len(face.vertices) == 4
        for index in face.loop_indices:
            vertex = basket.data.loops[index].vertex_index
            x, _, z = vertices[vertex]
            uv.data[index].uv = (x * 8, z * 8) if len(face.vertices) != 4 else ((vertex % size) * 0.17, z * 8)
    handles = []
    for side in (-1, 1):
        path = [(0.083 * cos(pi * i / 28), side * (0.167 + 0.041 * sin(pi * i / 28)),
                 0.373 - 0.030 * sin(pi * i / 28)) for i in range(29)]
        grip = tube("衣物篓_独立棉织提把", path, 0.007, seam)
        for vertex in grip.data.vertices:
            vertex.co.z = 0.36 + (vertex.co.z - 0.36) * 0.86
        handles.append(grip)
    return [basket, *handles]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "entry-details/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bathroom-basics/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    vanity = scene.objects["A113"]
    place_new(BRUSH, toothbrush(), vanity.matrix_world @ Vector((0.363, 0.005, TOP)), radians(13))
    place_new(SOAP, soap_bar(), vanity.matrix_world @ Vector((-0.351, 0.103, TOP)), pi / 2)
    _, _, wall, _, _, thickness, _ = next(row for row in WALLS if row[0] == "bath_north")
    north = wall - thickness / 2
    metal = satin_steel(TOWEL)
    place_new(TOWEL, hand_towel(metal), (6.52, north, 1.49))
    # 卷纸架与浴巾挂杆共用表面规格，GLB 分别打包。
    place_new(PAPER, paper_holder(metal), (6.32, north, 0.84))
    place_new(HAMPER, hamper(), (6.074, 2.81, FLOOR_TOP), radians(-6))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["bathroom-wash-items"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if args.build_only:
        return
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in args.views:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
