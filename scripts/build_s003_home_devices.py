"""制作无绳吸尘器、顶装晾衣架和墙装门铃的可复用首款。"""

import argparse
from math import cos, pi, sin, tau
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
from build_s003_kitchen_props import lathe, rod
from build_s003_living import RENDERS, cylinder, place_new, room_material
from build_s003_reusable_openings import parent_parts

VACUUM, RACK, BELL = "A198", "A199", "A200"
VIEWS = {
    "utility-stick-vacuum": ((5.22, 5.25, 0.96), (4.43, 4.18, 0.58), 32),
    "utility-drying-rack": ((5.98, 3.68, 1.46), (4.75, 3.35, 2.54), 25),
    "entry-doorbell": ((9.07, -0.60, 1.44), (9.34, -0.067, 1.33), 55),
}


def vacuum_head(shell, rubber, green, steel):
    yoke = hinge("吸尘器_地刷俯仰轴", (0, 0, 0.045))
    deck = [
        rounded_box("吸尘器_滚刷上盖", (0, -0.036, 0.037), (0.244, 0.102, 0.034), 0.014, shell),
        rounded_box("吸尘器_滚刷底板前导流边", (0, -0.077, 0.014), (0.215, 0.014, 0.012), 0.004, shell),
        rounded_box("吸尘器_滚刷底板后导流边", (0, -0.024, 0.014), (0.215, 0.018, 0.012), 0.004, shell),
        rounded_box("吸尘器_地刷前防撞包胶", (0, -0.086, 0.022), (0.233, 0.009, 0.016), 0.004, rubber),
        rounded_box("吸尘器_后横向吸腔", (0, 0.012, 0.023), (0.166, 0.025, 0.032), 0.011, shell),
    ]
    axle = rod("吸尘器_独立可拆滚刷芯", (-0.103, -0.050, 0.017), (0.103, -0.050, 0.017), 0.008, rubber)
    for side in (-1, 1):
        x = side * 0.104
        deck.append(rod("吸尘器_地刷行走轮", (x - 0.008, 0.025, 0.020),
                        (x + 0.008, 0.025, 0.020), 0.020, rubber))
        deck.append(rod("吸尘器_轮面轴销", (x + side * 0.007, 0.025, 0.020),
                        (x + side * 0.009, 0.025, 0.020), 0.006, steel))
        deck.append(rounded_box("吸尘器_滚刷侧端承座", (side * 0.113, -0.039, 0.025),
                                (0.017, 0.081, 0.038), 0.007, shell))
    deck.append(axle)
    for phase in (0, pi):
        coil = [(0.198 * i / 72 - 0.099, -0.050 + 0.0105 * cos(phase + 2.7 * tau * i / 72),
                 0.017 + 0.0105 * sin(phase + 2.7 * tau * i / 72)) for i in range(73)]
        deck.append(tube("吸尘器_螺旋植毛条", coil, 0.0026, green, 8))
    joint = [rod("吸尘器_地刷支承铰管", (-0.037, 0, 0.045), (0.037, 0, 0.045), 0.012, steel),
             tube("吸尘器_活动弯颈吸管", [(0, -0.012, 0.035), (0, 0.007, 0.054), (0, 0.009, 0.076),
                 (0, 0, 0.108), (0, 0, 0.131)], 0.018, shell, 24),
             rounded_box("吸尘器_地刷拆卸锁扣", (0, -0.019, 0.112), (0.019, 0.008, 0.028), 0.003, green)]
    return [*joint, parent_parts(yoke, deck), *deck]


def stick_vacuum():
    steel = satin_steel(VACUUM)
    aluminum = room_material("吸尘器_烟灰阳极氧化铝管", (0.223, 0.245, 0.230), 0.37, 0.78)
    shell = room_material("吸尘器_石墨注塑壳", (0.054, 0.069, 0.067), 0.40)
    green = room_material("吸尘器_烟松绿纤维增强壳", (0.129, 0.227, 0.185), 0.47)
    rubber = room_material("吸尘器_微纹橡胶件", (0.029, 0.035, 0.033), 0.73)
    amber = room_material("吸尘器_充电触点", (0.55, 0.354, 0.127), 0.32, 0.81)
    acrylic = room_material("吸尘器_烟灰半透尘杯PC", (0.62, 0.71, 0.67), 0.21)
    acrylic.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.86
    route = [(0, 0.018, 0.950), (0, 0.055, 0.950), (0, 0.075, 0.962), (0, 0.081, 0.986),
             (0, 0.083, 1.067), (0, 0.077, 1.091), (0, 0.059, 1.111), (0, 0.038, 1.113),
             (0, 0.022, 1.102), (0, 0.013, 1.078), (0, 0.005, 1.050), (0, 0.002, 1.015), (0, 0.002, 1.011)]
    grip = tube("吸尘器_贯通闭环握柄", route, 0.0165, green, 24)
    grip.modifiers.new("把手注塑连续转角", "SUBSURF").levels = 2
    for vertex in grip.data.vertices:
        vertex.co.x *= 1.26
    dust_cup = lathe("吸尘器_可拆透明集尘内外双壁", acrylic, [(0.022, 0.757), (0.041, 0.757),
                    (0.050, 0.768), (0.053, 0.869), (0.0525, 0.891), (0.047, 0.892),
                    (0.048, 0.876), (0.046, 0.771), (0.042, 0.766), (0.020, 0.765)], 0.757, 0.765)
    parts = [
        *vacuum_head(shell, rubber, green, steel), grip, dust_cup,
        cylinder("吸尘器_阳极氧化铝下伸缩管", (0, 0, 0.288), 0.014, 0.34, aluminum, vertices=64),
        cylinder("吸尘器_阳极氧化铝上主管", (0, 0, 0.593), 0.0155, 0.315, aluminum, vertices=64),
        cylinder("吸尘器_伸缩锁止环", (0, 0, 0.452), 0.018, 0.048, shell),
        cylinder("吸尘器_尘杯下方快拆导管", (0, 0, 0.747), 0.022, 0.048, shell),
        cylinder("吸尘器_锥形旋风分离芯", (0, 0, 0.831), 0.014, 0.091, shell, narrow=0.037),
        cylinder("吸尘器_尘杯下取盖及胶圈", (0, 0, 0.777), 0.050, 0.012, rubber, vertices=64),
        cylinder("吸尘器_电机鼓壳下段", (0, 0, 0.928), 0.053, 0.077, shell, vertices=64),
        cylinder("吸尘器_排风槽内壁", (0, 0, 0.988), 0.045, 0.042, rubber, vertices=64),
        cylinder("吸尘器_电机顶盖", (0, 0, 1.013), 0.052, 0.012, green, vertices=64),
        rounded_box("吸尘器_导轨滑装锂电池", (0, 0.062, 0.918), (0.076, 0.074, 0.045), 0.007, shell),
        rounded_box("吸尘器_握把内侧电源扳键", (0, 0.065, 1.017), (0.022, 0.011, 0.027), 0.004, rubber),
        rounded_box("吸尘器_尘杯释放键", (0, -0.052, 0.790), (0.019, 0.011, 0.039), 0.003, green),
    ]
    for i in range(38):
        angle = tau * i / 38
        vane = rounded_box("吸尘器_有间隙的电机排风翅", (0.050 * cos(angle), 0.050 * sin(angle), 0.992),
                            (0.007, 0.005, 0.038), 0.001, shell)
        vane.rotation_euler.z = angle
        parts.append(vane)
    dock = [rounded_box("吸尘器_背挂充电座", (0, 0.123, 0.928), (0.097, 0.028, 0.134), 0.007, shell),
            rounded_box("吸尘器_对接托唇", (0, 0.105, 0.897), (0.083, 0.028, 0.010), 0.003, shell)]
    for x in (-0.032, 0.032):
        dock.append(rod("吸尘器_充电座锁墙螺钉", (x, 0.107, 0.975), (x, 0.111, 0.975), 0.0035, steel))
        dock.append(cylinder("吸尘器_充电接触簧片", (x * 0.42, 0.1035, 0.904), 0.003, 0.006, amber, vertices=24))
    mount = hinge("吸尘器_充电座安装轴", (0, 0.137, 0.928))
    return [*parts, parent_parts(mount, dock), *dock]


def drying_rack():
    steel = satin_steel(RACK)
    ivory = room_material("晾衣架_骨白粉末喷涂铝件", (0.68, 0.639, 0.551), 0.42, 0.12)
    rubber = room_material("晾衣架_消音塑胶止口", (0.17, 0.175, 0.155), 0.7)
    bottom = -0.88
    parts = []
    for x in (-0.51, 0.51):
        parts.extend([
            rounded_box("晾衣架_吊顶安装底板", (x, 0, -0.010), (0.123, 0.129, 0.020), 0.007, ivory),
            rounded_box("晾衣架_吊杆上段伸缩外管", (x, 0, -0.250), (0.028, 0.032, 0.464), 0.004, ivory),
            rounded_box("晾衣架_带限位内轨的下滑管", (x, 0, -0.647), (0.023, 0.023, 0.452), 0.003, steel),
            rounded_box("晾衣架_与四根圆杆相接的横梁", (x, 0, bottom), (0.032, 0.342, 0.031), 0.005, ivory),
            cylinder("晾衣架_下放限位止口", (x, 0, -0.483), 0.016, 0.014, rubber, vertices=36),
        ])
        for y in (-0.042, 0.042):
            parts.append(cylinder("晾衣架_天花锚钉头", (x, y, -0.021), 0.005, 0.003, steel, vertices=28))
    for y in (-0.138, -0.046, 0.046, 0.138):
        parts.append(rod("晾衣架_家用不锈钢晾杆", (-0.566, y, bottom), (0.566, y, bottom), 0.008, steel))
        for x in (-0.566, 0.566):
            parts.append(rod("晾衣架_圆杆非锐边端塞", (x - 0.005, y, bottom),
                             (x + 0.005, y, bottom), 0.0082, ivory))
    return parts


def doorbell():
    frame = room_material("门铃_氧化深青灰铝框", (0.103, 0.125, 0.116), 0.42, 0.56)
    face = room_material("门铃_抗指纹灰黑正面", (0.025, 0.034, 0.032), 0.31)
    gasket = room_material("门铃_深碳防水垫圈", (0.015, 0.018, 0.016), 0.78)
    metal = room_material("门铃_低反光金属按钮", (0.31, 0.34, 0.307), 0.37, 0.74)
    lens = room_material("门铃_镜头密封光学玻璃", (0.008, 0.024, 0.022), 0.17)
    lens.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.23
    light = room_material("门铃_奶白透光状态圈", (0.58, 0.71, 0.58), 0.32)
    parts = [rounded_box("门铃_墙面线路密封后垫", (0, -0.0025, 0), (0.047, 0.005, 0.112), 0.002, gasket),
             rounded_box("门铃_独立铝压铸机身", (0, -0.014, 0), (0.050, 0.024, 0.119), 0.006, frame),
             rounded_box("门铃_独立黑色正面与装配缝", (0, -0.026, 0), (0.046, 0.006, 0.112), 0.0025, face)]
    for name, z, outer, y, surface in (
        ("上部相机镜座", 0.030, 0.011, -0.029, gasket),
        ("凸弧宽角镜头", 0.030, 0.0082, -0.031, lens),
        ("环形按键光导", -0.024, 0.0125, -0.030, light),
        ("独立镀层门铃钮", -0.024, 0.0109, -0.0326, metal),
        ("上方环境光传感窗", 0.047, 0.0016, -0.029, lens),
    ):
        part = cylinder(f"门铃_{name}", (0, y, z), outer, 0.0032, surface, vertices=56)
        part.rotation_euler.x = pi / 2
        parts.append(part)
    panel = parts[2]
    for x in (-0.012, -0.008, -0.004, 0, 0.004, 0.008, 0.012):
        cutter = rounded_box("门铃_扬声器开孔刀具", (x, -0.027, -0.0435),
                             (0.0018, 0.012, 0.0048), 0.0006, gasket)
        bpy.context.view_layer.objects.active = panel
        cut = panel.modifiers.new("冲切扬声器贯穿孔", "BOOLEAN")
        cut.operation, cut.solver, cut.object = "DIFFERENCE", "EXACT", cutter
        bpy.ops.object.modifier_apply(modifier=cut.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    return parts


def cladding_mount(scene, x, z):
    for part in scene.objects:
        if not part.name.startswith("入口_可换木板"):
            continue
        points = [part.matrix_world @ Vector(point) for point in part.bound_box]
        if min(p.x for p in points) <= x <= max(p.x for p in points) and min(p.z for p in points) <= z <= max(p.z for p in points):
            return (part.matrix_world.translation.x, min(p.y for p in points), z)
    raise ValueError("门铃安装点没有命中入户饰面")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "utility-ironing/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "home-devices/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    place_new(VACUUM, stick_vacuum(), (4.43, 4.197, 0.002), pi)
    place_new(RACK, drying_rack(), (4.77, 3.36, 3.0))
    place_new(BELL, doorbell(), cladding_mount(scene, 9.37, 1.33))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["utility-stick-vacuum"]
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
