"""从 S001 洞口发布带真实窗扇与门铰的独立资产。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_kitchen_props import rod
from build_s003_living import RENDERS, cylinder, place_new, room_material

DOOR, WINDOW = "A174", "A175"
VIEWS = {
    "bedroom-hinged-door": ((2.90, 4.99, 1.62), (1.53, 3.86, 1.09), 31),
    "bedroom-window-frame": ((1.38, 2.63, 1.51), (0.10, 1.85, 1.66), 34),
}


def selected_opening(wall_name, index):
    _, axis, center, _, _, _, openings = next(wall for wall in WALLS if wall[0] == wall_name)
    left, right, bottom, top = openings[index]
    along = (left + right) / 2
    origin = (along, center, bottom) if axis == "x" else (center, along, bottom)
    return origin, right - left, top - bottom


def wood_board(name, xyz, size, material, grain=0):
    part = board(name, xyz, size, material, grain, (xyz[0] + xyz[2]) * 0.174)
    part.modifiers[0].width = 0.0023
    return part


def rectangle(name, center, width, height, depth, lip, material, make_panel=rounded_box):
    x, y, z = center
    parts = [make_panel(name + "_竖边", (x + sign * (width - lip) / 2, y, z),
                        (lip, depth, height), 0.0015, material) for sign in (-1, 1)]
    parts.extend(make_panel(name + "_横边", (x, y, z + sign * (height - lip) / 2),
                            (width - 2 * lip, depth, lip), 0.0015, material) for sign in (-1, 1))
    return parts


def parent_parts(controller, moving):
    bpy.context.view_layer.update()
    for obj in moving:
        pose = obj.matrix_world.copy()
        obj.parent = controller
        obj.matrix_world = pose
    return controller


def hinged_door(width, height):
    oak, _ = white_oak_material("室内门_白橡径切木皮", "WoodUV")
    brass = room_material("室内门_深暖镍五金", (0.19, 0.15, 0.10), 0.37, 0.73)
    gasket = room_material("室内门_低反光弹性止口", (0.145, 0.122, 0.096), 0.75)
    parts = []
    edge, jamb, reveal = 0.005, 0.032, 0.004
    outer = width / 2 - edge
    for sign in (-1, 1):
        parts.append(wood_board("室内门_装配深框", (sign * (outer - jamb / 2), 0, (height - 0.009) / 2),
                                (jamb, 0.118, height - 0.009), oak, 2))
        for y in (-0.069, 0.069):
            parts.append(wood_board("室内门_两侧压墙线脚", (sign * (outer - 0.008), y, (height - 0.006) / 2),
                                    (0.048, 0.018, height - 0.006), oak, 2))
        parts.append(rounded_box("室内门_侧止口胶条", (sign * (outer - jamb - 0.002), 0.024, (height - 0.041) / 2),
                                 (0.005, 0.006, height - 0.041), 0.0019, gasket))
    parts.append(wood_board("室内门_跨上框", (0, 0, height - edge - jamb / 2),
                            (2 * (outer - jamb), 0.118, jamb), oak))
    for y in (-0.069, 0.069):
        parts.append(wood_board("室内门_两侧上压边", (0, y, height - 0.014), (width - 0.031, 0.018, 0.045), oak))

    anchor = bpy.data.objects.new("内门开启_门扇铰轴", None)
    bpy.context.scene.collection.objects.link(anchor)
    axis_x, axis_y = -outer + jamb + reveal, -0.027
    anchor.location = (axis_x, axis_y, 0)
    leaf_w = 2 * (outer - jamb - reveal)
    leaf_h = height - jamb - edge - 0.012
    moving = [wood_board("室内门_独立木皮平板门扇", (0, -0.001, leaf_h / 2 + 0.009),
                         (leaf_w, 0.043, leaf_h), oak, 2)]
    for z in (0.261, 1.061, 1.849):
        parts.append(cylinder("室内门_三点可见铰接轴管", (axis_x, axis_y, z), 0.0075, 0.061, brass, vertices=28))
        moving.append(rounded_box("室内门_铰座叶片", (axis_x + 0.018, -0.023, z), (0.037, 0.006, 0.053), 0.002, brass))
    for side in (-1, 1):
        x, z = leaf_w / 2 - 0.064, 1.022
        rosette = cylinder("室内门_执手圆座", (x, side * 0.023, z), 0.025, 0.0095, brass)
        rosette.rotation_euler.x = pi / 2
        moving.extend((rosette, rod("室内门_执手短轴", (x, side * 0.026, z), (x, side * 0.054, z), 0.010, brass),
                       rounded_box("室内门_圆角笔直执手", (x - 0.046, side * 0.055, z),
                                   (0.112, 0.018, 0.015), 0.005, brass)))
    moving.append(rounded_box("室内门_锁边金属面", (leaf_w / 2, -0.001, 1.019), (0.004, 0.027, 0.106), 0.0012, brass))
    parent_parts(anchor, moving)
    anchor.rotation_euler.z = -pi / 2
    return [*parts, anchor, *moving]


def double_window(width, height):
    oak, _ = white_oak_material("外窗_室内白橡木衬", "WoodUV")
    aluminum = room_material("外窗_暖灰喷涂型材", (0.16, 0.172, 0.142), 0.43, 0.27)
    gasket = room_material("外窗_深灰气密胶条", (0.058, 0.063, 0.056), 0.83)
    glazing = room_material("外窗_透明玻璃", (0.95, 0.98, 0.96), 0.065)
    glazing.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.99
    fit_w, fit_h = width - 0.009, height - 0.009
    center = fit_h / 2 + 0.0045
    lip = 0.050
    parts = rectangle("外窗_四周主框", (0, 0.009, center), fit_w, fit_h, 0.139, lip, aluminum)
    parts.extend(rectangle("外窗_室内白橡饰边", (0, -0.070, center), fit_w, fit_h, 0.027, 0.041, oak,
                           lambda name, xyz, size, radius, mat: wood_board(name, xyz, size, mat, 2 if size[2] > size[0] else 0)))
    parts.append(rounded_box("外窗_贯通中挺", (0, 0.003, center), (0.054, 0.130, fit_h - 2 * lip), 0.0025, aluminum))
    inner_w = (fit_w - 2 * lip - 0.054) / 2
    inner_h = fit_h - 2 * lip
    for side in (-1, 1):
        x = side * (inner_w / 2 + 0.027)
        trim = 0.031
        moving = rectangle("外窗_独立扇框", (x, -0.012, center), inner_w - 0.005, inner_h - 0.005, 0.059, trim, aluminum)
        clear_w, clear_h = inner_w - 2 * trim, inner_h - 2 * trim
        moving.extend(rectangle("外窗_闭合隔热玻璃压边", (x, -0.014, center), clear_w, clear_h, 0.016, 0.009, gasket))
        for y in (-0.024, -0.008):
            moving.append(rounded_box("外窗_双层独立玻璃", (x, y, center), (clear_w - 0.012, 0.004, clear_h - 0.012),
                                      0.0008, glazing))
        if side < 0:
            pivot = bpy.data.objects.new("外窗开启_内开扇轴", None)
            bpy.context.scene.collection.objects.link(pivot)
            pivot.location = (x - (inner_w - 0.005) / 2 + 0.013, -0.042, center)
            hx = x + inner_w / 2 - 0.023
            moving.extend((rounded_box("外窗_执手底座", (hx, -0.047, center), (0.023, 0.013, 0.060), 0.003, aluminum),
                           rounded_box("外窗_可转窗柄", (hx, -0.061, center - 0.026), (0.016, 0.016, 0.083), 0.004, aluminum)))
            parts.append(parent_parts(pivot, moving))
        parts.extend(moving)
    return parts


def replace(scene, prefix, asset, builder, origin, width, height, angle=0):
    old = [obj for obj in scene.objects if obj.name.startswith(prefix + "_")]
    if not old:
        raise ValueError(f"待更新洞口缺少源窗扇或门扇 {prefix}")
    for obj in old:
        bpy.data.objects.remove(obj, do_unlink=True)
    place_new(asset, builder(width, height), Vector(origin), angle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "major-daily-assets/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "reusable-openings/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    replace(scene, "opening_bedroom_north_0", DOOR, hinged_door, *selected_opening("bedroom_north", 0))
    replace(scene, "opening_west_0", WINDOW, double_window, *selected_opening("west", 0), pi / 2)
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["bedroom-hinged-door"]
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
