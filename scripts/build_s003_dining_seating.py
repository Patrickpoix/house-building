"""在 S003 餐桌两侧安装四把餐椅，并另存完整场景。"""

import argparse
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_dining import install_chairs


STAGES = ROOT / "stages/S003"
VIEWS = {
    "dining-seating": ((4.24, 5.73, 1.54), (6.13, 7.64, 0.73), 29),
    "dining-chair-detail": ((7.43, 5.92, 1.12), (6.45, 6.74, 0.42), 42),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "kitchen-cooktop/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "dining-seating/house.blend")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.absolute(), args.output.absolute()
    if source.resolve() == output.resolve():
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if "dining-table" not in scene.objects or "dining-chair" in scene.objects:
        raise RuntimeError("输入工程应有餐桌，且尚未安装餐椅")
    wood, _ = white_oak_material("餐椅_白橡木", "WoodUV")
    install_chairs("dining-chair", wood)
    cameras = {name: scene_camera(scene, name, *view) for name, view in VIEWS.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(ROOT / "renders/S003" / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
