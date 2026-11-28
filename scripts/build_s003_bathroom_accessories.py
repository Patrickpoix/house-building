"""制作吸水浴垫、落地马桶刷与带支架的淋浴刮水器。"""

import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_breakfast import glaze
from build_s003_cooktop import scene_camera
from build_s003_dining import rounded_rectangle
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe, rod
from build_s003_living import LIBRARY, RENDERS, cylinder, mesh_object, place_new, room_material, textile
from build_s003_utility import FLOOR_TOP
import texture_a019_study as maps

MAT, TOILET_BRUSH, SQUEEGEE = "A193", "A194", "A195"
VIEWS = {
    "bathroom-cotton-mat": ((5.73, 0.86, 1.34), (5.22, 1.13, 0.16), 29),
    "bathroom-toilet-brush": ((6.36, 1.70, 0.78), (5.88, 2.18, 0.29), 38),
    "bathroom-squeegee": ((4.92, 1.19, 1.55), (4.09, 0.94, 1.35), 43),
}


def cotton_pile():
    fabric = room_material("浴垫_浅烟青棉毛圈", (0.21, 0.31, 0.266), 0.85)
    fabric.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.18
    maps.OUTPUT = LIBRARY / MAT
    size = maps.RESOLUTION
    grid = (np.arange(size, dtype=np.float32) + 0.5) / size
    row = grid[:, None] * 126
    col = grid[None, :] * 132 + 0.5 * (np.floor(row) % 2)
    y = ((row % 1) - 0.5) / 0.45
    x = ((col % 1) - 0.5 + 0.17 * y ** 2) / 0.49
    rng = np.random.default_rng(193)
    grain = rng.standard_normal((size, size), dtype=np.float32)
    stitch = np.exp(-((np.sqrt(x ** 2 + y ** 2) - 0.63) / 0.29) ** 2)
    fiber = 0.046 * grain + 0.060 * np.sin(18 * x + 8 * y)
    du = np.maximum(np.abs((grid[None, :] - 0.5) * 0.61) - 0.258, 0)
    dv = np.maximum(np.abs((grid[:, None] - 0.5) * 0.428) - 0.168, 0)
    inset = 0.030 - np.hypot(du, dv)
    border = np.exp(-((inset - 0.011) / 0.0015) ** 2) + np.exp(-((inset - 0.018) / 0.0015) ** 2)
    height = stitch * (1 - 0.55 * border) + fiber
    tint = 0.72 + 0.34 * stitch + 0.17 * fiber - 0.12 * border
    dy, dx = np.gradient(height)
    normal = np.clip(np.stack((0.5 - 0.76 * dx, 0.5 - 0.76 * dy, np.ones_like(height)), axis=-1), 0, 1)
    textures = {name: maps.save_image("bath_mat_" + name, data, name != "BaseColor") for name, data in (
        ("BaseColor", tint[..., None] * np.array((0.214, 0.312, 0.267), dtype=np.float32)),
        ("Roughness", np.clip(0.83 + 0.06 * height, 0, 1)), ("Normal", normal), ("Metallic", np.zeros_like(height)),
    )}
    maps.connect_maps(fabric, textures)
    for image in textures.values():
        image.filepath = str(maps.OUTPUT / "textures" / bpy.path.basename(image.filepath))
        image.pack()
    return fabric


def cotton_mat():
    fabric = cotton_pile()
    binding = textile("浴垫_烟青包边短织带", (0.225, 0.306, 0.268))
    sole = room_material("浴垫_带微点的弹性防滑底", (0.088, 0.126, 0.103), 0.84)
    stack = ((0.004, 0.586, 0.407, 0.026), (0.0078, 0.610, 0.428, 0.032),
             (0.0109, 0.602, 0.422, 0.029), (0.0114, 0.574, 0.394, 0.021))
    runs = 16
    profile = [list(rounded_rectangle(w, d, z, radius, runs)) for z, w, d, radius in stack]
    count = len(profile[0])
    vertices = [point for row in profile for point in row]
    faces = [tuple(reversed(range(count)))]
    for layer in range(len(profile) - 1):
        for i in range(count):
            a, b = layer * count + i, layer * count + (i + 1) % count
            faces.append((a, b, b + count, a + count))
    faces.append(tuple(range((len(profile) - 1) * count, len(vertices))))
    body = mesh_object("浴垫_棉面圆角曲边与连续包边", vertices, faces, [fabric, binding])
    uv = body.data.uv_layers.new(name="棉织实尺UV")
    for face in body.data.polygons:
        face.material_index = int(face.index <= 2 * count)
        for index in face.loop_indices:
            x, y, z = vertices[body.data.loops[index].vertex_index]
            if face.material_index:
                uv.data[index].uv = (x * 9 + 0.2, y * 9 + z * 12)
            else:
                uv.data[index].uv = (x / 0.61 + 0.5, y / 0.428 + 0.5)
    backing = rounded_box("浴垫_朝下弹性底层", (0, 0, 0.0027), (0.584, 0.407, 0.0054), 0.002, sole)
    return [backing, body]


def brush():
    ceramic = glaze(TOILET_BRUSH, "马桶刷座_含砂乳白陶釉", (0.64, 0.59, 0.48), 0.36)
    steel = room_material("马桶刷_拉丝不锈钢", (0.57, 0.552, 0.52), 0.33, 0.82)
    rubber = room_material("马桶刷_暖灰软握套", (0.241, 0.236, 0.21), 0.71)
    bristle = room_material("马桶刷_深灰尼龙丝簇", (0.112, 0.111, 0.09), 0.71)
    cup = lathe("马桶刷座_带积液内腔的陶杯", ceramic, [(0.038, 0.001), (0.044, 0), (0.054, 0.003),
                (0.057, 0.011), (0.057, 0.142), (0.056, 0.157), (0.053, 0.160), (0.049, 0.159),
                (0.048, 0.151), (0.050, 0.141), (0.050, 0.017), (0.046, 0.012), (0.037, 0.011)], 0.001, 0.011)
    head = lathe("马桶刷_刷丝根部内芯", rubber, [(0.014, 0.044), (0.021, 0.061), (0.022, 0.091),
                 (0.020, 0.113), (0.012, 0.120), (0.006, 0.120)], 0.044, 0.120)
    stem = rod("马桶刷_可拆装细钢柄", (0, 0, 0.068), (0, 0, 0.390), 0.0058, steel)
    lid = cylinder("马桶刷_遮挡刷头的薄盖盘", (0, 0, 0.162), 0.052, 0.004, steel, vertices=72)
    hold = lathe("马桶刷_上段软握套", rubber, [(0.006, 0.318), (0.009, 0.321), (0.011, 0.337),
                 (0.0105, 0.396), (0.008, 0.411), (0.004, 0.414)], 0.318, 0.414)
    vertices, faces = [], []
    rng = np.random.default_rng(194)
    for z in np.linspace(0.049, 0.111, 8):
        for i in range(32):
            angle = tau * (i + rng.uniform(-0.19, 0.19)) / 32
            reach = min(0.046, 0.024 + 0.022 * sin(pi * (z - 0.033) / 0.097) + rng.uniform(-0.0012, 0.0006))
            n = len(vertices)
            for radius, shift in ((0.014, 0), (reach, rng.uniform(-0.004, 0.004))):
                vertices.extend((radius * cos(angle + 0.018 * cos(tau * j / 5)),
                                 radius * sin(angle + 0.018 * cos(tau * j / 5)),
                                 z + shift + 0.0006 * sin(tau * j / 5)) for j in range(5))
            for j in range(5):
                k = (j + 1) % 5
                faces.append((n + j, n + k, n + k + 5, n + j + 5))
            faces.append(tuple(range(n + 5, n + 10)))
    filaments = mesh_object("马桶刷_成束尼龙刷丝", vertices, faces, [bristle])
    uv = filaments.data.uv_layers.new(name="刷丝UV")
    for loop in filaments.data.loops:
        index = loop.vertex_index % 10
        uv.data[loop.index].uv = (index % 5 / 4, int(index >= 5))
    return [cup, head, filaments, stem, lid, hold]


def squeegee():
    body = room_material("刮水器_炭绿纤维增强柄", (0.116, 0.186, 0.158), 0.53)
    rubber = room_material("刮水器_柔性灰硅胶刮边", (0.142, 0.176, 0.158), 0.84)
    steel = room_material("刮水器_不锈薄背夹", (0.41, 0.408, 0.38), 0.32, 0.78)
    hook = room_material("刮水器_吸盘墙托", (0.62, 0.633, 0.582), 0.61)
    crossbar = rounded_box("刮水器_一字弹性刮条夹", (0, -0.036, 0), (0.268, 0.018, 0.025), 0.005, steel)
    blade = rounded_box("刮水器_可换薄硅胶刃", (0, -0.038, 0.014), (0.260, 0.006, 0.020), 0.0024, rubber)
    head = rounded_box("刮水器_T形夹头", (0, -0.037, -0.015), (0.048, 0.030, 0.023), 0.007, body)
    grip = lathe("刮水器_水滴截面手柄", body, [(0.008, -0.149), (0.012, -0.142), (0.016, -0.119),
                 (0.016, -0.075), (0.014, -0.043), (0.012, -0.020), (0.010, -0.016)], -0.149, -0.016)
    grip.location.y = -0.035
    for vertex in grip.data.vertices:
        vertex.co.y *= 0.82
    pad = cylinder("刮水器_墙贴紧吸附盘", (0, -0.0035, -0.083), 0.028, 0.007, hook, vertices=48)
    pad.rotation_euler.x = pi / 2
    support = rounded_box("刮水器_吸盘和篮托连接背脊", (0, -0.007, -0.105), (0.029, 0.012, 0.058), 0.004, hook)
    bracket = rounded_box("刮水器_墙座承托底舌", (0, -0.026, -0.154), (0.027, 0.043, 0.010), 0.003, hook)
    clip = tube("刮水器_C形弹性限位夹", [(0.018 * cos(angle), -0.035 + 0.018 * sin(angle), -0.135)
                for angle in np.linspace(-0.20 * pi, 1.20 * pi, 29)], 0.0035, hook)
    return [crossbar, blade, head, grip, pad, support, bracket, clip]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "window-plant/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bathroom-accessories/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    place_new(MAT, cotton_mat(), (5.307, 1.13, FLOOR_TOP), pi / 2)
    place_new(TOILET_BRUSH, brush(), (5.961, 2.27, FLOOR_TOP))
    tile = scene.objects["卫浴_西墙薄釉砖"]
    face_x = max((tile.matrix_world @ Vector(point)).x for point in tile.bound_box)
    place_new(SQUEEGEE, squeegee(), (face_x, 0.985, 1.39), pi / 2)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["bathroom-cotton-mat"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if args.build_only:
        return
    for name in VIEWS:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
