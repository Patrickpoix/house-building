"""在 S001 白模上构建可复跑的门窗研究稿。"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S001"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_s001_whitebox import WALLS, box, material, aim


def place(name, axis, fixed, along, depth, z, width, thickness, height, mat):
    center = (along, fixed + depth, z) if axis == "x" else (fixed + depth, along, z)
    size = (width, thickness, height) if axis == "x" else (thickness, width, height)
    obj = box(name, center, size, mat)
    bevel = obj.modifiers.new("edge_highlight", "BEVEL")
    bevel.width = 0.003
    bevel.segments = 3
    obj.modifiers.new("weighted_normals", "WEIGHTED_NORMAL")
    return obj


def make_frame(name, axis, fixed, a, b, low, high, mat):
    jamb = 0.035
    for along in (a + jamb / 2, b - jamb / 2):
        place(name + "_jamb", axis, fixed, along, 0, (low + high) / 2, jamb, 0.095, high - low, mat)
    for z in (low + jamb / 2, high - jamb / 2):
        place(name + "_rail", axis, fixed, (a + b) / 2, 0, z, b - a - 2 * jamb, 0.095, jamb, mat)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / "whitebox.blend"))
    bpy.context.preferences.filepaths.save_version = 0
    frame = material("opening_warm_wood", (0.37, 0.25, 0.14), 0.43)
    panel = material("opening_door_panel", (0.60, 0.49, 0.34), 0.50)
    metal = material("opening_hardware", (0.17, 0.16, 0.13), 0.28)
    metal.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = 0.85
    glass = material("opening_glass", (0.77, 0.86, 0.83), 0.08)
    shader = glass.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Transmission Weight"].default_value = 0.95
    doors = 0
    windows = 0
    for wall_name, axis, fixed, _, _, thickness, openings in WALLS:
        for index, (a, b, low, high) in enumerate(openings):
            key = f"opening_{wall_name}_{index}"
            if low > 0:
                windows += 1
                make_frame(key, axis, fixed, a, b, low, high, frame)
                width = b - a - 0.07
                panes = max(1, math.ceil(width / 1.20))
                for divider in range(1, panes):
                    place(key + "_mullion", axis, fixed, a + 0.035 + width * divider / panes, 0,
                          (low + high) / 2, 0.035, 0.075, high - low - 0.07, frame)
                for pane in range(panes):
                    pane_width = width / panes
                    left = a + 0.035 + pane_width * pane + (0.0175 if pane else 0)
                    right = a + 0.035 + pane_width * (pane + 1) - (0.0175 if pane + 1 < panes else 0)
                    place(key + "_glass", axis, fixed, (left + right) / 2, 0,
                          (low + high) / 2, right - left, 0.008, high - low - 0.07, glass)
                continue
            doors += 1
            # 门洞底部不设置门槛，保留地面连续性。
            make_frame(key, axis, fixed, a, b, 0, high, frame)
            threshold = bpy.data.objects.get(key + "_rail")
            bpy.data.objects.remove(threshold, do_unlink=True)
            hinge_along = a + 0.037
            swing = math.pi / 2 if wall_name in ("south", "bath_east") else -math.pi / 2
            # 铰轴位于门板开启侧，避免旋转时门板切入侧框。
            depth = math.copysign(0.023, swing) * (1 if axis == "x" else -1)
            hinge_position = (hinge_along, fixed + depth, 0) if axis == "x" else (fixed + depth, hinge_along, 0)
            bpy.ops.object.empty_add(type="PLAIN_AXES", location=hinge_position)
            hinge = bpy.context.object
            hinge.name = key + "_hinge"
            width = b - a - 0.074
            leaf = place(key + "_leaf", axis, fixed, hinge_along + width / 2, 0, (high - 0.04) / 2,
                         width, 0.04, high - 0.04, panel)
            handles = []
            for depth in (-0.027, 0.027):
                handles.append(place(key + "_handle", axis, fixed, b - 0.12, depth, 1.0, 0.11, 0.012, 0.018, metal))
            for obj in [leaf, *handles]:
                transform = obj.matrix_world.copy()
                obj.parent = hinge
                obj.matrix_world = transform
            hinge.rotation_euler.z = swing
    scene = bpy.context.scene
    camera = scene.camera
    camera.location = (18, -15, 25)
    camera.data.clip_start = 0.1
    camera.data.ortho_scale = 15
    aim(camera, (5, 5, 0))
    scene.render.filepath = str(OUTPUT / "openings-axonometric.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "openings-study.blend"))
    bpy.ops.render.render(write_still=True)
    print(f"门窗研究稿：{doors} 樘门、{windows} 处窗。")


if __name__ == "__main__":
    main()
