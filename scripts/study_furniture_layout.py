"""以家具占位和离散圆形通行包络检查 S001；不是最终家具模型。"""

from collections import deque
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S001"
STEP = 0.05
RADIUS = 0.35
COUNT = round(10 / STEP)

# 仅为平面设计占位，坐标为 x_min、y_min、x_max、y_max（米）。
FURNITURE = [
    ("bed", (0.30, 0.25, 1.90, 2.35)),
    ("wardrobe", (3.20, 0.25, 3.90, 2.00)),
    ("shower", (4.15, 0.20, 5.05, 1.10)),
    ("vanity", (4.15, 1.50, 4.80, 2.40)),
    ("toilet", (5.30, 1.65, 6.00, 2.40)),
    ("washer", (4.15, 2.65, 4.80, 3.35)),
    ("utility", (6.20, 2.65, 6.90, 3.40)),
    ("storage", (9.15, 2.10, 9.80, 3.80)),
    ("sofa", (0.25, 5.60, 1.15, 7.80)),
    ("bookshelf", (0.22, 8.50, 0.55, 9.65)),
    ("chair", (2.65, 8.65, 3.40, 9.40)),
    ("dining", (5.15, 6.65, 6.95, 8.15)),
    ("kitchen", (9.10, 4.70, 9.80, 9.60)),
    ("counter", (7.15, 9.10, 9.05, 9.80)),
]
TARGETS = {"bedroom": (2.55, 3.05), "bathroom": (6.30, 1.45),
           "utility": (5.80, 3.10), "living": (2.10, 6.00), "dining": (6.15, 5.65)}
START = (8.65, 0.65)


def object_rect(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return min(p.x for p in points), min(p.y for p in points), max(p.x for p in points), max(p.y for p in points)


def near_rect(x, y, rect):
    left, bottom, right, top = rect
    dx = max(left - x, 0, x - right)
    dy = max(bottom - y, 0, y - top)
    return dx * dx + dy * dy < RADIUS * RADIUS


def cell(point):
    return tuple(min(COUNT - 1, max(0, int(value / STEP))) for value in point)


def flat_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Emission Color"].default_value = (*color, 1)
    shader.inputs["Emission Strength"].default_value = 0.5
    return mat


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / "openings-study.blend"))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.view_layer.update()
    obstacles = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if obj.name.startswith("wall_"):
            points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            if min(p.z for p in points) < 1.0 < max(p.z for p in points):
                obstacles.append(object_rect(obj))
        elif obj.name.startswith("opening_") and ("_leaf" in obj.name or "_handle" in obj.name or "_jamb" in obj.name):
            obstacles.append(object_rect(obj))
    obstacles.extend(rect for _, rect in FURNITURE)
    blocked = set()
    for iy in range(COUNT):
        y = (iy + 0.5) * STEP
        for ix in range(COUNT):
            x = (ix + 0.5) * STEP
            if x < RADIUS or y < RADIUS or x > 10 - RADIUS or y > 10 - RADIUS or any(near_rect(x, y, r) for r in obstacles):
                blocked.add((ix, iy))
    start = cell(START)
    if start in blocked:
        raise RuntimeError("入口起点不满足通行包络")
    previous = {start: None}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            next_cell = (x + dx, y + dy)
            if 0 <= next_cell[0] < COUNT and 0 <= next_cell[1] < COUNT and next_cell not in blocked and next_cell not in previous:
                previous[next_cell] = (x, y)
                queue.append(next_cell)
    paths = {}
    for name, point in TARGETS.items():
        cursor = cell(point)
        if cursor not in previous:
            raise RuntimeError(f"入口不能以 {RADIUS * 2:.2f} m 圆形包络到达 {name} {point}")
        path = []
        while cursor is not None:
            path.append(((cursor[0] + 0.5) * STEP, (cursor[1] + 0.5) * STEP))
            cursor = previous[cursor]
        paths[name] = path
    mat = flat_material("layout_footprint_only", (0.56, 0.39, 0.24))
    text_mat = flat_material("layout_label", (0.035, 0.045, 0.035))
    for name, (x0, y0, x1, y1) in FURNITURE:
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, 0.10))
        obj = bpy.context.object
        obj.name = "FOOTPRINT_" + name
        obj.dimensions = (x1 - x0, y1 - y0, 0.20)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mat)
        bpy.ops.object.text_add(location=((x0 + x1) / 2, (y0 + y1) / 2, 0.22))
        label = bpy.context.object
        label.name = "LABEL_" + name
        label.data.body = name
        label.data.align_x = "CENTER"
        label.data.align_y = "CENTER"
        label.data.size = 0.18
        label.data.materials.append(text_mat)
    route_mat = flat_material("layout_route", (0.05, 0.42, 0.25))
    for name, path in paths.items():
        curve = bpy.data.curves.new("route_" + name, "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 0.014
        spline = curve.splines.new("POLY")
        spline.points.add(len(path) - 1)
        for point, (x, y) in zip(spline.points, path):
            point.co = (x, y, 0.03, 1)
        obj = bpy.data.objects.new("route_" + name, curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(route_mat)
    scene = bpy.context.scene
    camera = scene.camera
    camera.location = (5, 5, 25)
    camera.rotation_euler = (0, 0, 0)
    camera.data.ortho_scale = 11.3
    camera.data.clip_start = 23.8
    scene.render.filepath = str(OUTPUT / "layout-study.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "layout-study.blend"))
    bpy.ops.render.render(write_still=True)
    print(f"{len(FURNITURE)} 个占位；{len(paths)} 条路线在 {STEP:.2f} m 网格和直径 {2 * RADIUS:.2f} m 包络下可达。")


if __name__ == "__main__":
    main()
