"""在 S003 的独立副本中检验开放起居餐厨木地板；不覆盖白模基线。"""

from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "stages" / "S003" / "house-baseline.blend"
OUT = ROOT / "stages" / "S003" / "floor-study"
TEXTURES = ROOT / "assets" / "materials" / "wood_floor"


def wood_floor_surface(name, bounds, material, z=0.002):
    x0, y0, x1, y1 = bounds
    vertices = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    layer = mesh.uv_layers.new(name="FloorUV")
    # 贴图原始图块宽约 1.7 m。
    for loop in mesh.loops:
        point = mesh.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = ((point.x - x0) / 1.7, (point.y - y0) / 1.7)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material)
    return obj


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

    wood_floor_surface("STUDY_起居餐厨木地板", (0.2, 4.06, 9.8, 9.8), mat)
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
