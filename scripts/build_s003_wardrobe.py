"""用双轨移门衣柜替换 S003 主卧储物体块。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bedroom import BEDROOM_FLOOR
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, cylinder, place_new, room_material


ASSET = "A110"
STAGES = ROOT / "stages/S003"
WIDTH = 1.730
HEIGHT = 2.245
DEPTH = 0.655
CASE_DEPTH = 0.580
CASE_CENTER = 0.042
SIDE = 0.024
DOOR_WIDTH = 0.865
DOOR_HEIGHT = 2.089
DOOR_BOTTOM = 0.094
DOOR_TRAVEL = 0.807
VIEWS = {
    "bedroom-wardrobe": ((1.27, 3.67, 1.59), (3.28, 1.16, 1.24), 31),
    "wardrobe-detail": ((2.71, 2.74, 1.49), (3.23, 1.31, 1.12), 44),
}


def wardrobe():
    wood, _ = white_oak_material("移门衣柜_白橡木皮", "WoodUV")
    anodized = room_material("移门衣柜_暖灰阳极铝", (0.15, 0.13, 0.102), 0.4, 0.6)
    rail_metal = room_material("衣柜_挂杆拉丝镍", (0.36, 0.33, 0.28), 0.35, 0.68)
    parts = []

    def panel(name, position, size, grain=2, offset=0, material=wood):
        obj = board(name, position, size, material, grain, offset)
        parts.append(obj)
        return obj

    side_x = (WIDTH - SIDE) / 2
    inner = WIDTH - 2 * SIDE
    for side in (-1, 1):
        panel("衣柜_通高侧板", (side * side_x, -0.002, HEIGHT / 2),
              (SIDE, DEPTH + 0.012, HEIGHT), offset=0.22 * side)
    panel("衣柜_连续背板", (0, DEPTH / 2 - 0.010, HEIGHT / 2), (inner, 0.014, HEIGHT - 0.028), offset=0.4)
    panel("衣柜_顶板", (0, CASE_CENTER, HEIGHT - 0.014), (inner, CASE_DEPTH, 0.028), 0, 0.37)
    panel("衣柜_底板", (0, CASE_CENTER, 0.074), (inner, CASE_DEPTH, 0.028), 0, 0.53)
    panel("衣柜_后退踢脚", (0, -0.178, 0.032), (inner, 0.024, 0.064), 0, 0.3)
    panel("衣柜_中隔板", (-0.094, 0.044, 1.157), (0.024, 0.538, 2.138), offset=0.56)
    left_center = (-inner / 2 - 0.106) / 2
    right_center = (inner / 2 - 0.082) / 2
    for index, z in enumerate((0.47, 0.86, 1.23, 1.58, 1.94)):
        panel("衣柜_叠放层板", (left_center, 0.048, z), (inner / 2 - 0.106, 0.526, 0.024), 0, 0.13 * index)
    bay_width = inner / 2 + 0.082
    for z in (0.338, 1.942):
        panel("衣柜_挂区隔板", (right_center, 0.048, z), (bay_width, 0.526, 0.024), 0, 0.35)
    hangbar = cylinder("衣柜_实心挂衣杆", (right_center, 0.039, 1.821), 0.014, bay_width, rail_metal)
    hangbar.rotation_euler.y = pi / 2
    parts.append(hangbar)
    for x in (right_center - bay_width / 2 + 0.009, right_center + bay_width / 2 - 0.009):
        collar = cylinder("衣柜_挂杆端座", (x, 0.039, 1.821), 0.025, 0.018, rail_metal)
        collar.rotation_euler.y = pi / 2
        parts.append(collar)

    panel("衣柜_上轨承板", (0, -0.291, 2.210), (inner, 0.100, 0.023), 0, 0.2)
    panel("衣柜_下轨承板", (0, -0.291, 0.079), (inner, 0.100, 0.023), 0, 0.2)
    for track_y in (-0.322, -0.274):
        for z in (0.093, 2.193):
            panel("衣柜_上下独立导轨", (0, track_y, z), (inner, 0.018, 0.011), 0, material=anodized)
    for label, x, y in (("左", -0.409, -0.322), ("右", 0.409, -0.274)):
        prefix = f"衣柜_{label}移门"
        panel(f"{prefix}_面板", (x, y, DOOR_BOTTOM + DOOR_HEIGHT / 2),
              (DOOR_WIDTH, 0.023, DOOR_HEIGHT), offset=0.37 + x)
        # 拉手靠近各自外侧，错层移门重合时拉手不会挡住另一扇门。
        pull_x = x + (-0.366 if label == "左" else 0.366)
        panel(f"{prefix}_拉条", (pull_x, y - 0.024, 1.14), (0.013, 0.012, 0.318), material=anodized)
        for z in (1.025, 1.255):
            panel(f"{prefix}_拉条支脚", (pull_x, y - 0.016, z), (0.011, 0.014, 0.025), material=anodized)
    return parts


def render_glb_openings(render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / ASSET / f"{ASSET}.glb"))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("衣柜回导检查")
    scene.world.color = (0.28, 0.28, 0.28)
    doors = {side: [obj for obj in scene.objects if obj.name.startswith(f"衣柜_{side}移门")]
             for side in ("左", "右")}
    if any(len(parts) != 4 for parts in doors.values()):
        raise RuntimeError("GLB 缺少可独立检查的移门或拉手")
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
    for position, power, size in (((-2, -3.1, 3.3), 265, 2.9), ((1.9, -2, 2.5), 190, 2.5)):
        bpy.ops.object.light_add(type="AREA", location=position)
        light = bpy.context.object
        light.data.energy = power
        light.data.size = size
        light.rotation_euler = (Vector((0, 0, 1.2)) - light.location).to_track_quat("-Z", "Y").to_euler()
    camera = scene_camera(scene, "wardrobe-open", (-1.10, -4.6, 2.37), (0, 0, 1.10), 47)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.70
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 30
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = (850, 950)
    for side, shift, view in (("左", DOOR_TRAVEL, "wardrobe-shelves-glb"),
                              ("右", -DOOR_TRAVEL, "wardrobe-hanging-glb")):
        for obj in doors[side]:
            obj.location.x += shift
        scene.render.filepath = str(render_dir / f"{view}.png")
        bpy.ops.render.render(write_still=True)
        for obj in doors[side]:
            obj.location.x -= shift


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bedroom-bed/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bedroom-wardrobe/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    old = scene.objects["STUDY_wardrobe"]
    origin = old.location.copy()
    origin.z = scene.objects[BEDROOM_FLOOR].data.vertices[0].co.z
    bpy.data.objects.remove(old, do_unlink=True)
    place_new(ASSET, wardrobe(), origin, -pi / 2)
    cameras = {name: scene_camera(scene, name, *view) for name, view in VIEWS.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    render_dir = args.renders.resolve()
    render_dir.mkdir(parents=True, exist_ok=True)
    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    render_glb_openings(render_dir)


if __name__ == "__main__":
    main()
