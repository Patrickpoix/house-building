"""发布窗边高桌、高脚椅、入户门及共用的湿区门。"""

import argparse
from math import copysign, cos, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_kitchen_props import rod
from build_s003_lived_in import ring_surface
from build_s003_living import RENDERS, cylinder, place_new, room_material
from build_s003_reusable_openings import parent_parts, rectangle, selected_opening, wood_board

STOOL, TABLE, ENTRY, WET = "A182", "A183", "A184", "A185"
TABLE_POS = (5.94, 9.565, 0.002)
STOOL_POS = (5.97, 9.415, 0.002)
TABLE_WIDTH, TABLE_DEPTH, TABLE_HEIGHT = 1.49, 0.454, 0.904
SEAT_HEIGHT = 0.633
VIEWS = {
    "dining-window-counter": ((7.35, 8.23, 1.47), (5.97, 9.51, 0.62), 31),
    "dining-stool-joints": ((6.61, 8.56, 0.91), (5.99, 9.38, 0.58), 37),
    "entry-door-exterior": ((10.18, -2.72, 1.47), (8.69, 0.05, 1.13), 36),
    "entry-door-interior": ((8.56, 2.49, 1.47), (8.67, 0.15, 1.10), 26),
    "bathroom-wet-door": ((8.41, 1.73, 1.49), (7.24, 0.95, 1.15), 24),
}


def furniture():
    oak, _ = white_oak_material("窗边高桌_自然油白橡", "WoodUV")
    powder = room_material("窗边家具_灰绿细纹粉末涂层", (0.115, 0.154, 0.136), 0.43, 0.16)
    rubber = room_material("窗边家具_深灰防滑脚套", (0.043, 0.048, 0.040), 0.8)
    fastener = room_material("窗边家具_磷化钢五金", (0.09, 0.093, 0.083), 0.33, 0.68)
    return oak, powder, rubber, fastener


def window_table(materials):
    oak, powder, rubber, fastener = materials
    slab = board("窗桌_整块圆边白橡台板", (0, 0, TABLE_HEIGHT - 0.020),
                 (TABLE_WIDTH, TABLE_DEPTH, 0.040), oak, 0, 0.37)
    slab.modifiers[0].width, slab.modifiers[0].segments = 0.013, 6
    parts = [slab]
    for x in (-0.664, 0.664):
        for y in (-0.165, 0.165):
            parts.append(rounded_box("窗桌_焊接矩管腿", (x, y, 0.432), (0.034, 0.034, 0.852), 0.003, powder))
            parts.append(rounded_box("窗桌_包底静音尼龙脚座", (x, y, 0.005), (0.037, 0.037, 0.010), 0.002, rubber))
        for z in (0.203, 0.841):
            parts.append(rounded_box("窗桌_端框连撑", (x, 0, z), (0.028, 0.327, 0.025), 0.002, powder))
        parts.append(rounded_box("窗桌_台面下可拆连接耳", (x, -0.059, 0.858),
                                 (0.083, 0.072, 0.014), 0.004, powder))
        for side in (-1, 1):
            parts.append(cylinder("窗桌_固定台板螺钉", (x + side * 0.028, -0.059, 0.850), 0.006, 0.005, fastener, vertices=24))
    for z in (0.228, 0.841):
        parts.append(rounded_box("窗桌_后侧抗侧移长撑", (0, 0.165, z), (1.322, 0.030, 0.026), 0.003, powder))
    return parts


def bent_wood(name, rings, oak, grain_axis):
    part = ring_surface(name, rings, [oak], (True, True))
    uv = part.data.uv_layers.active
    uv.name = "WoodUV"
    for face in part.data.polygons:
        normal_axis = max(range(3), key=lambda axis: abs(face.normal[axis]))
        axes = [axis for axis in range(3) if axis != normal_axis]
        grain = grain_axis if grain_axis in axes else axes[-1]
        cross = next(axis for axis in axes if axis != grain)
        for index in face.loop_indices:
            point = part.data.vertices[part.data.loops[index].vertex_index].co
            uv.data[index].uv = (point[cross] * 2, point[grain] * 2)
    return part


def counter_stool(materials):
    oak, powder, rubber, fastener = materials
    parts = []
    feet_y, knees_y = (-0.215, 0.207), (-0.150, 0.132)
    for side in (-1, 1):
        for y, upper_y in zip(feet_y, knees_y):
            foot = (side * 0.197, y, 0.012)
            knee = (side * 0.164, upper_y, 0.603)
            parts.extend((rod("高脚椅_外撇粉末喷涂钢腿", foot, knee, 0.012, powder),
                          cylinder("高脚椅_四只橡胶脚垫", (foot[0], foot[1], 0.008), 0.0135, 0.016, rubber, vertices=32)))
        parts.append(rod("高脚椅_两侧承重横撑", (side * 0.181, -0.186, 0.284),
                         (side * 0.181, 0.168, 0.284), 0.009, powder))
        parts.append(rod("高脚椅_外露弯背立杆", (side * 0.164, -0.15, 0.589),
                         (side * 0.154, -0.214, 0.872), 0.010, powder))
        for y in (-0.111, 0.107):
            parts.append(cylinder("高脚椅_座面底部修配螺钉", (side * 0.144, y, 0.599), 0.006, 0.005, fastener, vertices=24))
    for y, z in ((0.178, 0.244), (-0.19, 0.253), (-0.149, 0.594), (0.132, 0.594)):
        half = 0.181 if z < 0.3 else 0.161
        parts.append(rod("高脚椅_前脚踏及座下撑管", (-half, y, z), (half, y, z), 0.010, powder))
    outline = []
    for factor, z in ((0.12, 0.601), (0.93, 0.600), (1.00, 0.608), (1.00, SEAT_HEIGHT),
                      (0.93, SEAT_HEIGHT + 0.003), (0.52, SEAT_HEIGHT - 0.009), (0.13, SEAT_HEIGHT - 0.014)):
        outline.append([
            (0.195 * factor * copysign(abs(cos(tau * i / 64)) ** 0.55, cos(tau * i / 64)),
             0.178 * factor * copysign(abs(sin(tau * i / 64)) ** 0.55, sin(tau * i / 64)), z)
            for i in range(64)
        ])
    parts.append(bent_wood("高脚椅_浅碟压弯白橡座面", outline, oak, 0))
    back = []
    for x, scale in ((-0.178, 0.68), (-0.174, 0.92), (-0.162, 1), (-0.13, 1.02),
                     (-0.065, 1.04), (0, 1.04), (0.065, 1.04), (0.13, 1.02),
                     (0.162, 1), (0.174, 0.92), (0.178, 0.68)):
        y = -0.187 - 0.027 * (x / 0.178) ** 2
        back.append([(x, y + dy * scale - dz * 0.17, 0.822 + dz * scale)
                     for dy, dz in ((0.006, -0.064), (0.010, -0.059), (0.010, 0.053), (0.005, 0.063),
                                    (-0.004, 0.064), (-0.010, 0.058), (-0.010, -0.058), (-0.004, -0.064))])
    parts.append(bent_wood("高脚椅_双向弧形白橡靠板", back, oak, 0))
    return parts


def hinge(name, position):
    pivot = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.location = position
    return pivot


def lever_set(prefix, x, center_y, half_thickness, z, material):
    parts = []
    for side in (-1, 1):
        y = center_y + side * half_thickness
        backplate = rounded_box(prefix + "_执手背座", (x, y, z), (0.041, 0.011, 0.106), 0.008, material)
        stem = rod(prefix + "_执手转轴", (x, y, z + 0.020), (x, y + side * 0.037, z + 0.020), 0.010, material)
        handle = rounded_box(prefix + "_圆边横执手", (x - 0.048, y + side * 0.038, z + 0.020),
                             (0.120, 0.019, 0.016), 0.007, material)
        parts.extend((backplate, stem, handle))
    return parts


def door_frame(prefix, width, height, depth, bottom, finish, seal):
    fit = width - 0.008
    frame = rectangle(prefix + "_三维主框", (0, 0, height / 2), fit, height - 0.009, depth, 0.033, finish)
    bottom_rail = frame[-2]
    bottom_rail.scale.z = bottom / 0.033
    bottom_rail.location.z = bottom / 2
    stop_w, stop_h = fit - 0.058, height - 0.033 - bottom
    stops = rectangle(prefix + "_连续弹性止口", (0, 0.011, bottom + stop_h / 2),
                      stop_w, stop_h, 0.015, 0.009, seal)
    stops[-2].location.z += 0.002
    return [*frame, *stops]


def entrance_door(width, height):
    oak, _ = white_oak_material("入户门_户外油封白橡", "WoodUV")
    coating = room_material("入户门_灰绿喷涂框及实心背板", (0.12, 0.178, 0.155), 0.37, 0.15)
    gasket = room_material("入户门_碳灰EPDM止风密封", (0.036, 0.039, 0.036), 0.82)
    metal = room_material("入户门_深暖灰不锈锁具", (0.227, 0.191, 0.139), 0.33, 0.72)
    parts = door_frame("入户门", width, height, 0.183, 0.014, coating, gasket)
    core_w, core_h, center_z = width - 0.083, height - 0.063, (height - 0.063) / 2 + 0.018
    left = -core_w / 2
    pivot = hinge("入户门_内开铰轴", (left - 0.003, 0.045, 0))
    moving = [rounded_box("入户门_保温压合门扇", (0, 0.014, center_z),
                          (core_w, 0.051, core_h), 0.003, coating)]
    # 户外侧窄槽由独立板件保留，能看见门扇侧缘和板缝深度。
    for side in (-1, 1):
        moving.append(wood_board("入户门_户外白橡周边梃", (side * (core_w / 2 - 0.034), -0.019, center_z),
                                 (0.068, 0.018, core_h), oak, 2))
    clear = core_w - 0.136
    for i in range(9):
        x = clear * ((i + 0.5) / 9 - 0.5)
        moving.append(wood_board("入户门_竖向白橡通长板", (x, -0.018, center_z),
                                 (clear / 9 - 0.0026, 0.019, core_h - 0.003), oak, 2))
    moving.extend(lever_set("入户门", core_w / 2 - 0.071, 0.0055, 0.0335, 1.021, metal))
    for y in (-0.029, 0.043):
        lock = cylinder("入户门_独立锁芯端面", (core_w / 2 - 0.071, y, 0.935), 0.016, 0.008, metal, vertices=36)
        lock.rotation_euler.x = pi / 2
        moving.append(lock)
    for z in (0.28, 1.09, 1.90):
        parts.append(cylinder("入户门_室内三点重载铰管", (left - 0.003, 0.045, z), 0.009, 0.091, metal, vertices=32))
        moving.append(rounded_box("入户门_铰链门扇页", (left + 0.023, 0.040, z), (0.043, 0.006, 0.072), 0.0018, metal))
    moving.append(rounded_box("入户门_锁舌边板", (core_w / 2, 0.009, 1.03), (0.003, 0.035, 0.214), 0.001, metal))
    return [*parts, parent_parts(pivot, moving), *moving]


def wet_door(width, height):
    enamel = room_material("湿区门_米灰聚酯粉末涂层", (0.55, 0.54, 0.47), 0.37, 0.14)
    gasket = room_material("湿区门_深灰密封条", (0.098, 0.108, 0.092), 0.75)
    steel = room_material("湿区门_缎面不锈钢执手", (0.35, 0.34, 0.30), 0.32, 0.75)
    panel = room_material("湿区门_苔灰哑光防潮复合板", (0.24, 0.30, 0.264), 0.51)
    glass = room_material("湿区门_透光磨砂夹胶玻璃", (0.85, 0.91, 0.865), 0.40)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.86
    parts = door_frame("湿区门", width, height, 0.121, 0.013, enamel, gasket)
    leaf_w, leaf_h = width - 0.082, height - 0.060
    z0, y0, lip = 0.019, -0.020, 0.049
    pivot = hinge("湿区门_外开铰轴", (-leaf_w / 2 - 0.002, -0.046, 0))
    moving = rectangle("湿区门_四边铝合金扇框", (0, y0, z0 + leaf_h / 2),
                       leaf_w, leaf_h, 0.037, lip, enamel)
    opening_w = leaf_w - 2 * lip
    cross_z = 0.895
    moving.append(rounded_box("湿区门_水平分隔中挺", (0, y0, cross_z), (opening_w, 0.040, 0.048), 0.0024, enamel))
    low, high = (z0 + lip, cross_z - 0.023), (cross_z + 0.023, z0 + leaf_h - lip)
    for (lo, hi), material, label in ((low, panel, "下段防踢实板"), (high, glass, "上段磨砂玻璃")):
        middle = (lo + hi) / 2
        for side in (-1, 1):
            moving.extend(rectangle("湿区门_压条胶边", (0, y0 + side * 0.009, middle),
                                    opening_w + 0.002, hi - lo, 0.007, 0.009, gasket))
        moving.append(rounded_box("湿区门_" + label, (0, y0, middle),
                                  (opening_w - 0.009, 0.010, hi - lo - 0.006), 0.0018, material))
    latch_x = (leaf_w - lip) / 2
    moving.extend(lever_set("湿区门", latch_x, y0, 0.020, 0.995, steel))
    for z in (0.263, 1.108, 1.872):
        parts.append(cylinder("湿区门_三点防潮铰管", (-leaf_w / 2 - 0.002, -0.046, z), 0.0075, 0.077, steel, vertices=28))
        moving.append(rounded_box("湿区门_铰管连接片", (-leaf_w / 2 + 0.021, -0.040, z),
                                  (0.040, 0.005, 0.061), 0.002, steel))
    parent_parts(pivot, moving)
    pivot.rotation_euler.z = -pi / 2
    return [*parts, pivot, *moving]


def clear_opening(scene, prefix):
    old = [obj for obj in scene.objects if obj.name.startswith(prefix + "_")]
    if not old:
        raise ValueError(f"未找到待替换洞口 {prefix}")
    for obj in old:
        bpy.data.objects.remove(obj, do_unlink=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "table-and-cleaning/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "counter-seating-and-doors/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    materials = furniture()
    place_new(TABLE, window_table(materials), TABLE_POS)
    place_new(STOOL, counter_stool(materials), STOOL_POS)
    for prefix in ("opening_south_2", "opening_bath_east_0", "opening_utility_north_0"):
        clear_opening(scene, prefix)
    origin, width, height = selected_opening("south", 2)
    place_new(ENTRY, entrance_door(width, height), origin)
    origin, width, height = selected_opening("bath_east", 0)
    place_new(WET, wet_door(width, height), origin, pi / 2)
    utility_origin, utility_width, utility_height = selected_opening("utility_north", 0)
    if abs(utility_width - width) > 0.0001 or abs(utility_height - height) > 0.0001:
        raise ValueError("湿区门使用同一资产的两个洞口需要相同净尺寸")
    source_instance = scene.objects[WET]
    utility = bpy.data.objects.new(f"{WET}_家政门", None)
    utility.instance_type = "COLLECTION"
    utility.instance_collection = source_instance.instance_collection
    utility.matrix_world = Matrix.Translation(utility_origin) @ Matrix.Rotation(pi, 4, "Z")
    scene.collection.objects.link(utility)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["dining-window-counter"]
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
