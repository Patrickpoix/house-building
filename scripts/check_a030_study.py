"""检查 A030 研究稿的袋身尺度、边界和开口；不代替材质及装配验收。"""

import bmesh
import bpy
from mathutils import Vector

body = bpy.data.objects["A030_generated_body"]
if any(abs(actual - target) / target > 0.02 for actual, target in zip(body.dimensions, (0.36, 0.12, 0.40))):
    raise AssertionError(f"袋身尺寸不符：{tuple(body.dimensions)}")
if not body.data.uv_layers:
    raise AssertionError("袋身缺少 UV")
bm = bmesh.new()
bm.from_mesh(body.data)
invalid = sum(not edge.is_manifold for edge in bm.edges)
bm.free()
if invalid:
    raise AssertionError(f"袋身存在 {invalid} 条非流形边")
handles = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name.startswith("A030_handle")
           and not obj.name.startswith("A030_handle_tab")]
if len(handles) != 2:
    raise AssertionError(f"提带数量异常：{len(handles)}")
depsgraph = bpy.context.evaluated_depsgraph_get()
hit, point, _, _, obj, _ = bpy.context.scene.ray_cast(
    depsgraph, Vector((0, 0, 0.65)), Vector((0, 0, -1)), distance=0.65
)
if not hit or obj != body or point.z > 0.35:
    raise AssertionError("袋口中心射线未到达袋内")
print(f"A030 研究稿检查通过：袋身 {tuple(round(x, 3) for x in body.dimensions)} m，非流形边 {invalid}，两个提带；袋口中心可达。")
