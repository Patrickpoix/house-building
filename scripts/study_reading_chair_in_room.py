"""将原始阅读椅临时放入 S003；保留原模型及基线工程。"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "stages" / "S003" / "house-baseline.blend"
SOURCE = ROOT / "tripo" / "outputs" / "reading-chair" / "tripo-original.glb"
OUT = ROOT / "stages" / "S003" / "reading-chair-study"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith("STUDY_reading_chair_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise RuntimeError("阅读椅导入后没有网格")
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ Vector(corner) for obj in imported for corner in obj.bound_box]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    factor = 0.78 / (hi.z - lo.z)
    center = (lo + hi) / 2
    for obj in imported:
        obj.location = (obj.location - Vector((center.x, center.y, lo.z))) * factor + Vector((3.02, 9.02, 0))
        obj.scale *= factor
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    scene.render.filepath = str(OUT / "living-chair-study.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-chair-study.blend"))
    bpy.ops.render.render(write_still=True)
    print("临时阅读椅：等比缩放至高度 0.78 m；未通过正式验收。")


if __name__ == "__main__":
    main()
