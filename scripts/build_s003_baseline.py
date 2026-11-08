"""从 S001 另存可回退的整屋基线及起居空间检查镜头。"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stages" / "S003"
SOURCE = ROOT / "stages" / "S001" / "furnished-study.blend"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0

    camera_data = bpy.data.cameras.new("living_baseline_camera")
    camera = bpy.data.objects.new("living_baseline_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (5.85, 5.0, 1.55)
    target = Vector((1.2, 8.1, 1.15))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 24
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT / "living-baseline.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-baseline.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
