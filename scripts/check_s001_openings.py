"""检查门窗研究稿的数量、父子关系和门洞估算净宽。"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_s001_whitebox import WALLS

doors, windows = 0, 0
bpy.context.view_layer.update()
for wall, axis, fixed, _, _, _, openings in WALLS:
    for index, (left, right, low, high) in enumerate(openings):
        key = f"opening_{wall}_{index}"
        jambs = [obj for obj in bpy.context.scene.objects if obj.name.startswith(key + "_jamb")]
        if len(jambs) != 2:
            raise AssertionError(f"{key} 缺少门窗框侧边")
        if low:
            windows += 1
            if not any(obj.name.startswith(key + "_glass") for obj in bpy.context.scene.objects):
                raise AssertionError(f"{key} 缺少玻璃")
        else:
            doors += 1
            hinge = bpy.data.objects[key + "_hinge"]
            leaf = bpy.data.objects[key + "_leaf"]
            if leaf.parent != hinge or not math.isclose(abs(hinge.rotation_euler.z), math.pi / 2, abs_tol=1e-5):
                raise AssertionError(f"{key} 门扇未按设计开启")
            along_axis = 0 if axis == "x" else 1
            occupied_end = max((obj.matrix_world @ Vector(corner))[along_axis]
                               for obj in hinge.children for corner in obj.bound_box)
            clear_estimate = right - 0.035 - occupied_end
            if clear_estimate <= 0:
                raise AssertionError(f"{key} 开门时通道被占满")
            print(f"{key}: 开启 90°，包围盒估算净宽 {clear_estimate:.3f} m")
if (doors, windows) != (4, 7):
    raise AssertionError(f"门窗数量异常：{doors}, {windows}")
print("门窗研究稿数量及门扇开启检查通过；扫掠另由 check_s001_door_sweep.py 检查。")
