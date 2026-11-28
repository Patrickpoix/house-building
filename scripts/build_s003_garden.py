"""完成庭边书屋的屋盖、入户步道及窗外庭院。"""

import argparse
from math import atan2, hypot, radians, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s001_whitebox import HEIGHT, WALLS
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, RENDERS, mesh_object, place_new, room_material


TREE, SHRUB, PAVER, SCREEN = "A131", "A132", "A133", "A134"
GRADE = -0.20
PAVER_WIDTH, PAVER_LENGTH = 0.72, 0.57
SCREEN_WIDTH, SCREEN_HEIGHT = 1.80, 1.62
VIEWS = {
    "garden-arrival": ((15.1, -11.9, 3.14), (5.88, 3.25, 1.30), 33),
    "garden-northwest": ((-10.8, 16.7, 3.55), (3.95, 7.00, 1.49), 31),
    "garden-from-kitchen": ((6.97, 8.01, 1.59), (8.03, 9.83, 1.32), 32),
    "garden-from-reading-chair": ((3.34, 6.16, 1.55), (1.28, 8.62, 1.23), 25),
}


def image_material(label, asset, normal_strength):
    mat = room_material(label, (0.45, 0.45, 0.45), 0.62)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes["Principled BSDF"]
    for suffix, channel in (("diff", "Base Color"), ("rough", "Roughness"), ("nor_gl", "Normal")):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(LIBRARY / "materials" / asset / f"{asset}_{suffix}_2k.jpg"),
                                         check_existing=True)
        tex.image.colorspace_settings.name = "sRGB" if suffix == "diff" else "Non-Color"
        if suffix == "nor_gl":
            normal = nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = normal_strength
            links.new(tex.outputs["Color"], normal.inputs["Color"])
            links.new(normal.outputs["Normal"], shader.inputs[channel])
        else:
            links.new(tex.outputs["Color"], shader.inputs[channel])
    return mat


def material_ground(name, points, material, period):
    ground = mesh_object(name, points, [(0, 1, 2, 3)], [material])
    uv = ground.data.uv_layers.new(name="MeterUV")
    for index, point in enumerate(points):
        uv.data[index].uv = (point[0] / period, point[1] / period)
    return ground


def rectangle_ground(name, x, y, height, material, period):
    return material_ground(name, [(x[0], y[0], height), (x[1], y[0], height),
                                  (x[1], y[1], height), (x[0], y[1], height)],
                           material, period)


def ground(site):
    grass = image_material("庭院草地_实拍", "grass_ground", 0.48)
    gravel = image_material("庭院碎石落叶_实拍", "leaf_scattered_gravel", 0.76)
    site.objects["ground"].hide_render = True
    site.objects["ground"].hide_viewport = True
    shader = grass.node_tree.nodes["Principled BSDF"]
    color = shader.inputs["Base Color"].links[0].from_socket
    tint = grass.node_tree.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (0.55, 0.70, 0.39, 1)
    grass.node_tree.links.new(color, tint.inputs[1])
    grass.node_tree.links.new(tint.outputs["Color"], shader.inputs["Base Color"])
    rectangle_ground("庭院_草地", (-150, 150), (-150, 150), GRADE, grass, 1.76)
    for name, x, y in (
        ("南入口", (6.84, 10.21), (-5.95, 0.01)),
        ("西侧碎石温庭", (-2.17, 0.01), (3.70, 9.96)),
        ("北侧碎石庭", (-1.97, 10.00), (9.97, 12.42)),
        ("东侧碎石边", (10, 11.32), (2.07, 9.92)),
    ):
        rectangle_ground("庭院_" + name, x, y, GRADE + 0.004, gravel, 1.80)


def roof():
    dark = room_material("屋盖_炭灰立边金属", (0.079, 0.092, 0.090), 0.44, 0.52)
    rib = room_material("屋盖_扣缝细边", (0.062, 0.071, 0.069), 0.38, 0.56)
    cedar, _ = white_oak_material("檐底_浅色木板", "WoodUV")
    wall = next(obj.active_material for obj in bpy.context.scene.objects if obj.name.startswith("wall_north"))
    ridge, ridge_y = HEIGHT + 1.08, 4.78
    eaves = HEIGHT + 0.19
    width = 10.84
    for edge_y, wall_y in ((-0.54, 0.10), (10.47, 9.90)):
        length = hypot(ridge_y - edge_y, ridge - eaves)
        slope = atan2(ridge - eaves, ridge_y - edge_y)
        mid_y = (ridge_y + edge_y) / 2
        mid_z = (ridge + eaves) / 2
        cover = rounded_box("屋盖_双向排水金属坡面", (5, mid_y, mid_z), (width, length + 0.04, 0.035),
                            0.007, dark)
        cover.rotation_euler.x = slope
        for index in range(26):
            x = 5 - width / 2 + 0.12 + index * (width - 0.24) / 25
            seam = rounded_box("屋盖_直立锁边", (x, mid_y - 0.014 * sin(slope), mid_z + 0.027),
                               (0.018, length - 0.018, 0.029), 0.004, rib)
            seam.rotation_euler.x = slope
        board("屋盖_檐底木饰面", (5, edge_y + (0.19 if edge_y < 0 else -0.19), eaves - 0.072),
              (width, 0.42, 0.040), cedar, 0, 0.13)
        rounded_box("屋盖_檐口包边", (5, edge_y, eaves - 0.034), (width + 0.02, 0.042, 0.16), 0.006, rib)
        wall_top = eaves + (ridge - eaves) * abs((wall_y - edge_y) / (ridge_y - edge_y))
        board("屋盖_檐下墙体封口", (5, wall_y, (HEIGHT + wall_top) / 2),
              (9.60, 0.20, wall_top - HEIGHT), wall, 0, 0)
        for x in (-0.43, 10.43):
            fascia = rounded_box("屋盖_山墙斜封檐板", (x, mid_y, mid_z - 0.053),
                                 (0.049, length + 0.02, 0.124), 0.008, dark)
            fascia.rotation_euler.x = slope
    rounded_box("屋盖_屋脊扣帽", (5, ridge_y, ridge + 0.023), (width + 0.035, 0.094, 0.038), 0.010, rib)
    profile = [(0, HEIGHT - 0.025), (10, HEIGHT - 0.025),
               (10, eaves + (ridge - eaves) * 0.47 / (10.47 - ridge_y)),
               (ridge_y, ridge - 0.017), (0, eaves + (ridge - eaves) * 0.54 / (ridge_y + 0.54))]
    vertices = [(x, y, z) for x in (-0.002, 0.20, 9.80, 10.002) for y, z in profile]
    faces = []
    for start in (0, 10):
        faces.extend((tuple(reversed(range(start, start + 5))), tuple(range(start + 5, start + 10))))
        for index in range(5):
            a, b = start + index, start + (index + 1) % 5
            faces.append((a, b, b + 5, a + 5))
    mesh_object("屋盖_封闭两侧山墙", vertices, faces, [wall])
    for x in (-0.014, 10.014):
        board("屋盖_山墙滴水线", (x, 5, HEIGHT + 0.004), (0.032, 10.006, 0.040), rib, 1, 0)


def exterior_trim():
    wood, _ = white_oak_material("入口_浅烟木竖向饰面", "WoodUV")
    stone = image_material("外墙_水泥勒脚", "concrete_floor_worn_001", 0.48)
    trim = room_material("入口_灰褐包边", (0.122, 0.104, 0.083), 0.44, 0.35)
    entry = next(wall for wall in WALLS if wall[0] == "south")
    left, right, _, high = next(opening for opening in entry[-1] if opening[2] == 0)
    segments = ((7.24, left, 0.035), (left, right, high), (right, 9.65, 0.035))
    for start, end, low in segments:
        total = end - start
        count = round(total / 0.135)
        pitch = total / count
        for index in range(count):
            x = start + pitch * (index + 0.5)
            board("入口_可换木板", (x, -0.019, (low + 2.95) / 2),
                  (pitch - 0.005, 0.035, 2.95 - low), wood, 2, x * 0.66)
    board("入口_木饰面上收边", (8.445, -0.025, 2.951), (2.43, 0.044, 0.028), trim, 0, 0)
    for start, end, y in ((0, left, -0.012), (right, 10, -0.012), (0, 10, 10.012)):
        board("外墙_横向防溅勒脚", ((start + end) / 2, y, -0.068),
              (end - start, 0.034, 0.267), stone, 0, 0.43)
    for x in (-0.012, 10.012):
        board("外墙_山墙防溅勒脚", (x, 5, -0.068), (0.034, 10, 0.267), stone, 1, 0.24)


def link_copy(asset, location, angle=0, scale=1):
    obj = asset.copy()
    obj.location = location
    obj.rotation_euler.z = angle
    obj.scale = (scale,) * 3
    bpy.context.scene.collection.objects.link(obj)
    return obj


def plants(asset, source, slug, positions):
    if source:
        path = source / slug / f"{slug}_2k.gltf"
        bpy.ops.import_scene.gltf(filepath=str(path))
        objects = list(bpy.context.selected_objects)
        if not objects or any(obj.type != "MESH" for obj in objects):
            raise RuntimeError(f"无法读取绿植网格：{path}")
        low = min((obj.matrix_world @ Vector(corner)).z for obj in objects for corner in obj.bound_box)
        for obj in objects:
            obj.location.z -= low
        place_new(asset, objects, positions[0][0], positions[0][1])
    else:
        with bpy.data.libraries.load(str(LIBRARY / asset / f"{asset}.blend"), link=True, relative=True) as (src, dst):
            if asset not in src.collections:
                raise RuntimeError(f"{asset} 缺少可链接集合")
            dst.collections = [asset]
        base = bpy.data.objects.new(asset, None)
        base.instance_type = "COLLECTION"
        base.instance_collection = dst.collections[0]
        base.location, base.rotation_euler.z = positions[0][:2]
        bpy.context.scene.collection.objects.link(base)
    base = bpy.context.scene.objects[asset]
    base.scale = (positions[0][2],) * 3
    for location, angle, scale in positions[1:]:
        link_copy(base, location, angle, scale)


def paths():
    stone = image_material("步道_细磨浅灰板", "concrete_floor_worn_001", 0.58)
    # 以已建门洞中心对齐最高一块踏步，其余板面略低以露出接缝。
    entry_wall = next(wall for wall in WALLS if wall[0] == "south")
    left, right, _, _ = next(opening for opening in entry_wall[-1] if opening[2] == 0)
    step_center = (left + right) / 2
    tile = board("步道_独立方石", (0, 0, 0.028), (PAVER_WIDTH, PAVER_LENGTH, 0.056), stone, 1, 0.09)
    tile.modifiers[0].width = 0.012
    # 板底沉入碎石表面 1 mm，板角受承托。
    bed_z = GRADE + 0.003
    place_new(PAVER, [tile], (step_center - PAVER_WIDTH / 2 - 0.008, -1.19, bed_z))
    paver = bpy.context.scene.objects[PAVER]
    for row in range(8):
        y = -1.19 - row * (PAVER_LENGTH + 0.022)
        for side in (-1, 1):
            if row or side > 0:
                link_copy(paver, (step_center + side * (PAVER_WIDTH / 2 + 0.008), y, bed_z))
    for i in range(16):
        link_copy(paver, (-1.5 + i * 0.74, 10.72, bed_z))
    threshold = board("入户_宽踏步及落尘平台", (step_center, -0.434, -0.101),
                      (1.42, 0.868, 0.176), stone, 0, 0.38)
    threshold.modifiers[0].width = 0.011


def privacy_screen():
    wood, _ = white_oak_material("庭院屏风_浅木竖条", "WoodUV")
    steel = room_material("庭院屏风_下端锚固套", (0.115, 0.106, 0.091), 0.50, 0.54)
    width, height = SCREEN_WIDTH, SCREEN_HEIGHT
    parts = []
    for x in (-width / 2 + 0.039, width / 2 - 0.039):
        parts.extend((board("庭院屏风_立柱", (x, 0, height / 2 + 0.025), (0.078, 0.081, height - 0.025), wood, 2, x),
                      board("庭院屏风_立柱底套", (x, 0, 0.036), (0.09, 0.09, 0.072), steel, 2, 0)))
    for z in (0.19, 1.43):
        parts.append(board("庭院屏风_背面横撑", (0, 0.010, z), (width - 0.146, 0.046, 0.067), wood, 0, z))
    for i in range(21):
        x = (width - 0.206) * (i / 20 - 0.5)
        parts.append(board("庭院屏风_通风竖条", (x, -0.029, 0.844), (0.051, 0.040, 1.46), wood, 2, i * 0.11))
    place_new(SCREEN, parts, (6.1, 12.36, GRADE))
    screen = bpy.context.scene.objects[SCREEN]
    for x in (7.94, 9.78):
        link_copy(screen, (x, 12.36, GRADE))
    for y in (4.5, 6.34, 8.18):
        link_copy(screen, (12.15, y, GRADE), -radians(90))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bedroom-lighting/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "garden-enclosure/house.blend")
    parser.add_argument("--plant-source", type=Path)
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if any(scene.objects.get(asset) for asset in (TREE, SHRUB, PAVER, SCREEN)):
        raise RuntimeError("输入工程已布置庭院")
    ground(scene)
    roof()
    exterior_trim()
    paths()
    privacy_screen()
    plants(TREE, args.plant_source, "tree_small_02", (
        ((-3.40, 6.80, GRADE), 0.91, 0.94), ((5.58, 13.48, GRADE), -1.43, 1.0),
        ((-3.19, 0.96, GRADE), 1.90, 0.86), ((-3.30, 14.48, GRADE), 0.55, 1.12),
        ((14.65, 7.75, GRADE), -0.71, 0.96), ((1.01, -4.96, GRADE), 1.27, 0.91),
    ))
    plants(SHRUB, args.plant_source, "shrub_01", (
        ((-1.55, 4.51, GRADE + 0.006), 0.18, 0.63), ((-1.60, 7.98, GRADE + 0.006), 1.9, 0.60),
        ((3.20, 11.64, GRADE + 0.006), 2.27, 0.58), ((7.19, 11.63, GRADE + 0.006), 0.14, 0.66),
        ((9.72, 11.57, GRADE + 0.006), 1.94, 0.55), ((10.96, 6.67, GRADE + 0.006), 0.88, 0.54),
        ((-1.04, -1.13, GRADE), -0.12, 0.74), ((6.62, -1.11, GRADE), 2.13, 0.56),
        ((9.99, -0.98, GRADE + 0.006), -0.89, 0.52),
    ))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["garden-from-reading-chair"]
    bpy.ops.file.pack_all()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    args.renders.mkdir(parents=True, exist_ok=True)
    exposure = scene.view_settings.exposure
    for name in args.views:
        scene.camera = scene.objects[name]
        scene.view_settings.exposure = exposure - 1.75 if name in ("garden-arrival", "garden-northwest") else exposure
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
