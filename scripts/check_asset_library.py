"""在干净场景追加 BLEND、回导 GLB，核对正式资产的尺度、UV 和自包含性。"""

import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# 格式往返应保留原轴心和尺度。亚毫米误差允许曲面求值及坐标精度差异。
BOUNDS_TOLERANCE_M = 0.0005


def inspect_objects(objects):
    bpy.context.view_layer.update()
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if not meshes:
        raise ValueError("没有可用网格")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum, maximum = np.full(3, np.inf), np.full(3, -np.inf)
    images = set()
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            if not mesh.polygons or not mesh.uv_layers or not mesh.materials:
                raise ValueError(f"{obj.name} 缺少面、UV 或材质")
            if mesh.validate(verbose=False):
                raise ValueError(f"{obj.name} 的网格需要修复")
            for material in mesh.materials:
                if not material or not material.node_tree:
                    raise ValueError(f"{obj.name} 有空材质或未启用的材质节点")
                for node in material.node_tree.nodes:
                    if node.type != "TEX_IMAGE":
                        continue
                    image = node.image
                    if not image or not image.packed_file or not all(image.size):
                        raise ValueError(f"{material.name} 有未打包或不可读取的贴图")
                    images.add((image.name, *image.size))
            points = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get("co", points)
            transform = np.asarray(evaluated.matrix_world, dtype=np.float64)
            points = points.reshape(-1, 3) @ transform[:3, :3].T + transform[:3, 3]
            if not np.isfinite(points).all():
                raise ValueError(f"{obj.name} 有无效顶点坐标")
            minimum = np.minimum(minimum, points.min(axis=0))
            maximum = np.maximum(maximum, points.max(axis=0))
        finally:
            evaluated.to_mesh_clear()
    return {"mesh_count": len(meshes), "bounds_m": [minimum.tolist(), maximum.tolist()],
            "size_m": (maximum - minimum).round(4).tolist(), "packed_images": sorted(images)}


def check_asset(folder):
    asset = folder.name
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(folder / f"{asset}.blend"), link=False) as (available, requested):
        if asset not in available.collections:
            raise ValueError("BLEND 缺少同名集合")
        requested.collections = [asset]
    collection = requested.collections[0]
    bpy.context.scene.collection.children.link(collection)
    blend = inspect_objects(collection.all_objects)
    # 追加本地集合后也会留下来源库记录，实际依赖由数据块的 library 指针决定。
    linked = {block.library.filepath for block in bpy.data.user_map() if block.library}
    if linked:
        raise ValueError(f"BLEND 存在外部链接数据块 {', '.join(sorted(linked))}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(folder / f"{asset}.glb"))
    glb = inspect_objects(bpy.context.scene.objects)
    difference = np.max(np.abs(np.asarray(blend["bounds_m"]) - glb["bounds_m"]))
    if difference > BOUNDS_TOLERANCE_M:
        raise ValueError(f"GLB 相对 BLEND 的轴心或包围盒偏移达 {difference:.4f} m")
    return {"asset": asset, "blend": blend, "glb": glb, "bounds_delta_m": round(float(difference), 6)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("assets", nargs="+", help="正式资产文件夹名称")
    parser.add_argument("--library", type=Path, default=ROOT / "assets")
    parser.add_argument("--house", type=Path, help="核对给定工程的装配引用")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.house:
        bpy.ops.wm.open_mainfile(filepath=str(args.house.resolve()))
        for lib in bpy.data.libraries:
            if not lib.filepath.startswith("//") or not Path(bpy.path.abspath(lib.filepath)).is_file():
                raise ValueError(f"工程有失效或绝对路径的链接库 {lib.filepath}")
        placed = {obj.instance_collection.name for obj in bpy.context.scene.objects
                  if obj.instance_collection and obj.instance_collection.library}
        missing = set(args.assets) - placed
        if missing:
            raise ValueError(f"工程缺少实际装配的资产 {', '.join(sorted(missing))}")
    failures = []
    for asset in args.assets:
        try:
            info = check_asset(args.library.resolve() / asset)
        except (RuntimeError, ValueError, OSError) as error:
            failures.append(f"{asset} {error}")
        else:
            print("ASSET " + json.dumps(info, ensure_ascii=False), flush=True)
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
