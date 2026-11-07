"""核对 A019 结构研究稿的尺寸与槽口，不将其作为成品资产验收。"""

import bpy
from mathutils import Vector

scene = bpy.context.scene
objects = [obj for obj in scene.objects if obj.type == "MESH" and obj.name.startswith("A019_")]
if len(objects) != 29:
    raise AssertionError(f"结构件数量异常：{len(objects)}")
points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
dimensions = tuple(max(p[i] for p in points) - min(p[i] for p in points) for i in range(3))
if any(abs(actual - target) / target > 0.02 for actual, target in zip(dimensions, (0.28, 0.32, 0.25))):
    raise AssertionError(f"整体尺寸超出设计容差：{dimensions}")
if abs(min(p.z for p in points)) > 0.001:
    raise AssertionError("底部未落在 z=0")
depsgraph = bpy.context.evaluated_depsgraph_get()
for origin, direction, expected in [
    ((0.15, 0.025, 0.075), (-1, 0, 0), "A019_side_vent"),
    ((0, 0.006, 0.26), (0, 0, -1), "A019_steam_vent"),
]:
    hit, _, _, _, obj, _ = scene.ray_cast(depsgraph, Vector(origin), Vector(direction), distance=0.03)
    if not hit or not obj.name.startswith(expected):
        raise AssertionError(f"槽口中心未命中内部件：{expected}，实际：{obj.name if obj else '无'}")
hinge = bpy.data.objects["A019_lid_hinge_pivot"]
hinge.rotation_euler.x = -1.308996939
bpy.context.view_layer.update()
hit, location, _, _, obj, _ = scene.ray_cast(depsgraph, Vector((0, 0, 0.4)), Vector((0, 0, -1)), distance=0.4)
if not hit or obj.name != "A019_inner_pot" or location.z > 0.18:
    raise AssertionError("打开盖后内胆中心不可达")
print(f"A019 研究稿检查通过：{len(objects)} 件，尺寸 {tuple(round(x, 4) for x in dimensions)} m；两个槽口和打开盖的内胆中心可达。")
