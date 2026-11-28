"""为玄关与起居安装可独立复用的日用品。"""

import argparse
from math import cos, pi, radians, sin, tau
from pathlib import Path
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
from build_s003_cooking_station import satin_steel
from build_s003_kitchen_everyday import tube
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material, textile, upholstered

HOOKS, MEMO, KEYS, MAT, NOTEBOOK, MIRROR = (f"A{i}" for i in range(150, 156))
VIEWS = {
    "entry-arrival-interior": ((8.66, 0.64, 1.59), (7.84, 2.90, 1.10), 22),
    "entry-bench-and-hooks": ((8.87, 2.07, 1.44), (7.23, 2.92, 1.04), 29),
    "entry-drop-zone": ((8.66, 3.10, 1.19), (9.57, 3.47, 0.89), 46),
    "entry-bookshelf-journal": ((1.02, 9.02, 1.58), (0.39, 9.30, 1.435), 57),
    "entry-doormat": ((8.55, 1.70, 0.76), (8.70, 0.55, 0.08), 37),
}


def entry_hooks():
    wood, _ = white_oak_material("玄关挂钩_圆角橡木横板", "WoodUV")
    brass = room_material("玄关挂钩_暗铜", (0.32, 0.22, 0.115), 0.37, 0.71)
    backing = board("玄关挂钩_隐藏安装板", (0, -0.010, 0), (0.525, 0.020, 0.081), wood, 0, 0.27)
    backing.modifiers[0].width = 0.006
    parts = [backing]
    for x in (-0.167, 0, 0.167):
        base = cylinder("玄关挂钩_螺纹圆座", (x, -0.024, 0.006), 0.017, 0.012, brass)
        base.rotation_euler.x = pi / 2
        path = [(x, y, z) for y, z in ((-0.026, 0.006), (-0.040, -0.007), (-0.046, -0.027),
                                      (-0.057, -0.041), (-0.071, -0.039), (-0.079, -0.028),
                                      (-0.080, -0.008), (-0.077, 0.009))]
        hook = tube("玄关挂钩_圆弯挂趾", path, 0.007, brass)
        rounding = hook.modifiers.new("铸铜转弯抛圆", "SUBSURF")
        rounding.levels = 2
        tip = cylinder("玄关挂钩_端头", (x, -0.077, 0.010), 0.010, 0.007, brass)
        parts.extend((base, hook, tip))
    return parts


def message_board():
    wood, _ = white_oak_material("留言板_橡木窄框", "WoodUV")
    magnetic = room_material("留言板_暖灰哑光磁吸钢板", (0.23, 0.22, 0.19), 0.57, 0.33)
    paper = room_material("留言板_本色卡纸", (0.68, 0.57, 0.42), 0.83)
    envelope = room_material("留言板_浅色折口信封", (0.79, 0.74, 0.61), 0.82)
    pin = room_material("留言板_松针绿磁扣", (0.14, 0.21, 0.17), 0.42)
    parts = [board("留言板_漆面与钢背板", (0, -0.007, 0), (0.431, 0.014, 0.292), magnetic, 0, 0.12)]
    for sign in (-1, 1):
        parts.extend((
            board("留言板_侧框", (sign * 0.223, -0.011, 0), (0.015, 0.022, 0.322), wood, 2, 0),
            board("留言板_横框", (0, -0.011, sign * 0.153), (0.431, 0.022, 0.016), wood, 0, 0.19),
        ))
    for x, z, w, h, angle, material in ((-0.089, -0.005, 0.118, 0.146, -5, paper),
                                      (0.059, -0.026, 0.153, 0.094, 9, envelope)):
        note = rounded_box("留言板_随手夹存纸件", (x, -0.015, z), (w, 0.002, h), 0.0007, material)
        note.rotation_euler.y = radians(angle)
        pin_head = cylinder("留言板_夹纸磁扣", (x, -0.018, z + h * 0.33), 0.005, 0.008, pin)
        pin_head.rotation_euler.x = pi / 2
        parts.extend((note, pin_head))
    return parts


def keyring():
    nickel = satin_steel(KEYS)
    bow = room_material("钥匙_深绿护片", (0.067, 0.14, 0.12), 0.43)
    ring = tube("钥匙串_双圈卷制钢环", [(0.016 * cos(t), 0.016 * sin(t), 0.0012 + 0.0022 * t / (2 * tau))
               for t in (2 * tau * i / 100 for i in range(101))], 0.0009, nickel)
    parts = [ring]
    outline = [(-0.011, -0.0046), (0.024, -0.0046), (0.030, -0.0024), (0.026, 0.0031),
               (0.021, 0.0031), (0.019, 0.0014), (0.017, 0.0014), (0.015, 0.0048),
               (0.011, 0.0048), (0.009, 0.0025), (0.006, 0.0048), (-0.011, 0.0048)]
    for angle, height in ((-18, 0.001), (45, 0.004)):
        def rotate(x, y):
            return (0.023 + x * cos(radians(angle)) - y * sin(radians(angle)),
                    0.004 + x * sin(radians(angle)) + y * cos(radians(angle)))

        points = [(*rotate(x, y), height + z) for z in (0, 0.0016) for x, y in outline]
        size = len(outline)
        faces = [tuple(reversed(range(size))), tuple(range(size, 2 * size))]
        faces.extend((i, (i + 1) % size, (i + 1) % size + size, i + size) for i in range(size))
        blade = mesh_object("钥匙_带细台阶的胚片", points, faces, [nickel])
        uv = blade.data.uv_layers.new(name="钥匙金属UV")
        for loop in blade.data.loops:
            x, y = outline[loop.vertex_index % size]
            uv.data[loop.index].uv = ((x + 0.011) / 0.041, (y + 0.0046) / 0.0094)
        edge = blade.modifiers.new("胚片边缘倒圆", "BEVEL")
        edge.width = 0.00055
        edge.segments = 3
        center = rotate(-0.014, 0)
        eye = tube("钥匙_握片贯通眼", [(center[0] + 0.007 * cos(t), center[1] + 0.007 * sin(t), height + 0.002)
                   for t in (tau * i / 36 for i in range(37))], 0.002, bow)
        parts.extend((blade, eye))
    return parts

def doormat():
    center = textile("玄关落尘垫_苔褐粗织", (0.22, 0.19, 0.13))
    edge = textile("玄关落尘垫_深褐包缝", (0.095, 0.076, 0.052))
    backing = upholstered("玄关落尘垫_平织包边底", (0, 0, 0.004), (0.74, 0.45, 0.008), edge, 0.003, repeats=(3, 2))
    pile = upholstered("玄关落尘垫_中心短绒", (0, 0, 0.0075), (0.706, 0.416, 0.006),
                      center, 0.002, repeats=(5, 4))
    for material in (center, edge):
        for node in material.node_tree.nodes:
            if node.type == "NORMAL_MAP":
                node.inputs["Strength"].default_value = 0.68
    return [backing, pile]


def travel_journal():
    cover = textile("旅行手记_松针绿书布", (0.113, 0.205, 0.163))
    paper = room_material("旅行手记_暖白压页", (0.81, 0.75, 0.61), 0.82)
    fold = textile("旅行手记_棉线束边", (0.47, 0.36, 0.22))
    parts = [rounded_box("旅行手记_连续圆书脊", (-0.071, 0, 0.012), (0.019, 0.214, 0.024), 0.008, cover)]
    for z in (0.0015, 0.022):
        parts.append(rounded_box("旅行手记_硬纸布封", (0, 0, z), (0.156, 0.218, 0.003), 0.0012, cover))
    for row in range(12):
        z = 0.0037 + row * 0.00151
        seed_angle = 0.18 * sin(row * 1.83)
        section = rounded_box("旅行手记_分帖纸芯", (0.001, 0, z), (0.147, 0.208, 0.00164), 0.0004, paper)
        section.rotation_euler.z = radians(seed_angle)
        parts.append(section)
    parts.append(rounded_box("旅行手记_闭合橡筋带", (0.054, 0, 0.024), (0.009, 0.218, 0.0019), 0.0008, fold))
    return parts


def mirror():
    wood, _ = white_oak_material("玄关镜_白橡边与挂背", "WoodUV")
    silver = room_material("玄关镜_银膜镜面", (0.92, 0.95, 0.94), 0.025, 1)
    frame = board("玄关镜_连续楔形木框", (0, -0.016, 0), (0.394, 0.032, 0.758), wood, 2, 0.20)
    frame.modifiers[0].width = 0.014
    face = rounded_box("玄关镜_带边磨砂收口的镜片", (0, -0.032, 0), (0.365, 0.003, 0.727), 0.0013, silver)
    return [frame, face]


def shelf_top(instance, name, target_z):
    candidates = (part for part in instance.instance_collection.objects if name in part.name)
    levels = (max((instance.matrix_world @ part.matrix_world @ Vector(corner)).z for corner in part.bound_box)
              for part in candidates)
    return min(levels, key=lambda z: abs(z - target_z))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "breakfast/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "entry-details/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    _, _, wall, _, _, thick, _ = next(spec for spec in WALLS if spec[0] == "bath_east")
    entry_face = wall + thick / 2
    place_new(HOOKS, entry_hooks(), (entry_face, 2.77, 1.37), pi / 2)
    place_new(MEMO, message_board(), (entry_face, 3.56, 1.46), pi / 2)
    _, _, _, _, _, _, south = next(spec for spec in WALLS if spec[0] == "south")
    left, right, _, _ = next(opening for opening in south if opening[2] == 0)
    place_new(MAT, doormat(), ((left + right) / 2, 0.553, 0))
    place_new(MIRROR, mirror(), (entry_face, 2.78, 1.99), pi / 2)
    cabinet = scene.objects["A119"]
    place_new(KEYS, keyring(), (9.53, 3.45, shelf_top(cabinet, "可调搁板", 0.79)), radians(-14))
    shelf = scene.objects["living-bookshelf"]
    place_new(NOTEBOOK, travel_journal(), (0.414, 9.33, shelf_top(shelf, "书架层板_", 1.43)), radians(-13))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["entry-bench-and-hooks"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in args.views:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
