"""制作独立的微波炉、双槽烤面包机和安装式吸顶灯。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s001_whitebox import HEIGHT
from build_s003_bedroom import STAGES
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_counter_seating_and_doors import hinge
from build_s003_kitchen_props import lathe, rod
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material
from build_s003_reusable_openings import parent_parts, rectangle
from build_s003_table_setting import place_repeated

MICROWAVE, TOASTER, CEILING_LIGHT = "A189", "A190", "A191"
VIEWS = {
    "kitchen-small-appliances": ((8.24, 5.66, 1.54), (9.33, 5.37, 1.04), 36),
    "bathroom-ceiling-light": ((6.58, 1.31, 1.67), (5.58, 1.40, 2.98), 33),
}


def microwave_screen(material):
    x_range, z_range, y = (-0.195, 0.104), (0.053, 0.252), -0.159
    vertices, faces = [], []
    for axis, steps in ((0, 125), (2, 84)):
        anchor = x_range if axis == 0 else z_range
        for i in range(1, steps):
            center = anchor[0] + i * (anchor[1] - anchor[0]) / steps
            narrow = (center - 0.00024, center + 0.00024)
            xs, zs = (narrow, z_range) if axis == 0 else (x_range, narrow)
            depth = y - axis * 0.00010
            first = len(vertices)
            vertices.extend(((xs[0], depth, zs[0]), (xs[1], depth, zs[0]),
                             (xs[1], depth, zs[1]), (xs[0], depth, zs[1])))
            faces.append(tuple(range(first, first + 4)))
    screen = mesh_object("微波炉_门内屏蔽网", vertices, faces, [material])
    uv = screen.data.uv_layers.new(name="屏蔽网UV")
    for loop in screen.data.loops:
        x, _, z = vertices[loop.vertex_index]
        uv.data[loop.index].uv = ((x - x_range[0]) / 0.299, (z - z_range[0]) / 0.199)
    return screen


def microwave():
    finish = room_material("微波炉_骨白钢板涂层", (0.69, 0.665, 0.60), 0.41, 0.14)
    interior = room_material("微波炉_暖灰易清洁内胆", (0.40, 0.41, 0.37), 0.42, 0.11)
    charcoal = room_material("微波炉_石墨密封框和面板", (0.058, 0.060, 0.054), 0.36)
    glass = room_material("微波炉_茶灰观察玻璃", (0.13, 0.145, 0.126), 0.13)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.50
    plate = room_material("微波炉_旋转盘钠钙玻璃", (0.80, 0.89, 0.83), 0.14)
    plate.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
    steel = satin_steel(MICROWAVE)
    panel_light = room_material("微波炉_浅灰键面符号", (0.50, 0.54, 0.53), 0.52)
    shell = rectangle("微波炉_外壳折边围框", (0, 0.009, 0.154), 0.464, 0.273, 0.305, 0.012, finish)
    shell.append(rounded_box("微波炉_独立背盖", (0, 0.165, 0.154), (0.462, 0.020, 0.271), 0.006, finish))
    shell.extend(rectangle("微波炉_五面连续加热舱", (-0.034, -0.003, 0.154), 0.349, 0.237, 0.287, 0.009, interior))
    shell.append(rounded_box("微波炉_内胆背面", (-0.034, 0.135, 0.154), (0.339, 0.014, 0.227), 0.008, interior))
    shell.append(rounded_box("微波炉_磁控管侧舱围护", (0.174, 0.011, 0.149), (0.097, 0.302, 0.247), 0.009, charcoal))
    shell.extend(rectangle("微波炉_内腔前止口", (-0.036, -0.148, 0.152), 0.377, 0.262, 0.013, 0.022, charcoal))
    shell.append(cylinder("微波炉_三角传动轴盖", (-0.034, -0.007, 0.050), 0.026, 0.019, charcoal, vertices=36))
    gl = lathe("微波炉_独立凸边玻璃转盘", plate, [(0.087, 0.060), (0.112, 0.060), (0.117, 0.063),
                 (0.117, 0.068), (0.112, 0.072), (0.109, 0.070), (0.103, 0.066), (0.077, 0.066)], 0.060, 0.066)
    gl.location = (-0.034, -0.007, 0)
    shell.append(gl)
    for x in (-0.188, 0.183):
        for y in (-0.108, 0.128):
            shell.append(cylinder("微波炉_耐温防滑脚垫", (x, y, 0.011), 0.013, 0.022, charcoal, vertices=24))
    shell.append(rounded_box("微波炉_操控盖板", (0.186, -0.152, 0.154), (0.091, 0.027, 0.271), 0.004, finish))
    shell.append(rounded_box("微波炉_暗色待机显示窗", (0.185, -0.168, 0.231), (0.060, 0.004, 0.029), 0.0025, charcoal))
    for z, radius in ((0.148, 0.0215), (0.078, 0.0157)):
        dial = cylinder("微波炉_实体编码旋钮", (0.185, -0.175, z), radius, 0.023, steel, vertices=48)
        dial.rotation_euler.x = pi / 2
        shell.append(dial)
        shell.append(rounded_box("微波炉_刻度定位线", (0.185, -0.187, z + radius * 0.53),
                                 (0.002, 0.0015, 0.009), 0.0006, panel_light))
    for i in range(8):
        shell.append(rounded_box("微波炉_侧板散热百叶", (0.232, 0.056 + 0.010 * i, 0.213),
                                 (0.003, 0.006, 0.063), 0.001, charcoal))
    pivot = hinge("微波炉_门左铰轴", (-0.225, -0.166, 0))
    closing = rectangle("微波炉_独立门扇边框", (-0.046, -0.164, 0.153), 0.366, 0.269, 0.031, 0.034, charcoal)
    closing.append(rounded_box("微波炉_连续观察玻璃", (-0.046, -0.171, 0.154), (0.302, 0.008, 0.205), 0.004, glass))
    closing.append(microwave_screen(charcoal))
    closing.extend(rectangle("微波炉_内门屏蔽层止口", (-0.057, -0.154, 0.153), 0.290, 0.214, 0.006, 0.013, steel))
    for y, z in ((-0.186, 0.072), (-0.186, 0.235)):
        closing.append(rod("微波炉_竖握把端座", (0.104, y + 0.011, z), (0.104, y - 0.023, z), 0.0085, steel))
    closing.append(rod("微波炉_独立圆杆握把", (0.104, -0.209, 0.064), (0.104, -0.209, 0.244), 0.009, steel))
    return [*shell, parent_parts(pivot, closing), *closing]


def toaster():
    enamel = room_material("面包机_低饱和苔绿外壳", (0.185, 0.246, 0.185), 0.38, 0.15)
    polymer = room_material("面包机_耐热黑色下圈", (0.064, 0.068, 0.058), 0.51)
    heating = room_material("面包机_镍铬发热丝冷态", (0.24, 0.179, 0.135), 0.47, 0.70)
    steel = satin_steel(TOASTER)
    parts = [rounded_box("面包机_包底隔热脚座", (0, 0, 0.020), (0.298, 0.165, 0.025), 0.011, polymer)]
    body = rounded_box("面包机_整形涂装外壳", (0, 0, 0.096), (0.303, 0.172, 0.145), 0.025, enamel)
    cap = rounded_box("面包机_拉丝钢冲孔顶板", (0, 0, 0.163), (0.289, 0.154, 0.018), 0.007, steel)
    parts.extend((body, cap))
    for y in (-0.037, 0.037):
        cutter = rounded_box("面包槽加工体", (0, y, 0.137), (0.244, 0.039, 0.103), 0.007, polymer)
        bpy.context.view_layer.objects.active = cutter
        bpy.ops.object.modifier_apply(modifier=cutter.modifiers[0].name)
        for section in (body, cap):
            cut = section.modifiers.new("加工真实贯通槽口", "BOOLEAN")
            cut.object = cutter
            bpy.context.view_layer.objects.active = section
            bpy.ops.object.modifier_apply(modifier=cut.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
        for nudge in (-0.017, 0.017):
            parts.append(rounded_box("面包机_独立槽内反射钢片", (0, y + nudge, 0.126), (0.234, 0.004, 0.071), 0.0018, steel))
            for z in (0.108, 0.121, 0.134, 0.146):
                parts.append(rod("面包机_槽内发热丝", (-0.108, y + nudge * 0.85, z),
                                 (0.108, y + nudge * 0.85, z), 0.0009, heating))
        for x in (-0.087, -0.043, 0, 0.043, 0.087):
            parts.append(rod("面包机_升降承托杆", (x, y - 0.015, 0.092), (x, y + 0.015, 0.092), 0.0017, steel))
    parts.append(rounded_box("面包机_可抽拉集屑盘面", (0.148, 0, 0.036), (0.014, 0.116, 0.015), 0.004, steel))
    parts.append(rounded_box("面包机_弹臂滑行导槽", (0.151, 0, 0.123), (0.005, 0.011, 0.060), 0.003, polymer))
    parts.append(rod("面包机_弹臂轴", (0.150, 0, 0.144), (0.169, 0, 0.144), 0.004, steel))
    parts.append(rounded_box("面包机_隔热压杆头", (0.172, 0, 0.144), (0.018, 0.041, 0.012), 0.005, polymer))
    dial = cylinder("面包机_火候旋钮", (0.154, 0.042, 0.074), 0.013, 0.018, steel, vertices=40)
    dial.rotation_euler.y = pi / 2
    parts.append(dial)
    for x in (-0.113, 0.113):
        for y in (-0.057, 0.057):
            parts.append(cylinder("面包机_四只橡胶脚垫", (x, y, 0.0047), 0.011, 0.0094, polymer, vertices=24))
    return parts


def ceiling_light():
    rim = room_material("吸顶灯_哑光陶白铝圈", (0.72, 0.705, 0.645), 0.40, 0.09)
    lens = room_material("吸顶灯_奶白蛋白扩散罩", (0.84, 0.78, 0.65), 0.27)
    shader = lens.node_tree.nodes["Principled BSDF"]
    shader.inputs["Emission Color"].default_value = (1, 0.87, 0.67, 1)
    shader.inputs["Emission Strength"].default_value = 1.35
    back = cylinder("吸顶灯_背部安装罐", (0, 0, -0.007), 0.128, 0.014, rim, vertices=72)
    bezel = lathe("吸顶灯_旋扣边框", rim, [(0.113, -0.044), (0.133, -0.043), (0.141, -0.034),
                  (0.141, -0.023), (0.138, -0.015), (0.125, -0.005), (0.118, -0.005), (0.117, -0.034)], -0.044, -0.034)
    cover = lathe("吸顶灯_前侧连续弧形漫射罩", lens, [(0.041, -0.049), (0.100, -0.047),
                  (0.118, -0.043), (0.121, -0.038), (0.119, -0.036), (0.109, -0.035)], -0.049, -0.035)
    return [back, bezel, cover]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "kitchen-modules/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "small-appliances/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    top = scene.objects["A123"].location.z
    place_new(MICROWAVE, microwave(), (9.46, 5.05, top), -pi / 2)
    place_new(TOASTER, toaster(), (9.55, 5.69, top), pi)
    lights = [obj for obj in scene.objects if obj.type == "LIGHT" and obj.name.startswith(
        ("卫浴_吸顶灯", "家政间_吸顶灯", "玄关_暖白吸顶灯"))]
    if not lights:
        raise ValueError("未找到现有吸顶灯的光源位置")
    placements = [(Vector((light.location.x, light.location.y, HEIGHT)), 0) for light in lights]
    place_repeated(CEILING_LIGHT, ceiling_light(), placements)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-small-appliances"]
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
