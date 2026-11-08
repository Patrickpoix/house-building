"""以分板木书架替换 S003 占位体；独立保存供结构和房间检查。"""

from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "stages" / "S003" / "daylight-study" / "house-daylight-study.blend"
OUT = ROOT / "stages" / "S003" / "bookshelf-study"
TEXTURES = ROOT / "assets" / "materials" / "white_oak_veneer"


def board(name, center, dimensions, material, grain_axis, offset):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name="WoodUV")
    uv.name = "WoodUV"
    for polygon in obj.data.polygons:
        normal_axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
        axes = [i for i in range(3) if i != normal_axis]
        vertical = grain_axis if grain_axis in axes else axes[-1]
        horizontal = next(i for i in axes if i != vertical)
        for loop_id in polygon.loop_indices:
            co = obj.data.vertices[obj.data.loops[loop_id].vertex_index].co + obj.location
            uv.data[loop_id].uv = (co[horizontal] / 0.5 + offset, co[vertical] / 0.5)
    bevel = obj.modifiers.new("板边微倒角", "BEVEL")
    bevel.width = 0.0015
    bevel.segments = 3
    obj.modifiers.new("平滑法线", "WEIGHTED_NORMAL")
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    placeholder = bpy.data.objects.get("STUDY_bookshelf")
    if placeholder is None:
        raise RuntimeError("未找到书架占位体，停止以避免重复装配")
    bpy.data.objects.remove(placeholder, do_unlink=True)
    mat = bpy.data.materials.new("书架_白橡木皮_试验")
    mat.use_nodes = True
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "WoodUV"
    images = []
    for suffix, channel, color_space in (("diff", "Base Color", "sRGB"),
                                         ("rough", "Roughness", "Non-Color"),
                                         ("nor_gl", "Normal", "Non-Color")):
        path = TEXTURES / f"white_oak_veneer_{suffix}_2k.jpg"
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = color_space
        images.append((image, path))
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        if channel == "Normal":
            normal = tree.nodes.new("ShaderNodeNormalMap")
            tree.links.new(tex.outputs["Color"], normal.inputs["Color"])
            tree.links.new(normal.outputs["Normal"], shader.inputs[channel])
        else:
            tree.links.new(tex.outputs["Color"], shader.inputs[channel])
    shader.inputs["Metallic"].default_value = 0.0

    # 宽沿 Y、深沿 X；板件各自保留，内部连接尚需设计。
    for i, y in enumerate((8.509, 9.641)):
        board(f"书架侧板_{i}", (0.385, y, 1.05), (0.33, 0.018, 2.1), mat, 2, i * 0.23)
    board("书架背板", (0.226, 9.075, 1.05), (0.012, 1.114, 2.1), mat, 2, 0.14)
    for i, z in enumerate((0.06, 0.40, 0.74, 1.08, 1.42, 1.76, 2.091)):
        board(f"书架层板_{i}", (0.391, 9.075, z), (0.318, 1.114, 0.018), mat, 1, i * 0.13)
    scene = bpy.context.scene
    camera = scene.camera
    for name, position, target, lens in (
        ("living", (5.85, 5.0, 1.55), (1.2, 8.1, 1.15), 24),
        ("bookshelf-close", (1.85, 7.55, 1.50), (0.37, 9.08, 1.05), 48),
    ):
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = lens
        scene.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    camera.location = (5.85, 5.0, 1.55)
    camera.rotation_euler = (Vector((1.2, 8.1, 1.15)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 24
    scene.render.filepath = str(OUT / "living.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-bookshelf-study.blend"))
    for image, path in images:
        image.filepath = bpy.path.relpath(str(path))
    bpy.ops.wm.save_mainfile()
    print("书架分板研究已保存；接头、材质与空间仍待验收。")


if __name__ == "__main__":
    main()
