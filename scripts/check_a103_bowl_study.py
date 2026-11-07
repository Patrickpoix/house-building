"""核对陶碗研究稿的结构和贴图；不代替外观验收。"""

from pathlib import Path
import bmesh
import bpy
from mathutils import Vector

obj = bpy.data.objects["A103_bowl"]
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = obj.evaluated_get(depsgraph)
mesh = evaluated.to_mesh()
try:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    invalid = sum(not edge.is_manifold for edge in bm.edges)
    bm.free()
    if invalid:
        raise AssertionError(f"碗网格存在 {invalid} 条非流形边")
    coords = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    size = tuple(max(p[i] for p in coords) - min(p[i] for p in coords) for i in range(3))
    if not (0.22 < size[0] < 0.235 and 0.22 < size[1] < 0.235 and 0.085 < size[2] < 0.095):
        raise AssertionError(f"碗尺寸异常：{size}")
finally:
    evaluated.to_mesh_clear()
hit, point, _, _, found, _ = bpy.context.scene.ray_cast(depsgraph, Vector((0, 0, 0.15)), Vector((0, 0, -1)), distance=0.15)
if not hit or found != obj or not 0.015 < point.z < 0.03:
    raise AssertionError("碗中心无法从顶部到达内底")
for mat in obj.data.materials:
    for key in ("BaseColor", "Roughness", "Metallic", "Normal"):
        node = mat.node_tree.nodes.get("PBR_" + key)
        if node is None or node.image is None or not Path(bpy.path.abspath(node.image.filepath)).is_file():
            raise AssertionError(f"{mat.name} 缺少 {key} 贴图")
        if tuple(node.image.size) != (2048, 2048):
            raise AssertionError(f"{mat.name} 的 {key} 尺寸错误")
        expected = "sRGB" if key == "BaseColor" else "Non-Color"
        if node.image.colorspace_settings.name != expected or not node.outputs["Color"].is_linked:
            raise AssertionError(f"{mat.name} 的 {key} 颜色空间或连接错误")
print(f"A103 研究稿：尺寸 {tuple(round(v, 4) for v in size)} m；闭合网格、可达内底，2 组 2048 贴图路径及节点检查通过。")
