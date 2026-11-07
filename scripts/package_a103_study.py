"""把陶碗研究稿保存为可链接的独立资产包；不表示已经通过质量验收。"""

from pathlib import Path
import shutil
import bpy

ROOT = Path(__file__).resolve().parent.parent
source = ROOT / "stages" / "S002" / "A103-study"
target = ROOT / "assets" / "A103-study"
target.mkdir(parents=True, exist_ok=True)
(target / "textures").mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source / "study.blend"))
for image in bpy.data.images:
    if image.source != "FILE" or not image.filepath.startswith("//textures/"):
        continue
    original = Path(bpy.path.abspath(image.filepath))
    if not original.is_file():
        raise FileNotFoundError(original)
    shutil.copy2(original, target / "textures" / original.name)
collection = bpy.data.collections.new("A103_bowl_study")
collection.objects.link(bpy.data.objects["A103_bowl"])
collection.asset_mark()
bpy.data.libraries.write(str(target / "A103-study.blend"), {collection}, path_remap="NONE")
print(f"已写入研究资产包：{target}")
