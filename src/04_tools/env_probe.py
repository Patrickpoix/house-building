"""环境通路验证：headless 建模 / 倒角 / PBR 节点 / Cycles CPU 渲染。

只做一次性的通路检查；验证图属于探针产物，不属于交付成果，可随时删除。
运行：blpython src/04_tools/env_probe.py
"""
import bpy, os, math
import mathutils

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

RENDER = str(C.R_SHEETS / "env_check.png")

# 清空
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials):
    bpy.data.materials.remove(m)

# 1. 建模 + 倒角
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.5))
cube = bpy.context.object
cube.name = "test_cube"
bev = cube.modifiers.new("bevel", 'BEVEL')
bev.width = 0.04
bev.segments = 3
cube.modifiers.new("weighted_normal", 'WEIGHTED_NORMAL')

bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.3, depth=0.6, location=(1.4, 0, 0.3))
cyl = bpy.context.object
cyl.name = "test_cyl"
b = cyl.modifiers.new("bevel", 'BEVEL'); b.width = 0.02; b.segments = 2
cyl.modifiers.new("weighted_normal", 'WEIGHTED_NORMAL')

# 2. PBR 材质节点（Principled BSDF + 贴图节点连线）
mat = bpy.data.materials.new("test_pbr"); mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")
for nm in ("Base Color", "Roughness", "Metallic"):
    img = nt.nodes.new('ShaderNodeTexImage'); img.name = nm
    nt.links.new(img.outputs['Color'], bsdf.inputs[nm])
nm_node = nt.nodes.new('ShaderNodeNormalMap')
nt.links.new(nm_node.outputs['Normal'], bsdf.inputs['Normal'])
cube.data.materials.append(mat)

# 3. 灯光 + 相机 + 地面
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.object
fm = bpy.data.materials.new("floor"); fm.diffuse_color = (0.6, 0.6, 0.6, 1); fm.use_nodes = True
fm.node_tree.nodes.get("Principled BSDF").inputs['Base Color'].default_value = (0.55, 0.55, 0.55, 1)
floor.data.materials.append(fm)

ld = bpy.data.lights.new("area", 'AREA'); ld.energy = 800; ld.shape = 'DISK'; ld.size = 4
lo = bpy.data.objects.new("area", ld); bpy.context.collection.objects.link(lo); lo.location = (1, -2, 4)

cam = bpy.data.cameras.new("cam"); co = bpy.data.objects.new("cam", cam)
bpy.context.collection.objects.link(co); co.location = (3.5, -5, 3)
co.rotation_euler = (mathutils.Vector((0.6, 0, 0.5)) - co.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = co

# 4. 渲染配置：Cycles CPU + 降噪
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x = 480; sc.render.resolution_y = 320; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = RENDER
sc.world.color = (0.05, 0.05, 0.05)

print("ENGINE", sc.render.engine, "DEVICE", sc.cycles.device)
print("BLENDER", bpy.app.version_string)
bpy.ops.render.render(write_still=True)
ok = os.path.exists(RENDER) and os.path.getsize(RENDER) > 1000
print("RENDER_OK", ok, os.path.getsize(RENDER) if os.path.exists(RENDER) else 0)
print("PROBE_DONE")
