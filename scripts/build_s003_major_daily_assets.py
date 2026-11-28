"""制作细嘴壶、两门冰箱、插座和墙壁开关的可复用首款。"""

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
from build_s003_bookshelf_study import white_oak_material
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe, rod
from build_s003_lived_in import ring_surface
from build_s003_living import RENDERS, cylinder, place_new, room_material

KETTLE, FRIDGE, OUTLET, SWITCH = ("A170", "A171", "A172", "A173")
VIEWS = {
    "kitchen-refrigerator": ((6.12, 7.37, 1.53), (4.49, 9.37, 1.06), 40),
    "kitchen-gooseneck": ((8.34, 6.11, 1.46), (9.46, 6.58, 1.04), 54),
    "entry-wall-switch": ((7.81, 1.25, 1.40), (7.06, 1.73, 1.13), 52),
}


def kettle():
    enamel = room_material("细嘴壶_石墨蓝搪瓷", (0.098, 0.137, 0.143), 0.28, 0.16)
    steel = satin_steel(KETTLE)
    wood, _ = white_oak_material("细嘴壶_隔热橡木握柄", "WoodUV")
    profile = [(0.042, 0), (0.066, 0), (0.076, 0.004), (0.080, 0.014), (0.081, 0.061),
               (0.076, 0.114), (0.072, 0.126), (0.068, 0.131), (0.063, 0.131),
               (0.062, 0.127), (0.068, 0.113), (0.076, 0.059), (0.077, 0.018), (0.066, 0.009), (0.047, 0.009)]
    body = lathe("细嘴壶_内外连续搪瓷壶身", enamel, profile, 0, 0.009)
    lid = lathe("细嘴壶_独立圆盖和环缘", enamel, [(0.035, 0.127), (0.057, 0.127), (0.064, 0.131), (0.064, 0.136),
                (0.054, 0.140), (0.039, 0.142), (0.023, 0.143)], 0.127, 0.143)
    knob = cylinder("细嘴壶_隔热盖钮", (0, 0, 0.150), 0.013, 0.015, wood)
    path = [(0.072, 0.029, 0.014), (0.087, 0.034, 0.012), (0.101, 0.046, 0.010),
            (0.107, 0.067, 0.0084), (0.109, 0.093, 0.0074), (0.116, 0.119, 0.0065),
            (0.131, 0.143, 0.0057), (0.150, 0.155, 0.0050), (0.173, 0.162, 0.0048)]
    outer, bore = [], []
    for row, (x, z, radius) in enumerate(path):
        before, after = path[max(0, row - 1)], path[min(row + 1, len(path) - 1)]
        direction = Vector((after[0] - before[0], 0, after[1] - before[1])).normalized()
        vector = Vector((0, 1, 0))
        cross = direction.cross(vector)
        points = [vector * cos(tau * i / 24) + cross * sin(tau * i / 24) for i in range(24)]
        outer.append([Vector((x, 0, z)) + radius * p for p in points])
        bore.append([Vector((x, 0, z)) + (radius - 0.0011) * p for p in points])
    spout = ring_surface("细嘴壶_真空腔渐缩鹅颈管", outer + list(reversed(bore)), [steel], closed_rows=True)
    grip_path = [(-0.065, 0, 0.114), (-0.089, 0, 0.129), (-0.112, 0, 0.126), (-0.134, 0, 0.107),
                 (-0.139, 0, 0.079), (-0.128, 0, 0.052), (-0.111, 0, 0.039), (-0.077, 0, 0.033)]
    grip = tube("细嘴壶_独立弧形木握柄", grip_path, 0.009, wood, sides=20)
    # 橡木节点使用显式命名 UV。
    grip.data.uv_layers.active.name = "WoodUV"
    smooth = grip.modifiers.new("握柄连续圆弧", "SUBSURF")
    smooth.levels = 2
    return [body, lid, knob, grip, spout,
            rod("细嘴壶_上握柄座", (-0.066, 0, 0.115), (-0.087, 0, 0.127), 0.010, steel),
            rod("细嘴壶_下握柄座", (-0.076, 0, 0.033), (-0.104, 0, 0.038), 0.009, steel)]


def refrigerator():
    steel = satin_steel(FRIDGE)
    shell = room_material("冰箱_浅砂灰细纹烤漆", (0.54, 0.51, 0.445), 0.42, 0.12)
    inside = room_material("冰箱_暖白热成型内胆", (0.74, 0.77, 0.71), 0.41)
    rubber = room_material("冰箱_灰色磁吸密封胶条", (0.15, 0.165, 0.156), 0.69)
    glass = room_material("冰箱_略青透明钢化搁板", (0.79, 0.94, 0.88), 0.14)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.95
    parts = []

    def panel(name, xyz, size, material, radius=0.005):
        part = rounded_box("冰箱_" + name, xyz, size, radius, material)
        parts.append(part)
        return part

    for x in (-0.285, 0.285):
        panel("保温侧板", (x, 0.045, 0.920), (0.045, 0.549, 1.758), shell, 0.011)
        panel("白色侧内胆", (x * 0.900, 0.037, 0.925), (0.009, 0.514, 1.690), inside)
    panel("压缩机后背和箱后板", (0, 0.293, 0.920), (0.524, 0.052, 1.752), shell, 0.010)
    panel("冷风后内壁", (0, 0.263, 0.922), (0.520, 0.012, 1.686), inside)
    for z in (0.059, 0.625, 1.777):
        panel("隔温横板", (0, 0.044, z), (0.538, 0.545, 0.046), shell)
        panel("内胆横缘", (0, 0.037, z + (0.027 if z < 1.7 else -0.027)), (0.516, 0.520, 0.010), inside)
    for z in (0.94, 1.22, 1.51):
        panel("层架透明面", (0, 0.060, z), (0.502, 0.426, 0.006), glass, 0.002)
        for y in (-0.152, 0.26):
            panel("玻璃层架托条", (0, y, z), (0.511, 0.018, 0.013), inside, 0.003)
    for z in (0.115, 0.355, 0.686):
        panel("抽屉滑板", (0, 0.048, z), (0.484, 0.432, 0.022), inside)
        panel("抽面浅青挡板", (0, -0.160, z + 0.078), (0.475, 0.018, 0.166), glass, 0.009)
        panel("抽屉内收握沿", (0, -0.164, z + 0.158), (0.477, 0.031, 0.016), inside)
    for x in (-0.226, 0.226):
        for y in (-0.166, 0.232):
            parts.append(cylinder("冰箱_落地调平脚", (x, y, 0.018), 0.023, 0.036, rubber))

    for number, bottom, height in [(1, 0.046, 0.570), (2, 0.623, 1.174)]:
        hinge = bpy.data.objects.new(f"冰箱_{number}号门左铰轴", None)
        bpy.context.scene.collection.objects.link(hinge)
        hinge.location = (-0.284, -0.252, bottom)
        parts.append(hinge)
        center = bottom + height / 2
        moving = [panel("独立烤漆门", (0, -0.266, center), (0.611, 0.066, height), shell, 0.018),
                  panel("门背内板", (0, -0.225, center), (0.538, 0.026, height - 0.055), inside, 0.008)]
        for x in (-0.269, 0.269):
            moving.append(panel("门封竖边", (x, -0.226, center), (0.012, 0.009, height - 0.041), rubber, 0.003))
        for z in (bottom + 0.019, bottom + height - 0.019):
            moving.append(panel("门封横边", (0, -0.226, z), (0.542, 0.009, 0.012), rubber, 0.003))
        handle = bottom + height - 0.095 if number == 1 else bottom + 0.117
        moving.extend((panel("门把底座", (0.224, -0.303, handle), (0.027, 0.027, 0.131), rubber),
                       panel("独立拉丝细把手", (0.224, -0.323, handle), (0.021, 0.026, 0.157), steel, 0.008)))
        for z in ((bottom + 0.12,) if number == 1 else (bottom + 0.19, bottom + 0.53, bottom + 0.89)):
            moving.extend((panel("门架底盘", (0, -0.177, z), (0.464, 0.078, 0.016), inside),
                           panel("门架防掉落沿", (0, -0.136, z + 0.043), (0.466, 0.012, 0.083), glass)))
        bpy.context.view_layer.update()
        for part in moving:
            world = part.matrix_world.copy()
            part.parent = hinge
            part.matrix_world = world
    return parts


def plate(asset, contact):
    face = room_material(f"{asset}_微纹米白面板", (0.73, 0.713, 0.656), 0.47)
    dark = room_material(f"{asset}_孔槽和分缝", (0.14, 0.139, 0.125), 0.62)
    metal = room_material(f"{asset}_暗灰固定件", (0.38, 0.39, 0.36), 0.45, 0.62)
    frame = rounded_box(f"{asset}_贴墙圆方独立面板", (0, -0.006, 0), (0.086, 0.012, 0.086), 0.0035, face)
    if contact:
        holes = ((-0.011, 0.021, 0), (0.011, 0.021, 0), (0, -0.001, 0),
                 (-0.013, -0.019, -28), (0.013, -0.019, 28))
        pieces = [frame]
        # 槽为真实网格凹口，暗色填片位于面板内部。
        for x, z, tilt in holes:
            die = rounded_box("插座临时孔刀", (x, -0.011, z), (0.0028, 0.008, 0.0094), 0.00065, dark)
            die.rotation_euler.y = radians(tilt)
            cut = frame.modifiers.new("真实插口", "BOOLEAN")
            cut.operation, cut.object = "DIFFERENCE", die
            bpy.context.view_layer.objects.active = frame
            bpy.ops.object.modifier_apply(modifier=cut.name)
            bpy.data.objects.remove(die, do_unlink=True)
            liner = rounded_box("插座_孔内暗衬", (x, -0.0085, z), (0.0031, 0.0012, 0.0096), 0.0007, dark)
            liner.rotation_euler.y = radians(tilt)
            pieces.append(liner)
        return pieces
    rocker = rounded_box("开关_独立微倾翘板", (0, -0.0123, 0), (0.049, 0.0045, 0.059), 0.0018, face)
    rocker.rotation_euler.x = radians(2.5)
    return [frame, rounded_box("开关_环形压边与暗缝", (0, -0.011, 0), (0.053, 0.003, 0.063), 0.0025, dark), rocker,
            rounded_box("开关_定位标记", (0, -0.016, -0.019), (0.010, 0.0014, 0.0014), 0.0006, metal)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "lived-in/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "major-daily-assets/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    place_new(KETTLE, kettle(), (9.49, 6.57, scene.objects["A123"].location.z), radians(-15))
    place_new(FRIDGE, refrigerator(), (4.41, 9.452, 0.002))
    socket = scene.objects["起居插座"]
    position = Vector((0.2, socket.location.y, socket.location.z))
    bpy.data.objects.remove(socket, do_unlink=True)
    place_new(OUTLET, plate(OUTLET, contact=True), position, pi / 2)
    place_new(SWITCH, plate(SWITCH, contact=False), (7.06, 1.73, 1.14), pi / 2)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-refrigerator"]
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
