"""在书架研究副本中试验背板木纹、底部收口与层板托销。"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import board

SOURCE = ROOT / "stages" / "S003" / "bookshelf-study" / "house-bookshelf-study.blend"
ALTERNATE_BACK = "--alternate-back" in sys.argv
OUT = ROOT / "stages" / "S003" / ("bookshelf-refinement" if ALTERNATE_BACK else "bookshelf-geometry")
TEXTURES = ROOT / "assets" / "materials" / "oak_veneer_01"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    images = []
    if ALTERNATE_BACK:
        back = bpy.data.objects["书架背板"]
        mat = bpy.data.materials.new("书架背板_橡木皮_试验")
        mat.use_nodes = True
        tree = mat.node_tree
        shader = tree.nodes.get("Principled BSDF")
        uv = tree.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "WoodUV"
        for suffix, resolution, channel, color_space in (
            ("diff", "4k", "Base Color", "sRGB"),
            ("rough", "2k", "Roughness", "Non-Color"),
            ("nor_gl", "2k", "Normal", "Non-Color"),
        ):
            path = TEXTURES / f"oak_veneer_01_{suffix}_{resolution}.jpg"
            image = bpy.data.images.load(str(path), check_existing=True)
            image.colorspace_settings.name = color_space
            images.append((image, path))
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
        back.data.materials.clear()
        back.data.materials.append(mat)
        layer = back.data.uv_layers["WoodUV"]
        for polygon in back.data.polygons:
            normal_axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
            axes = [i for i in range(3) if i != normal_axis]
            vertical = 2 if 2 in axes else axes[-1]
            horizontal = next(i for i in axes if i != vertical)
            for loop_id in polygon.loop_indices:
                co = back.data.vertices[back.data.loops[loop_id].vertex_index].co + back.location
                layer.data[loop_id].uv = (co[horizontal] / 1.8 + 0.13, co[vertical] / 1.8)

    original_wood = bpy.data.materials["书架_白橡木皮_试验"]
    board("书架底座前板", (0.515, 9.075, 0.025), (0.018, 1.114, 0.05), original_wood, 1, 0.37)
    metal = bpy.data.materials.new("层板托销_金属")
    metal.use_nodes = True
    bsdf = metal.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.42, 0.41, 0.38, 1)
    bsdf.inputs["Metallic"].default_value = 0.85
    bsdf.inputs["Roughness"].default_value = 0.32
    # 托销各与侧板和层板接触；此为方案示意，不代表结构强度已验证。
    for level in (0.40, 0.74, 1.08, 1.42, 1.76):
        for x in (0.29, 0.48):
            for y in (8.523, 9.627):
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.003, depth=0.012,
                                                   location=(x, y, level - 0.012),
                                                   rotation=(math.pi / 2, 0, 0))
                obj = bpy.context.object
                obj.name = "书架层板托销"
                obj.data.materials.append(metal)

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
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "house-bookshelf-refinement.blend"))
    for image, path in images:
        image.filepath = bpy.path.relpath(str(path))
    bpy.ops.wm.save_mainfile()
    print("书架局部精修研究已保存；仍需近景及结构验收。")


if __name__ == "__main__":
    main()
