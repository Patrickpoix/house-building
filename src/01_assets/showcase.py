"""01b 资产库「144 个预览模块」展示图（呼应视频）。

不修改资产库本体：打开资产库后在内存里搭陈列场景，直接渲染一张总览图，
不另存重复的 showcase.blend（几何与母库完全重复，约 44 MiB）。
asset_library.blend 保持干净的 144 个 Collection，Append / Instance 时
不会混入展台地板与灯光。
"""
import bpy, math, os

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

LIB = str(C.LIBRARY_BLEND)
SHOW_PNG = str(C.R_SHEETS / "asset_library_showcase.png")

bpy.ops.wm.open_mainfile(filepath=LIB)
scene = bpy.context.scene

assets = sorted([c for c in bpy.data.collections if c.name.startswith("AST_")],
                key=lambda c: c.name)
print("ASSET_COLLECTIONS", len(assets))

show = bpy.data.collections.new("SHOWCASE_144_MODULES")
scene.collection.children.link(show)

COLS = 12
GAP_X, GAP_Y = 1.5, 1.5
for i, c in enumerate(assets):
    row, col = divmod(i, COLS)
    e = bpy.data.objects.new("SHOW_" + c.name, None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = c
    # 阵列中心放在远离住宅的位置，不影响资产本体
    e.location = (col * GAP_X - (COLS - 1) * GAP_X / 2,
                  -row * GAP_Y - 14.0, 0)
    show.objects.link(e)

# 阵列展台地面 + 灯光 + 相机（便于直接出一张总览图）
mat = bpy.data.materials.new("showcase_floor"); mat.use_nodes = True
mat.node_tree.nodes.get("Principled BSDF").inputs['Base Color'].default_value = (0.16, 0.17, 0.19, 1)
mat.node_tree.nodes.get("Principled BSDF").inputs['Roughness'].default_value = 0.85
bpy.ops.mesh.primitive_plane_add(size=1.0)
fl = bpy.context.object
fl.name = "SHOWCASE_floor"
fl.scale = (20, 20, 1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
fl.location = (0, -14.0 - (math.ceil(len(assets) / COLS) - 1) * GAP_Y / 2, -0.02)
fl.data.materials.append(mat)
for c in list(fl.users_collection):
    c.objects.unlink(fl)
show.objects.link(fl)

ld = bpy.data.lights.new("SHOWCASE_key", 'AREA')
ld.energy = 5000; ld.shape = 'DISK'; ld.size = 14
lo = bpy.data.objects.new("SHOWCASE_key", ld); show.objects.link(lo)
lo.location = (0, -22, 16)
lo.rotation_euler = (0, 0, 0)

cd = bpy.data.cameras.new("SHOWCASE_cam"); cd.lens = 35
co = bpy.data.objects.new("SHOWCASE_cam", cd); show.objects.link(co)
cy = -14.0 - (math.ceil(len(assets) / COLS) - 1) * GAP_Y / 2
co.location = (0, cy - 16, 13)
from mathutils import Vector
co.rotation_euler = (Vector((0, cy, 0)) - co.location).to_track_quat('-Z', 'Y').to_euler()

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600; scene.render.resolution_y = 1000
scene.render.image_settings.file_format = 'PNG'
scene.camera = co
scene.render.filepath = SHOW_PNG

print("SHOWCASE_ADDED", len(assets))
bpy.ops.render.render(write_still=True)
print("SHOWCASE_RENDER", os.path.exists(SHOW_PNG), os.path.getsize(SHOW_PNG) if os.path.exists(SHOW_PNG) else 0)
