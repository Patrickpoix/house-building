"""用原餐厨尺寸装配排烟罩、烤箱及分舱地柜。"""

import argparse
from math import pi, radians
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bathroom_vanity import area_light
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, RENDERS, cylinder, place_new, publish_asset, room_material
import texture_a019_study as textures


HOOD, OVEN, CASE = "A120", "A121", "A122"
VIEWS = {
    "kitchen-cooking-station": ((7.28, 7.10, 1.56), (9.41, 8.14, 1.31), 26),
    "kitchen-cooking-detail": ((8.24, 7.42, 1.43), (9.39, 8.04, 0.99), 35),
}
OVEN_SHELF_Z = 0.250


def satin_steel(asset):
    steel = room_material(f"{asset}_拉丝不锈钢", (0.53, 0.52, 0.49), 0.33, 0.86)
    textures.OUTPUT = LIBRARY / asset
    maps = textures.create_maps("satin-steel", (0.53, 0.52, 0.49), 0.86, 0.33, 0.033, int(asset[1:]))
    textures.connect_maps(steel, maps)
    for image in maps.values():
        image.filepath = str(textures.OUTPUT / "textures" / bpy.path.basename(image.filepath))
        image.pack()
    return steel


def hood(width, depth, duct_height):
    steel = satin_steel(HOOD)
    charcoal = room_material("烟罩_深色内框", (0.083, 0.088, 0.079), 0.46, 0.21)
    opal = room_material("烟罩_磨砂工作灯", (0.93, 0.89, 0.80), 0.33)
    shader = opal.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Emission Color"].default_value = (1, 0.79, 0.56, 1)
    shader.inputs["Emission Strength"].default_value = 4.5
    parts = [
        rounded_box("烟罩_折边金属外壳", (0, 0, 0.055), (width, depth, 0.100), 0.012, steel),
        board("烟罩_下沉滤网衬板", (0, 0.032, 0.010), (width - 0.047, depth - 0.098, 0.009),
              charcoal, 0, 0),
        rounded_box("烟罩_直通烟道罩", (0, depth / 2 - 0.141, 0.105 + duct_height / 2),
                    (0.267, 0.267, duct_height), 0.005, steel),
        rounded_box("烟罩_前缘嵌入导光板", (0, -depth / 2 + 0.052, 0.003),
                    (width - 0.131, 0.019, 0.006), 0.002, opal),
    ]
    frame_width = (width - 0.091) / 2
    filter_depth = depth - 0.125
    for side in (-1, 1):
        x = side * (frame_width + 0.013) / 2
        y = 0.032
        for sign in (-1, 1):
            parts.append(board("烟罩_滤网纵向边框", (x + sign * (frame_width - 0.012) / 2, y, 0.011),
                               (0.013, filter_depth, 0.019), steel, 1, 0))
            parts.append(board("烟罩_滤网横向边框", (x, y + sign * (filter_depth - 0.010) / 2, 0.011),
                               (frame_width - 0.025, 0.011, 0.019), steel, 0, 0))
        for slat in range(11):
            offset = (slat - 5) * (filter_depth - 0.034) / 10
            parts.append(board("烟罩_不锈钢导油折片", (x, y + offset, 0.009),
                               (frame_width - 0.029, 0.013, 0.017), steel, 0, slat / 11))
        parts.append(board("烟罩_滤网卡扣", (x, y - filter_depth / 2 + 0.026, 0.001),
                           (0.048, 0.014, 0.008), charcoal, 0, 0))
    for x in (0.083, 0.126, 0.169, 0.212):
        part = cylinder("烟罩_隐藏触控键", (x, -depth / 2, 0.050), 0.006, 0.002, charcoal, vertices=24)
        part.rotation_euler.x = pi / 2
        parts.append(part)
    return parts


def oven(width):
    steel = satin_steel(OVEN)
    dark = room_material("烤箱_亚光深碳钢", (0.071, 0.074, 0.069), 0.37, 0.44)
    vitreous = room_material("烤箱_内胆深灰搪瓷", (0.099, 0.103, 0.101), 0.35)
    window = room_material("烤箱_双面耐热观察窗", (0.49, 0.51, 0.51), 0.14)
    shader = window.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Transmission Weight"].default_value = 0.68
    shader.inputs["IOR"].default_value = 1.47
    joint = room_material("烤箱_密封垫和后部缝", (0.037, 0.039, 0.037), 0.61)
    parts = []

    def panel(name, location, size, mat, radius=0.004):
        part = rounded_box(f"烤箱_{name}", location, size, radius, mat)
        parts.append(part)
        return part

    depth = 0.541
    inner_w = width - 0.102
    for side in (-1, 1):
        panel("侧壳", (side * (width - 0.041) / 2, 0.043, 0.289), (0.036, depth - 0.047, 0.537), dark)
        panel("搪瓷腔侧板", (side * inner_w / 2, 0.007, 0.259), (0.014, 0.414, 0.392), vitreous)
    panel("底壳", (0, 0.040, 0.021), (width - 0.015, depth - 0.048, 0.036), dark)
    panel("内胆烘烤底板", (0, 0.007, 0.065), (inner_w, 0.415, 0.017), vitreous)
    panel("内胆上壁", (0, 0.007, 0.452), (inner_w, 0.415, 0.020), vitreous)
    panel("内胆后壁", (0, 0.214, 0.256), (inner_w, 0.018, 0.392), vitreous)
    panel("隔热后罩", (0, 0.269, 0.287), (width - 0.022, 0.027, 0.529), dark)
    panel("上隔热盖", (0, 0.037, 0.539), (width - 0.018, depth - 0.038, 0.022), dark)
    panel("底部通风饰条", (0, -0.249, 0.025), (width, 0.024, 0.031), steel)
    panel("控制饰板", (0, -0.246, 0.519), (width, 0.029, 0.104), dark, 0.009)
    panel("时钟显示玻璃", (0, -0.263, 0.522), (0.141, 0.007, 0.038), window, 0.002)
    for x in (-0.183, 0.183):
        knob = cylinder("烤箱_控温旋钮", (x, -0.271, 0.520), 0.025, 0.024, steel)
        knob.rotation_euler.x = pi / 2
        parts.append(knob)
        panel("旋钮指示线", (x, -0.284, 0.537), (0.0022, 0.002, 0.008), dark, 0.0005)
    for side in (-1, 1):
        for z in (0.146, 0.246, 0.348):
            panel("烤架滑道", (side * (inner_w / 2 - 0.015), 0.003, z), (0.022, 0.385, 0.014), vitreous)
    for i in range(12):
        panel("搁架金属条", ((i - 5.5) * (inner_w - 0.067) / 11, 0.017, 0.253),
              (0.005, 0.402, 0.006), steel, 0.002)
    for y in (-0.184, 0.218):
        panel("搁架边框", (0, y, 0.253), (inner_w - 0.051, 0.009, 0.009), steel, 0.003)
    fan = cylinder("烤箱_可见风机后罩", (0, 0.194, 0.268), 0.118, 0.019, dark, vertices=64)
    fan.rotation_euler.x = pi / 2
    parts.append(fan)
    for item in range(7):
        panel("风机罩导流槽", (0, 0.183, 0.224 + item * 0.014), (0.123, 0.004, 0.003), joint, 0.001)

    # 玻璃嵌在独立框的实际开口中，视线可进入烘烤腔。
    door_parts = []
    start_door = len(parts)
    panel("上门框", (0, -0.255, 0.422), (width, 0.031, 0.086), dark, 0.007)
    panel("下门框", (0, -0.255, 0.086), (width, 0.031, 0.085), dark, 0.007)
    for side in (-1, 1):
        panel("门框立边", (side * (width - 0.052) / 2, -0.255, 0.252), (0.052, 0.031, 0.258), dark)
        panel("把手端座", (side * (width / 2 - 0.103), -0.274, 0.417), (0.036, 0.055, 0.028), steel)
    panel("防烫横拉手", (0, -0.303, 0.417), (width - 0.096, 0.026, 0.024), steel, 0.006)
    panel("内外中空玻璃", (0, -0.252, 0.253), (width - 0.099, 0.007, 0.261), window)
    door_parts.extend(parts[start_door:])
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, -0.258, 0.054))
    hinge = bpy.context.object
    hinge.name = "烤箱_门下铰"
    bpy.context.view_layer.update()
    for part in door_parts:
        world = part.matrix_world.copy()
        part.parent = hinge
        part.matrix_world = world
    parts.append(hinge)
    return parts


def cabinet_bays(scene, east_doors, oven_door, top_z, wall_face):
    old_case = scene.objects["餐厨_东侧柜箱"]
    back_x = min(old_case.location.x + old_case.dimensions.x / 2, wall_face - 0.004)
    cabinet_face = old_case.location.x - old_case.dimensions.x / 2
    depth = back_x - cabinet_face
    step = (east_doors[-1].location.y - east_doors[0].location.y) / (len(east_doors) - 1)
    floor, top = 0.090, top_z - 0.060
    paint = east_doors[0].active_material
    oak, _ = white_oak_material("餐厨地柜_白橡内装", "WoodUV")
    bronze = bpy.data.materials["五金_深青铜"]
    center_x = (cabinet_face + back_x) / 2
    parts = []

    def panel(name, pos, dimensions, material, grain=2):
        obj = board(name, pos, dimensions, material, grain, pos[1] * 0.18)
        parts.append(obj)
        return obj

    for index, door in enumerate(east_doors):
        y = door.location.y
        if index == 0:
            panel("东柜_起侧封板", (center_x, y - step / 2 + 0.008, (floor + top) / 2),
                  (depth, 0.016, top - floor), oak)
        panel("东柜_分舱侧板", (center_x, y + step / 2 - 0.008, (floor + top) / 2),
              (depth, 0.016, top - floor), oak)
        panel("东柜_独立可拆背板", (back_x - 0.009, y, (floor + top) / 2),
              (0.017, step - 0.016, top - floor), oak)
        panel("东柜_底舱承板", (center_x, y, floor + 0.012), (depth, step - 0.023, 0.022), oak, 1)
        if door == oven_door:
            panel("东柜_烤箱耐重托板", (center_x, y, OVEN_SHELF_Z - 0.014),
                  (depth - 0.025, step - 0.030, 0.028), oak, 1)
            panel("东柜_烤箱下收纳面", (door.location.x, y, 0.171),
                  (0.022, step - 0.006, 0.142), paint, 1)
        elif index in (1, 4):
            for z in (0.223, 0.483, 0.743):
                drawer_width, drawer_depth = step - 0.076, depth - 0.075
                drawer_x = cabinet_face + drawer_depth / 2 + 0.009
                panel("东柜_深抽面板", (door.location.x, y, z), (0.022, step - 0.006, 0.253), paint, 1)
                panel("东柜_深抽拉手", (door.location.x - 0.025, y, z + 0.051),
                      (0.028, 0.132, 0.017), bronze, 1)
                panel("东柜_深抽承重底", (drawer_x, y, z - 0.092), (drawer_depth, drawer_width, 0.014), oak, 1)
                panel("东柜_深抽后沿", (drawer_x + drawer_depth / 2 - 0.007, y, z - 0.016),
                      (0.014, drawer_width, 0.146), oak, 1)
                for sign in (-1, 1):
                    panel("东柜_深抽侧帮", (drawer_x, y + sign * (drawer_width / 2 - 0.007), z - 0.016),
                          (drawer_depth, 0.014, 0.146), oak, 0)
                    panel("东柜_深抽侧轨", (drawer_x, y + sign * (drawer_width / 2 + 0.005), z - 0.062),
                          (drawer_depth - 0.040, 0.013, 0.023), bronze, 0)
        else:
            panel("东柜_齐平门板", door.location, door.dimensions, paint)
            panel("东柜_小门把手", (door.location.x - 0.025, y, 0.815), (0.028, 0.125, 0.017), bronze, 1)
            panel("东柜_活动搁板", (center_x + 0.015, y, 0.460),
                  (depth - 0.050, step - 0.030, 0.021), oak, 1)
    origin = old_case.location.copy()
    origin.z = 0.0
    for obsolete in [old_case, *east_doors, *(o for o in scene.objects if o.name.startswith("餐厨_东侧拉手"))]:
        bpy.data.objects.remove(obsolete, do_unlink=True)
    publish_asset(CASE, parts, origin)


def build(source, output):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    east = next(row for row in WALLS if row[0] == "east")
    wall_face = east[2] - east[5] / 2
    window_end = max(end for _, end, _, _ in east[-1])
    doors = sorted((o for o in scene.objects if o.name.startswith("餐厨_东侧门板")), key=lambda o: o.location.y)
    door = next(o for o in doors if o.location.y - o.dimensions.y / 2 > window_end + 0.06)
    y = door.location.y
    oven_width = door.dimensions.y - 0.016
    oven_x = door.location.x + 0.256
    counter = scene.objects["餐厨_东侧台面"]
    top = max((counter.matrix_world @ Vector(p)).z for p in counter.bound_box)
    cabinet_bays(scene, doors, door, top, wall_face)

    scene.objects["A105"].location.y = y
    scene.objects["A019"].location.y = 6.93
    apron = scene.objects["A031"]
    apron_move = 9.02 - apron.location.y
    apron.location.y += apron_move
    scene.objects["东墙_围裙挂钩"].location.y += apron_move
    place_new(OVEN, oven(oven_width), Vector((oven_x, y, OVEN_SHELF_Z - 0.003)), -pi / 2)
    hood_z, hood_depth, hood_width = 1.675, 0.512, 0.704
    hood_x = wall_face - hood_depth / 2 - 0.004
    place_new(HOOD, hood(hood_width, hood_depth, 2.967 - hood_z - 0.105),
              Vector((hood_x, y, hood_z)), -pi / 2)
    backsplash = room_material("餐厨_清水暖灰背板", (0.49, 0.45, 0.394), 0.48)
    board("餐厨_排烟工位防溅板", (wall_face - 0.005, y, (hood_z + top) / 2),
          (0.010, hood_width + 0.108, hood_z - top), backsplash, 2, 0)
    area_light("餐厨_烟罩工作照明", (hood_x - hood_depth / 2 + 0.052, y, hood_z - 0.011),
               (9.38, y, top), 19, 0.64, (1.0, 0.86, 0.72))

    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-cooking-station"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)


def render_export(asset, render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / asset / f"{asset}.glb"))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("餐厨工位回导照明")
    scene.world.color = (0.28, 0.28, 0.28)
    if asset == OVEN:
        hinge = next(obj for obj in scene.objects if obj.name.startswith("烤箱_门下铰"))
        hinge.rotation_mode = "XYZ"
        hinge.rotation_euler.x = radians(85)
        location, target, lens, extent = (1.10, -2.35, 1.26), (0, -0.16, 0.26), 57, 0.96
    elif asset == HOOD:
        location, target, lens, extent = (0.68, -1.18, -0.73), (0, 0.03, 0.18), 48, 1.41
    else:
        for obj in scene.objects:
            if obj.name.startswith(("东柜_深抽面板", "东柜_深抽拉手", "东柜_齐平门板", "东柜_小门把手")):
                obj.hide_render = True
        location, target, lens, extent = (-5.2, -2.8, 2.6), (0, 0, 0.40), 48, 5.5
    area_light("回导主光", (-2.8, -3.1, 2.8), target, 200, 3.0, (1.0, 0.97, 0.92))
    area_light("回导检视补光", (1.3, -1.3, -1.1), target, 65, 1.8, (0.91, 0.95, 1.0))
    scene.camera = scene_camera(scene, f"kitchen-{asset}-review", location, target, lens)
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = extent
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = (1200, 780)
    scene.render.filepath = str(render_dir / f"kitchen-{asset.lower()}-glb.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "utility-and-entry-storage/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "cooking-station/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    build(source, output)
    scene = bpy.context.scene
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in VIEWS:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    for asset in (HOOD, OVEN, CASE):
        render_export(asset, args.renders.resolve())


if __name__ == "__main__":
    main()
