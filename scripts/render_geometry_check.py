"""回导 GLB 后渲染几何或 PBR 检查图。"""

import argparse
from math import radians
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


VIEWS = {
    "front": (2, -4, 2),
    "rear": (-2, 4, 2.4),
    "side": (4, -0.4, 0.7),
    "top": (0, -0.01, 4),
}


def main():
    if "--" not in sys.argv:
        raise SystemExit("用法：blender -b --python render_geometry_check.py -- 输入.glb 输出.png [--preserve-materials]")
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--preserve-materials", action="store_true")
    parser.add_argument("--view", choices=VIEWS, default="front")
    parser.add_argument("--rotate-z", metavar=("对象", "角度"), nargs=2, action="append", default=[])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, destination = args.source, args.destination
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
    for name, angle in args.rotate_z:
        target = bpy.context.scene.objects.get(name)
        if target is None:
            raise ValueError(f"回导场景缺少指定轴心 {name}")
        target.matrix_basis @= Matrix.Rotation(radians(float(angle)), 4, "Z")
    bpy.context.view_layer.update()
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("输入中没有网格")
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    center = (low + high) / 2
    extent = max(high - low)
    if extent <= 0:
        raise RuntimeError("网格包围盒无体积")
    if not args.preserve_materials:
        material = bpy.data.materials.new("geometry_preview")
        material.diffuse_color = (0.65, 0.68, 0.66, 1)
        for obj in meshes:
            obj.data.materials.clear()
            obj.data.materials.append(material)
    bpy.ops.object.light_add(type="AREA", location=center + Vector((extent * 2, -extent * 3, extent * 4)))
    light = bpy.context.object
    light.data.energy = 500 * extent * extent
    light.data.size = 3 * extent
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(location=center + extent * Vector(VIEWS[args.view]))
    camera = bpy.context.object
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = extent * 1.8
    scene = bpy.context.scene
    scene.camera = camera
    scene.world = bpy.data.worlds.new("geometry_preview_world")
    scene.world.color = (0.3, 0.3, 0.3)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    destination.parent.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(destination.resolve())
    bpy.ops.render.render(write_still=True)
    print(f"预览：{len(meshes)} 个网格；包围盒 {tuple(high - low)}")


if __name__ == "__main__":
    main()
