"""制作 V011 双灶，另存保留原住宅链接的 S003 餐厨工程。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import board
from build_s003_living import cylinder, place_new, room_material


ASSET = "A105"
WIDTH, DEPTH = 0.585, 0.355
ZONE_CENTERS = (-0.144, 0.144)
GLASS_Z = 0.056


def glass_material():
    texture_path = ROOT / f"assets/{ASSET}/textures/glass-basecolor.png"
    texture_path.parent.mkdir(parents=True, exist_ok=True)
    size = 2048
    pixels = np.arange(size, dtype=np.float32) + 0.5
    x = (pixels[None, :] / size - 0.5) * WIDTH
    y = (pixels[:, None] / size - 0.5) * DEPTH
    antialias = max(WIDTH, DEPTH) / size
    marks = np.zeros((size, size), dtype=np.float32)

    def stroke(distance, opacity):
        coverage = np.clip(0.5 - distance / antialias, 0, 1)
        np.maximum(marks, coverage * opacity, out=marks)

    for center in ZONE_CENTERS:
        dx, dy = x - center, y - 0.028
        radius = np.hypot(dx, dy)
        angle = np.arctan2(dy, dx)
        pattern = 0.31 + 0.37 * (np.abs(np.sin(angle * 2)) > 0.19)
        stroke(np.abs(radius - 0.101) - 0.00066, pattern)
        stroke(np.abs(radius - 0.085) - 0.00038, 0.36)
        stroke(np.maximum(np.abs(dx) - 0.004, np.abs(dy) - 0.0005), 0.50)
        stroke(np.maximum(np.abs(dx) - 0.0005, np.abs(dy) - 0.004), 0.50)

        control_y = y + 0.128
        for offset in (-0.024, 0.024):
            button_x = dx - offset
            stroke(np.maximum(np.abs(button_x) - 0.0036, np.abs(control_y) - 0.00045), 0.72)
        stroke(np.maximum(np.abs(dx - 0.024) - 0.00045, np.abs(control_y) - 0.0036), 0.72)
        stroke(np.maximum(np.abs(dx) - 0.008, np.abs(control_y) - 0.0042), 0.16)

    power_y = y + 0.128
    power_ring = np.abs(np.hypot(x, power_y) - 0.0055) - 0.00048
    stroke(np.where((power_y > 0.003) & (np.abs(x) < 0.0028), 1, power_ring), 0.75)
    stroke(np.maximum(np.abs(x) - 0.00048, np.abs(power_y - 0.005) - 0.0033), 0.75)

    dark = np.array((0.024, 0.028, 0.030), dtype=np.float32)
    ink = np.array((0.53, 0.55, 0.54), dtype=np.float32)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = dark + marks[:, :, None] * (ink - dark)
    image = bpy.data.images.new("A105_微晶玻璃印刷_2K", width=size, height=size, alpha=False)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(texture_path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)

    material = room_material("双灶_丝印微晶玻璃", tuple(dark), 0.36)
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Coat Weight"].default_value = 0.12
    shader.inputs["Coat Roughness"].default_value = 0.29
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(texture_path), check_existing=True)
    texture.extension = "EXTEND"
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    return material


def cooktop():
    chassis = room_material("双灶_石墨色机壳", (0.026, 0.030, 0.032), 0.44, 0.24)
    rubber = room_material("双灶_橡胶脚及散热槽", (0.009, 0.010, 0.012), 0.74)
    glass = glass_material()
    plate = board("双灶_微晶面板", (0, 0, GLASS_Z - 0.004), (WIDTH, DEPTH, 0.008), glass, 0, 0)
    plate.modifiers[0].width = 0.0034
    plate.modifiers[0].segments = 5
    plate.data.materials.append(chassis)
    for polygon in plate.data.polygons:
        if polygon.normal.z < 0.5:
            polygon.material_index = 1
            continue
        for loop in polygon.loop_indices:
            point = plate.data.vertices[plate.data.loops[loop].vertex_index].co
            plate.data.uv_layers.active.data[loop].uv = (point.x / WIDTH + 0.5, point.y / DEPTH + 0.5)

    housing_depth = 0.331
    body = board("双灶_收边机壳", (0, 0, 0.029), (0.564, housing_depth, 0.040), chassis, 0, 0)
    body.modifiers[0].width = 0.007
    body.modifiers[0].segments = 5
    objects = [plate, body]
    for x in (-0.24, 0.24):
        for y in (-0.133, 0.133):
            objects.append(cylinder("双灶_防滑脚", (x, y, 0.006), 0.013, 0.012, rubber))
    for center in ZONE_CENTERS:
        for index in range(9):
            x = center + (index - 4) * 0.009
            slot = board("双灶_散热格栅", (x, housing_depth / 2, 0.029), (0.0045, 0.001, 0.011), rubber, 0, 0)
            objects.append(slot)
    socket = board("双灶_后部电源接口", (0, housing_depth / 2, 0.028), (0.022, 0.004, 0.014), rubber, 0, 0)
    objects.append(socket)
    return objects


def scene_camera(scene, name, position, target, lens):
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    scene.collection.objects.link(camera)
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.lens = lens
    return camera


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "house.blend")
    parser.add_argument("--output", type=Path, default=ROOT / "stages/S003/kitchen-cooktop/house.blend")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if ASSET in scene.objects:
        raise RuntimeError(f"输入工程已安装 {ASSET}")
    counter = scene.objects["餐厨_东侧台面"]
    counter_top = max((counter.matrix_world @ Vector(corner)).z for corner in counter.bound_box)
    placeholder = scene.objects["STUDY_hob"]
    origin = Vector((placeholder.location.x, placeholder.location.y, counter_top))
    bpy.data.objects.remove(placeholder, do_unlink=True)
    place_new(ASSET, cooktop(), origin, -pi / 2)
    views = {
        "kitchen-cooktop": ((6.96, 5.28, 1.62), (9.17, 6.97, 1.02), 31),
        "cooktop-detail": ((8.55, 5.67, 1.69), (9.43, 5.98, 0.970), 50),
    }
    cameras = {name: scene_camera(scene, name, *view) for name, view in views.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    render_dir = ROOT / "renders/S003"
    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
