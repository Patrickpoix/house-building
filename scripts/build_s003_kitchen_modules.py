"""发布一体开孔石英台面、壁挂层架和穿孔洗滤篮。"""

import argparse
from math import cos, pi, sin, sqrt, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe
from build_s003_living import LIBRARY, RENDERS, cylinder, mesh_object, place_new, publish_asset, room_material
import texture_a019_study as maps

WORKTOP, SHELF, COLANDER = "A186", "A187", "A188"
VIEWS = {
    "kitchen-quartz-and-sink": ((7.19, 8.64, 1.52), (8.04, 9.47, 0.95), 37),
    "kitchen-open-shelf": ((8.47, 8.34, 1.78), (9.27, 9.68, 2.06), 39),
    "kitchen-colander": ((8.77, 7.65, 1.46), (9.39, 7.43, 1.02), 45),
}


def quartz():
    material = room_material("暖白石英石_细砂和透明矿粒", (0.72, 0.68, 0.60), 0.30)
    maps.OUTPUT = LIBRARY / WORKTOP
    rng = np.random.default_rng(186)
    size = maps.RESOLUTION
    noise = rng.random((size, size), dtype=np.float32)
    coarse = sum(np.roll(noise, shift, axis=axis) for axis in (0, 1) for shift in (-2, 2)) * 0.25
    crystals = np.maximum(0, coarse - 0.76)
    matrix = (coarse - 0.5) * 0.055 + (noise - 0.5) * 0.013 - crystals * 0.48
    # 稀疏深色矿粒嵌在已磨平的基质里，法线起伏保持在很小的范围。
    dark = np.clip((noise - 0.997) * 280, 0, 0.7)
    mottled = matrix - (dark + 0.30 * np.roll(dark, 1, axis=0)) * 0.19
    base = np.array((0.73, 0.69, 0.62), dtype=np.float32)
    color = np.clip((1 + mottled[:, :, None]) * base, 0, 1)
    rough = np.clip(0.31 + matrix * 0.8 + dark * 0.04, 0, 1)
    dy, dx = np.gradient(matrix)
    normal = np.stack((0.5 - 1.8 * dx, 0.5 - 1.8 * dy, np.ones_like(matrix)), axis=-1)
    textures = {name: maps.save_image("warm-quartz_" + name, data, name != "BaseColor") for name, data in (
        ("BaseColor", color), ("Roughness", rough), ("Normal", normal),
        ("Metallic", np.zeros_like(rough)),
    )}
    maps.connect_maps(material, textures)
    for image in textures.values():
        image.filepath = str(maps.OUTPUT / "textures" / bpy.path.basename(image.filepath))
        image.pack()
    return material


def publish_worktop(scene):
    material = quartz()
    parts = [scene.objects[name] for name in ("餐厨_北侧一体开孔台面", "餐厨_东侧台面")]
    points = [part.matrix_world @ Vector(p) for part in parts for p in part.bound_box]
    low = Vector(min(p[i] for p in points) for i in range(3))
    high = Vector(max(p[i] for p in points) for i in range(3))
    for part in parts:
        part.data.materials.clear()
        part.data.materials.append(material)
        uv = part.data.uv_layers.active or part.data.uv_layers.new(name="石英统一实尺UV")
        for face in part.data.polygons:
            axis = max(range(3), key=lambda i: abs(face.normal[i]))
            u, v = [i for i in range(3) if i != axis]
            for index in face.loop_indices:
                point = part.matrix_world @ part.data.vertices[part.data.loops[index].vertex_index].co
                uv.data[index].uv = ((point[u] - low[u]) / 0.44, (point[v] - low[v]) / 0.44)
    origin = Vector((*((low + high) / 2)[:2], low.z))
    publish_asset(WORKTOP, parts, origin)


def wall_shelf():
    oak, _ = white_oak_material("餐厨层架_油封白橡", "WoodUV")
    enamel = room_material("餐厨层架_深苔色粉末涂层", (0.13, 0.165, 0.143), 0.47, 0.15)
    screw_mat = room_material("餐厨层架_磷化螺钉", (0.092, 0.089, 0.081), 0.45, 0.61)
    panel = board("壁挂层架_实木层板", (0, -0.126, 0.018), (1.020, 0.246, 0.038), oak, 0, 0.27)
    panel.modifiers[0].width = 0.0035
    parts = [panel]
    for x in (-0.353, 0.353):
        parts.append(rounded_box("壁挂层架_长圆背板", (x, -0.005, -0.058), (0.052, 0.010, 0.162), 0.004, enamel))
        parts.append(rounded_box("壁挂层架_板下承托角钢", (x, -0.108, -0.009), (0.038, 0.207, 0.019), 0.003, enamel))
        brace = rounded_box("壁挂层架_斜向传力撑", (x, -0.086, -0.065), (0.020, 0.191, 0.017), 0.003, enamel)
        brace.rotation_euler.x = -0.65
        parts.append(brace)
        for z in (-0.097, 0.005):
            screw = cylinder("壁挂层架_墙装五金", (x, -0.010, z), 0.006, 0.004, screw_mat, vertices=24)
            screw.rotation_euler.x = pi / 2
            parts.append(screw)
    return parts


def perforated_shell(steel):
    radius_z = [(0.038, 0.014), (0.057, 0.018), (0.075, 0.025), (0.091, 0.037),
                (0.103, 0.052), (0.112, 0.070), (0.118, 0.090), (0.120, 0.104)]
    vertices, faces, uv_points = [], [], []
    sectors = 30
    # 每区块的四边中点和四角共用顶点，开孔后整体加厚。
    border = ((0, 0), (0.5, 0), (1, 0), (1, 0.5), (1, 1), (0.5, 1), (0, 1), (0, 0.5))
    edge_vertices = {}

    def vertex(i, j):
        row = min(int(j), len(radius_z) - 2)
        a, b = radius_z[row:row + 2]
        k = j - row
        radius, z = a[0] + k * (b[0] - a[0]), a[1] + k * (b[1] - a[1])
        angle = (i + 0.28 * sin(j * pi / 2)) * tau / sectors
        vertices.append((radius * cos(angle), radius * sin(angle), z))
        uv_points.append((i / sectors, j / (len(radius_z) - 1)))
        return len(vertices) - 1

    for j in range(len(radius_z) - 1):
        for i in range(sectors):
            edge = []
            for u, v in border:
                key = ((i + u) % sectors, j + v)
                if key not in edge_vertices:
                    edge_vertices[key] = vertex(*key)
                edge.append(edge_vertices[key])
            hole = [vertex(i + 0.5 + (u - 0.5) * 0.37 / sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2),
                           j + 0.5 + (v - 0.5) * 0.21 / sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2))
                    for u, v in border]
            for k in range(len(edge)):
                nxt = (k + 1) % len(edge)
                faces.append((edge[k], edge[nxt], hole[nxt], hole[k]))
    bottom = [edge_vertices[(i * 0.5, 0)] for i in range(2 * sectors)]
    faces.append(tuple(reversed(bottom)))
    shell = mesh_object("洗滤篮_连续冲孔不锈钢碗身", vertices, faces, [steel])
    uv = shell.data.uv_layers.new(name="拉丝方向UV")
    for face in shell.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        coordinates = [uv_points[i] for i in face.vertices]
        seam = max(u for u, _ in coordinates) - min(u for u, _ in coordinates) > 0.5
        for index, (u, v) in zip(face.loop_indices, coordinates):
            if face.use_smooth:
                uv.data[index].uv = (u + int(seam and u < 0.15), v)
            else:
                x, y, _ = vertices[shell.data.loops[index].vertex_index]
                uv.data[index].uv = (x * 5 + 0.5, y * 5 + 0.5)
    solid = shell.modifiers.new("冲孔贯穿钢板", "SOLIDIFY")
    solid.thickness = 0.0015
    bevel = shell.modifiers.new("冲口软化边缘", "BEVEL")
    bevel.width, bevel.segments = 0.0004, 2
    return shell


def colander():
    steel = satin_steel(COLANDER)
    parts = [perforated_shell(steel)]
    bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=12, location=(0, 0, 0.105),
                                    major_radius=0.120, minor_radius=0.0035)
    rim = bpy.context.object
    rim.name = "洗滤篮_防割钢板卷边"
    rim.data.materials.append(steel)
    for face in rim.data.polygons:
        face.use_smooth = True
    parts.append(rim)
    parts.append(lathe("洗滤篮_落地焊接圈足", steel, [(0.053, 0.009), (0.054, 0.002), (0.053, 0.0),
                       (0.049, 0.0), (0.048, 0.002), (0.051, 0.012), (0.043, 0.019)], 0.009, 0.019))
    for side in (-1, 1):
        shape = [(side * x, y, z) for x, y, z in ((0.116, -0.023, 0.095), (0.130, -0.022, 0.101),
                 (0.150, -0.019, 0.100), (0.160, -0.009, 0.097), (0.161, 0.009, 0.097),
                 (0.150, 0.019, 0.100), (0.131, 0.022, 0.101), (0.116, 0.023, 0.095))]
        handle = tube("洗滤篮_抓握钢丝耳", shape, 0.0037, steel, sides=12)
        handle.modifiers.new("钢丝对称收角", "SUBSURF").levels = 2
        parts.append(handle)
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "counter-seating-and-doors/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "kitchen-modules/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    countertop_z = scene.objects["A123"].location.z
    publish_worktop(scene)
    place_new(SHELF, wall_shelf(), (9.19, 9.8, 2.063))
    place_new(COLANDER, colander(), (9.39, 7.53, countertop_z), -pi / 7)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-quartz-and-sink"]
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
