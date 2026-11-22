"""制作餐桌陶杯、车线餐垫，并接续 S003 餐厨工程。"""

import argparse
from math import cos, pi, sin
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_a103_bowl_study import ceramic_vessel, material as glaze_material
from build_s003_cooktop import scene_camera
from build_s003_dining import rounded_rectangle
from build_s003_living import LIBRARY, mesh_object, place_new, room_material, textile
import texture_a019_study as textures


MUG = "A106"
MAT = "A107"
MUG_PROFILE = (
    (0.026, 0.0035), (0.030, 0.0035), (0.031, 0.002), (0.032, 0),
    (0.035, 0), (0.036, 0.0011), (0.036, 0.004), (0.038, 0.006),
    (0.040, 0.012), (0.042, 0.023), (0.045, 0.042), (0.046, 0.065),
    (0.045, 0.083), (0.045, 0.092), (0.0445, 0.094), (0.0435, 0.095),
    (0.0418, 0.095), (0.0405, 0.094), (0.040, 0.092), (0.040, 0.085),
    (0.041, 0.064), (0.040, 0.047), (0.038, 0.032), (0.035, 0.023),
    (0.030, 0.016), (0.024, 0.0145), (0.012, 0.014),
)
VIEWS = {
    "dining-table-setting": ((4.24, 5.73, 1.54), (6.13, 7.64, 0.73), 29),
    "table-setting-detail": ((6.96, 6.77, 1.36), (6.45, 7.25, 0.77), 44),
}


def mug():
    textures.OUTPUT = LIBRARY / MUG
    glaze = glaze_material("青灰石陶釉", (0.33, 0.42, 0.39), 0.27, 106)
    for node in glaze.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.image.filepath = str(textures.OUTPUT / "textures" / bpy.path.basename(node.image.filepath))
            node.image.pack()
    clay = room_material("露胎圈足", (0.36, 0.26, 0.18), 0.65)
    cup = ceramic_vessel(
        glaze, clay, MUG_PROFILE, name="马克杯_带圈足的空心杯身", underside_z=0.0035,
        inner_floor_z=0.014, foot_height=0.004, planar_inner_row=24,
        uv_size=(0.12, 0.125), uv_repeats=2,
    )

    # 两端埋入厚壁，保留干净的内杯壁和贯通握孔。
    steps, sides = 48, 20
    vertices = []
    for step in range(steps + 1):
        angle = (step / steps - 0.5) * pi
        x = 0.038 + 0.003 * sin(angle) + 0.033 * cos(angle)
        z = 0.052 + 0.029 * sin(angle)
        tangent = Vector((0.003 * cos(angle) - 0.033 * sin(angle), 0, 0.029 * cos(angle)))
        normal = tangent.cross(Vector((0, 1, 0))).normalized()
        for side in range(sides):
            cross = 2 * pi * side / sides
            offset = normal * (0.007 * cos(cross)) + Vector((0, 0.0058 * sin(cross), 0))
            vertices.append(Vector((x, 0, z)) + offset)

    faces = [tuple(range(sides))]
    for step in range(steps):
        for side in range(sides):
            a = step * sides + side
            b = step * sides + (side + 1) % sides
            faces.append((b, a, a + sides, b + sides))
    faces.append(tuple(reversed(range(steps * sides, len(vertices)))))
    handle = mesh_object("马克杯_椭圆截面单柄", vertices, faces, [glaze])
    uv = handle.data.uv_layers.new(name="ceramic_uv")
    for face in handle.data.polygons:
        is_side = len(face.vertices) == 4
        face.use_smooth = is_side
        segment = (face.index - 1) % sides
        for loop in face.loop_indices:
            vertex = handle.data.loops[loop].vertex_index
            row, side = divmod(vertex, sides)
            if is_side:
                if segment == sides - 1 and side == 0:
                    side = sides
                uv.data[loop].uv = (side / sides, row / steps)
            else:
                angle = 2 * pi * side / sides
                uv.data[loop].uv = (0.5 + 0.15 * cos(angle), 0.5 + 0.15 * sin(angle))
    # 细分会抬高圈足，以评估网格的实际接触面作为资产原点。
    bpy.context.view_layer.update()
    evaluated = cup.evaluated_get(bpy.context.evaluated_depsgraph_get())
    bottom = min(vertex.co.z for vertex in evaluated.data.vertices)
    cup.location.z -= bottom
    handle.location.z -= bottom
    return [cup, handle]


def placemat():
    linen = textile("餐垫_亚麻平织", (0.40, 0.30, 0.20))
    binding = textile("餐垫_加密锁边", (0.31, 0.21, 0.125))
    nodes = linen.node_tree.nodes
    diffuse = nodes.new("ShaderNodeTexImage")
    # 0.16 m 纹理平铺 96 根经纬纱，相邻经纬纱交替压在表面。
    threads = 96
    coordinate = np.arange(textures.RESOLUTION, dtype=np.float32) * threads / textures.RESOLUTION
    strand = np.sin(pi * (coordinate % 1)) ** 0.55
    parity = coordinate.astype(np.int32) % 2
    over = parity[:, None] == parity[None, :]
    yarn = np.where(over, strand[None, :], strand[:, None])
    dye = np.random.default_rng(107).uniform(0.92, 1.08, size=threads).astype(np.float32)
    strand_dye = dye[coordinate.astype(np.int32)]
    shade = (0.58 + 0.46 * yarn) * np.where(over, strand_dye[None, :], strand_dye[:, None])
    colors = np.where(over[:, :, None], (0.72, 0.64, 0.49), (0.62, 0.52, 0.36))
    textures.OUTPUT = LIBRARY / MAT
    diffuse.image = textures.save_image("餐垫_亚麻经纬_BaseColor", shade[:, :, None] * colors, False)
    diffuse.image.filepath = str(textures.OUTPUT / "textures" / bpy.path.basename(diffuse.image.filepath))
    diffuse.image.pack()
    cloth_shader = nodes.get("Principled BSDF")
    linen.node_tree.links.new(diffuse.outputs["Color"], cloth_shader.inputs["Base Color"])
    cloth_shader.inputs["Normal"].links[0].from_node.inputs["Strength"].default_value = 0.72
    # 轻微隆起的锁边顶面连接外托边与平织主体，侧面保留织物厚度。
    profile = (
        (0.416, 0.296, 0.0000, 0.023),
        (0.420, 0.300, 0.0016, 0.025),
        (0.418, 0.298, 0.0043, 0.024),
        (0.405, 0.285, 0.0044, 0.018),
        (0.401, 0.281, 0.0036, 0.017),
    )
    corner_steps = 9
    size = 4 * corner_steps
    vertices = [point for ring in profile for point in rounded_rectangle(*ring, corner_steps)]
    faces = [tuple(reversed(range(size)))]
    for row in range(len(profile) - 1):
        for col in range(size):
            a = row * size + col
            b = row * size + (col + 1) % size
            faces.append((a, b, b + size, a + size))
    faces.append(tuple(range(len(vertices) - size, len(vertices))))
    obj = mesh_object("餐垫_平织芯与锁边", vertices, faces, [linen, binding])
    uv = obj.data.uv_layers.new(name="WeaveUV")
    for face in obj.data.polygons:
        face.material_index = int(len(face.vertices) == 4)
        for loop in face.loop_indices:
            x, y, _ = obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uv.data[loop].uv = (x / 0.16, y / 0.16)
    return obj


def place_repeated(asset, objects, positions):
    origin, angle = positions[0]
    place_new(asset, objects, origin, angle)
    scene = bpy.context.scene
    original = scene.objects[asset]
    for position, angle in positions[1:]:
        instance = original.copy()
        scene.collection.objects.link(instance)
        instance.location = position
        instance.rotation_euler.z = angle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "stages/S003/dining-seating/house.blend")
    parser.add_argument("--output", type=Path, default=ROOT / "stages/S003/table-setting/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if not scene.objects.get("dining-chair") or scene.objects.get(MUG) or scene.objects.get(MAT):
        raise RuntimeError("输入工程须含正式餐椅，且餐桌新资产尚未安装")
    table = scene.objects["dining-table"]
    top = table.instance_collection.objects["餐桌_整板桌面"]
    table_top = max((table.matrix_world @ top.matrix_world @ Vector(corner)).z for corner in top.bound_box)
    mat = placemat()
    # 最后一面是锁边围住的平织面，杯脚不按锁边顶点定位。
    mat_top = mat.data.polygons[-1].center.z
    mats, mugs = [], []
    for row in (-1, 1):
        for col in (-1, 1):
            center = table.location + Vector((col * 0.45, row * 0.225, 0))
            center.z = table_top
            mats.append((center, row * col * 0.013))
            if row == -1 or col == 1:
                cups = center + Vector((0.085, -row * 0.056, mat_top))
                mugs.append((cups, row * 0.27 + col * 0.23))
    place_repeated(MAT, [mat], mats)
    place_repeated(MUG, mug(), mugs)
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
