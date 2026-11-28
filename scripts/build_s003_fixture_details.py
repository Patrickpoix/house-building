"""制作顶装排风口、吹风机、抽纸盒与长柄鞋拔。"""

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
from build_s003_dining import rounded_rectangle
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import rod
from build_s003_lived_in import ring_surface
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material

VENT, DRYER, TISSUE, SHOEHORN = "A201", "A202", "A203", "A204"
VIEWS = {
    "bathroom-exhaust-grille": ((6.47, 1.94, 1.65), (5.67, 1.46, 2.91), 36),
    "bathroom-hair-dryer": ((4.98, 2.13, 1.51), (4.21, 2.36, 1.28), 43),
    "living-tissue-box": ((2.63, 6.33, 1.02), (1.85, 6.71, 0.48), 57),
    "entry-shoehorn": ((8.08, 3.11, 1.41), (7.13, 2.94, 1.16), 49),
}


def exhaust_grille():
    powder = room_material("排风口_骨白粉末涂层", (0.64, 0.659, 0.606), 0.53)
    dark = room_material("排风口_藏灰聚丙烯风道", (0.037, 0.052, 0.046), 0.75)
    screw = room_material("排风口_镀镍固定件", (0.41, 0.414, 0.37), 0.43, 0.73)
    rim = []
    for width, height in ((0.222, -0.003), (0.226, -0.017), (0.215, -0.025),
                          (0.181, -0.025), (0.175, -0.018), (0.178, -0.004)):
        rim.append(list(rounded_rectangle(width, width, height, 0.017, 16)))
    bevel = ring_surface("排风口_通风开口连续圆角边框", rim[::-1], [powder], closed_rows=True)
    parts = [bevel, rounded_box("排风口_70毫米风箱", (0, 0, 0.035), (0.197, 0.197, 0.070), 0.011, dark)]
    for y in (-0.075, -0.060, -0.045, -0.030, -0.015, 0, 0.015, 0.030, 0.045, 0.060, 0.075):
        vane = rounded_box("排风口_斜向盖缝风叶", (0, y, -0.019), (0.175, 0.010, 0.004), 0.0015, powder)
        vane.rotation_euler.x = pi / 5
        parts.append(vane)
    for x in (-0.099, 0.099):
        for y in (-0.097, 0.097):
            parts.append(cylinder("排风口_面框角位锚钉", (x, y, -0.025), 0.0027, 0.002, screw, vertices=24))
    return parts


def dryer_barrel(shell, liner, metal):
    # 原点在壁座，出风口朝室内，后进风网与叶轮之间留空腔。
    stations = ((-0.053, 0.035, 0.034), (-0.065, 0.038, 0.037), (-0.090, 0.039, 0.038),
                (-0.163, 0.034, 0.031), (-0.195, 0.025, 0.023), (-0.222, 0.021, 0.016),
                (-0.247, 0.021, 0.013), (-0.247, 0.017, 0.009), (-0.223, 0.017, 0.012),
                (-0.189, 0.021, 0.019), (-0.095, 0.035, 0.034), (-0.056, 0.031, 0.030))
    rings = [[(rx * cos(tau * i / 64), y, 0.132 + rz * sin(tau * i / 64))
              for i in range(64)] for y, rx, rz in stations]
    barrel = ring_surface("吹风机_中空风筒和收束风嘴", rings, [shell, liner], closed_rows=True)
    for face in barrel.data.polygons:
        face.material_index = int(face.index // 64 >= 7)
    parts = [barrel, rod("吹风机_内部轴流风扇轮毂", (0, -0.082, 0.132), (0, -0.099, 0.132), 0.009, metal)]
    for i in range(7):
        angle = tau * i / 7
        part = rounded_box("吹风机_可见轴流叶片", (0.017 * cos(angle), -0.095, 0.132 + 0.017 * sin(angle)),
                           (0.026, 0.005, 0.010), 0.002, liner)
        part.rotation_euler.y = -angle
        parts.append(part)
    for x in (-0.023, -0.014, -0.005, 0.005, 0.014, 0.023):
        half = (0.030 ** 2 - x ** 2) ** 0.5
        parts.append(rod("吹风机_后滤网格条", (x, -0.054, 0.132 - half), (x, -0.054, 0.132 + half), 0.0014, metal))
    return parts


def hair_dryer():
    metal = satin_steel(DRYER)
    shell = room_material("吹风机_雾青抗热树脂喷涂", (0.187, 0.284, 0.295), 0.39)
    liner = room_material("吹风机_耐高温深灰内壳", (0.041, 0.049, 0.045), 0.61)
    switch = room_material("吹风机_暖灰滑键和线皮", (0.124, 0.134, 0.121), 0.63)
    mount = room_material("吹风机_骨白壁托", (0.61, 0.622, 0.563), 0.47)
    parts = dryer_barrel(shell, liner, metal)
    handle = tube("吹风机_实心圆角握柄", [(0, -0.095, 0.110), (0, -0.088, 0.078), (0, -0.073, 0.039),
                  (0, -0.065, -0.009), (0, -0.068, -0.018)], 0.0155, shell, 32)
    handle.modifiers.new("注塑握把连续弯弧", "SUBSURF").levels = 2
    for vertex in handle.data.vertices:
        vertex.co.x *= 1.15
    cable = [(0, -0.068, -0.017), (0, -0.069, -0.038), (0.008, -0.063, -0.067), (0.029, -0.057, -0.087)]
    for i in range(110):
        angle = 0.49 + tau * 2.53 * i / 109
        cable.append((0.007 + 0.026 * cos(angle), -0.057 + 0.015 * i / 109, -0.109 + 0.025 * sin(angle)))
    end = Vector(cable[-1])
    plug = end + Vector((0.007, 0, 0.022))
    cable.append(plug)
    wire = tube("吹风机_靠墙盘绕电源线", cable, 0.0031, switch)
    wire.modifiers.new("电线自然弯曲", "SUBSURF").levels = 1
    parts.extend([handle, wire, rounded_box("吹风机_风量及热量滑键", (0, -0.101, 0.063), (0.019, 0.009, 0.022), 0.003, switch),
                  rounded_box("吹风机_壁托固定背板", (0, -0.009, 0.041), (0.079, 0.018, 0.138), 0.008, mount),
                  rounded_box("吹风机_背板侧收纳线扣", (0.031, -0.032, -0.080), (0.018, 0.039, 0.017), 0.004, mount),
                  rounded_box("吹风机_绝缘插头", plug, (0.028, 0.015, 0.024), 0.004, switch)])
    for x in (-0.007, 0.007):
        parts.append(rod("吹风机_圆头插销", plug + Vector((x, 0, 0.010)), plug + Vector((x, 0, 0.022)), 0.0022, metal))
    fork = [(-0.033, -0.011, 0.009), (-0.033, -0.056, 0.009), (-0.027, -0.082, 0.009),
            (-0.019, -0.091, 0.009)]
    for sign in (-1, 1):
        parts.append(tube("吹风机_双臂承托壁座", [(sign * x, y, z) for x, y, z in fork], 0.0075, mount))
    return parts


def tissue_box():
    outer = room_material("抽纸盒_微砂灰陶", (0.407, 0.339, 0.267), 0.61)
    foot = room_material("抽纸盒_深色止滑胶条", (0.094, 0.085, 0.072), 0.80)
    paper = room_material("抽纸盒_暖白薄绵纸", (0.82, 0.794, 0.69), 0.88)
    paper.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.14
    rings = []
    for w, d, z, radius in ((0.198, 0.109, 0.006, 0.020), (0.216, 0.128, 0.013, 0.026),
                            (0.217, 0.128, 0.073, 0.026), (0.205, 0.118, 0.084, 0.025),
                            (0.139, 0.027, 0.084, 0.013), (0.133, 0.020, 0.078, 0.009),
                            (0.13, 0.022, 0.074, 0.009), (0.203, 0.116, 0.071, 0.024),
                            (0.204, 0.117, 0.019, 0.024), (0.197, 0.108, 0.010, 0.020)):
        rings.append(list(rounded_rectangle(w, d, z, radius, 18)))
    bezel = ring_surface("抽纸盒_连壁陶瓷壳和长出纸孔", rings, [outer], closed_rows=True)
    parts = [bezel, rounded_box("抽纸盒_滑入式底板", (0, 0, 0.008), (0.194, 0.103, 0.010), 0.004, outer)]
    for x in (-0.066, 0.066):
        parts.append(rounded_box("抽纸盒_独立接地止滑条", (x, 0, 0.003), (0.021, 0.077, 0.006), 0.0025, foot))
    vertices, faces = [], []
    cols, rows = 28, 21
    for row in range(rows):
        t = row / (rows - 1)
        for col in range(cols):
            u = col / (cols - 1) - 0.5
            x = 0.118 * u * (0.84 + 0.28 * t)
            y = -0.005 - 0.038 * t ** 2 + 0.010 * t * sin(12 * u + 2 * t)
            z = 0.077 + 0.043 * sin(t * 2.4) + 0.014 * t * sin(9 * u + 1.1)
            vertices.append((x, y, z))
    for row in range(rows - 1):
        for col in range(cols - 1):
            i = row * cols + col
            faces.append((i, i + cols, i + cols + 1, i + 1))
    sheet = mesh_object("抽纸盒_软折的单张薄纸", vertices, faces, [paper])
    uv = sheet.data.uv_layers.new(name="纸面展开UV")
    for polygon in sheet.data.polygons:
        polygon.use_smooth = True
        for index in polygon.loop_indices:
            row, col = divmod(sheet.data.loops[index].vertex_index, cols)
            uv.data[index].uv = (col / (cols - 1), row / (rows - 1))
    sheet.modifiers.new("纸页微薄厚度", "SOLIDIFY").thickness = 0.00024
    parts.append(sheet)
    return parts


def long_shoehorn():
    metal = satin_steel(SHOEHORN)
    leather = room_material("鞋拔_焦糖皮挂绳", (0.32, 0.123, 0.063), 0.57)
    dark = room_material("鞋拔_石墨手握包胶", (0.048, 0.060, 0.052), 0.68)
    vertices, faces = [], []
    rows, cols = 46, 15
    for row in range(rows):
        length = row / (rows - 1)
        lower = max(0, (length - 0.49) / 0.51)
        end = max(0, (length - 0.91) / 0.09)
        span = 0.011 + 0.019 * sin(pi * 0.62 * lower) ** 1.3
        for col in range(cols):
            u = 2 * col / (cols - 1) - 1
            x = u * span
            y = -0.008 - 0.015 * sin(pi * length) + 0.011 * u ** 2 * sin(pi * length) - 0.010 * length ** 2
            z = -0.027 - 0.414 * length + 0.027 * end ** 2 * (1 - (1 - u ** 2) ** 0.5)
            vertices.append((x, y, z))
    for row in range(rows - 1):
        for col in range(cols - 1):
            i = row * cols + col
            faces.append((i, i + 1, i + cols + 1, i + cols))
    plate = mesh_object("鞋拔_连续勺面和弹性钢柄", vertices, faces, [metal])
    uv = plate.data.uv_layers.new(name="沿钢勺拉丝UV")
    for polygon in plate.data.polygons:
        polygon.use_smooth = True
        for i in polygon.loop_indices:
            row, col = divmod(plate.data.loops[i].vertex_index, cols)
            uv.data[i].uv = (col / (cols - 1), row / (rows - 1))
    plate.modifiers.new("冲压不锈钢实体壁", "SOLIDIFY").thickness = 0.0018
    grip = rounded_box("鞋拔_长柄防滑包胶", (0, -0.010, -0.069), (0.025, 0.011, 0.105), 0.005, dark)
    loop = [(0.013 * sin(tau * i / 40), -0.009 + 0.007 * cos(tau * i / 40),
             -0.018 + 0.024 * cos(tau * i / 40)) for i in range(41)]
    strap = tube("鞋拔_贯通悬挂皮环", loop, 0.002, leather)
    return [plate, grip, strap]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "home-devices/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "fixture-details/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    place_new(VENT, exhaust_grille(), (5.67, 1.46, 3.0))
    west = scene.objects["卫浴_西墙薄釉砖"]
    face_x = max((west.matrix_world @ Vector(point)).x for point in west.bound_box)
    place_new(DRYER, hair_dryer(), (face_x, 2.305, 1.19), pi / 2)
    table = scene.objects["living-coffee-table"]
    table_z = max((table.matrix_world @ obj.matrix_world @ Vector(corner)).z
                  for obj in table.instance_collection.all_objects if obj.type == "MESH" for corner in obj.bound_box)
    place_new(TISSUE, tissue_box(), (table.location.x - 0.18, table.location.y + 0.04, table_z), -pi / 11)
    hook = scene.objects["A150"]
    global_hook = hook.matrix_world @ Vector((0.17, -0.068, 0.012))
    place_new(SHOEHORN, long_shoehorn(), global_hook, hook.rotation_euler.z)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["bathroom-hair-dryer"]
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
