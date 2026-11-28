"""从组装后的住宅文件渲染各房间和整屋尺度检查图。"""

import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


DEFAULT_VIEWS = (
    "garden-arrival", "living", "dining-window-counter", "kitchen-in-use",
    "bedroom-bed", "bathroom-complete", "utility-folding", "entry-arrival-interior", "house-plan",
)


def setup_cycles(scene, device):
    scene.render.engine = "CYCLES"
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.device = "CPU"
    if device == "CUDA":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        devices = prefs.get_devices_for_type("CUDA")
        if not any(item.type == "CUDA" for item in devices):
            raise RuntimeError("未发现可用 CUDA 设备，改用 --device CPU 重跑")
        for item in devices:
            item.use = item.type == "CUDA"
        scene.cycles.device = "GPU"


def plan_view(scene):
    # 只改变本次渲染的遮挡，场景文件继续保留完整屋面和室内吊顶。
    for item in scene.objects:
        if item.name.startswith(("屋盖_", "ceiling_hidden_for_inspection")):
            item.hide_render = True
        if item.instance_collection and item.instance_collection.name in {"A191", "A199", "A201"}:
            item.hide_render = True
    camera = scene.objects["camera_plan"]
    camera.location = Vector((5, 5, 18))
    camera.rotation_euler = (0, 0, 0)
    camera.data.clip_start = 0.1
    camera.data.ortho_scale = 11.6
    return camera


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("views", nargs="*", default=DEFAULT_VIEWS)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "renders/S003")
    parser.add_argument("--device", choices=("CPU", "CUDA"), default="CPU")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--samples", type=int, default=48)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    scene = bpy.context.scene
    setup_cycles(scene, args.device)
    scene.cycles.samples = args.samples
    scene.cycles.adaptive_threshold = 0.045
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_persistent_data = True
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for view in args.views:
        if view == "house-plan":
            continue
        scene.camera = scene.objects[view]
        scene.render.resolution_x, scene.render.resolution_y = args.width, round(args.width * 0.72)
        scene.render.filepath = str(output / f"review-{view}.png")
        bpy.ops.render.render(write_still=True)
    if "house-plan" in args.views:
        scene.camera = plan_view(scene)
        scene.render.resolution_x = scene.render.resolution_y = args.width
        scene.render.filepath = str(output / "review-house-plan.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
