"""检查 Tripo GLB 的网格、UV、材质节点和贴图；不修改原始资产。"""
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
if len(args) != 2:
    raise SystemExit("用法：-- 输入.glb 输出.json")
source, output = map(Path, args)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
meshes = []
for obj in bpy.data.objects:
    if obj.type == "MESH":
        mesh = obj.data
        mesh.calc_loop_triangles()
        uv_info = []
        for uv in mesh.uv_layers:
            coords = np.empty(len(uv.data) * 2, dtype=np.float32)
            uv.data.foreach_get("uv", coords)
            coords = coords.reshape(-1, 2)
            triangles = np.array([tri.loops[:] for tri in mesh.loop_triangles], dtype=np.int32)
            points = coords[triangles]
            a, b = points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]
            area2 = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
            uv_info.append({"name": uv.name, "min": coords.min(axis=0).tolist(),
                            "max": coords.max(axis=0).tolist(),
                            "triangles_with_near_zero_uv_area": int((area2 < 1e-12).sum()),
                            "triangles": len(triangles)})
        bm = bmesh.new()
        bm.from_mesh(mesh)
        nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
        bm.free()
        meshes.append({"name": obj.name, "vertices": len(obj.data.vertices),
                       "faces": len(obj.data.polygons), "uv_layers": [uv.name for uv in obj.data.uv_layers],
                       "uv_analysis": uv_info, "nonmanifold_edges": nonmanifold,
                       "dimensions_m_unscaled": list(obj.dimensions)})
materials = []
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    nodes = mat.node_tree.nodes
    shader = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    channels = {}
    if shader:
        for name in ("Base Color", "Roughness", "Metallic", "Normal"):
            socket = shader.inputs[name]
            channels[name] = [{"node": link.from_node.name, "type": link.from_node.type,
                               "output": link.from_socket.name} for link in socket.links]
    textures = []
    for node in nodes:
        if node.type != "TEX_IMAGE" or not node.image:
            continue
        image = node.image
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        sample = pixels.reshape(-1, 4)[::64, :3]
        textures.append({"node": node.name, "image": image.name, "size": list(image.size),
                         "colorspace": image.colorspace_settings.name, "packed": bool(image.packed_file),
                         "sample_rgb_min": sample.min(axis=0).tolist(),
                         "sample_rgb_max": sample.max(axis=0).tolist()})
    links = [{"from": link.from_node.name, "output": link.from_socket.name,
              "to": link.to_node.name, "input": link.to_socket.name} for link in mat.node_tree.links]
    materials.append({"name": mat.name, "channels": channels, "textures": textures, "links": links})
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"source": str(source), "meshes": meshes, "materials": materials},
                             ensure_ascii=False, indent=2), encoding="utf-8")
print(f"检查完成：{len(meshes)}个网格，{len(materials)}个节点材质；{output}")
