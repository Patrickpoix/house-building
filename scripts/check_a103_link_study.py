"""将资产库研究稿链接到住宅占位场景，检查贴图并渲染。"""

from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S002" / "A103-study"
library = ROOT / "assets" / "A103-study" / "A103-study.blend"
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "stages" / "S001" / "layout-study.blend"))
bpy.context.preferences.filepaths.save_version = 0
bpy.data.objects["LABEL_dining"].hide_render = True
with bpy.data.libraries.load(str(library), link=True) as (available, requested):
    if "A103_bowl_study" not in available.collections:
        raise RuntimeError("资产库缺少陶碗集合")
    requested.collections = ["A103_bowl_study"]
collection = requested.collections[0]
if collection.library is None:
    raise RuntimeError("陶碗不是链接资产")
instance = bpy.data.objects.new("linked_A103_bowl_study", None)
instance.instance_type = "COLLECTION"
instance.instance_collection = collection
instance.location = (6.0, 7.4, 0.20)
bpy.context.scene.collection.objects.link(instance)
images = set()
for obj in collection.objects:
    for mat in obj.data.materials:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                path = Path(bpy.path.abspath(node.image.filepath, library=node.image.library))
                if not path.is_file():
                    raise FileNotFoundError(path)
                images.add(path)
if len(images) != 8:
    raise RuntimeError(f"链接贴图数量异常：{len(images)}")
scene = bpy.context.scene
camera = scene.camera
camera.location = (6.8, 6.4, 0.95)
camera.rotation_euler = (Vector((6.0, 7.4, 0.24)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.clip_start = 0.05
camera.data.ortho_scale = 0.65
scene.render.resolution_x = scene.render.resolution_y = 900
scene.cycles.samples = 48
scene.render.filepath = str(OUTPUT / "linked-in-layout.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "linked-layout-study.blend"))
bpy.ops.render.render(write_still=True)
print("已从资产库链接陶碗集合并检查 8 张贴图路径；占位环境不是最终住宅。")
