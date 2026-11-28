"""安装餐桌的搪瓷吊灯及餐区墙面的木框版画。"""

import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_s001_whitebox import HEIGHT, WALLS
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_kitchen_props import lathe
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material


PENDANT, PRINT = "A135", "A136"
SHELL_BOTTOM = -0.995
LENS_Z = SHELL_BOTTOM + 0.016
PRINT_SOURCE = ROOT / "references" / PRINT / "garden-woodcut.png"
VIEWS = {
    "dining-pendant-day": ((4.33, 5.35, 1.64), (6.54, 7.77, 1.36), 23),
    "dining-pendant-dusk": ((4.33, 5.35, 1.64), (6.54, 7.77, 1.36), 23),
    "dining-woodcut": ((4.35, 5.76, 1.49), (4.58, 4.09, 1.45), 49),
}


def pendant_parts():
    enamel = room_material("餐桌灯_红褐烧瓷", (0.197, 0.083, 0.053), 0.28, 0.12)
    steel = satin_steel(PENDANT)
    opal = room_material("餐桌灯_柔白扩散面", (0.92, 0.88, 0.77), 0.45)
    shader = opal.node_tree.nodes["Principled BSDF"]
    shader.inputs["Emission Color"].default_value = (1, 0.77, 0.51, 1)
    shader.inputs["Emission Strength"].default_value = 2.10
    cord = room_material("餐桌灯_深咖色悬吊线", (0.073, 0.052, 0.036), 0.64)
    profile = [
        (0.030, 0.152), (0.048, 0.147), (0.066, 0.132), (0.089, 0.108),
        (0.115, 0.078), (0.145, 0.052), (0.177, 0.029), (0.202, 0.011),
        (0.205, 0.006), (0.204, 0.001), (0.199, 0.001), (0.195, 0.007),
        (0.191, 0.014), (0.163, 0.033), (0.133, 0.056), (0.093, 0.100),
        (0.061, 0.130), (0.045, 0.141), (0.027, 0.145),
    ]
    shell = lathe("餐桌灯_连续卷口搪瓷伞罩", enamel, profile, 0.152, 0.145)
    shell.location.z = SHELL_BOTTOM
    start, end = SHELL_BOTTOM + 0.165, -0.027
    return [
        shell,
        cylinder("餐桌灯_内嵌扩散盘", (0, 0, LENS_Z), 0.194, 0.006, opal, vertices=96),
        cylinder("餐桌灯_吊顶杯", (0, 0, -0.012), 0.071, 0.024, enamel),
        cylinder("餐桌灯_吊顶应力套", (0, 0, -0.029), 0.011, 0.015, steel),
        cylinder("餐桌灯_线芯", (0, 0, (end + start) / 2), 0.003, end - start, cord),
        cylinder("餐桌灯_灯罩锁帽", (0, 0, SHELL_BOTTOM + 0.151), 0.026, 0.036, steel),
    ]


def woodcut_parts():
    width, height, lip = 0.82, 0.68, 0.021
    art_width, art_height = 0.67, 0.5025
    wood, _ = white_oak_material("版画_白橡窄边", "WoodUV")
    matte = room_material("版画_无酸纸卡", (0.80, 0.734, 0.64), 0.87)
    back = room_material("版画_硬纸衬板", (0.19, 0.132, 0.085), 0.88)
    art = room_material("版画_暖色棉纸印痕", (0.82, 0.66, 0.47), 0.82)
    image_node = art.node_tree.nodes.new("ShaderNodeTexImage")
    image_node.image = bpy.data.images.load(str(PRINT_SOURCE), check_existing=True)
    image_node.image.pack()
    art.node_tree.links.new(image_node.outputs["Color"], art.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    parts = [
        board("版画_背板", (0, 0.009, 0), (width - lip, 0.012, height - lip), back, 2, 0),
        board("版画_背挂条", (0, 0.0045, 0.248), (0.24, 0.009, 0.035), wood, 0, 0),
    ]
    for side in (-1, 1):
        parts.extend((
            board("版画_衬纸侧边", (side * (width - 2 * lip + art_width) / 4, 0.020, 0),
                  ((width - 2 * lip - art_width) / 2, 0.002, art_height), matte, 2, 0),
            board("版画_衬纸上下边", (0, 0.020, side * (height - 2 * lip + art_height) / 4),
                  (width - 2 * lip, 0.002, (height - 2 * lip - art_height) / 2), matte, 0, 0),
        ))
    surface = mesh_object("版画_庭边晨色", [
        (-art_width / 2, 0.0205, -art_height / 2), (-art_width / 2, 0.0205, art_height / 2),
        (art_width / 2, 0.0205, art_height / 2), (art_width / 2, 0.0205, -art_height / 2),
    ], [(0, 1, 2, 3)], [art])
    uv = surface.data.uv_layers.new(name="纸面满幅")
    for index, point in enumerate(((0, 0), (0, 1), (1, 1), (1, 0))):
        uv.data[index].uv = point
    parts.append(surface)
    outer = [(-width / 2, -height / 2), (width / 2, -height / 2),
             (width / 2, height / 2), (-width / 2, height / 2)]
    inner = [(x - (lip if x > 0 else -lip), z - (lip if z > 0 else -lip)) for x, z in outer]
    for side in range(4):
        following = (side + 1) % 4
        outline = [outer[side], outer[following], inner[following], inner[side]]
        vertices = [(x, y, z) for y in (0.002, 0.032) for x, z in outline]
        strip = mesh_object("版画_四十五度拼角窄框", vertices, [
            (0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
            (2, 6, 7, 3), (3, 7, 4, 0),
        ], [wood])
        uv = strip.data.uv_layers.new(name="WoodUV")
        for loop in strip.data.loops:
            x, y, z = vertices[loop.vertex_index]
            transverse, length = (z, x) if side % 2 == 0 else (x, z)
            uv.data[loop.index].uv = ((transverse + y) * 4.1, length * 2 + 0.27 * side)
        bevel = strip.modifiers.new("天然木窄边倒角", "BEVEL")
        bevel.width = 0.0015
        bevel.segments = 3
        strip.modifiers.new("框面法线", "WEIGHTED_NORMAL")
        parts.append(strip)
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "garden-enclosure/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "dining-lighting/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if any(scene.objects.get(asset) for asset in (PENDANT, PRINT)):
        raise RuntimeError("输入工程已装配餐桌灯或版画")
    table = scene.objects["dining-table"]
    position = Vector((table.location.x, table.location.y, HEIGHT))
    place_new(PENDANT, pendant_parts(), position)
    _, _, wall_y, start, _, thick, openings = next(w for w in WALLS if w[0] == "utility_north")
    art_x = (start + openings[0][0]) / 2
    place_new(PRINT, woodcut_parts(), (art_x, wall_y + thick / 2, 1.46))

    source = bpy.data.lights.new("餐桌_单盏暖光", "AREA")
    source.shape = "DISK"
    source.size = 0.37
    source.energy = 27
    source.spread = 1.84
    source.color = (1, 0.70, 0.45)
    fixture = bpy.data.objects.new(source.name, source)
    scene.collection.objects.link(fixture)
    fixture.location = position + Vector((0, 0, LENS_Z - 0.008))
    fixture["fixture"] = PENDANT

    cameras = {name: scene_camera(scene, name, *view) for name, view in VIEWS.items()}
    scene.camera = cameras["dining-pendant-day"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    world_strength = scene.world.node_tree.nodes["Background"].inputs["Strength"]
    daylight = world_strength.default_value
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in args.views:
        scene.camera = cameras[name]
        world_strength.default_value = daylight * 0.055 if name.endswith("-dusk") else daylight
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
