"""将 Tripo 沙发临时试放，检查尺寸和房间比例；模型背部尚有缺陷。"""
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "stages/S003/chair-fabric-room-study/house-chair-fabric-study.blend"
SOFA = ROOT / "tripo/outputs/living-sofa/tripo-original.glb"
OUT = ROOT / "stages/S003/sofa-room-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.preferences.filepaths.save_version = 0
for name in ("STUDY_sofa_base", "STUDY_sofa_back"):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"找不到沙发占位：{name}")
    bpy.data.objects.remove(obj, do_unlink=True)
before = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(SOFA))
meshes = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]
if len(meshes) != 1:
    raise RuntimeError(f"沙发网格数量异常：{len(meshes)}")
sofa = meshes[0]
sofa.name = "STUDY_sofa_tripo_original"
sofa.matrix_world = Matrix.Rotation(math.pi / 2, 4, "Z") @ sofa.matrix_world
sofa.scale *= 2.2
bpy.context.view_layer.update()
points = [sofa.matrix_world @ Vector(p) for p in sofa.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
sofa.location += Vector((0.72 - (low.x + high.x) / 2, 6.7 - (low.y + high.y) / 2, -low.z))
bpy.context.view_layer.update()
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 1200, 800
scene.cycles.samples = 48
scene.cycles.use_denoising = True
camera = scene.camera
for name, position, target, lens in (
    ("living", (5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
    ("sofa-close", (3.1, 5.0, 1.25), (0.72, 6.7, 0.45), 35),
):
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-sofa-study.blend"))
print("沙发仅试放；背面双面座垫及空间碰撞待修复。")
