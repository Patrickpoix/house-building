"""将阅读椅材质对照版放入当前起居室，保留各来源工程。"""
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "stages/S003/side-table-study/house-side-table-study.blend"
CHAIR = ROOT / "tripo/outputs/reading-chair/fabric-study-v2/chair-fabric-study.blend"
OUT = ROOT / "stages/S003/chair-fabric-room-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.preferences.filepaths.save_version = 0
removed = 0
for obj in list(bpy.context.scene.objects):
    if obj.name.startswith("STUDY_reading_chair_"):
        bpy.data.objects.remove(obj, do_unlink=True)
        removed += 1
if not removed:
    raise RuntimeError("未找到阅读椅占位，避免重复装配")
with bpy.data.libraries.load(str(CHAIR), link=False) as (source, target):
    names = [name for name in source.objects if name.startswith("tripo_node_")]
    if len(names) != 1:
        raise RuntimeError(f"阅读椅网格数量异常：{len(names)}")
    target.objects = names
chair = target.objects[0]
bpy.context.scene.collection.objects.link(chair)
bpy.context.view_layer.update()
points = [chair.matrix_world @ Vector(p) for p in chair.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
factor = 0.78 / (high.z - low.z)
center = (low + high) / 2
chair.location = (chair.location - Vector((center.x, center.y, low.z))) * factor + Vector((3.02, 9.02, 0))
chair.scale *= factor
chair.name = "STUDY_reading_chair_fabric_v2"
bpy.context.view_layer.update()
scene = bpy.context.scene
camera = scene.camera
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1200, 800
for name, position, target, lens in (
    ("living", (5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
    ("chair-close", (4.75, 7.35, 1.35), (3.02, 9.02, 0.43), 45),
):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-chair-fabric-study.blend"))
print("阅读椅材质研究稿已试放，结构、贴图与房间仍待正式验收。")
