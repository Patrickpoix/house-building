"""制作玄关毛毡鞋、起居精装书和靠垫、主卧床头钟的可复用首款。"""

import argparse
from math import cos, pi, radians, sin, sqrt, tau
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import lathe
from build_s003_living import RENDERS, cylinder, mesh_object, place_new, room_material, textile

SLIPPERS, BOOK, CUSHION, CLOCK = ("A166", "A167", "A168", "A169")
VIEWS = {
    "entry-felt-slippers": ((8.32, 2.12, 0.72), (7.51, 2.61, 0.17), 39),
    "living-book-and-cushion": ((2.55, 5.12, 1.39), (1.52, 6.26, 0.47), 29),
    "bedroom-bedside-clock": ((2.1, 1.31, 1.20), (0.71, 0.78, 0.56), 51),
}


def felt_material():
    mat = room_material("室内鞋_麦色密实毛毡", (0.36, 0.23, 0.14), 0.83)
    rng = np.random.default_rng(166)
    size = 2048
    grain = rng.standard_normal((size, size), dtype=np.float32)
    broad = rng.standard_normal((128, 128), dtype=np.float32)
    broad = broad.repeat(16, axis=0).repeat(16, axis=1)
    for _ in range(4):
        broad = (2 * broad + np.roll(broad, 2, 0) + np.roll(broad, -2, 1)) / 4
    fiber = sum(np.roll(grain, (i, i * 2), (0, 1)) for i in range(5)) / 2.24
    color = np.clip(1 + 0.085 * broad + 0.055 * fiber, 0.62, 1.36)
    dy, dx = np.gradient(fiber)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes["Principled BSDF"]
    shader.inputs["Sheen Weight"].default_value = 0.16
    for role, rgb in (
        ("BaseColor", color[..., None] * np.array([0.36, 0.23, 0.14], dtype=np.float32)),
        ("Normal", np.stack((0.5 - dx * 0.09, 0.5 - dy * 0.09, np.ones_like(dx)), axis=-1)),
    ):
        image = bpy.data.images.new(f"A166_Felt_{role}", width=size, height=size)
        image.colorspace_settings.name = "sRGB" if role == "BaseColor" else "Non-Color"
        rgba[..., :3] = np.clip(rgb, 0, 1)
        image.pixels.foreach_set(rgba.ravel())
        image.pack()
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        if role == "BaseColor":
            links.new(texture.outputs["Color"], shader.inputs["Base Color"])
        else:
            normal = nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = 0.35
            links.new(texture.outputs["Color"], normal.inputs["Color"])
            links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return mat


def ring_surface(name, rings, materials, caps=(False, False), closed_rows=False):
    columns = len(rings[0])
    vertices = [tuple(point) for row in rings for point in row]
    faces = []
    rows = len(rings) if closed_rows else len(rings) - 1
    for row in range(rows):
        for col in range(columns):
            a = row * columns + col
            b = row * columns + (col + 1) % columns
            faces.append((a, b, (b + columns) % len(vertices), (a + columns) % len(vertices)))
    if caps[0]:
        faces.append(tuple(reversed(range(columns))))
    if caps[1]:
        faces.append(tuple(range(len(vertices) - columns, len(vertices))))
    part = mesh_object(name, vertices, faces, materials)
    uv = part.data.uv_layers.new(name="分面UV")
    for face in part.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        for loop in face.loop_indices:
            index = part.data.loops[loop].vertex_index
            row, col = divmod(index, columns)
            u = col / columns
            if len(face.vertices) == 4 and face.index % columns == columns - 1 and col == 0:
                u = 1
            v = row / rows
            if closed_rows and face.index // columns == rows - 1 and row == 0:
                v = 1
            if len(face.vertices) != 4:
                x, y, _ = vertices[index]
                u, v = 0.5 + x * 5, 0.5 + y * 3
            uv.data[loop].uv = (u, v)
    return part


def slippers():
    felt = felt_material()
    lining = room_material("室内鞋_浅麦色内衬", (0.53, 0.44, 0.31), 0.83)
    rubber = room_material("室内鞋_石墨防滑橡胶", (0.061, 0.055, 0.049), 0.84)
    binding = textile("室内鞋_肉桂斜纹包边", (0.26, 0.122, 0.065))
    angles = [tau * i / 96 for i in range(96)]

    def sole_outline(angle):
        forward = -cos(angle)
        x = sin(angle) * (0.052 - 0.008 * forward - 0.004 * forward ** 2)
        x += 0.007 * (1 - forward) / 2
        return x, 0.136 * forward

    def toe_lift(y):
        return 0.009 * max(0, (-y - 0.084) / 0.052) ** 2

    parts = []
    for side in (-1, 1):
        name = "左" if side == -1 else "右"
        transform = Matrix.Translation((side * 0.064, side * 0.008, 0)) @ Matrix.Rotation(side * 0.055, 4, "Z")
        sole_rings = [[(side * x * width, y * width, z + toe_lift(y))
                       for x, y in map(sole_outline, angles)]
                      for width, z in ((0.956, 0.0015), (0.993, 0.0035), (1, 0.0065), (0.977, 0.0114))]
        vamp = []
        for row in range(19):
            s = row / 18
            ring = []
            for angle in angles:
                ox, oy = sole_outline(angle)
                hx = 0.004 + 0.041 * sin(angle)
                hy = 0.059 - 0.070 * cos(angle)
                hz = 0.0215 + 0.041 * ((1 + cos(angle)) / 2) ** 3.8
                x = ox * sqrt(max(0, 1 - s * s)) + hx * (1 - sqrt(max(0, 1 - s * s)))
                y = oy + (hy - oy) * (s ** 1.40)
                z = (0.0105 + toe_lift(oy)) * (1 - s) + hz * s + 0.014 * sin(pi * s) * ((1 + cos(angle)) / 2)
                ring.append((side * x, y, z))
            vamp.append(ring)
        collar = vamp[-1]
        # 镜像后反转环的绕序，保持鞋面法线朝外。
        if side < 0:
            sole_rings = [list(reversed(ring)) for ring in sole_rings]
            vamp = [list(reversed(ring)) for ring in vamp]
        sole = ring_surface(f"{name}鞋_成型防滑外底", sole_rings, [rubber], (True, True))
        upper = ring_surface(f"{name}鞋_环形绒面与贯通鞋口", vamp, [felt, lining])
        thickness = upper.modifiers.new("鞋面及贴合内衬厚度", "SOLIDIFY")
        thickness.thickness = 0.0033
        thickness.offset = -1
        thickness.material_offset = 1
        bed_rings = [[(x * scale, y * scale, z + toe_lift(y) * 0.35) for x, y, _ in sole_rings[-1]]
                     for scale, z in ((0.87, 0.0106), (0.92, 0.0145), (0.86, 0.0172))]
        footbed = ring_surface(f"{name}鞋_独立压实鞋床", bed_rings, [lining], (True, True))
        # 包边采用闭合圆环，最后一段与第一段共享顶点。
        seam_rings = []
        for angle, (x, y, z) in zip(angles, collar):
            seam_rings.append([(x + side * sin(angle) * 0.0026 * cos(tau * i / 10),
                                y - cos(angle) * 0.0026 * cos(tau * i / 10),
                                z - side * 0.0026 * sin(tau * i / 10)) for i in range(10)])
        seam = ring_surface(f"{name}鞋_环形织带滚边", seam_rings, [binding], closed_rows=True)
        treads = []
        for row in range(10):
            y = -0.104 + row * 0.022
            fraction = y / 0.136
            width = sqrt(1 - fraction ** 2) * (0.052 - 0.008 * fraction - 0.004 * fraction ** 2)
            center = 0.007 * (1 - fraction) / 2
            for half in (-1, 1):
                tread = rounded_box(f"{name}鞋_双斜坡防滑纹", (side * (center + half * width * 0.47), y,
                                                                   toe_lift(y) + 0.00115),
                                    (width * 0.72, 0.007, 0.0023), 0.001, rubber)
                tread.rotation_euler.z = radians(16) * half * side
                treads.append(tread)
        bpy.context.view_layer.update()
        shoe = [sole, upper, footbed, seam, *treads]
        for part in shoe:
            part.matrix_world = transform @ part.matrix_world
        parts.extend(shoe)
    return parts


def hardback():
    cloth = textile("精装书_深墨青布面", (0.102, 0.207, 0.184))
    paper = room_material("精装书_本白书页", (0.74, 0.66, 0.48), 0.86)
    darker = room_material("精装书_书口薄层", (0.50, 0.435, 0.32), 0.88)
    foil = room_material("精装书_浅金压印", (0.55, 0.38, 0.15), 0.52, 0.55)
    parts = [rounded_box("精装书_布脊", (-0.080, 0, 0.018), (0.019, 0.236, 0.036), 0.008, cloth),
             rounded_box("精装书_装订书页", (0.002, 0, 0.018), (0.159, 0.225, 0.029), 0.003, paper)]
    for z in (0.002, 0.034):
        parts.append(rounded_box("精装书_圆角书封硬板", (0.000, 0, z), (0.175, 0.240, 0.004), 0.0015, cloth))
    for i in range(24):
        z = 0.005 + i * 0.00111
        parts.append(rounded_box("精装书_页边短纹", (0.0809, 0, z),
                                 (0.0008, 0.218 - 0.008 * sin(i * 1.74), 0.00022), 0.0001, darker))
    outline = [(-0.054, -0.087, 0.0362), (0.063, -0.087, 0.0362),
               (0.063, 0.086, 0.0362), (-0.054, 0.086, 0.0362), (-0.054, -0.087, 0.0362)]
    parts.append(tube("精装书_烫金边线", outline, 0.00047, foil))
    for i in range(5):
        y = -0.031 + i * 0.011
        line = [(x, y + 0.014 * sin(i * 0.55 + x * 49), 0.0363) for x in np.linspace(-0.036, 0.047, 24)]
        parts.append(tube("精装书_版画式波纹压印", line, 0.00063, foil))
    return parts


def cushion():
    fabric = textile("靠垫_烧陶红亚麻", (0.30, 0.080, 0.038))
    welt = textile("靠垫_同色缝边", (0.20, 0.056, 0.028))
    perimeter = [(0.214 * cos(a), 0.205 * sin(a)) for a in (tau * i / 128 for i in range(128))]
    perimeter = [(0.214 * (1 if x >= 0 else -1) * abs(x / 0.214) ** 0.55,
                  0.205 * (1 if z >= 0 else -1) * abs(z / 0.205) ** 0.55) for x, z in perimeter]
    parts = []
    for side in (-1, 1):
        rings = []
        for row in range(22):
            r = 1 - row * 0.044
            points = []
            for x, z in perimeter:
                bulge = max(0, 1 - r ** 3) ** 0.66
                # 缝边只在局部收紧，填棉撑平中央的正反裁片。
                seam_weight = sin(pi * max(0, (r - 0.68) / 0.32)) ** 2
                wrinkle = 0.0022 * sin(99 * x + 0.8 * sin(130 * z)) * seam_weight
                points.append((r * x + 0.006 * sin(r * z * 12), side * (0.002 + 0.077 * bulge + wrinkle),
                               0.202 + r * z + 0.005 * cos(r * x * 15)))
            rings.append(points if side < 0 else list(reversed(points)))
        part = ring_surface("靠垫_裁片鼓面", rings, [fabric], (False, True))
        for face in part.data.polygons:
            for index in face.loop_indices:
                x, _, z = part.data.vertices[part.data.loops[index].vertex_index].co
                part.data.uv_layers.active.data[index].uv = ((x + 0.22) * 5.7, z * 5.7)
        parts.append(part)
    seam = [(x + 0.006 * sin(z * 12), 0, 0.202 + z + 0.005 * cos(x * 15)) for x, z in perimeter]
    parts.append(tube("靠垫_拼缝滚边", seam + [seam[0]], 0.0026, welt))
    rotation = Matrix.Rotation(radians(-14), 4, "X")
    for part in parts:
        part.matrix_world = rotation @ part.matrix_world
    return parts


def alarm_clock():
    shell = room_material("床头钟_米灰粉末涂层", (0.52, 0.46, 0.35), 0.46)
    white = room_material("床头钟_哑光面盘", (0.79, 0.75, 0.60), 0.71)
    ink = room_material("床头钟_石墨刻度", (0.043, 0.056, 0.049), 0.57)
    amber = room_material("床头钟_朱砂秒针", (0.54, 0.14, 0.072), 0.48)
    clear = room_material("床头钟_透明面罩", (0.97, 0.98, 0.97), 0.082)
    clear.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1
    housing = lathe("床头钟_后壳和凹进表圈", shell,
                    [(0.039, -0.028), (0.049, -0.025), (0.056, -0.016), (0.057, 0.017),
                     (0.056, 0.022), (0.052, 0.023), (0.050, 0.020), (0.050, 0.004), (0.037, 0.004)],
                    -0.028, 0.004)
    parts = [housing, cylinder("床头钟_表盘", (0, 0, 0.007), 0.0495, 0.002, white),
             cylinder("床头钟_独立玻璃面罩", (0, 0, 0.018), 0.0507, 0.0022, clear, vertices=96),
             cylinder("床头钟_指针共轴帽", (0, 0, 0.012), 0.0028, 0.003, ink)]
    for i in range(60):
        angle = tau * i / 60
        length = 0.0063 if i % 5 == 0 else 0.0026
        marker = rounded_box("床头钟_精细分度", (0.044 * sin(angle), 0.044 * cos(angle), 0.0081),
                             (0.0013 if i % 5 == 0 else 0.0005, length, 0.00035), 0.00016, ink)
        marker.rotation_euler.z = -angle
        parts.append(marker)
    for angle, length, width, z, material in ((300, 0.027, 0.0028, 0.0098, ink),
                                               (57, 0.039, 0.0018, 0.0112, ink),
                                               (190, 0.040, 0.0008, 0.0123, amber)):
        spin = radians(angle)
        hand = rounded_box("床头钟_独立指针", (0.43 * length * sin(spin), 0.43 * length * cos(spin), z),
                           (width, length, 0.0005), 0.00022, material)
        hand.rotation_euler.z = -spin
        parts.append(hand)
    turn = Matrix.Translation((0, 0, 0.062)) @ Matrix.Rotation(pi / 2, 4, "X")
    bpy.context.view_layer.update()
    for part in parts:
        part.matrix_world = turn @ part.matrix_world
    parts.extend((rounded_box("床头钟_低重心防滑底座", (0, 0.006, 0.005), (0.074, 0.058, 0.010), 0.004, shell),
                  cylinder("床头钟_顶端止闹键", (0, 0.003, 0.120), 0.011, 0.007, ink)))
    return parts


def top_z(instance):
    return max((instance.matrix_world @ part.matrix_world @ Vector(point)).z
               for part in instance.instance_collection.objects if part.type == "MESH"
               for point in part.bound_box)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "household-essentials/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "lived-in/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--views", nargs="+", choices=VIEWS, default=list(VIEWS))
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    place_new(SLIPPERS, slippers(), (7.62, 2.61, 0.0), radians(72))
    table = scene.objects["living-coffee-table"]
    scene.objects["A103"].location.y += 0.050
    place_new(BOOK, hardback(), (2.145, 6.505, top_z(table)), radians(-20))
    sofa = scene.objects["living-sofa"]
    place_new(CUSHION, cushion(), sofa.matrix_world @ Vector((-0.64, -0.075, 0.449)), pi / 2 + radians(9))
    cabinet = scene.objects["A112"]
    place_new(CLOCK, alarm_clock(), (cabinet.location.x + 0.05, cabinet.location.y + 0.04, top_z(cabinet)), radians(105))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["living-book-and-cushion"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if args.build_only:
        return
    args.renders.mkdir(parents=True, exist_ok=True)
    for name in args.views:
        scene.camera = scene.objects[name]
        scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
