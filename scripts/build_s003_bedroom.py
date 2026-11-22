"""用可链接床架和床品替换 S003 卧室占位，并检查房间实景。"""

import argparse
from math import sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_floor_study import wood_floor_surface
from build_s003_living import mesh_object, place_new, textile, upholstered


BED = "A108"
BEDDING = "A109"
STAGES = ROOT / "stages/S003"
OPEN_AREA_FLOOR = "STUDY_起居餐厨木地板"
BEDROOM_FLOOR = "卧室_木地板"
ROOM_BOUNDS = (0.20, 0.20, 3.94, 3.94)
BED_CENTER = (1.60, 0.267)
VIEWS = {
    "bedroom-bed": ((2.61, 3.66, 1.49), (1.51, 1.32, 0.71), 26),
    "bedroom-bed-detail": ((2.59, 1.92, 1.53), (1.48, 0.91, 0.54), 35),
}


def bed_frame(wood):
    points = [
        board("床架_床头下横撑", (0, 0, 0.311), (1.64, 0.066, 0.128), wood, 0, 0.15),
        board("床架_床头顶梁", (0, 0, 0.839), (1.64, 0.059, 0.040), wood, 0, 0.26),
        board("床架_床尾围板", (0, 2.075, 0.269), (1.64, 0.045, 0.115), wood, 0, 0.3),
        board("床架_中心托梁", (0, 1.058, 0.260), (0.068, 1.95, 0.060), wood, 1, 0.37),
        board("床架_中心落地撑", (0, 1.058, 0.119), (0.064, 0.066, 0.238), wood, 2, 0.35),
    ]
    for side in (-1, 1):
        points.extend((
            board("床架_床头立柱", (side * 0.781, 0, 0.428), (0.063, 0.063, 0.856), wood, 2, side * 0.31),
            board("床架_长围板", (side * 0.782, 1.055, 0.269), (0.060, 2.020, 0.115), wood, 1, side * 0.26),
            board("床架_排骨条承台", (side * 0.739, 1.053, 0.278), (0.033, 1.963, 0.043), wood, 1, side * 0.36),
        ))
        foot = board("床架_床尾短脚", (side * 0.769, 2.049, 0.133), (0.074, 0.077, 0.266), wood, 2, side * 0.54)
        for vertex in foot.data.vertices:
            if vertex.co.z < 0:
                vertex.co.x *= 0.76
                vertex.co.y *= 0.76
        points.append(foot)
    for index in range(12):
        points.append(board("床架_实木排骨条", (0, 0.164 + index * 0.160, 0.311),
                            (1.535, 0.086, 0.024), wood, 0, index * 0.09))
    cloth = textile("床头板_苔灰混纺", (0.28, 0.30, 0.24))
    points.append(upholstered("床头板_软包面", (0, 0.008, 0.602), (1.51, 0.095, 0.451), cloth, 0.044))
    return points


def pillow(cloth, center, angle):
    # 鼓起的中部和较薄的封边由同一个封闭表面构成。
    steps = 30
    row = steps + 1
    side_size = row * row
    vertices, faces = [], []
    for side in (1, -1):
        for j in range(row):
            v = 2 * j / steps - 1
            for i in range(row):
                u = 2 * i / steps - 1
                x = 0.31 * u * (1 - 0.065 * v**8)
                y = 0.221 * v * (1 - 0.087 * u**8)
                swell = ((1 - u * u) * (1 - v * v)) ** 0.69
                depth = 0.062 if side > 0 else 0.024
                z = side * (0.008 + depth * swell) + 0.0025 * swell * sin(4 * u + v)
                vertices.append((x, y, z))
    for j in range(steps):
        for i in range(steps):
            a = row * j + i
            face = (a, a + 1, a + row + 1, a + row)
            faces.extend((face, tuple(index + side_size for index in reversed(face))))
    perimeter = (
        list(range(steps)) + [steps + j * row for j in range(steps)]
        + [steps * row + i for i in range(steps, 0, -1)] + [j * row for j in range(steps, 0, -1)]
    )
    for a, b in zip(perimeter, perimeter[1:] + perimeter[:1]):
        faces.append((b, a, a + side_size, b + side_size))
    obj = mesh_object("睡枕_蓬松枕芯与包边", vertices, faces, [cloth])
    uv = obj.data.uv_layers.new(name="FabricUV")
    for face in obj.data.polygons:
        face.use_smooth = True
        for loop in face.loop_indices:
            vertex = obj.data.loops[loop].vertex_index
            j, i = divmod(vertex % side_size, row)
            uv.data[loop].uv = (i / steps * 2, j / steps * 1.4)
    obj.location = center
    obj.rotation_euler.z = angle
    return obj


def quilt(cloth):
    def edge_fall(distance):
        t = max(0.0, min(distance, 1.0))
        return t * t * (3 - 2 * t)

    xs, ys = 66, 54
    vertices, faces = [], []
    for j in range(ys + 1):
        v = j / ys
        y = 0.747 + 1.420 * v
        for i in range(xs + 1):
            u = 2 * i / xs - 1
            x = 0.891 * u
            # 下垂起点由床垫侧面和床尾净边确定，避免薄被经过床垫内部。
            skirt = max(edge_fall((abs(x) - 0.769) / 0.12), edge_fall((y - 2.050) / 0.116))
            hem = max(abs(u)**14, v**18)
            wave = sin(17 * u + 6 * v) * (0.003 + 0.013 * hem) + 0.005 * sin(9 * v - 2 * u)
            fold = 0.009 * (1 - edge_fall(v * 18))
            round_y = y - 0.021 * (abs(u) ** 14) * (v ** 14)
            vertices.append((x, round_y, 0.544 - 0.170 * skirt + wave + fold))
    for j in range(ys):
        for i in range(xs):
            a = (xs + 1) * j + i
            faces.append((a, a + 1, a + xs + 2, a + xs + 1))
    obj = mesh_object("薄被_沿床侧与床尾下垂", vertices, faces, [cloth])
    uv = obj.data.uv_layers.new(name="FabricUV")
    for face in obj.data.polygons:
        face.use_smooth = True
        for loop in face.loop_indices:
            x, y, _ = obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uv.data[loop].uv = (x / 0.30, y / 0.30)
    thickness = obj.modifiers.new("薄被夹棉厚度", "SOLIDIFY")
    thickness.thickness = 0.026
    thickness.offset = -1
    smooth = obj.modifiers.new("被沿圆顺", "SUBSURF")
    smooth.levels = 1
    return obj


def bedding():
    ivory = textile("床品_暖白棉布", (0.72, 0.67, 0.57))
    moss = textile("床品_苔绿薄被", (0.25, 0.32, 0.23))
    mattress = upholstered("床垫_圆边与床笠", (0, 1.071, 0.419),
                           (1.536, 1.957, 0.192), ivory, 0.059, repeats=(4, 5))
    pillow_z = mattress.location.z + mattress.dimensions.z / 2 + 0.030
    return [mattress, pillow(ivory, (-0.366, 0.392, pillow_z), -0.035),
            pillow(ivory, (0.366, 0.385, pillow_z), 0.026), quilt(moss)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "table-setting/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bedroom-bed/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    previous = [obj for obj in scene.objects if obj.name.startswith(
        ("STUDY_bed_base", "STUDY_bed_head", "STUDY_mattress", "STUDY_pillow")
    )]
    if len(previous) != 5 or scene.objects.get(BED) or scene.objects.get(BEDROOM_FLOOR):
        raise RuntimeError("输入工程须保留原卧室床位，且尚未装入正式床架")
    floor = wood_floor_surface(BEDROOM_FLOOR, ROOM_BOUNDS, scene.objects[OPEN_AREA_FLOOR].data.materials[0])
    origin = Vector((*BED_CENTER, floor.data.vertices[0].co.z))
    for obj in previous:
        bpy.data.objects.remove(obj, do_unlink=True)
    wood, _ = white_oak_material("床架_白橡木皮", "WoodUV")
    place_new(BED, bed_frame(wood), origin)
    place_new(BEDDING, bedding(), origin)
    cameras = {name: scene_camera(scene, name, *view) for name, view in VIEWS.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    render_dir = args.renders.resolve()
    render_dir.mkdir(parents=True, exist_ok=True)
    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
