"""在 S003 的独立副本中检验开放起居餐厨木地板；不覆盖白模基线。"""

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "stages" / "S003" / "house-baseline.blend"
OUT = ROOT / "stages" / "S003" / "floor-study"
TEXTURES = ROOT / "assets" / "materials" / "wood_floor"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    mat = bpy.data.materials.new("起居餐厨木地板_试验")
    mat.use_nodes = True
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "FloorUV"
    loaded_images = []
    for suffix, channel, color_space in (("diff", "Base Color", "sRGB"),
                                         ("rough", "Roughness", "Non-Color"),
                                         ("nor_gl", "Normal", "Non-Color")):
        path = TEXTURES / f"wood_floor_{suffix}_2k.jpg"
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = color_space
        loaded_images.append((image, path))
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        tree.links.new(uv.outputs["UV"], node.inputs["Vector"])
        if channel == "Normal":
            normal = tree.nodes.new("ShaderNodeNormalMap")
            tree.links.new(node.outputs["Color"], normal.inputs["Color"])
            tree.links.new(normal.outputs["Normal"], shader.inputs[channel])
        else:
            tree.links.new(node.outputs["Color"], shader.inputs[channel])
    shader.inputs["Metallic"].default_value = 0.0

    # 官方图块宽约 1.7 m；按米映射，保持物理尺寸。
    vertices = [(0.2, 4.06, 0.002), (9.8, 4.06, 0.002),
                (9.8, 9.8, 0.002), (0.2, 9.8, 0.002)]
    mesh = bpy.data.meshes.new("开放区地板网格")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    layer = mesh.uv_layers.new(name="FloorUV")
    for poly in mesh.polygons:
        for loop_id in poly.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_id].vertex_index].co
            layer.data[loop_id].uv = ((vertex.x - 0.2) / 1.7, (vertex.y - 4.06) / 1.7)
    obj = bpy.data.objects.new("STUDY_起居餐厨木地板", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    scene = bpy.context.scene
    scene.render.filepath = str(OUT / "living-floor.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-floor-study.blend"))
    for image, path in loaded_images:
        image.filepath = bpy.path.relpath(str(path))
    bpy.ops.wm.save_mainfile()
    bpy.ops.render.render(write_still=True)
    print("开放区木地板试验已保存；房间及材质仍待验收。")


if __name__ == "__main__":
    main()
