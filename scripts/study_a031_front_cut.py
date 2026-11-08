"""试验去掉 A031 生成网格背半部；结果仅用于判断可否保留正面细节。"""
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stages" / "S002" / "A031-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "tripo" / "outputs" / "A031" / "tripo-original.glb"))
obj = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bm = bmesh.new()
bm.from_mesh(obj.data)
# 模型正面朝 -Y；剖切仅用于观察，不声称修复了口袋或布料拓扑。
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                       dist=0.00001, plane_co=(0, 0, 0), plane_no=(0, 1, 0),
                       clear_outer=True, clear_inner=False)
bm.to_mesh(obj.data)
bm.free()
obj.name = "A031_front_cut_study"
solidify = obj.modifiers.new("test_fabric_thickness", "SOLIDIFY")
solidify.thickness = 0.002
solidify.offset = -1
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "front-cut-study.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT / "front-cut-study.glb"), export_format="GLB")
print("已保存 A031 正面剖切研究，尚需多视图检查。")
