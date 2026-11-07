"""渲染指定研究稿的固定局部，用于暴露纹理与连接问题。"""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

if "--" not in sys.argv:
    raise SystemExit("用法：blender -b study-textured.blend --python render_study_closeup.py -- A019|A030")
asset = sys.argv[sys.argv.index("--") + 1]
targets = {"A019": ((0, -0.12, 0.19), 0.18), "A030": ((0, -0.06, 0.31), 0.24)}
if asset not in targets:
    raise ValueError(f"未知研究稿：{asset}")
target, scale = targets[asset]
scene = bpy.context.scene
camera = scene.camera
camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.ortho_scale = scale
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.cycles.samples = 64
filename = sys.argv[sys.argv.index("--") + 2] if len(sys.argv) > sys.argv.index("--") + 2 else "closeup-preview.png"
scene.render.filepath = str(Path(bpy.data.filepath).parent / filename)
bpy.ops.render.render(write_still=True)
