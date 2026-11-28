"""补齐垃圾收纳、调味、洗涤和衣物挂放的独立首款。"""

import argparse
from math import cos, pi, radians, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe, rod
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material, textile

BIN, BOTTLE, SPONGE, HANGER, SCRUBBER = (f"A{i}" for i in range(161, 166))
VIEWS = {
    "kitchen-pedal-bin": ((8.27, 4.09, 0.94), (9.61, 4.41, 0.25), 45),
    "kitchen-oil-and-sponge": ((8.33, 8.81, 1.64), (8.94, 9.40, 0.98), 31),
    "kitchen-sponge-detail": ((7.85, 8.85, 1.36), (8.36, 9.345, 0.947), 48),
    "entry-hanger": ((8.48, 2.36, 1.49), (7.19, 2.62, 1.26), 46),
    "utility-scrub-brush": ((5.71, 3.64, 1.25), (5.18, 2.88, 0.96), 57),
}


def pedal_bin():
    steel = satin_steel(BIN)
    dark = room_material("脚踏桶_深灰脚圈与内桶", (0.102, 0.118, 0.108), 0.62)
    profile = [(0.099, 0.016), (0.116, 0.018), (0.123, 0.026), (0.126, 0.040),
               (0.128, 0.064), (0.128, 0.362), (0.127, 0.391), (0.122, 0.397),
               (0.117, 0.397), (0.117, 0.387), (0.121, 0.071), (0.112, 0.043),
               (0.096, 0.031), (0.068, 0.031)]
    bucket = lathe("脚踏桶_折边金属壳和内腔", steel, profile, 0.016, 0.031)
    lid_profile = [(0.094, 0.401), (0.114, 0.400), (0.126, 0.399), (0.130, 0.403),
                   (0.130, 0.409), (0.125, 0.414), (0.115, 0.419), (0.080, 0.420)]
    lid = lathe("脚踏桶_独立圆盖", steel, lid_profile, 0.401, 0.420)
    lower = cylinder("脚踏桶_橡胶减振底圈", (0, 0, 0.010), 0.120, 0.020, dark)
    lining = lathe("脚踏桶_可提内胆", dark, [(0.067, 0.040), (0.103, 0.042), (0.113, 0.052),
                  (0.116, 0.380), (0.118, 0.390), (0.114, 0.391), (0.110, 0.383),
                  (0.108, 0.076), (0.102, 0.056), (0.073, 0.051)], 0.040, 0.051)
    pedal = rounded_box("脚踏桶_脚踏连杆与踏板", (0, -0.129, 0.034), (0.082, 0.081, 0.016), 0.006, steel)
    hinge = rounded_box("脚踏桶_后盖铰轴座", (0, 0.110, 0.391), (0.057, 0.029, 0.023), 0.005, dark)
    # 防滑纹与踏板形体分开，边缘靠近脚背时仍为圆角。
    ribs = [rounded_box("脚踏桶_踏面止滑纹", (0, -0.147 + i * 0.008, 0.042),
                        (0.062, 0.003, 0.002), 0.0008, dark) for i in range(4)]
    return [bucket, lower, lining, lid, hinge, pedal, *ribs]


def oil_bottle():
    amber = room_material("油瓶_深橄榄绿玻璃", (0.22, 0.34, 0.13), 0.20)
    shader = amber.node_tree.nodes["Principled BSDF"]
    shader.inputs["Transmission Weight"].default_value = 0.66
    shader.inputs["IOR"].default_value = 1.47
    steel = satin_steel(BOTTLE)
    gasket = room_material("油瓶_石墨密封塞", (0.050, 0.058, 0.045), 0.56)
    profile = [(0.022, 0.003), (0.029, 0), (0.035, 0.003), (0.037, 0.007), (0.039, 0.018),
               (0.040, 0.128), (0.039, 0.148), (0.037, 0.161), (0.030, 0.173),
               (0.018, 0.180), (0.013, 0.191), (0.013, 0.206), (0.014, 0.210),
               (0.011, 0.212), (0.010, 0.208), (0.010, 0.193), (0.014, 0.184),
               (0.025, 0.175), (0.036, 0.137), (0.036, 0.024), (0.030, 0.014), (0.020, 0.011)]
    vessel = lathe("调味油瓶_内外连续厚玻璃", amber, profile, 0.003, 0.011)
    neck = cylinder("调味油瓶_旋口套及防渗圈", (0, 0, 0.206), 0.015, 0.015, steel)
    seal = cylinder("调味油瓶_塞下硅胶圈", (0, 0, 0.187), 0.011, 0.022, gasket)
    spout = tube("调味油瓶_倾斜注油嘴", [(0, 0, 0.208), (0, 0, 0.222), (0.005, 0, 0.234), (0.021, 0, 0.251)], 0.005, steel)
    hole = cylinder("调味油瓶_端口深色孔", (0.0216, 0, 0.2515), 0.0027, 0.0004, gasket)
    hole.rotation_euler.y = radians(45)
    return [vessel, neck, seal, spout, hole]


def dish_sponge():
    foam = textile("洗涤海绵_黄褐开孔泡棉", (0.62, 0.45, 0.185))
    pad = textile("洗涤海绵_墨绿磨擦面", (0.092, 0.172, 0.107))
    for material in (foam, pad):
        shader = material.node_tree.nodes["Principled BSDF"]
        shader.inputs["Normal"].links[0].from_node.inputs["Strength"].default_value = 0.75
    bottom = rounded_box("洗涤海绵_回弹泡棉", (0, 0, 0.012), (0.105, 0.065, 0.024), 0.009, foam)
    top = rounded_box("洗涤海绵_薄纤维擦片", (0, 0, 0.024), (0.104, 0.064, 0.005), 0.002, pad)
    for part in (bottom, top):
        for loop in part.data.uv_layers.active.data:
            loop.uv *= 3
    return [bottom, top]


def clothes_hanger():
    wood, _ = white_oak_material("衣架_白橡连贯肩弧", "WoodUV")
    steel = satin_steel(HANGER)
    profile = [(-0.210, -0.147), (-0.207, -0.124), (-0.146, -0.098), (-0.082, -0.071),
               (-0.043, -0.049), (-0.018, -0.043), (0.018, -0.043), (0.043, -0.050),
               (0.082, -0.071), (0.146, -0.098), (0.207, -0.124), (0.210, -0.147),
               (0.198, -0.159), (0.135, -0.141), (0.076, -0.111), (0.020, -0.093),
               (0.0, -0.090), (-0.020, -0.093), (-0.076, -0.111), (-0.135, -0.141), (-0.198, -0.159)]
    vertices = [(x, y, z) for y in (0.033, 0.051) for x, z in profile]
    count = len(profile)
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    faces.extend((i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count))
    frame = mesh_object("衣架_实木肩弧", vertices, faces, [wood])
    uv = frame.data.uv_layers.new(name="WoodUV")
    for loop in frame.data.loops:
        x, y, z = vertices[loop.vertex_index]
        uv.data[loop.index].uv = ((z + y) * 2.5, x * 2.6 + 0.5)
    bevel = frame.modifiers.new("衣料接触边倒圆", "BEVEL")
    bevel.width = 0.003
    bevel.segments = 4
    frame.modifiers.new("木肩法线", "WEIGHTED_NORMAL")
    hook_path = [(0, 0.041, -0.065), (0, 0.039, -0.019), (0, 0.028, -0.013),
                 (0, 0.015, -0.010), (0, 0.010, -0.001), (0, 0.003, 0.0036),
                 (0, -0.004, 0.0028), (0, -0.009, -0.003), (0, -0.008, -0.012)]
    hook = tube("衣架_独立弯曲挂钩", hook_path, 0.0028, steel)
    bar = rod("衣架_下方挂裤撑杆", (-0.194, 0.042, -0.151), (0.194, 0.042, -0.151), 0.007, steel)
    return [frame, hook, bar]


def cleaning_brush():
    wood, _ = white_oak_material("清洁刷_温灰橡木握把", "WoodUV")
    fiber = room_material("清洁刷_深米色剑麻", (0.49, 0.37, 0.20), 0.78)
    body = board("清洁刷_两端圆头握把", (0, 0, 0.029), (0.142, 0.049, 0.027), wood, 0, 0.09)
    body.modifiers[0].width = 0.013
    verts, faces = [], []
    for xi in range(-8, 9):
        for yi in range(-2, 3):
            if (xi / 9) ** 2 + (yi / 3) ** 2 > 1:
                continue
            for i in range(5):
                x, y = xi * 0.0068 + 0.0018 * cos(tau * i / 5), yi * 0.007 + 0.0018 * sin(tau * i / 5)
                z = 0.0004 * (1 + sin(i + xi * 1.57 + yi))
                base = len(verts)
                for height, span, shift in ((z, 0.00042, 1), (0.018, 0.00061, 0.85)):
                    verts.extend((x + span * cos(tau * j / 5), shift * y + span * sin(tau * j / 5), height)
                                 for j in range(5))
                for j in range(5):
                    a, b = base + j, base + (j + 1) % 5
                    faces.append((a, b, b + 5, a + 5))
                faces.extend((tuple(reversed(range(base, base + 5))), tuple(range(base + 5, base + 10))))
    brush = mesh_object("清洁刷_密实成束剑麻", verts, faces, [fiber])
    uv = brush.data.uv_layers.new(name="刷毛UV")
    for loop in brush.data.loops:
        index = loop.vertex_index % 10
        uv.data[loop.index].uv = (index % 5 / 4, int(index >= 5))
    return [body, brush]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bathroom-basics/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "household-essentials/house.blend")
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
    place_new(BIN, pedal_bin(), (9.59, 4.417, 0.002), -pi / 2)
    sink = scene.objects["A123"]
    counter_top = sink.location.z
    place_new(BOTTLE, oil_bottle(), (9.53, 9.40, counter_top), radians(-28))
    place_new(SPONGE, dish_sponge(), sink.location + Vector((0.413, -0.12, 0)), radians(16))
    hooks = scene.objects["A150"]
    place_new(HANGER, clothes_hanger(), hooks.matrix_world @ Vector((-0.167, -0.078, 0.011)), pi / 2)
    utility_counter = scene.objects["A117"]
    surface = next(part for part in utility_counter.instance_collection.objects if "连续折叠台面" in part.name)
    top = max((utility_counter.matrix_world @ surface.matrix_world @ Vector(p)).z for p in surface.bound_box)
    place_new(SCRUBBER, cleaning_brush(), (5.20, 2.89, top), radians(-27))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-oil-and-sponge"]
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
