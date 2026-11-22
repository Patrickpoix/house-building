"""把餐厨新资产安装到已验收的 S003 工程并输出对应室内镜头。"""

import argparse
from math import cos, pi, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_living import place_new, textile, upholstered


HOUSE = ROOT / "house.blend"
RENDERS = ROOT / "renders/S003"
VIEWS = {
    "tray": ("dining-serving-tray", (7.72, 8.27, 1.61), (8.62, 9.45, 0.99), 56),
    "table": ("dining-table", (4.65, 5.50, 1.55), (6.12, 7.40, 0.85), 28),
    "chair": ("dining-chair", (7.40, 6.03, 1.25), (6.19, 7.07, 0.59), 38),
}


def rounded_rectangle(width, depth, z, radius, corner_steps):
    for corner, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        cx, cy = sx * (width / 2 - radius), sy * (depth / 2 - radius)
        for step in range(corner_steps):
            angle = (corner + step / (corner_steps - 1)) * pi / 2
            yield (cx + radius * cos(angle), cy + radius * sin(angle), z)


def tray(wood):
    profile = (
        (0.368, 0.248, 0.000, 0.029),
        (0.380, 0.260, 0.007, 0.035),
        (0.380, 0.260, 0.032, 0.035),
        (0.376, 0.256, 0.034, 0.033),
        (0.362, 0.242, 0.034, 0.028),
        (0.358, 0.238, 0.031, 0.026),
        (0.340, 0.220, 0.010, 0.019),
        (0.333, 0.213, 0.007, 0.018),
    )
    corner_steps = 9
    ring_size = 4 * corner_steps
    vertices = [point for ring in profile for point in rounded_rectangle(*ring, corner_steps)]
    faces = [tuple(reversed(range(ring_size)))]
    for ring in range(len(profile) - 1):
        for i in range(ring_size):
            a = ring_size * ring + i
            b = ring_size * ring + (i + 1) % ring_size
            faces.append((a, b, b + ring_size, a + ring_size))
    faces.append(tuple(range(len(vertices) - ring_size, len(vertices))))
    mesh = bpy.data.meshes.new("托盘_圆角整木")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="WoodUV")
    for face in mesh.polygons:
        # 托盘内外底面使用连续横纹，立边沿圆角过渡。
        normal_axis = max(range(3), key=lambda axis: abs(face.normal[axis]))
        u, v = (axis for axis in range(3) if axis != normal_axis)
        for loop_id in face.loop_indices:
            point = mesh.vertices[mesh.loops[loop_id].vertex_index].co
            uv.data[loop_id].uv = (0.19 + point[u] / 0.5, 0.41 + point[v] / 0.5)
        face.use_smooth = len(face.vertices) == 4
    obj = bpy.data.objects.new("白橡木有沿托盘", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(wood)
    return obj


def table(wood):
    objects = [board("餐桌_整板桌面", (0, 0, 0.735), (1.72, 0.88, 0.04), wood, 0, 0.25)]
    objects[0].modifiers[0].width = 0.012
    objects[0].modifiers[0].segments = 5
    for x in (-0.75, 0.75):
        for y in (-0.33, 0.33):
            leg = board("餐桌_木脚", (x, y, 0.358), (0.063, 0.063, 0.716), wood, 2, x * 0.36 + y)
            for vertex in leg.data.vertices:
                if vertex.co.z < 0:
                    vertex.co.x *= 0.69
                    vertex.co.y *= 0.69
                    vertex.co.x += 0.013 if x > 0 else -0.013
                    vertex.co.y += 0.013 if y > 0 else -0.013
            objects.append(leg)
    for y in (-0.33, 0.33):
        objects.append(board("餐桌_长围板", (0, y, 0.667), (1.453, 0.027, 0.098), wood, 0, 0.53))
    for x in (-0.75, 0.75):
        objects.append(board("餐桌_短围板", (x, 0, 0.667), (0.027, 0.615, 0.098), wood, 1, 0.13))
    return objects


def chair(wood):
    cloth = textile("餐椅_暖灰织物", (0.31, 0.29, 0.25))
    objects = [
        upholstered("餐椅_座垫", (0, -0.011, 0.433), (0.432, 0.415, 0.066), cloth, 0.028),
        upholstered("餐椅_靠背软包", (0, 0.185, 0.711), (0.424, 0.063, 0.192), cloth, 0.027, -0.16),
    ]
    for side in (-1, 1):
        x = side * 0.199
        front = board("餐椅_前脚", (x, -0.169, 0.201), (0.040, 0.040, 0.402), wood, 2, side * 0.37)
        back = board("餐椅_后脚及背柱", (x, 0.177, 0.403), (0.043, 0.046, 0.806), wood, 2, side * 0.24)
        for vertex in front.data.vertices:
            if vertex.co.z < 0:
                vertex.co.x *= 0.77
                vertex.co.y = vertex.co.y * 0.77 - 0.02
        for vertex in back.data.vertices:
            vertex.co.y += 0.037 * vertex.co.z / 0.403
        objects.extend((front, back))
        objects.append(board("餐椅_侧座框", (x, 0.003, 0.383), (0.039, 0.354, 0.042), wood, 1, side * 0.14))
    for y, z in ((-0.169, 0.383), (0.177, 0.383), (0.190, 0.623)):
        objects.append(board("餐椅_横撑", (0, y, z), (0.395, 0.040, 0.042), wood, 0, y))
    return objects


def install_chairs(asset, wood):
    placements = (
        (5.60, 6.72, pi), (6.50, 6.72, pi),
        (5.60, 8.08, 0), (6.50, 8.08, 0),
    )
    x, y, angle = placements[0]
    place_new(asset, chair(wood), Vector((x, y, 0)), angle)
    scene = bpy.context.scene
    first = scene.objects[asset]
    for x, y, angle in placements[1:]:
        instance = first.copy()
        scene.collection.objects.link(instance)
        instance.location = (x, y, 0)
        instance.rotation_euler.z = angle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("item", choices=VIEWS)
    item = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]).item
    bpy.ops.wm.open_mainfile(filepath=str(HOUSE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    asset, viewpoint, target, lens = VIEWS[item]
    if asset not in scene.objects:
        wood, _ = white_oak_material("餐厨家具_白橡木")
        if item == "tray":
            place_new(asset, [tray(wood)], Vector((8.62, 9.45, 0.94)), pi / 15)
        elif item == "table":
            for obj in list(scene.objects):
                if obj.name == "STUDY_dining_top" or obj.name.startswith("STUDY_table_leg"):
                    bpy.data.objects.remove(obj, do_unlink=True)
            position = Vector((6.05, 7.40, 0))
            bpy.context.view_layer.update()
            place_new(asset, table(wood), position)
        else:
            install_chairs(asset, wood)
    camera_name = f"kitchen-{item}"
    camera = scene.objects.get(camera_name)
    if camera is None:
        data = bpy.data.cameras.new(camera_name)
        camera = bpy.data.objects.new(camera_name, data)
        scene.collection.objects.link(camera)
    camera.location = viewpoint
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    bpy.context.view_layer.update()
    bpy.ops.wm.save_mainfile(compress=True)

    scene.camera = camera
    scene.render.filepath = str(RENDERS / f"{camera_name}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
