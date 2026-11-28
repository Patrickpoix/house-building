"""发布蒸汽熨斗与壁挂折叠熨衣板，在家政间检查收放净空。"""

import argparse
from math import atan2, cos, hypot, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_counter_seating_and_doors import hinge
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import rod
from build_s003_lived_in import ring_surface
from build_s003_living import LIBRARY, RENDERS, cylinder, place_new, room_material, textile
from build_s003_reusable_openings import parent_parts

IRON, BOARD = "A196", "A197"
BOARD_AXIS = (0, -0.084, 0.065)
STRUT_AXIS = (-0.113, 0.531)
STRUT_RECEIVER = (-0.060, -0.115)
STRUT_SIDE = 0.101
STRUT_RUN = STRUT_RECEIVER[0] - (BOARD_AXIS[1] - (STRUT_AXIS[1] - BOARD_AXIS[2]))
STRUT_DROP = BOARD_AXIS[2] + STRUT_AXIS[0] - BOARD_AXIS[1] - STRUT_RECEIVER[1]
STRUT_ANGLE = -atan2(STRUT_DROP, STRUT_RUN)
VIEWS = {
    "utility-steam-iron": ((6.05, 3.60, 1.41), (5.59, 2.91, 1.02), 44),
    "utility-ironing-board": ((5.70, 3.78, 1.45), (4.14, 3.54, 1.28), 31),
    "utility-ironing-board-open": ((5.51, 3.18, 1.30), (4.57, 3.53, 0.85), 32),
}


def sole_parts(materials):
    steel, skin, tank = materials
    outline = [(-0.068, 0.096), (-0.064, 0.058), (-0.054, 0.012), (-0.041, -0.034),
               (-0.027, -0.071), (-0.010, -0.111), (-0.002, -0.132), (0.002, -0.132),
               (0.010, -0.111), (0.027, -0.071), (0.041, -0.034), (0.054, 0.012),
               (0.064, 0.058), (0.068, 0.096), (0.061, 0.111), (0.048, 0.115),
               (-0.048, 0.115), (-0.061, 0.111)]
    parts = []
    sections = (
        ("蒸汽熨斗_独立压合底板", steel, ((0.93, 0, 0.001), (1, 0, 0.005), (1, 0, 0.012), (0.97, 0, 0.015))),
        ("蒸汽熨斗_隔热外壳", skin, ((0.96, 0, 0.014), (0.97, 0, 0.024), (0.86, 0.006, 0.053), (0.73, 0.015, 0.061))),
        ("蒸汽熨斗_半透储水壶", tank, ((0.82, 0.007, 0.050), (0.81, 0.008, 0.062),
                                        (0.68, 0.016, 0.080), (0.61, 0.027, 0.087))),
    )
    for name, material, profile in sections:
        rings = [[(x * scale, y * scale + shift, z) for x, y in outline] for scale, shift, z in profile]
        obj = ring_surface(name, rings, [material], (True, True))
        edge = obj.modifiers.new("注塑件连续圆边", "BEVEL")
        edge.width, edge.segments = 0.0023, 3
        obj.modifiers.new("连续面法线", "WEIGHTED_NORMAL").keep_sharp = True
        parts.append(obj)
    return parts


def steam_iron():
    steel = satin_steel(IRON)
    light = room_material("蒸汽熨斗_软白耐热外壳", (0.72, 0.696, 0.612), 0.46)
    tank = room_material("蒸汽熨斗_半透蓝绿色水箱", (0.122, 0.257, 0.227), 0.31)
    tank.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.31
    rubber = room_material("蒸汽熨斗_灰青弹性握套", (0.12, 0.17, 0.148), 0.66)
    parts = sole_parts((steel, light, tank))
    profile = [(0, -0.070, 0.056), (0, -0.069, 0.068), (0, -0.058, 0.104), (0, -0.040, 0.128),
               (0, -0.011, 0.136), (0, 0.030, 0.137), (0, 0.065, 0.131), (0, 0.091, 0.107),
               (0, 0.098, 0.078), (0, 0.096, 0.044)]
    frame = tube("蒸汽熨斗_弓形握把框架", profile, 0.014, light, sides=20)
    frame.modifiers.new("握持转角平顺", "SUBSURF").levels = 2
    for vertex in frame.data.vertices:
        vertex.co.x *= 1.58
    grip = tube("蒸汽熨斗_加厚防滑握套", [(0, -0.039, 0.131), (0, -0.014, 0.136),
                   (0, 0.029, 0.138), (0, 0.064, 0.132)], 0.010, rubber, sides=24)
    for vertex in grip.data.vertices:
        vertex.co.x *= 1.8
    parts.extend((frame, grip))
    parts.append(cylinder("蒸汽熨斗_独立温控转盘", (0, 0.015, 0.087), 0.022, 0.014, rubber, vertices=40))
    parts.append(rounded_box("蒸汽熨斗_喷雾按键", (0, -0.047, 0.131), (0.020, 0.017, 0.010), 0.004, tank))
    parts.append(cylinder("蒸汽熨斗_前口独立水塞", (0, -0.070, 0.068), 0.014, 0.006, light, vertices=32))
    parts.append(rod("蒸汽熨斗_应力缓冲电缆接头", (0, 0.092, 0.073), (0, 0.119, 0.080), 0.007, rubber))
    coil = [(0, 0.115, 0.080), (0.014, 0.144, 0.082), (0.052, 0.175, 0.058),
            (0.084, 0.199, 0.028), (0.119, 0.203, 0.0055)]
    for i in range(148):
        t = i / 147
        angle = 1.19 + tau * 2.88 * t
        coil.append((0.094 + (0.068 + 0.016 * t) * cos(angle),
                     0.140 + (0.067 + 0.019 * t) * sin(angle), 0.0055 + 0.014 * t))
    end = Vector(coil[-1])
    tail = (end - Vector(coil[-3])).normalized()
    tail.z = 0
    tail.normalize()
    side = Vector((-tail.y, tail.x, 0))
    base = end + 0.025 * tail
    base.z = 0.0115
    coil.extend((end + 0.012 * tail, base))
    cable = tube("蒸汽熨斗_盘绕织覆电源线", coil, 0.0038, rubber)
    cable.modifiers.new("入线段缓弯", "SUBSURF").levels = 1
    plug = rounded_box("蒸汽熨斗_双脚插头绝缘壳", base, (0.034, 0.041, 0.023), 0.005, rubber)
    plug.rotation_euler.z = atan2(tail.y, tail.x) - pi / 2
    parts.extend((cable, plug))
    for sign in (-1, 1):
        pin = base + tail * 0.017 + sign * side * 0.0088
        parts.append(rod("蒸汽熨斗_双脚插头金属插销", pin, pin + 0.016 * tail, 0.0024, steel))
    for y in (-0.039, -0.015, 0.010, 0.035, 0.061, 0.084):
        spread = 0.025 + (y + 0.04) * 0.11
        for side in (-1, 1):
            hole = cylinder("蒸汽熨斗_汽孔切削体", (side * spread, y, 0.0005), 0.0026, 0.009, rubber, vertices=24)
            bpy.context.view_layer.objects.active = parts[0]
            cut = parts[0].modifiers.new("冲压底板蒸汽孔", "BOOLEAN")
            cut.operation, cut.solver, cut.object = "DIFFERENCE", "EXACT", hole
            bpy.ops.object.modifier_apply(modifier=cut.name)
            bpy.data.objects.remove(hole, do_unlink=True)
    return parts


def ironing_board():
    fabric = textile("熨衣板_雾蓝可拆纯棉罩", (0.177, 0.272, 0.310))
    binding = textile("熨衣板_原色棉滚边", (0.46, 0.42, 0.35))
    deck = room_material("熨衣板_深灰冲压板骨架", (0.16, 0.173, 0.16), 0.48, 0.39)
    finish = room_material("熨衣板_陶白墙托烤漆", (0.62, 0.603, 0.538), 0.42, 0.15)
    metal = room_material("熨衣板_镀锌铰轴", (0.42, 0.42, 0.38), 0.34, 0.71)
    edge = ((0.155, 0.048), (0.170, 0.051), (0.177, 0.059), (0.180, 0.074), (0.180, 0.550),
            (0.178, 0.591), (0.173, 0.637), (0.164, 0.696), (0.153, 0.761), (0.138, 0.837),
            (0.121, 0.909), (0.103, 0.967), (0.084, 1.003), (0.065, 1.027), (0.046, 1.042),
            (0.025, 1.049), (0.010, 1.051))
    outline = [(-x, z) for x, z in edge] + [(0, 1.052)] + list(reversed(edge))
    rings = [[(scale * x, depth, 0.55 + scale * (z - 0.55)) for x, z in reversed(outline)]
             for scale, depth in ((0.984, -0.073), (1.0, -0.079), (1.0, -0.098), (0.979, -0.104))]
    panel = ring_surface("熨衣板_微拱棉罩与连续侧边", rings, [fabric, binding], (True, True))
    for face in panel.data.polygons:
        face.material_index = int(len(face.vertices) == 4)
        for index in face.loop_indices:
            x, y, z = panel.data.vertices[panel.data.loops[index].vertex_index].co
            panel.data.uv_layers.active.data[index].uv = (x * 8 + 0.3, z * 8 + y * 3)
    smoothing = panel.modifiers.new("圆顺耐磨棉边", "BEVEL")
    smoothing.width, smoothing.segments = 0.005, 3
    fixed = [rounded_box("熨衣板_墙装竖向承载背板", (0, -0.016, 0.157), (0.275, 0.032, 0.614), 0.010, finish)]
    moving = [panel]
    for x in (-STRUT_SIDE, STRUT_SIDE):
        fixed.append(rounded_box("熨衣板_下部铰轴承座", (x, -0.050, 0.065), (0.05, 0.076, 0.065), 0.007, finish))
        moving.append(rounded_box("熨衣板_背面承力纵筋", (x, -0.118, 0.468), (0.024, 0.029, 0.824), 0.0045, deck))
        moving.append(rounded_box("熨衣板_轴套与板下支架", (x, -0.098, 0.070), (0.044, 0.038, 0.072), 0.007, deck))
        receiver_y, receiver_z = STRUT_RECEIVER
        receiver_x = x + (0.025 if x > 0 else -0.025)
        fixed.append(rounded_box("熨衣板_可锁斜撑墙座", (receiver_x, -0.044, receiver_z - 0.012),
                                 (0.048, 0.042, 0.021), 0.004, finish))
        for shift in (-0.019, 0.019):
            fixed.append(rounded_box("熨衣板_墙座限位耳", (receiver_x + shift, receiver_y, receiver_z),
                                     (0.009, 0.026, 0.030), 0.003, deck))
        for z in (-0.115, 0.406):
            screw = cylinder("熨衣板_锁墙螺钉", (x, -0.029, z), 0.007, 0.004, metal, vertices=30)
            screw.rotation_euler.x = pi / 2
            fixed.append(screw)
    fixed.append(rod("熨衣板_横向贯穿铰轴", (-0.149, -0.084, 0.065), (0.149, -0.084, 0.065), 0.011, metal))
    fixed.append(rounded_box("熨衣板_收拢位置防倾锁扣", (0, -0.065, 0.752), (0.042, 0.119, 0.036), 0.006, finish))
    fixed.append(rounded_box("熨衣板_锁扣墙座", (0, -0.010, 0.752), (0.057, 0.020, 0.093), 0.007, finish))
    pivot = hinge("熨衣板_放下轴", BOARD_AXIS)
    moving.append(rod("熨衣板_底部横梁", (-0.137, -0.103, 0.13), (0.137, -0.103, 0.13), 0.011, deck))
    struts = []
    length = hypot(STRUT_RUN, STRUT_DROP)
    for side, label in ((-1, "左"), (1, "右")):
        x = (STRUT_SIDE + 0.025) * side
        y, z = STRUT_AXIS
        controller = hinge(f"熨衣板_{label}斜撑轴", (x, y, z))
        shaft = rod("熨衣板_折藏斜撑管", (x, y, z), (x, y, z - length), 0.006, metal)
        tip = rounded_box("熨衣板_斜撑止滑脚", (x, y, z - length), (0.015, 0.015, 0.019), 0.004, deck)
        parent_parts(controller, [shaft, tip])
        struts.extend((shaft, tip))
        moving.extend((controller, rod("熨衣板_斜撑转轴", (x - side * 0.022, y, z),
                                        (x + side * 0.008, y, z), 0.008, metal)))
    return [*fixed, parent_parts(pivot, moving), *moving, *struts]


def show_board_open(scene):
    closed = scene.objects[BOARD]
    with bpy.data.libraries.load(str(LIBRARY / BOARD / f"{BOARD}.blend")) as (_, destination):
        destination.collections = [BOARD]
    opened = destination.collections[0]
    for part in opened.objects:
        if part.name.startswith("熨衣板_放下轴"):
            part.rotation_euler.x = pi / 2
        if part.name.startswith(("熨衣板_左斜撑轴", "熨衣板_右斜撑轴")):
            part.rotation_euler.x = STRUT_ANGLE
    closed.instance_collection = opened
    bpy.context.view_layer.update()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bathroom-accessories/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "utility-ironing/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    at = scene.objects["A165"].location
    place_new(IRON, steam_iron(), at + Vector((0.397, 0.015, 0)), pi / 2)
    place_new(BOARD, ironing_board(), (4.063, 3.53, 0.81), pi / 2)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["utility-steam-iron"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if args.build_only:
        return
    for name in VIEWS:
        if name == "utility-ironing-board-open":
            show_board_open(scene)
        scene.camera = scene.objects[name]
        scene.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
