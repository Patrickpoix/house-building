"""从地板研究稿建立封顶日光试验，保留原有阶段工程。"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "stages" / "S003" / "floor-study" / "house-floor-study.blend"
OUT = ROOT / "stages" / "S003" / "daylight-study"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    ceiling = bpy.data.objects["ceiling_hidden_for_inspection"]
    ceiling.hide_render = False
    ceiling.hide_viewport = False
    bpy.data.objects["Area"].hide_render = True

    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    background = nodes.get("Background")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(42)
    sky.sun_rotation = math.radians(235)
    background.inputs["Strength"].default_value = 0.8
    world.node_tree.links.new(sky.outputs["Color"], background.inputs["Color"])
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    camera = scene.camera
    views = {
        "living": ((5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
        "kitchen": ((4.7, 5.2, 1.55), (8.5, 8.3, 1.1), 24),
        "floor-detail": ((2.7, 5.0, 1.15), (1.4, 7.8, 0.03), 35),
    }
    for name, (position, target, lens) in views.items():
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = lens
        scene.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    camera.location = views["living"][0]
    camera.rotation_euler = (Vector(views["living"][1]) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = views["living"][2]
    scene.render.filepath = str(OUT / "living.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-daylight-study.blend"))
    print("封顶日光试验已保存；房间和照明仍待验收。")


if __name__ == "__main__":
    main()
