"""核对研究稿贴图路径、颜色空间与节点连接；不代替外观验收。"""

import sys
from pathlib import Path

import bpy

asset = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "A019"
material_sets = {
    "A019": ("study_ivory_enamel", "study_brushed_steel", "study_graphite_polymer", "study_rubber"),
    "A030": ("study_flax_canvas", "study_olive_webbing", "study_natural_thread"),
}
if asset not in material_sets:
    raise ValueError(f"未知研究稿：{asset}")
materials = material_sets[asset]
checked = 0
for name in materials:
    mat = bpy.data.materials[name]
    nodes = mat.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    for map_name in ("BaseColor", "Roughness", "Metallic", "Normal"):
        node = nodes.get(f"PBR_{map_name}")
        if node is None or node.image is None:
            raise AssertionError(f"缺少贴图节点：{name} {map_name}")
        image = node.image
        if not Path(bpy.path.abspath(image.filepath)).is_file():
            raise AssertionError(f"贴图断链：{image.filepath}")
        if tuple(image.size) != (2048, 2048):
            raise AssertionError(f"贴图尺寸错误：{image.name} {tuple(image.size)}")
        expected = "sRGB" if map_name == "BaseColor" else "Non-Color"
        if image.colorspace_settings.name != expected:
            raise AssertionError(f"贴图颜色空间错误：{image.name}")
        if not node.outputs["Color"].is_linked:
            raise AssertionError(f"贴图未连接：{image.name}")
        if map_name != "Normal":
            socket_name = {"BaseColor": "Base Color", "Roughness": "Roughness", "Metallic": "Metallic"}[map_name]
            links = shader.inputs[socket_name].links
            if len(links) != 1 or links[0].from_node != node:
                raise AssertionError(f"贴图未连接到正确输入：{image.name}")
        else:
            links = shader.inputs["Normal"].links
            if len(links) != 1 or links[0].from_node.type != "NORMAL_MAP":
                raise AssertionError(f"法线转换节点缺失：{image.name}")
            normal_links = links[0].from_node.inputs["Color"].links
            if len(normal_links) != 1 or normal_links[0].from_node != node:
                raise AssertionError(f"法线贴图未连接到转换节点：{image.name}")
        checked += 1
    for socket in ("Base Color", "Roughness", "Metallic", "Normal"):
        if not shader.inputs[socket].is_linked:
            raise AssertionError(f"着色器输入未连接：{name} {socket}")
print(f"{asset} 研究稿检查通过：{checked} 张 2048 贴图路径、颜色空间及节点连接。")
