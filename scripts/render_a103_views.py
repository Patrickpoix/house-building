"""渲染陶碗研究稿的顶、侧、底视图，供人工检查。"""

from pathlib import Path
import bpy
from mathutils import Vector

scene = bpy.context.scene
camera = scene.camera
floor = bpy.data.objects["preview_floor_not_asset"]
lights = [obj for obj in scene.objects if obj.type == "LIGHT"]
scene.render.resolution_x = scene.render.resolution_y = 900
scene.cycles.samples = 48
output = Path(bpy.data.filepath).parent
for name, position, target in [
    ("top", (0, 0, 0.65), (0, 0, 0.04)),
    ("side", (0, -0.65, 0.10), (0, 0, 0.045)),
    ("bottom", (0, 0, -0.65), (0, 0, 0.04)),
]:
    floor.hide_render = name == "bottom"
    for light in lights:
        light.location.z = -abs(light.location.z) if name == "bottom" else abs(light.location.z)
        light.rotation_euler = (Vector((0, 0, 0.04)) - light.location).to_track_quat("-Z", "Y").to_euler()
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 0.275
    scene.render.filepath = str(output / f"view-{name}.png")
    bpy.ops.render.render(write_still=True)
