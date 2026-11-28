"""布置北侧洗涤台及东侧双灶的日常炊具。"""

import argparse
from math import cos, pi, radians, sin, tau
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_a103_bowl_study import ceramic_vessel
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import GLASS_Z, ZONE_CENTER_Y, ZONE_CENTERS, scene_camera
from build_s003_living import LIBRARY, RENDERS, cylinder, mesh_object, place_new, room_material
import texture_a019_study as pbr


POT, BOARD, RACK, SOAP = "A125", "A126", "A127", "A128"
VIEWS = {
    "kitchen-in-use": ((7.03, 6.91, 1.60), (9.12, 8.82, 1.18), 25),
    "kitchen-pot-prep": ((8.44, 7.45, 1.56), (9.41, 8.09, 1.02), 51),
    "kitchen-washing-props": ((7.11, 8.47, 1.62), (8.03, 9.48, 1.01), 34),
}


def lathe(name, surface, contour, bottom, inside):
    return ceramic_vessel(surface, surface, contour, name=name, underside_z=bottom,
                          inner_floor_z=inside, foot_height=0, planar_inner_row=len(contour) - 2,
                          uv_size=(0.25, 0.15), uv_repeats=2)


def rod(name, first, last, radius, metal):
    start, end = Vector(first), Vector(last)
    direction = end - start
    obj = cylinder(name, (start + end) / 2, radius, direction.length, metal, vertices=24)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def saucepan():
    steel = satin_steel(POT)
    phenolic = room_material("奶锅_深褐耐热酚醛", (0.072, 0.052, 0.037), 0.45)
    glass = room_material("奶锅_耐热玻璃", (0.91, 0.95, 0.96), 0.10)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1
    contour = (
        (0.067, 0.000), (0.073, 0.000), (0.077, 0.003), (0.080, 0.008), (0.081, 0.016),
        (0.083, 0.045), (0.086, 0.083), (0.087, 0.096), (0.090, 0.099), (0.090, 0.101),
        (0.088, 0.103), (0.085, 0.102), (0.083, 0.100), (0.082, 0.096), (0.080, 0.063),
        (0.079, 0.034), (0.077, 0.021), (0.072, 0.012), (0.065, 0.009), (0.050, 0.009),
    )
    rim = [(0.081, 0.098), (0.085, 0.099), (0.089, 0.103), (0.088, 0.108),
           (0.084, 0.109), (0.081, 0.107)]
    lid = [(0.012, 0.116), (0.034, 0.116), (0.057, 0.113), (0.079, 0.104),
           (0.081, 0.107), (0.080, 0.109), (0.070, 0.113),
           (0.056, 0.117), (0.033, 0.120), (0.012, 0.120)]
    parts = [
        lathe("奶锅_连续多层锅身", steel, contour, 0, 0.009),
        lathe("奶锅_弧面耐热玻璃盖", glass, lid, 0.116, 0.120),
        cylinder("奶锅_盖钮垫", (0, 0, 0.122), 0.017, 0.005, steel),
        cylinder("奶锅_盖钮握把", (0, 0, 0.135), 0.014, 0.025, phenolic, narrow=0.020),
        rounded_box("奶锅_把手承重卡座", (0.091, 0, 0.071), (0.025, 0.036, 0.027), 0.007, steel),
        rounded_box("奶锅_隔热手柄", (0.161, 0, 0.080), (0.128, 0.025, 0.019), 0.008, phenolic),
    ]
    # 盖圈形成真实环口，玻璃的上下表面保持透光。
    vertices = []
    sides = 96
    for radius, z in rim:
        vertices.extend((radius * cos(tau * i / sides), radius * sin(tau * i / sides), z) for i in range(sides))
    faces = []
    for row in range(len(rim)):
        for i in range(sides):
            a, b = row * sides + i, row * sides + (i + 1) % sides
            faces.append((a, b, (b + sides) % len(vertices), (a + sides) % len(vertices)))
    band = mesh_object("奶锅_玻璃盖包边", vertices, faces, [steel])
    uv = band.data.uv_layers.new(name="LidUV")
    for face in band.data.polygons:
        face.use_smooth = True
        for index in face.loop_indices:
            x, y, _ = vertices[band.data.loops[index].vertex_index]
            uv.data[index].uv = (0.5 + x / 0.18, 0.5 + y / 0.18)
    parts.append(band)
    for y in (-0.010, 0.010):
        pin = cylinder("奶锅_接头内侧实心铆钉", (0.080, y, 0.071), 0.0044, 0.005, steel)
        pin.rotation_euler.y = pi / 2
        parts.append(pin)
    return parts


def cutting_board():
    wood, _ = white_oak_material("砧板_白橡长纹", "WoodUV")
    middle, _ = white_oak_material("砧板_深色拼条", "WoodUV")
    shader = middle.node_tree.nodes["Principled BSDF"]
    color_node = shader.inputs["Base Color"].links[0].from_node
    pixels = np.empty(len(color_node.image.pixels), dtype=np.float32)
    color_node.image.pixels.foreach_get(pixels)
    oak = pixels.reshape(pbr.RESOLUTION, pbr.RESOLUTION, 4)[:, :, :3]
    # 将木纹染色保存进颜色图，避免 GLB 丢失 Blender 混色节点。
    pbr.OUTPUT = LIBRARY / BOARD
    color_node.image = pbr.save_image("dark-oak_BaseColor", oak * (0.77, 0.70, 0.61), False)
    color_node.image.filepath = str(pbr.OUTPUT / "textures/dark-oak_BaseColor.png")
    color_node.image.pack()
    slab = board("砧板_一体胶合板", (0, 0, 0.013), (0.322, 0.218, 0.026), wood, 0, 0.16)
    slab.modifiers[0].width = 0.006
    slab.modifiers[0].segments = 6
    # 边缘留出浅色握位，拼条可在回导时由独立网格保留。
    strip = board("砧板_深色端纹嵌条", (0, 0.075, 0.02605), (0.311, 0.008, 0.0002), middle, 0, 0.37)
    strip.modifiers[0].width = 0.00008
    return [slab, strip]


def draining_rack():
    steel = satin_steel(RACK)
    base = room_material("沥水架_石墨底托", (0.056, 0.064, 0.061), 0.49)
    feet = room_material("沥水架_防滑脚垫", (0.025, 0.031, 0.029), 0.72)
    parts = [rounded_box("沥水架_可抽洗底板", (0, 0, 0.010), (0.305, 0.237, 0.010), 0.004, base)]
    for x in (-0.148, 0.148):
        parts.append(rounded_box("沥水架_底托左右防溢沿", (x, 0, 0.019), (0.010, 0.229, 0.017), 0.004, base))
        for y in (-0.089, 0.089):
            parts.append(cylinder("沥水架_防滑脚垫", (x * 0.87, y, 0.003), 0.013, 0.006, feet))
    for y in (-0.114, 0.114):
        parts.append(rounded_box("沥水架_底托前后防溢沿", (0, y, 0.019), (0.291, 0.010, 0.017), 0.004, base))
        parts.append(rod("沥水架_承重横杆", (-0.136, y * 0.78, 0.030), (0.136, y * 0.78, 0.030), 0.005, steel))
        for x in (-0.121, 0.121):
            parts.append(rod("沥水架_横杆支座", (x, y * 0.78, 0.014), (x, y * 0.78, 0.032), 0.004, steel))
    for i in range(11):
        x = (i - 5) * 0.024
        parts.append(rod("沥水架_承碟底杆", (x, -0.089, 0.033), (x, 0.089, 0.033), 0.0027, steel))
    for i in range(6):
        x = (i - 2.5) * 0.040
        profile = [(x, -0.089, 0.034), (x + 0.014, -0.053, 0.101),
                   (x + 0.020, -0.035, 0.111), (x + 0.020, 0.035, 0.111),
                   (x + 0.014, 0.053, 0.101), (x, 0.089, 0.034)]
        parts.extend(rod("沥水架_斜插碟分隔杆", start, end, 0.0029, steel)
                     for start, end in zip(profile, profile[1:]))
    return parts


def soap_dispenser():
    steel = satin_steel(SOAP)
    glaze = room_material("洗涤剂瓶_灰绿釉", (0.20, 0.26, 0.18), 0.33)
    polymer = room_material("洗涤剂瓶_压泵密封芯", (0.055, 0.064, 0.051), 0.5)
    contour = (
        (0.026, 0.002), (0.030, 0.000), (0.035, 0.000), (0.038, 0.003),
        (0.039, 0.009), (0.039, 0.104), (0.037, 0.115), (0.028, 0.125),
        (0.018, 0.131), (0.016, 0.139), (0.013, 0.139), (0.012, 0.131),
        (0.014, 0.119), (0.031, 0.106), (0.034, 0.020), (0.027, 0.010),
    )
    return [
        lathe("洗涤剂瓶_连续陶瓷瓶体", glaze, contour, 0.002, 0.010),
        cylinder("洗涤剂瓶_旋口金属盖", (0, 0, 0.138), 0.018, 0.016, steel),
        cylinder("洗涤剂瓶_按压柱", (0, 0, 0.153), 0.0055, 0.020, steel),
        rounded_box("洗涤剂瓶_手按泵嘴", (0.013, 0, 0.165), (0.052, 0.019, 0.010), 0.004, steel),
        cylinder("洗涤剂瓶_出液孔芯", (0.034, 0, 0.159), 0.0032, 0.003, polymer),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "washing-station/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "kitchen-in-use/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    cooktop = scene.objects["A105"]
    pot_center = cooktop.matrix_world @ Vector((ZONE_CENTERS[0], ZONE_CENTER_Y, GLASS_Z))
    place_new(POT, saucepan(), pot_center, radians(-38))
    north_top = scene.objects["A123"].location.z
    place_new(BOARD, cutting_board(), Vector((9.40, 8.65, north_top)), radians(9))
    place_new(RACK, draining_rack(), Vector((8.54, 9.52, north_top)), radians(-2))
    place_new(SOAP, soap_dispenser(), Vector((7.48, 9.69, north_top)), radians(-58))
    tray = scene.objects["dining-serving-tray"]
    tray.location.x = 8.89
    tray.location.y = 9.49
    tray.rotation_euler.z = pi / 2
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["kitchen-in-use"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in VIEWS:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
