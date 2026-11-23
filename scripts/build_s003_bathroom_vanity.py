"""制作 S003 卫浴的一体陶瓷台盆、浴室柜和盥洗区饰面。"""

import argparse
from math import ceil, cos, pi, sin, tau
from pathlib import Path
from random import Random
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_dining import rounded_rectangle
from build_s003_living import LIBRARY, cylinder, mesh_object, place_new, room_material


ASSET = "A113"
WIDTH, DEPTH = 0.880, 0.522
TOP, BOTTOM = 0.868, 0.222


def basin(white):
    # 台面、卷边、斜盆壁、盆底和下水孔为连续网格。
    profile = (
        (0.874, 0.516, TOP - 0.049, 0.016, 0.000),
        (WIDTH, DEPTH, TOP - 0.039, 0.020, 0.000),
        (WIDTH, DEPTH, TOP - 0.010, 0.020, 0.000),
        (0.864, 0.506, TOP, 0.015, 0.000),
        (0.575, 0.334, TOP, 0.073, -0.035),
        (0.554, 0.313, TOP - 0.010, 0.068, -0.035),
        (0.528, 0.286, TOP - 0.041, 0.064, -0.032),
        (0.470, 0.238, TOP - 0.099, 0.063, -0.018),
        (0.405, 0.188, TOP - 0.120, 0.057, -0.008),
        (0.170, 0.116, TOP - 0.122, 0.050, 0.005),
        (0.058, 0.058, TOP - 0.130, 0.0288, 0.018),
        (0.054, 0.054, TOP - 0.141, 0.0268, 0.018),
    )
    steps, size = 15, 60
    vertices = [(x, y + shift, z) for w, d, height, radius, shift in profile
                for x, y, z in rounded_rectangle(w, d, height, radius, steps)]
    faces = []
    for row in range(len(profile) - 1):
        for index in range(size):
            a, b = size * row + index, size * row + (index + 1) % size
            faces.append((a, b, b + size, a + size))
    top = mesh_object("浴室柜_一体陶瓷台盆", vertices, faces, [white])
    uv = top.data.uv_layers.new(name="CeramicUV")
    for face in top.data.polygons:
        face.use_smooth = True
        normal_axis = max(range(3), key=lambda axis: abs(face.normal[axis]))
        u, v = (axis for axis in range(3) if axis != normal_axis)
        for loop in face.loop_indices:
            point = vertices[top.data.loops[loop].vertex_index]
            uv.data[loop].uv = (point[u] / WIDTH + 0.5, point[v] / DEPTH + 0.5)
    thickness = top.modifiers.new("陶瓷烧制厚度", "SOLIDIFY")
    thickness.thickness = 0.010
    return top


def faucet(metal, dark):
    path = [(0.181, TOP + 0.012), (0.181, 1.015)]
    path.extend((0.126 + 0.055 * cos(angle), 1.015 + 0.055 * sin(angle))
                for angle in [pi * i / 30 for i in range(1, 16)])
    path.append((0.009, 1.070))
    path.extend((0.009 - 0.029 * sin(angle), 1.041 + 0.029 * cos(angle))
                for angle in [pi * i / 22 for i in range(1, 12)])
    steps = 24
    centers = [Vector((0, y, z)) for y, z in path]
    vertices = []
    for i, center in enumerate(centers):
        tangent = centers[min(i + 1, len(centers) - 1)] - centers[max(i - 1, 0)]
        axis = tangent.normalized().cross(Vector((1, 0, 0)))
        for j in range(steps):
            angle = tau * j / steps
            vertices.append(center + 0.0108 * (axis * cos(angle) + Vector((sin(angle), 0, 0))))
    faces = [tuple(range(steps))]
    for i in range(len(centers) - 1):
        for j in range(steps):
            a, b = i * steps + j, i * steps + (j + 1) % steps
            faces.append((b, a, a + steps, b + steps))
    faces.append(tuple(reversed(range(len(vertices) - steps, len(vertices)))))
    spout = mesh_object("浴室柜_连续弧形龙头", vertices, faces, [metal])
    uv = spout.data.uv_layers.new(name="MetalUV")
    for face in spout.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        for loop in face.loop_indices:
            row, side = divmod(spout.data.loops[loop].vertex_index, steps)
            uv.data[loop].uv = (side / steps, row / (len(centers) - 1))
    lever = cylinder("浴室柜_龙头把手根部", (0.027, 0.181, 0.942), 0.015, 0.034, metal)
    lever.rotation_euler.y = pi / 2
    return [spout, lever,
            cylinder("浴室柜_龙头基座", (0, 0.181, TOP + 0.016), 0.031, 0.033, metal),
            cylinder("浴室柜_握柄", (0.045, 0.181, 0.960), 0.006, 0.040, metal),
            cylinder("浴室柜_起泡器", (0, -0.020, 1.039), 0.0084, 0.005, dark)]


def vanity():
    oak, _ = white_oak_material("浴室柜_防潮白橡木皮", "WoodUV")
    white = room_material("浴室柜_暖白烧釉陶瓷", (0.78, 0.78, 0.725), 0.26)
    metal = room_material("浴室柜_缎面不锈钢", (0.38, 0.37, 0.345), 0.27, 0.83)
    dark = room_material("浴室柜_排水孔与暗缝", (0.043, 0.045, 0.041), 0.55)
    parts = [basin(white), *faucet(metal, dark),
             cylinder("浴室柜_排水法兰", (0, 0.018, TOP - 0.136), 0.0278, 0.010, metal),
             cylinder("浴室柜_弹跳下水盖", (0, 0.018, TOP - 0.130), 0.0185, 0.009, metal),
             board("浴室柜_底板", (0, 0.005, BOTTOM + 0.010), (0.847, 0.466, 0.020), oak, 0, 0.32),
             board("浴室柜_背板", (0, 0.243, 0.521), (0.812, 0.024, 0.564), oak, 2, 0.14),
             board("浴室柜_连续背墙挂板", (0, 0.252, 0.740), (0.726, 0.020, 0.104), oak, 0, 0.33),
             board("浴室柜_分缝衬板", (0, -0.207, 0.512), (0.810, 0.026, 0.558), dark, 0, 0)]
    for side in (-1, 1):
        parts.append(board("浴室柜_承重侧板", (side * 0.412, 0.011, 0.520),
                           (0.024, 0.477, 0.594), oak, 2, side * 0.29))
    for z in (0.375, 0.660):
        parts.append(board("浴室柜_横纹抽屉面", (0, -0.235, z), (0.822, 0.024, 0.276), oak, 0, z))
        parts.append(board("浴室柜_抽屉哑光条形拉手", (0, -0.258, z + 0.086),
                           (0.188, 0.024, 0.014), metal, 0, 0))
    return parts


def bathroom_surfaces(bounds):
    x0, y0, x1, y1 = bounds
    rng = Random(113)
    grout = room_material("卫浴_地砖细缝", (0.33, 0.305, 0.270), 0.90)
    board("卫浴_铺砖底层", ((x0 + x1) / 2, (y0 + y1) / 2, 0.003), (x1-x0, y1-y0, 0.005), grout, 0, 0)
    tiles = [room_material(f"卫浴_砂岩哑光砖{i+1}", (g, g * 0.932, g * 0.83), 0.63)
             for i, g in enumerate((0.48, 0.49, 0.50, 0.512, 0.526))]
    step = 0.45
    for column in range(ceil((x1 - x0) / step)):
        a, b = x0 + column * step, min(x1, x0 + (column + 1) * step)
        for row in range(ceil((y1 - y0) / step)):
            c, d = y0 + row * step, min(y1, y0 + (row + 1) * step)
            board("卫浴_砂岩地砖", ((a + b) / 2, (c + d) / 2, 0.0055),
                  (b - a - 0.0025, d - c - 0.0025, 0.009), rng.choice(tiles), 0, 0)

    wall_tiles = [room_material(f"卫浴_墙砖釉色{i+1}", (g * 0.90, g, g * 0.95), 0.42)
                  for i, g in enumerate((0.56, 0.57, 0.582, 0.592))]
    rows, columns = 8, 12
    tile_h, tile_w = 1.560 / rows, (y1 - y0) / columns
    for row in range(rows):
        for column in range(columns):
            board("卫浴_西墙薄釉砖", (x0 + 0.0045, y0 + (column + 0.5) * tile_w, (row + 0.5) * tile_h),
                  (0.009, tile_w - 0.0019, tile_h - 0.0019), rng.choice(wall_tiles), 2, 0)


def area_light(name, loc, target, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = energy, size, color
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = loc
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()


def room_fixtures(west, center):
    frame = room_material("卫浴_镜框深锡灰", (0.15, 0.14, 0.128), 0.44, 0.56)
    glass = room_material("卫浴_银镜", (0.91, 0.92, 0.92), 0.025, 1.0)
    rounded_box("卫浴_圆角镜框", (west + 0.024, center, 1.549), (0.036, 0.716, 0.806), 0.015, frame)
    rounded_box("卫浴_镜面", (west + 0.042, center, 1.549), (0.006, 0.689, 0.779), 0.003, glass)
    light_body = room_material("卫浴_灯壳", (0.71, 0.70, 0.66), 0.48)
    diffuser = room_material("卫浴_暖白灯罩", (0.92, 0.87, 0.79), 0.38)
    shader = diffuser.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Emission Color"].default_value = (1, 0.87, 0.73, 1)
    shader.inputs["Emission Strength"].default_value = 2.0
    board("卫浴_镜前灯座", (west + 0.037, center, 2.016), (0.074, 0.61, 0.046), light_body, 1, 0)
    board("卫浴_镜前灯罩", (west + 0.075, center, 2.016), (0.006, 0.568, 0.028), diffuser, 1, 0)
    area_light("卫浴_镜前灯", (west + 0.084, center, 2.016), (west + 0.72, center, 1.10), 22, 0.49, (1, 0.89, 0.76))
    for x, y in ((west + 0.82, 1.87), (west + 1.91, 0.93)):
        cylinder("卫浴_吸顶灯边圈", (x, y, 2.970), 0.086, 0.052, light_body)
        cylinder("卫浴_吸顶灯罩", (x, y, 2.942), 0.078, 0.007, diffuser)
        area_light("卫浴_吸顶灯", (x, y, 2.932), (x, y, 0), 54, 0.36, (1, 0.91, 0.81))


def render_glb(render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / ASSET / f"{ASSET}.glb"))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("盥洗柜回导照明")
    scene.world.color = (0.28, 0.28, 0.28)
    area_light("回导主光", (-1.1, -1.9, 2.6), (0, 0, 0.67), 185, 1.9, (1, 1, 1))
    area_light("回导填光", (1.3, 0.75, 2.2), (0, 0, 0.82), 105, 1.7, (1, 1, 1))
    scene.camera = scene_camera(scene, "vanity-glb", (1.10, -2.10, 2.35), (0, 0, 0.68), 54)
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 1.44
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 28
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.filepath = str(render_dir / "bathroom-vanity-glb.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bedroom-furnishings/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bathroom-vanity/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    old = scene.objects["STUDY_vanity"]
    center = old.location.y
    walls = {row[0]: row for row in WALLS}
    west = walls["bedroom_east"][2] + walls["bedroom_east"][5] / 2
    south = walls["south"][2] + walls["south"][5] / 2
    east = walls["bath_east"][2] - walls["bath_east"][5] / 2
    north = walls["bath_north"][2] - walls["bath_north"][5] / 2
    for placeholder in (old, scene.objects["STUDY_basin"]):
        bpy.data.objects.remove(placeholder, do_unlink=True)
    bathroom_surfaces((west, south, east, north))
    place_new(ASSET, vanity(), (west + DEPTH / 2 + 0.009, center, 0.010), pi / 2)
    room_fixtures(west, center)
    views = {
        "bathroom-vanity": ((6.55, 1.16, 1.61), (4.30, 1.87, 1.12), 27),
        "bathroom-vanity-detail": ((5.38, 1.35, 1.46), (4.37, 1.96, 0.85), 43),
    }
    cameras = {name: scene_camera(scene, name, *view) for name, view in views.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    render_dir = args.renders.resolve()
    render_dir.mkdir(parents=True, exist_ok=True)
    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    render_glb(render_dir)


if __name__ == "__main__":
    main()
