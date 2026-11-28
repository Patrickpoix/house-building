"""按餐桌和餐垫的实际支撑面装配早餐器皿。"""

import argparse
from math import cos, radians, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a103_bowl_study import ceramic_vessel, material as ceramic_material
from build_s003_bedroom import STAGES
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe
from build_s003_living import LIBRARY, RENDERS, place_new, room_material
from build_s003_table_setting import place_repeated
import texture_a019_study as maps

PITCHER, PLATE, GLASS, SPOON = "A104", "A146", "A147", "A148"
VIEWS = {
    "dining-breakfast": ((4.75, 5.91, 1.55), (6.20, 7.58, 0.91), 32),
    "dining-ceramics": ((5.71, 6.59, 1.22), (6.02, 7.36, 0.84), 58),
}


def glaze(asset, title, color, roughness):
    maps.OUTPUT = LIBRARY / asset
    mat = ceramic_material(title, color, roughness, int(asset[1:]))
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.image.filepath = str(maps.OUTPUT / "textures" / bpy.path.basename(node.image.filepath))
            node.image.pack()
    return mat


def pitcher():
    cream = glaze(PITCHER, "手捏水壶_暖白细斑釉", (0.75, 0.675, 0.52), 0.31)
    clay = room_material("手捏水壶_无釉细陶足", (0.46, 0.35, 0.25), 0.71)
    profile = [(0.033, 0.003), (0.040, 0), (0.046, 0), (0.049, 0.004), (0.052, 0.011),
               (0.060, 0.028), (0.066, 0.054), (0.067, 0.078), (0.064, 0.103),
               (0.055, 0.127), (0.045, 0.147), (0.044, 0.159), (0.046, 0.171),
               (0.045, 0.175), (0.042, 0.176), (0.040, 0.173), (0.040, 0.160),
               (0.040, 0.148), (0.050, 0.126), (0.059, 0.103), (0.062, 0.078),
               (0.061, 0.057), (0.055, 0.034), (0.045, 0.017), (0.035, 0.013), (0.019, 0.013)]
    shell = ceramic_vessel(cream, clay, profile, name="水壶_捏嘴陶胎和连续壶腔", underside_z=0.003,
                           inner_floor_z=0.013, foot_height=0.007, planar_inner_row=24,
                           uv_size=(0.22, 0.14), uv_repeats=2)
    for vertex in shell.data.vertices:
        x, y, z = vertex.co
        length = (x * x + y * y) ** 0.5
        if length == 0:
            continue
        lobe = (max(0, -x / length) ** 18) * max(0, (z - 0.132) / 0.044) ** 1.6
        vertex.co.x -= 0.026 * lobe
        vertex.co.y *= 1 - 0.33 * lobe
        vertex.co.z += 0.005 * lobe
    # 使用一条连续握把，两个端点都进入壶壁。
    nodes = [(0.053, 0, 0.129), (0.066, 0, 0.138), (0.083, 0, 0.139), (0.103, 0, 0.128),
             (0.114, 0, 0.111), (0.116, 0, 0.092), (0.111, 0, 0.073),
             (0.098, 0, 0.059), (0.081, 0, 0.053), (0.061, 0, 0.050)]
    handle = tube("水壶_贯通D形陶握把", nodes, 0.0085, cream, sides=20)
    bevel = handle.modifiers.new("手压陶柄转角细化", "SUBSURF")
    bevel.levels = 2
    return [shell, handle]


def plate():
    surface = glaze(PLATE, "麦青釉面早餐盘", (0.44, 0.52, 0.44), 0.32)
    clay = room_material("餐盘_素陶圈足", (0.57, 0.43, 0.32), 0.66)
    profile = [(0.050, 0.003), (0.056, 0), (0.062, 0), (0.064, 0.003), (0.065, 0.006),
               (0.079, 0.007), (0.094, 0.014), (0.103, 0.021), (0.105, 0.025),
               (0.104, 0.028), (0.101, 0.029), (0.096, 0.024), (0.087, 0.019),
               (0.075, 0.015), (0.064, 0.013), (0.035, 0.012), (0.018, 0.012)]
    return [ceramic_vessel(surface, clay, profile, name="早餐盘_微翘盘沿和露胎圈足", underside_z=0.003,
                           inner_floor_z=0.012, foot_height=0.005, planar_inner_row=14,
                           uv_size=(0.22, 0.16), uv_repeats=2)]


def fluted_glass():
    glass = room_material("压纹水杯_烟灰透光玻璃", (0.78, 0.83, 0.73), 0.113)
    bsdf = glass.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Transmission Weight"].default_value = 1
    bsdf.inputs["IOR"].default_value = 1.48
    profile = [(0.019, 0), (0.027, 0), (0.031, 0.002), (0.032, 0.006), (0.033, 0.012),
               (0.034, 0.021), (0.035, 0.044), (0.037, 0.071), (0.038, 0.091),
               (0.038, 0.096), (0.036, 0.097), (0.034, 0.096), (0.033, 0.090),
               (0.032, 0.066), (0.030, 0.042), (0.028, 0.019), (0.026, 0.011), (0.015, 0.010)]
    cup = lathe("玻璃杯_实体杯壁与透光压纹", glass, profile, 0, 0.010)
    for i in range(1, 1 + 128 * 9):
        vertex = cup.data.vertices[i]
        x, y, z = vertex.co
        band = (min(1, z / 0.018, (0.096 - z) / 0.012)) * 0.0011
        multiplier = 1 + band * cos(tau * ((i - 1) % 128) / 8) / (x * x + y * y) ** 0.5
        vertex.co.x *= multiplier
        vertex.co.y *= multiplier
    return [cup]


def teaspoon(metal):
    bowl = lathe("茶匙_压制椭圆匙面", metal, [(0.005, 0), (0.012, 0.002), (0.017, 0.005),
                (0.019, 0.009), (0.018, 0.011), (0.016, 0.010), (0.013, 0.006),
                (0.009, 0.004), (0.005, 0.003)], 0, 0.003)
    for vertex in bowl.data.vertices:
        vertex.co.y *= 1.34
    bowl.location.y = 0.045
    stem = tube("茶匙_圆颈扁柄", [(0, -0.069, 0.0031), (0, -0.065, 0.0031), (0, -0.032, 0.0033),
                                    (0, 0.005, 0.0052), (0, 0.025, 0.0086)], 0.0031, metal)
    for vertex in stem.data.vertices:
        vertex.co.x *= 1.37
        vertex.co.z = max(0, vertex.co.z)
    return [bowl, stem]


def table_mats(scene):
    mats = [obj for obj in scene.objects if obj.instance_collection and obj.instance_collection.name == "A107"]
    source = mats[0].instance_collection.objects[0]
    textile_top = max(face.center.z for face in source.data.polygons if face.normal.z > 0.99 and len(face.vertices) > 4)
    return sorted(mats, key=lambda obj: (obj.location.y, obj.location.x)), textile_top


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "kitchen-everyday/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "breakfast/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    mat_objects, height = table_mats(scene)
    table = scene.objects["dining-table"]
    center = Vector((table.location.x, table.location.y, mat_objects[0].location.z))
    place_new(PITCHER, pitcher(), center + Vector((-0.179, 0.018, 0)), radians(-12))
    plates, teaspoons = [], []
    for mat in mat_objects:
        sign = 1 if mat.location.y > center.y else -1
        plates.append((mat.location + Vector((-0.044, sign * 0.021, height)), mat.rotation_euler.z))
        teaspoons.append((mat.location + Vector((-0.169, sign * 0.013, height)), radians(sign * 6)))
    place_repeated(PLATE, plate(), plates)
    place_repeated(SPOON, teaspoon(satin_steel(SPOON)), teaspoons)
    place_new(GLASS, fluted_glass(), mat_objects[2].location + Vector((0.106, -0.062, height)))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["dining-breakfast"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in args.views:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
