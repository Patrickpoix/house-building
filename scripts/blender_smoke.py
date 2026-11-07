"""用 Blender 后台渲染一个最小场景，输出位置由调用者提供。"""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

if "--" not in sys.argv:
    raise SystemExit("用法：blender -b --python blender_smoke.py -- 输出图像路径")

output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
bpy.ops.object.light_add(type="AREA", location=(3, -4, 6))
bpy.context.object.data.energy = 800
bpy.context.object.data.shape = "DISK"
bpy.context.object.data.size = 5
bpy.ops.object.camera_add(location=(4, -6, 4))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.render.resolution_x = 96
scene.render.resolution_y = 96
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(output)
bpy.ops.render.render(write_still=True)
print(f"Blender {bpy.app.version_string}; render: {output}")
