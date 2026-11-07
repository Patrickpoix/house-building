"""以连续布面重建 A030 袋身的独立试验，不覆盖原研究稿。"""

import math
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S002" / "A030-study"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_a030_study import mesh_grid, seam


def signed_power(value, power):
    return math.copysign(abs(value) ** power, value)


def front_surface(x, z):
    # 斜向的局部折线从袋底两侧向上延伸，袋口仍保持连续。
    envelope = math.sin(math.pi * min(1, max(0, z / 0.40))) ** 2
    broad = 0.0045 * math.sin(20 * x + 7 * z) + 0.002 * math.sin(45 * x - 15 * z)
    left = 0.010 * math.exp(-((x + 0.115 - 0.42 * z) / 0.024) ** 2 - ((z - 0.105) / 0.10) ** 2)
    right = -0.008 * math.exp(-((x - 0.125 + 0.35 * z) / 0.027) ** 2 - ((z - 0.10) / 0.09) ** 2)
    return -0.058 + envelope * (broad + left + right)


def create_body(canvas):
    count, rows = 160, 80
    vertices = []
    for row in range(rows + 1):
        z = 0.003 + 0.397 * row / rows
        for i in range(count):
            angle = 2 * math.pi * i / count
            x = 0.177 * signed_power(math.cos(angle), 0.48)
            y = 0.058 * signed_power(math.sin(angle), 0.48)
            fold = (front_surface(x, z) + 0.058) * abs(math.sin(angle)) ** 3
            y += fold if y < 0 else -fold * 0.6
            vertices.append((x, y, z))
    faces = []
    for row in range(rows):
        for i in range(count):
            nxt = (i + 1) % count
            faces.append((row * count + i, row * count + nxt, (row + 1) * count + nxt, (row + 1) * count + i))
    faces.append(tuple(reversed(range(count))))
    mesh = bpy.data.meshes.new("A030_continuous_body")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="fabric_uv")
    for face in mesh.polygons:
        for loop_index in face.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            row, column = divmod(vertex_index, count)
            u = column / count
            if len(face.vertices) == 4 and 0 in [v % count for v in face.vertices] and u > 0.5:
                u -= 1
            uv.data[loop_index].uv = (u, row / rows)
        face.use_smooth = len(face.vertices) == 4
    obj = bpy.data.objects.new("A030_continuous_body", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(canvas)
    thickness = obj.modifiers.new("fabric_thickness", "SOLIDIFY")
    thickness.thickness = 0.002
    thickness.offset = -1
    return obj


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / "study-textured.blend"))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.objects.remove(bpy.data.objects["A030_generated_body"], do_unlink=True)
    canvas = bpy.data.materials["study_flax_canvas"]
    thread = bpy.data.materials["study_natural_thread"]
    create_body(canvas)
    # 原研究稿的提带安装面比新袋面外移约 5 mm。
    for obj in bpy.context.scene.objects:
        if not obj.name.startswith(("A030_handle", "A030_handle_stitch")):
            continue
        if obj.type == "MESH":
            side_y = sum(vertex.co.y for vertex in obj.data.vertices) / len(obj.data.vertices)
        elif obj.type == "CURVE":
            side_y = obj.data.splines[0].points[0].co.y
        else:
            continue
        obj.location.y -= math.copysign(0.005, side_y)

    def pocket(u, v):
        x, z = (u - 0.5) * 0.19, 0.105 + v * 0.15
        lift = 0.0015 + 0.005 * math.sin(math.pi * u) * v ** 4
        return x, front_surface(x, z) - lift, z

    mesh_grid("A030_separate_pocket", 32, 24, pocket, canvas, 0.0015)
    # 三边固定，顶部留作口袋开口。
    path = [pocket(0.02, i / 20) for i in range(20, -1, -1)]
    path += [pocket(i / 32, 0.02) for i in range(1, 32)]
    path += [pocket(0.98, i / 20) for i in range(21)]
    seam("A030_pocket_stitch", [(x, y - 0.001, z) for x, y, z in path], thread)
    scene = bpy.context.scene
    scene.render.filepath = str(OUTPUT / "continuous-preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "continuous-study.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
