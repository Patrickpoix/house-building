"""制作首款平底煎锅、料理夹和电子厨房秤，并校核厨房接触。"""

import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_a103_bowl_study import ceramic_vessel
from build_s003_bedroom import STAGES
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import GLASS_Z, ZONE_CENTER_Y, ZONE_CENTERS, scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import rod
from build_s003_lived_in import ring_surface
from build_s003_living import LIBRARY, RENDERS, cylinder, place_new, room_material
import texture_a019_study as textures


PAN, TONGS, SCALE = "A206", "A207", "A208"
VIEWS = {
    "kitchen-skillet": ((8.69, 7.69, 1.55), (9.42, 7.93, 1.02), 54),
    "kitchen-tongs": ((8.72, 7.24, 1.39), (9.18, 7.30, 0.96), 61),
    "kitchen-scale": ((8.76, 6.06, 1.39), (9.51, 6.24, 0.96), 65),
}


def skillet():
    steel = satin_steel(PAN)
    enamel = room_material("煎锅_烟蓝耐热外壁", (0.070, 0.137, 0.160), 0.38)
    grip = room_material("煎锅_炭黑耐热手柄", (0.030, 0.038, 0.036), 0.57)
    coating = room_material("煎锅_矿点不粘涂层", (0.052, 0.057, 0.053), 0.51)
    textures.OUTPUT = LIBRARY / PAN
    maps = textures.create_maps("mineral-nonstick", (0.046, 0.050, 0.049), 0, 0.51, 0.14, 206)
    textures.connect_maps(coating, maps)
    for image in maps.values():
        image.filepath = str(LIBRARY / PAN / "textures" / bpy.path.basename(image.filepath))
        image.pack()

    contour = ((0.075, 0.004), (0.091, 0.004), (0.097, 0.005), (0.103, 0.009), (0.111, 0.020),
               (0.117, 0.034), (0.121, 0.046), (0.121, 0.050), (0.120, 0.051),
               (0.118, 0.051), (0.117, 0.049), (0.116, 0.045), (0.111, 0.031),
               (0.105, 0.020), (0.097, 0.014), (0.087, 0.013), (0.068, 0.013))
    body = ceramic_vessel(enamel, coating, contour, name="煎锅_连续压铸腔体和薄卷口", underside_z=0.004,
                          inner_floor_z=0.013, foot_height=0, planar_inner_row=14, uv_size=(0.25, 0.31), uv_repeats=1)
    body.data.materials.append(steel)
    sides = len(body.data.vertices) // len(contour)
    for face in body.data.polygons:
        row = (face.index - sides) // sides
        if 7 <= row <= 9:
            face.material_index = 2
        elif row >= 10:
            face.material_index = 1
    handle = tube("煎锅_椭圆防转手柄", [(0.131, 0, 0.037), (0.146, 0, 0.043), (0.181, 0, 0.052),
                  (0.222, 0, 0.056), (0.267, 0, 0.056), (0.277, 0, 0.055)], 0.012, grip, 32)
    for vertex in handle.data.vertices:
        vertex.co.y *= 1.36
    handle.modifiers.new("手柄圆顺过渡", "SUBSURF").levels = 1
    parts = [body, handle,
             cylinder("煎锅_磁感应钢盘", (0, 0, 0.003), 0.092, 0.006, steel, vertices=128),
             rounded_box("煎锅_承重铆接钢卡座", (0.127, 0, 0.0375), (0.025, 0.036, 0.020), 0.006, steel)]
    for y in (-0.010, 0.010):
        parts.append(rod("煎锅_内腔低圆头铆钉", (0.112, y, 0.037), (0.119, y, 0.037), 0.0047, steel))
    return parts


def cooking_tongs():
    steel = satin_steel(TONGS)
    silicone = room_material("料理夹_松烟绿隔热硅胶", (0.071, 0.127, 0.099), 0.66)
    arc = [(-0.111 + 0.0105 * cos(pi / 2 + pi * i / 24), 0.0105 * sin(pi / 2 + pi * i / 24)) for i in range(25)]
    tail = [(0.098, 0.031), (0.086, 0.031), (0.029, 0.026), (-0.061, 0.016), (-0.101, 0.0105)]
    path = [*tail, *arc, *((x, -y) for x, y in reversed(tail))]
    stations = []
    for i, (x, y) in enumerate(path):
        tangent = (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(0, i - 1)])).normalized()
        stations.append([(x - tangent.y * 0.00125 * cos(angle), y + tangent.x * 0.00125 * cos(angle),
                          0.0125 + 0.0095 * sin(angle)) for angle in (tau * k / 24 for k in range(24))])
    band = ring_surface("料理夹_连体折弯回弹钢片", stations, [steel], caps=(True, True))
    parts = [band]
    for sign in (-1, 1):
        pad = rounded_box("料理夹_拇指隔热握套", (-0.034, sign * 0.0195, 0.016), (0.089, 0.007, 0.017), 0.003, silicone)
        pad.rotation_euler.z = sign * 0.095
        parts.append(pad)
        rings = []
        for i in range(31):
            t = i / 30
            x = 0.072 + 0.057 * t
            nose = (1 - max(0.0, (t - 0.77) / 0.26) ** 2) ** 0.55
            width = (0.003 + 0.010 * sin(pi * t * 0.86) ** 1.2) * nose
            scallop = 0.0017 * sin(pi * t) * cos(8 * pi * t)
            rings.append([(x, sign * (0.030 + 0.0025 * t) + (width + scallop) * cos(angle),
                           0.012 + (0.007 + 0.005 * sin(pi * t)) * nose * sin(angle))
                          for angle in (tau * k / 36 for k in range(36))])
        jaw = ring_surface("料理夹_浅匙形波齿夹头", rings, [silicone], caps=(True, True))
        parts.append(jaw)
    return parts


def kitchen_scale():
    shell = room_material("电子秤_细砂白注塑侧壳", (0.68, 0.653, 0.584), 0.47)
    glass = room_material("电子秤_暖灰低铁称重面板", (0.49, 0.519, 0.476), 0.27)
    screen = room_material("电子秤_石墨液晶玻璃", (0.026, 0.043, 0.041), 0.23)
    ink = room_material("电子秤_低对比液晶笔画", (0.23, 0.36, 0.30), 0.64)
    foot = room_material("电子秤_橡胶微秤脚", (0.070, 0.079, 0.067), 0.80)
    steel = satin_steel(SCALE)
    parts = [rounded_box("电子秤_承重壳", (0, 0, 0.016), (0.191, 0.223, 0.025), 0.006, shell),
             rounded_box("电子秤_独立称重玻璃", (0, 0.022, 0.031), (0.184, 0.165, 0.008), 0.003, glass),
             rounded_box("电子秤_触控与显示嵌面", (0, -0.082, 0.030), (0.177, 0.043, 0.005), 0.002, steel),
             rounded_box("电子秤_凹平显示屏", (0, -0.083, 0.033), (0.064, 0.023, 0.002), 0.002, screen),
             rounded_box("电子秤_背面可拆电池盖", (0, 0.005, 0.004), (0.073, 0.043, 0.003), 0.001, foot)]
    for x in (-0.067, 0.067):
        for y in (-0.078, 0.078):
            parts.append(cylinder("电子秤_四角自稳脚", (x, y, 0.003), 0.010, 0.006, foot, vertices=40))
        parts.append(cylinder("电子秤_低行程控制键", (x, -0.082, 0.033), 0.008, 0.0035, glass, vertices=36))
    for x in (-0.005, 0.005):
        for y in (-0.087, -0.079):
            parts.append(rounded_box("电子秤_纵向液晶笔画", (x, y, 0.0341), (0.0012, 0.007, 0.0002), 0.00009, ink))
    for y in (-0.0915, -0.0745):
        parts.append(rounded_box("电子秤_横向液晶笔画", (0, y, 0.0341), (0.009, 0.0012, 0.0002), 0.00009, ink))
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "dishwasher/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "cooking-tools/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    cooktop = scene.objects["A105"]
    center = cooktop.matrix_world @ Vector((ZONE_CENTERS[1], ZONE_CENTER_Y, GLASS_Z))
    place_new(PAN, skillet(), center, -2.36)
    worktop_z = scene.objects["A123"].location.z
    place_new(TONGS, cooking_tongs(), (9.177, 7.30, worktop_z), -pi / 2)
    place_new(SCALE, kitchen_scale(), (9.51, 6.24, worktop_z), -pi / 2)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
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
