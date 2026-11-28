"""装配主卧的床头阅读灯与西窗罗马帘。"""

import argparse
from math import pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bedroom import STAGES
from build_s003_bedroom_furnishings import NIGHTSTAND
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_props import lathe, rod
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material, textile


LAMP, SHADE = "A129", "A130"
LAMP_YAW = -pi / 2
LAMP_HEAD = Vector((0.06, 0.32, -0.099))
VIEWS = {
    "bedroom-reading-day": ((2.90, 3.65, 1.60), (1.23, 0.98, 1.25), 24),
    "bedroom-reading-corner": ((1.56, 1.82, 1.46), (0.35, 0.86, 1.16), 38),
    "bedroom-reading-dusk": ((2.90, 3.65, 1.60), (1.23, 0.98, 1.25), 24),
}


def lamp_parts():
    bronze = room_material("阅读灯_烟青色粉末烤漆", (0.075, 0.108, 0.087), 0.44, 0.17)
    metal = satin_steel(LAMP)
    opal = room_material("阅读灯_低眩光乳白扩散片", (0.85, 0.79, 0.64), 0.41)
    shader = opal.node_tree.nodes["Principled BSDF"]
    shader.inputs["Emission Color"].default_value = (1, 0.72, 0.45, 1)
    shader.inputs["Emission Strength"].default_value = 1.6
    parts = [
        rounded_box("阅读灯_藏线背板", (0, 0.015, 0), (0.100, 0.030, 0.146), 0.014, bronze),
        rounded_box("阅读灯_转轴底座", (0, 0.042, 0.016), (0.043, 0.041, 0.055), 0.006, bronze),
        cylinder("阅读灯_墙侧铰轴", (0, 0.057, 0.017), 0.014, 0.058, metal),
        rod("阅读灯_上臂", (0, 0.058, 0.017), (-0.024, 0.214, 0.032), 0.009, bronze),
        cylinder("阅读灯_肘部双垫铰轴", (-0.024, 0.214, 0.032), 0.016, 0.032, metal),
        rod("阅读灯_伸臂", (-0.024, 0.214, 0.032), (0.06, 0.32, -0.022), 0.008, bronze),
        cylinder("阅读灯_灯罩锁紧颈", (0.06, 0.32, -0.037), 0.014, 0.040, bronze),
        cylinder("阅读灯_下缘拨钮", (-0.026, 0.031, -0.041), 0.006, 0.006, metal),
    ]
    parts[-1].rotation_euler.x = pi / 2
    profile = [
        (0.018, 0.057), (0.034, 0.054), (0.050, 0.044), (0.063, 0.027),
        (0.068, 0.009), (0.068, 0.002), (0.066, 0), (0.064, 0.002),
        (0.064, 0.010), (0.059, 0.027), (0.047, 0.040), (0.032, 0.049), (0.018, 0.052),
    ]
    shell = lathe("阅读灯_卷边冲压灯罩", bronze, profile, 0.057, 0.052)
    shell.location = LAMP_HEAD
    parts.append(shell)
    parts.append(cylinder("阅读灯_内嵌扩散面", LAMP_HEAD + Vector((0, 0, 0.006)),
                          0.0643, 0.006, opal, vertices=96))
    return parts


def shade_parts(width):
    cloth = textile("罗马帘_浅燕麦亚麻", (0.47, 0.40, 0.32))
    hem = cloth.copy()
    hem.name = "罗马帘_折边亚麻"
    hem.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.358, 0.28, 1)
    rail = room_material("罗马帘_暖灰头轨", (0.31, 0.292, 0.251), 0.40, 0.43)
    parts = [rounded_box("罗马帘_隐藏头轨", (0, 0.034, -0.018), (width, 0.055, 0.036), 0.004, rail)]
    for x in (-width * 0.39, 0, width * 0.39):
        parts.append(rounded_box("罗马帘_背墙托片", (x, 0.014, -0.005), (0.034, 0.028, 0.051), 0.002, rail))

    # 四根横杆约束折幅，低边比两端稍松，布片连续包到压条后方。
    contour = [
        (0.058, -0.015), (0.060, -0.18), (0.067, -0.345),
        (0.076, -0.395), (0.092, -0.454), (0.100, -0.507),
        (0.096, -0.530), (0.082, -0.538), (0.070, -0.527), (0.067, -0.501),
        (0.079, -0.505), (0.087, -0.553), (0.085, -0.577),
        (0.072, -0.587), (0.058, -0.576), (0.053, -0.552),
        (0.063, -0.553), (0.073, -0.602), (0.070, -0.625),
        (0.058, -0.633), (0.048, -0.624), (0.044, -0.610),
        (0.042, -0.654), (0.032, -0.659),
    ]
    columns = 72
    stride = columns + 1
    vertices = []
    for row, (depth, z) in enumerate(contour):
        for i in range(stride):
            u = i / columns
            sag = (row / (len(contour) - 1)) ** 1.6 * sin(pi * u)
            vertices.append(((u - 0.5) * (width - 0.016), depth + 0.009 * sag, z - 0.016 * sag))
    faces = []
    for row in range(len(contour) - 1):
        for col in range(columns):
            a = row * stride + col
            faces.append((a, a + 1, a + stride + 1, a + stride))
    fabric = mesh_object("罗马帘_连续折幅", vertices, faces, [cloth, hem])
    uv = fabric.data.uv_layers.new(name="FabricUV")
    distance = [0.0]
    for a, b in zip(contour, contour[1:]):
        distance.append(distance[-1] + (Vector(a) - Vector(b)).length)
    for face in fabric.data.polygons:
        face.use_smooth = True
        row, col = divmod(face.index, columns)
        if col in (0, columns - 1) or row == len(contour) - 2:
            face.material_index = 1
        for index in face.loop_indices:
            r, c = divmod(fabric.data.loops[index].vertex_index, stride)
            uv.data[index].uv = (c / columns * width / 0.23, distance[r] / 0.23)
    smooth = fabric.modifiers.new("亚麻折边圆弧", "SUBSURF")
    smooth.levels = smooth.render_levels = 2
    thick = fabric.modifiers.new("布面包边", "SOLIDIFY")
    thick.thickness = 0.0018
    thick.material_offset_rim = 1
    parts.append(fabric)
    for z, depth in ((-0.515, 0.079), (-0.569, 0.063), (-0.614, 0.052), (-0.649, 0.032)):
        parts.append(rod("罗马帘_反面插杆", (-width / 2 + 0.022, depth, z),
                         (width / 2 - 0.022, depth, z), 0.0037, hem))
    return parts


def install(scene):
    _, _, axis_x, _, _, thick, openings = next(wall for wall in WALLS if wall[0] == "west")
    wall = axis_x + thick / 2
    y_min, y_max, _, head = openings[0]
    lamp_at = Vector((wall, scene.objects[NIGHTSTAND].location.y, 1.19))
    assert lamp_at.y + 0.10 < y_min
    place_new(LAMP, lamp_parts(), lamp_at, LAMP_YAW)
    place_new(SHADE, shade_parts(y_max - y_min + 0.13), (wall, (y_min + y_max) / 2, head + 0.074), LAMP_YAW)

    light = bpy.data.lights.new("主卧_床头暖光", "AREA")
    light.shape = "DISK"
    light.size = 0.105
    light.energy = 7.0
    light.color = (1.0, 0.68, 0.41)
    light.spread = 1.65
    source = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(source)
    source.location = lamp_at + Matrix.Rotation(LAMP_YAW, 3, "Z") @ (LAMP_HEAD - Vector((0, 0, 0.005)))
    source.rotation_euler = (0, 0, 0)
    source["fixture"] = LAMP


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "kitchen-in-use/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bedroom-lighting/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if any(scene.objects.get(asset) for asset in (LAMP, SHADE)):
        raise RuntimeError("输入工程已包含主卧新增资产")
    install(scene)
    cameras = {name: scene_camera(scene, name, *view) for name, view in VIEWS.items()}
    scene.camera = cameras["bedroom-reading-day"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    world_strength = scene.world.node_tree.nodes["Background"].inputs["Strength"]
    args.renders.mkdir(parents=True, exist_ok=True)
    for name, camera in cameras.items():
        scene.camera = camera
        if name.endswith("-dusk"):
            world_strength.default_value *= 0.027
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
