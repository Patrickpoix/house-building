"""从家政阶段接续通高家政柜和玄关衣帽柜。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_s001_whitebox import WALLS
from build_s003_bathroom_vanity import area_light
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, RENDERS, cylinder, place_new, room_material
from build_s003_utility import FLOOR_TOP


UTILITY = "A118"
COAT = "A119"
SIDE = 0.022
PLINTH = 0.086
SHELF = 0.021
VIEWS = {
    "utility-storage": ((5.54, 3.87, 1.52), (6.54, 3.21, 1.12), 19),
    "entry-storage": ((7.97, 1.40, 1.55), (9.34, 3.07, 1.23), 24),
    "entry-key-shelf": ((8.45, 3.48, 1.43), (9.47, 3.46, 1.28), 39),
}


def cabinet(prefix, width, depth, height, is_coat):
    oak, _ = white_oak_material(f"{prefix}_白橡木皮", "WoodUV")
    paint = room_material(f"{prefix}_苔灰涂层", (0.225, 0.258, 0.220), 0.47)
    backing = room_material(f"{prefix}_后背米灰", (0.52, 0.498, 0.439), 0.66)
    metal = room_material(f"{prefix}_深锡五金", (0.154, 0.163, 0.139), 0.31, 0.72)
    parts = []
    local_front = -depth / 2
    inside_depth = depth - 0.044
    full_width = width - 2 * SIDE

    def panel(name, pos, size, mat=oak, grain=2):
        obj = board(f"{prefix}_{name}", pos, size, mat, grain, sum(pos) * 0.28)
        parts.append(obj)
        return obj

    for sign in (-1, 1):
        panel("通高侧板", (sign * (width - SIDE) / 2, 0, height / 2), (SIDE, depth, height))
    panel("后侧封板", (0, depth / 2 - 0.008, height / 2), (full_width, 0.016, height - 0.021), backing)
    panel("顶板", (0, 0, height - SIDE / 2), (full_width, inside_depth, SIDE), grain=0)
    panel("底板", (0, 0, PLINTH + SHELF / 2), (full_width, inside_depth, SHELF), grain=0)
    panel("内缩踢脚", (0, local_front + 0.076, PLINTH / 2), (full_width, 0.022, PLINTH), paint, 0)
    split = -0.17 if is_coat else -0.074
    panel("内隔板", (split, 0, (height + PLINTH) / 2),
          (SIDE, inside_depth, height - PLINTH - SIDE), grain=2)

    left_edge, right_edge = -full_width / 2, full_width / 2
    left_span = (left_edge, split - SIDE / 2)
    right_span = (split + SIDE / 2, right_edge)

    def shelf(span, z, *, front=0.033, mat=oak):
        lo, hi = span
        length = depth - front - 0.020
        panel("可调搁板", ((lo + hi) / 2, local_front + front + length / 2, z),
              (hi - lo, length, SHELF), mat, 0)

    def doors(span, bottom, top, opens_left, mat, label):
        lo, hi = span
        thickness = 0.022
        mid_height = (bottom + top) / 2
        door_y = local_front - thickness / 2 - 0.002
        panel(f"{label}门板", ((lo + hi) / 2, door_y, mid_height),
              (hi - lo - 0.004, thickness, top - bottom - 0.004), mat)
        grip_x = hi - 0.056 if opens_left else lo + 0.056
        grip_z = min(max(1.040, bottom + 0.105), top - 0.105)
        panel(f"{label}拉手", (grip_x, door_y - 0.023, grip_z), (0.014, 0.014, 0.142), metal)
        for z in (grip_z - 0.047, grip_z + 0.047):
            panel(f"{label}拉手脚", (grip_x, door_y - 0.014, z), (0.011, 0.019, 0.012), metal)

    if is_coat:
        for z in (0.31, 0.55, 0.78, 1.102, 1.78, 2.01):
            shelf(left_span, z)
        for z in (0.33, 1.925):
            shelf(right_span, z)
        c = (right_span[0] + right_span[1]) / 2
        rail = cylinder(f"{prefix}_挂衣杆", (c, 0.022, 1.813), 0.014, right_span[1] - right_span[0], metal)
        rail.rotation_euler.y = pi / 2
        parts.append(rail)
        doors(right_span, PLINTH + 0.024, height - 0.025, False, oak, "衣帽区")
        doors(left_span, PLINTH + 0.024, 0.789, True, paint, "鞋区")
        doors(left_span, 1.785, height - 0.025, True, paint, "上柜")
        panel("随手格木饰背板", ((left_span[0] + left_span[1]) / 2, depth / 2 - 0.022, 1.287),
              (left_span[1] - left_span[0], 0.012, 0.990))
    else:
        for z in (0.41, 0.72, 1.01, 1.28, 1.55, 1.88):
            shelf(left_span, z)
        shelf(right_span, 1.91)
        panel("清洁长柄夹安装板", ((right_span[0] + right_span[1]) / 2, depth / 2 - 0.029, 1.48),
              (right_span[1] - right_span[0] - 0.054, 0.018, 0.057), metal, 0)
        for x in (right_span[0] + 0.15, right_span[1] - 0.15):
            panel("清洁长柄弹性夹", (x, depth / 2 - 0.058, 1.48), (0.038, 0.047, 0.040), metal)
        doors(left_span, PLINTH + 0.024, height - 0.025, True, paint, "层板区")
        doors(right_span, PLINTH + 0.024, height - 0.025, False, paint, "长柄区")
    return parts


def add_storage(source, output):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    walls = {name: (fixed, thickness) for name, _, fixed, _, _, thickness, _ in WALLS}
    utility_east = walls["bath_east"][0] - walls["bath_east"][1] / 2
    coat_east = walls["east"][0] - walls["east"][1] / 2
    for asset, prefix, placeholder, wall_x, width, depth, height, floor in (
        (UTILITY, "家政高柜", "STUDY_utility_storage", utility_east, 1.180, 0.598, 2.320, FLOOR_TOP),
        (COAT, "玄关衣帽柜", "STUDY_entry_storage", coat_east, 1.724, 0.541, 2.290, 0.0),
    ):
        old = scene.objects[placeholder]
        center = old.location.y
        if asset == UTILITY:
            center = (walls["bath_north"][0] + walls["utility_north"][0]) / 2
        bpy.data.objects.remove(old, do_unlink=True)
        place_new(asset, cabinet(prefix, width, depth, height, asset == COAT),
                  Vector((wall_x - depth / 2 - 0.008, center, floor)), -pi / 2)

    linen = room_material("玄关_乳白磨砂导光", (0.89, 0.83, 0.69), 0.68)
    shade_shader = linen.node_tree.nodes.get("Principled BSDF")
    shade_shader.inputs["Emission Color"].default_value = (1.0, 0.78, 0.55, 1.0)
    shade_shader.inputs["Emission Strength"].default_value = 1.8
    metal = room_material("玄关_吸顶灯暖锡", (0.46, 0.42, 0.34), 0.46, 0.37)
    for x, y, watts in ((8.58, 1.18, 43), (8.52, 3.10, 40)):
        cylinder("玄关_吸顶灯安装座", (x, y, 2.970), 0.132, 0.055, metal)
        cylinder("玄关_吸顶灯乳白罩", (x, y, 2.943), 0.122, 0.020, linen)
        area_light("玄关_暖白吸顶灯", (x, y, 2.925), (x, y, 0), watts, 0.36, (1.0, 0.88, 0.76))

    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["entry-storage"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)


def render_glb(asset, render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / asset / f"{asset}.glb"))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("储物柜回导照明")
    scene.world.color = (0.27, 0.27, 0.27)
    # 回导检查中移开封闭门板及拉手，显露层板、隔板和挂杆。
    for obj in scene.objects:
        if any(f"_{part}" in obj.name for part in ("层板区", "长柄区", "衣帽区", "鞋区", "上柜")):
            obj.hide_render = True
    area_light("储物柜回导主光", (1.3, -3.6, 3.0), (0, 0, 1.23), 240, 2.55, (1.0, 0.97, 0.93))
    area_light("储物柜回导侧光", (-2.8, -0.5, 2.0), (0, 0, 1.20), 110, 1.8, (1, 1, 1))
    camera = scene_camera(scene, "storage-cutaway", (2.10, -4.2, 2.55), (0, 0, 1.15), 45)
    camera.data.type, camera.data.ortho_scale = "ORTHO", 2.64
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = (900, 1060)
    name = "utility-storage-glb" if asset == UTILITY else "entry-storage-glb"
    scene.render.filepath = str(render_dir / f"{name}.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "utility-folding/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "utility-and-entry-storage/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    add_storage(source, output)
    scene = bpy.context.scene
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in VIEWS:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    for asset in (UTILITY, COAT):
        render_glb(asset, args.renders.resolve())


if __name__ == "__main__":
    main()
