"""按内置生图参考制作带独立叶柄、陶盆和托碟的室内豆瓣绿。"""

import argparse
from math import cos, radians, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_s003_bedroom import STAGES
from build_s003_breakfast import glaze
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe
from build_s003_lived_in import ring_surface
from build_s003_living import LIBRARY, RENDERS, mesh_object, place_new, room_material
import texture_a019_study as maps

PLANT = "A192"
VIEWS = {
    "dining-window-plant": ((6.47, 8.70, 1.36), (5.48, 9.56, 1.06), 52),
}


def leaf_materials():
    leaf = room_material("豆瓣绿_烟青细脉革质叶面", (0.16, 0.28, 0.071), 0.36)
    mate = room_material("豆瓣绿_浅橄榄新叶", (0.24, 0.38, 0.109), 0.37)
    shader = leaf.node_tree.nodes["Principled BSDF"]
    shader.inputs["Subsurface Weight"].default_value = 0.077
    shader.inputs["Coat Weight"].default_value = 0.035
    shader.inputs["Coat Roughness"].default_value = 0.40
    shader.inputs["IOR"].default_value = 1.42
    maps.OUTPUT = LIBRARY / PLANT
    size = maps.RESOLUTION
    rng = np.random.default_rng(192)
    xs = np.linspace(-1, 1, size, dtype=np.float32)[None, :]
    ys = np.linspace(0, 1, size, dtype=np.float32)[:, None]
    distance = np.abs(xs)
    lateral = (ys - 0.205 * distance - 0.070 * distance ** 2 + 0.007 * np.sin(15 * xs))
    secondary = np.exp(-(np.sin(tau * 4.8 * lateral) / 0.12) ** 2) * distance * (1 - distance) * 1.9
    midrib = np.exp(-(xs / (0.024 - ys * 0.011)) ** 2) * (1 - 0.68 * ys)
    grain = rng.random((size, size), dtype=np.float32)
    lamina = 0.91 + 0.11 * distance + 0.12 * ys + 0.08 * np.sin(8.5 * ys + xs * 6.4) + (grain - 0.5) * 0.07
    tone = np.array((0.189, 0.300, 0.084), dtype=np.float32)
    tint = np.array((0.18, 0.16, 0.064), dtype=np.float32)
    base = lamina[:, :, None] * tone + (midrib * 0.54 + secondary * 0.23)[:, :, None] * tint
    surface = (grain - 0.5) * 0.027 + midrib * 0.09 + secondary * 0.038
    dy, dx = np.gradient(surface)
    normal = np.stack((0.5 - 4.0 * dx, 0.5 - 4.0 * dy, np.ones_like(surface)), axis=-1)
    textures = {name: maps.save_image("leaf_" + name, data, name != "BaseColor") for name, data in (
        ("BaseColor", base), ("Roughness", np.clip(0.48 + surface * 0.38, 0, 1)),
        ("Normal", normal), ("Metallic", np.zeros_like(surface)),
    )}
    maps.connect_maps(leaf, textures)
    for image in textures.values():
        image.filepath = str(maps.OUTPUT / "textures" / bpy.path.basename(image.filepath))
        image.pack()
    mate.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.15
    return leaf, mate


def stem(name, points, radius, material):
    points = [points[0], points[0].lerp(points[1], 0.10), *points[1:-1],
              points[-2].lerp(points[-1], 0.90), points[-1]]
    rings = []
    for i, point in enumerate(points):
        ratio = i / (len(points) - 1)
        cut = radius * (1 - ratio * 0.71)
        rings.append([(point.x + cut * cos(tau * j / 12), point.y + cut * sin(tau * j / 12), point.z)
                      for j in range(12)])
    result = ring_surface(name, rings, [material], (True, True))
    result.modifiers.new("幼茎轮廓细化", "SUBSURF").levels = 2
    return result


def blade(name, start, along, width, length, curl, twist, material):
    side = Vector((-along.y, along.x, 0)).normalized()
    normal = side.cross(along).normalized()
    rows, cols = 25, 13
    vertices, faces = [], []
    for row in range(rows):
        t = row / (rows - 1)
        silhouette = sin(np.pi * t) ** 0.53 * (0.74 + 0.53 * t)
        for col in range(cols):
            u = 2 * col / (cols - 1) - 1
            span = width * max(0.012, silhouette) * (1 + 0.06 * u * sin(4.7 * t))
            cupping = (0.0037 * u ** 2 + 0.0018 * u * sin(7.5 * t + twist)) * silhouette
            bend = curl * t ** 2 + cupping + span * twist * u * t ** 1.25
            vertices.append(start + along * (length * t) + side * (span * u) - normal * bend)
    for row in range(rows - 1):
        for col in range(cols - 1):
            a = row * cols + col
            faces.append((a, a + cols, a + cols + 1, a + 1))
    leaf = mesh_object(name, vertices, faces, [material])
    uv = leaf.data.uv_layers.new(name="顺叶脉UV")
    for face in leaf.data.polygons:
        face.use_smooth = True
        for index in face.loop_indices:
            row, col = divmod(leaf.data.loops[index].vertex_index, cols)
            uv.data[index].uv = (col / (cols - 1), row / (rows - 1))
    thickness = leaf.modifiers.new("叶片非零厚度", "SOLIDIFY")
    thickness.thickness = 0.00125
    return leaf


def soil():
    dirt = room_material("豆瓣绿_湿泥炭和树皮细粒", (0.054, 0.037, 0.022), 0.87)
    fiber = room_material("豆瓣绿_干燥纤维和树皮", (0.108, 0.073, 0.037), 0.85)
    gravel = room_material("豆瓣绿_盆土珍珠岩颗粒", (0.50, 0.441, 0.345), 0.87)
    rng = np.random.default_rng(92)
    rings = [[(r * cos(tau * i / 64), r * sin(tau * i / 64), 0.095 + rng.uniform(-0.002, 0.0015))
              for i in range(64)] for r in (0.006, 0.014, 0.024, 0.034, 0.044, 0.053, 0.061)]
    rings.reverse()
    top = ring_surface("豆瓣绿_不规则栽培基质", rings, [dirt, fiber], (False, True))
    for face in top.data.polygons:
        face.material_index = int(rng.random() < 0.17)
    vertices, faces = [], []
    for i in range(58):
        angle = rng.uniform(0, tau)
        radius = rng.uniform(0.010, 0.057)
        x, y = radius * cos(angle), radius * sin(angle)
        extent = rng.uniform(0.0009, 0.0029)
        n = len(vertices)
        vertices.extend(((x + extent, y, 0.096), (x, y + extent, 0.096), (x - extent, y, 0.095),
                         (x, y - extent, 0.096), (x + 0.3 * extent, y, 0.096 + extent), (x, y, 0.093)))
        for j in range(4):
            k = (j + 1) % 4
            faces.extend(((n + j, n + k, n + 4), (n + k, n + j, n + 5)))
    grit = mesh_object("豆瓣绿_盆土独立珍珠岩和碎皮", vertices, faces, [gravel, fiber])
    uv = grit.data.uv_layers.new(name="颗粒UV")
    for face in grit.data.polygons:
        face.material_index = int(face.index // 8 % 4 != 0)
        for index, point in zip(face.loop_indices, ((0, 0), (1, 0), (0.5, 1))):
            uv.data[index].uv = point
    return [top, grit]


def plant():
    ceramic = glaze(PLANT, "豆瓣绿_细沙砖红陶釉", (0.40, 0.129, 0.077), 0.42)
    green = room_material("豆瓣绿_青褐茎和短叶柄", (0.15, 0.194, 0.066), 0.53)
    mature, young = leaf_materials()
    pot = lathe("豆瓣绿_连续内外陶盆及卷沿", ceramic, [(0.045, 0.009), (0.054, 0.009), (0.059, 0.014),
                (0.061, 0.022), (0.062, 0.088), (0.063, 0.096), (0.066, 0.100), (0.067, 0.105),
                (0.065, 0.109), (0.060, 0.109), (0.058, 0.105), (0.059, 0.099), (0.056, 0.034),
                (0.054, 0.024), (0.046, 0.019), (0.038, 0.018)], 0.009, 0.018)
    tray = lathe("豆瓣绿_有接水凹槽的分体托碟", ceramic, [(0.046, 0), (0.060, 0), (0.065, 0.002), (0.068, 0.009),
                  (0.068, 0.014), (0.066, 0.017), (0.063, 0.015), (0.061, 0.009), (0.055, 0.009), (0.044, 0.009)], 0, 0.009)
    parts = [pot, tray, *soil()]
    layout = (
        (((-0.010, -0.009, 0.091), (-0.014, 0.007, 0.133), (-0.028, 0.016, 0.177), (-0.032, 0.023, 0.215), (-0.042, 0.027, 0.241)),
         ((1, 196, 0.15, 0.069, 0.035, -0.014, 0.12), (2, 308, 0.34, 0.074, 0.034, -0.008, -0.24),
          (2, 97, 0.25, 0.072, 0.032, -0.006, 0.24), (3, 61, 0.74, 0.065, 0.029, -0.008, 0.36),
          (4, 143, 0.79, 0.060, 0.025, -0.007, -0.17))),
        (((0.014, 0.009, 0.092), (0.025, 0.019, 0.130), (0.041, 0.020, 0.163), (0.056, 0.015, 0.191), (0.052, 0.024, 0.217)),
         ((1, 58, 0.23, 0.062, 0.028, -0.012, 0.13), (1, 353, 0.01, 0.051, 0.024, -0.006, -0.18),
          (2, 325, 0.27, 0.073, 0.032, -0.016, -0.24), (3, 138, 0.25, 0.069, 0.031, -0.011, 0.29),
          (4, 39, 0.63, 0.056, 0.024, -0.010, 0.28))),
        (((0.004, -0.020, 0.093), (0.009, -0.028, 0.118), (0.018, -0.044, 0.145), (0.023, -0.054, 0.171), (0.030, -0.051, 0.191)),
         ((1, 199, 0.14, 0.057, 0.025, -0.008, -0.24), (2, 266, 0.20, 0.070, 0.034, -0.018, 0.23),
          (2, 148, 0.26, 0.061, 0.027, -0.008, 0.22), (3, 355, 0.36, 0.059, 0.027, -0.010, -0.15),
          (4, 223, 0.55, 0.045, 0.019, -0.010, 0.14))),
    )
    for branch, leaves in layout:
        points = [Vector(point) for point in branch]
        parts.append(stem("豆瓣绿_独立青褐主茎", points, 0.006, green))
        for node, degrees, slope, length, width, curl, twist in leaves:
            angle = radians(degrees)
            along = Vector((cos(angle), sin(angle), slope * 1.33)).normalized()
            root = points[node]
            tip = root + along * 0.014 + Vector((0, 0, 0.007))
            parts.append(tube("豆瓣绿_与叶面连接的短叶柄", [root, (root + tip) / 2 + Vector((0, 0, -0.001)), tip], 0.00175, green, 12))
            parts.append(blade("豆瓣绿_厚椭圆叶片", tip, along, width * 1.12, length, curl, twist, mature))
        for degrees in (22, 175):
            angle = radians(degrees)
            along = Vector((0.36 * cos(angle), 0.36 * sin(angle), 0.88)).normalized()
            parts.append(blade("豆瓣绿_浅色顶梢新叶", points[-1], along, 0.010, 0.027, -0.006, 0.16, young))
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "small-appliances/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "window-plant/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    table = scene.objects["A183"]
    top = table.instance_collection.objects["窗桌_整块圆边白橡台板"]
    support_z = max((table.matrix_world @ top.matrix_world @ Vector(p)).z for p in top.bound_box)
    place_new(PLANT, plant(), (table.location.x - 0.44, table.location.y + 0.077, support_z), radians(-16))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["dining-window-plant"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if args.build_only:
        return
    scene.render.filepath = str(RENDERS / "dining-window-plant.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
