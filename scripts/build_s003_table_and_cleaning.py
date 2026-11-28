"""补餐叉、木筷、干粮罐、洗衣剂瓶和两款长柄清洁用品。"""

import argparse
from math import cos, radians, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_breakfast import table_mats
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_props import lathe, rod
from build_s003_lived_in import ring_surface
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material, textile
from build_s003_utility import FLOOR_TOP

FORK, CHOPSTICKS, JAR, DETERGENT, BROOM, MOP = (f"A{i}" for i in range(176, 182))
VIEWS = {
    "dining-fork-chopsticks": ((6.07, 6.47, 1.94), (6.06, 7.18, 0.78), 35),
    "utility-floor-care": ((6.29, 3.26, 1.52), (4.71, 3.81, 0.69), 30),
    "utility-detergent": ((5.99, 3.49, 1.39), (5.35, 2.90, 1.04), 52),
    "kitchen-pantry-jar": ((8.24, 7.12, 1.49), (9.50, 7.28, 1.05), 47),
}


def fork():
    metal = satin_steel(FORK)
    contour = [(-0.005, -0.098), (-0.009, -0.093), (-0.0085, -0.059), (-0.0060, -0.014),
               (-0.0058, 0.012), (-0.009, 0.027), (-0.013, 0.045)]
    for center in (-0.0099, -0.0033, 0.0033, 0.0099):
        contour.extend(((center - 0.0027, 0.055), (center - 0.0023, 0.088),
                        (center - 0.0012, 0.092), (center + 0.0012, 0.092),
                        (center + 0.0023, 0.088), (center + 0.0027, 0.055)))
    contour.extend(((0.013, 0.046), (0.009, 0.027), (0.0058, 0.012), (0.006, -0.014),
                    (0.0085, -0.059), (0.009, -0.093), (0.005, -0.098)))
    contour.reverse()
    count = len(contour)
    vertices = [(x, y, h + 0.0105 * (max(0, y + 0.009) / 0.101) ** 1.7)
                for h in (0, 0.0021) for x, y in contour]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    for i in range(count):
        nxt = (i + 1) % count
        faces.append((i, nxt, nxt + count, i + count))
    body = mesh_object("餐叉_一体弧颈与四叉齿", vertices, faces, [metal])
    uv = body.data.uv_layers.new(name="拉丝UV")
    for loop in body.data.loops:
        x, y, _ = vertices[loop.vertex_index]
        uv.data[loop.index].uv = (x * 10 + 0.5, y * 5 + 0.5)
    edge = body.modifiers.new("餐叉圆润握边", "BEVEL")
    edge.width, edge.segments = 0.00055, 3
    body.modifiers.new("叉面加权法线", "WEIGHTED_NORMAL")
    return [body]


def chopsticks():
    wood, _ = white_oak_material("筷子_径切白橡", "WoodUV")
    jade = room_material("筷子_末端墨青生漆", (0.086, 0.17, 0.135), 0.41)
    parts = []
    for x in (-0.009, 0.009):
        rings = []
        for y, radius in ((-0.117, 0.0030), (-0.115, 0.0038), (-0.093, 0.0038), (-0.089, 0.0038),
                          (-0.075, 0.0037), (0.068, 0.0024), (0.112, 0.00175), (0.117, 0.00145)):
            rings.append([(x + radius * cos(tau * i / 12), y, radius + radius * sin(-tau * i / 12))
                          for i in range(12)])
        stick = ring_surface("木筷_十二面渐收单支", rings, [wood, jade], (True, True))
        stick.data.uv_layers.active.name = "WoodUV"
        for face in stick.data.polygons:
            face.material_index = int(face.index < 24 or face.index == (len(rings) - 1) * 12)
            for index in face.loop_indices:
                vertex = stick.data.loops[index].vertex_index
                u = (rings[vertex // 12][vertex % 12][1] + 0.117) * 4.0
                stick.data.uv_layers.active.data[index].uv = (u, vertex % 12 / 12)
        parts.append(stick)
    return parts


def pantry_jar():
    glass = room_material("干粮罐_透明耐热玻璃", (0.94, 0.975, 0.951), 0.097)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1
    oak, _ = white_oak_material("干粮罐_上油白橡盖", "WoodUV")
    rubber = room_material("干粮罐_深米灰密封圈", (0.29, 0.239, 0.181), 0.64)
    wall = [(0.042, 0.001), (0.053, 0), (0.058, 0.003), (0.061, 0.011), (0.061, 0.168),
            (0.060, 0.180), (0.057, 0.184), (0.054, 0.183), (0.055, 0.173), (0.057, 0.165),
            (0.057, 0.014), (0.054, 0.008), (0.044, 0.006)]
    jar = lathe("干粮罐_有实底和贯通瓶口的玻璃壳", glass, wall, 0.001, 0.006)
    cap = cylinder("干粮罐_独立木盖", (0, 0, 0.188), 0.061, 0.014, oak, vertices=80)
    cap.data.uv_layers.active.name = "WoodUV"
    gasket = cylinder("干粮罐_木盖下方硅胶垫", (0, 0, 0.179), 0.0555, 0.006, rubber, vertices=80)
    return [jar, cap, gasket]


def detergent():
    polymer = room_material("洗衣剂瓶_淡琥珀再生聚合物", (0.52, 0.35, 0.17), 0.42)
    polymer.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.13
    lid = room_material("洗衣剂瓶_暖灰量杯盖", (0.22, 0.20, 0.16), 0.49)
    profile = [(0.038, 0), (0.051, 0), (0.056, 0.004), (0.058, 0.012), (0.058, 0.144),
               (0.055, 0.160), (0.041, 0.172), (0.025, 0.177), (0.021, 0.19), (0.021, 0.201),
               (0.017, 0.202), (0.017, 0.189), (0.022, 0.171), (0.053, 0.146), (0.053, 0.014),
               (0.046, 0.007), (0.031, 0.006)]
    bottle = lathe("洗衣剂瓶_内外双面模压罐身", polymer, profile, 0, 0.006)
    for vertex in bottle.data.vertices:
        vertex.co.y *= 0.76
    top = lathe("洗衣剂瓶_独立止滑旋盖", lid, [(0.014, 0.196), (0.023, 0.196), (0.025, 0.2),
                (0.025, 0.226), (0.023, 0.229), (0.011, 0.229)], 0.196, 0.229)
    ridges = []
    for i in range(32):
        a = tau * i / 32
        tooth = rounded_box("洗衣剂瓶_旋盖止滑筋", (0.0247 * cos(a), 0.0247 * sin(a), 0.212),
                            (0.0017, 0.0015, 0.023), 0.0005, lid)
        tooth.rotation_euler.z = a
        ridges.append(tooth)
    return [bottle, top, *ridges]


def broom():
    oak, _ = white_oak_material("扫帚_油封白橡刷头及柄", "WoodUV")
    bristles = room_material("扫帚_经修剪的深麦植物纤维", (0.37, 0.244, 0.105), 0.83)
    sleeve = room_material("扫帚_深苔接头", (0.13, 0.17, 0.125), 0.66, 0.23)
    bar = board("扫帚_圆头木底座", (0, 0, 0.071), (0.231, 0.047, 0.028), oak, 0, 0.26)
    bar.modifiers[0].width = 0.012
    shaft = rod("扫帚_长木圆柄", (0, 0, 0.081), (0, 0.11, 1.324), 0.013, oak)
    shaft.data.uv_layers.active.name = "WoodUV"
    ferrule = rod("扫帚_木座承力接头", (0, 0, 0.076), (0, 0.008, 0.168), 0.018, sleeve)
    vertices, faces = [], []
    for band in range(-2, 3):
        for col in range(-22, 23):
            for j in range(3):
                x, y = col * 0.0045 + 0.0012 * sin(col + j * 2), band * 0.007 + 0.0013 * cos(col - j)
                base = len(vertices)
                rings = ((1.18 * x, 1.26 * y, 0.0006 * (1 + sin(col * 2 + j)), 0.00036),
                         (x, y, 0.062 + 0.0010 * cos(col + j), 0.0006))
                for px, py, pz, radius in rings:
                    vertices.extend((px + radius * cos(tau * i / 5), py + radius * sin(tau * i / 5), pz)
                                    for i in range(5))
                for i in range(5):
                    a, b = base + i, base + (i + 1) % 5
                    faces.append((a, b, b + 5, a + 5))
                faces.extend((tuple(reversed(range(base, base + 5))), tuple(range(base + 5, base + 10))))
    brush = mesh_object("扫帚_连续排列的植物丝束", vertices, faces, [bristles])
    uv = brush.data.uv_layers.new(name="扫帚丝束UV")
    for loop in brush.data.loops:
        index = loop.vertex_index % 10
        uv.data[loop.index].uv = (index % 5 / 4, int(index >= 5))
    return [bar, shaft, ferrule, brush]


def flat_mop():
    microfiber = textile("平板拖把_深青可拆洗拖布", (0.116, 0.248, 0.237))
    body = room_material("平板拖把_米灰成型底板", (0.46, 0.46, 0.416), 0.47)
    grip = room_material("平板拖把_深灰纹理握套", (0.12, 0.148, 0.138), 0.62)
    steel = satin_steel(MOP)
    pad = rounded_box("平板拖把_圆边贴地微纤拖布", (0, 0, 0.006), (0.326, 0.115, 0.012), 0.0054, microfiber)
    for corner in pad.data.uv_layers.active.data:
        corner.uv *= 5.0
    head = rounded_box("平板拖把_脱卸式长板", (0, 0, 0.019), (0.313, 0.108, 0.017), 0.007, body)
    joint = rounded_box("平板拖把_双向万向轴壳", (0, 0, 0.038), (0.066, 0.038, 0.030), 0.007, grip)
    pivot = rod("平板拖把_可见横轴", (-0.027, 0, 0.046), (0.027, 0, 0.046), 0.008, steel)
    lower = rod("平板拖把_下段伸缩钢管", (0, 0, 0.050), (0, 0.070, 0.792), 0.0103, steel)
    upper = rod("平板拖把_上段伸缩钢管", (0, 0.058, 0.681), (0, 0.108, 1.21), 0.0086, steel)
    stop = rod("平板拖把_伸缩锁止套", (0, 0.064, 0.754), (0, 0.073, 0.811), 0.0137, grip)
    handle = rod("平板拖把_触手包胶握套", (0, 0.094, 1.06), (0, 0.112, 1.245), 0.0138, grip)
    return [pad, head, joint, pivot, lower, upper, stop, handle]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "reusable-openings/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "table-and-cleaning/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    mats, height = table_mats(scene)
    scene.objects["A106"].location.y += 0.073
    place_new(FORK, fork(), mats[0].location + Vector((0.125, -0.052, height)), radians(-3))
    place_new(CHOPSTICKS, chopsticks(), mats[1].location + Vector((0.183, 0, height)), radians(2))
    place_new(JAR, pantry_jar(), (9.53, 7.27, scene.objects["A123"].location.z))
    place_new(DETERGENT, detergent(), scene.objects["A165"].location + Vector((0.147, -0.026, 0)))
    place_new(BROOM, broom(), (4.44, 3.818, FLOOR_TOP))
    place_new(MOP, flat_mop(), (4.78, 3.815, FLOOR_TOP))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["dining-fork-chopsticks"]
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
