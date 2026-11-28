"""制作 16 L 帆布日用双肩包，按玄关换鞋凳校验尺寸与接触。"""

import argparse
from math import ceil, cos, hypot, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s003_bedroom import STAGES
from build_s003_cooktop import scene_camera
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import rod
from build_s003_lived_in import ring_surface
from build_s003_living import LIBRARY, RENDERS, mesh_object, place_new, room_material, textile
import texture_a019_study as textures


ASSET = "A209"
VIEW = "entry-daypack"


def waxed_canvas():
    material = textile("双肩包_蜂蜡赭黄帆布", (0.42, 0.23, 0.093))
    shader = material.node_tree.nodes["Principled BSDF"]
    shader.inputs["Sheen Weight"].default_value = 0.12
    shader.inputs["Specular IOR Level"].default_value = 0.24
    n = textures.RESOLUTION
    coords = np.linspace(0, 1, n, endpoint=False, dtype=np.float32)
    x, y = coords[None, :], coords[:, None]
    rng = np.random.default_rng(209)
    surface = np.zeros((n, n), dtype=np.float32)
    for cells, strength in ((9, 0.034), (29, 0.031), (83, 0.022)):
        grid = rng.normal(size=(cells, cells)).astype(np.float32)
        offsets = coords * cells
        i = offsets.astype(np.int32)
        blend = offsets - i
        blend = blend * blend * (3 - 2 * blend)
        j = (i + 1) % cells
        layer = (1 - blend)[None, :] * grid[i[:, None], i] + blend[None, :] * grid[i[:, None], j]
        upper = (1 - blend)[None, :] * grid[j[:, None], i] + blend[None, :] * grid[j[:, None], j]
        surface += strength * ((1 - blend)[:, None] * layer + blend[:, None] * upper)
    surface += 0.021 * (np.cos(tau * (173 * x + 211 * y)) + np.cos(tau * (174 * x - 212 * y)))
    color = np.array((0.46, 0.278, 0.098), dtype=np.float32) * (1 + surface[:, :, None])
    textures.OUTPUT = LIBRARY / ASSET
    image = textures.save_image("waxed-canvas_BaseColor", np.clip(color, 0, 1), False)
    image.filepath = str(textures.OUTPUT / "textures/waxed-canvas_BaseColor.png")
    image.pack()
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    material.node_tree.links.new(node.outputs["Color"], shader.inputs["Base Color"])
    return material


def panel_outline(width, z0, z1, lower, upper):
    corners = ((width - lower, z0 + lower, lower, -pi / 2),
               (width - upper, z1 - upper, upper, 0),
               (-width + upper, z1 - upper, upper, pi / 2),
               (-width + lower, z0 + lower, lower, pi))
    arc = [(x + radius * cos(angle + i * pi / 20), z + radius * sin(angle + i * pi / 20))
           for x, z, radius, angle in corners for i in range(11)]
    profile = []
    for (xa, za), (xb, zb) in zip(arc, arc[1:] + arc[:1]):
        count = max(1, ceil(hypot(xb - xa, zb - za) / 0.010))
        profile.extend((xa + (xb - xa) * i / count, za + (zb - za) * i / count) for i in range(count))
    return profile


def cloth_panel(name, outline, stations, center_z, cloth, depth):
    rings = []
    for magnitude, y in stations:
        ring = []
        for x, z in outline:
            x *= magnitude
            z = center_z + magnitude * (z - center_z)
            crease = sin(48 * x + 24 * z) * sin(35 * z - 4 * x)
            y_offset = depth * (0.43 + 0.57 * sin(pi * z / 0.42) ** 2) * crease
            ring.append((x, y + magnitude * y_offset, z))
        rings.append(ring)
    part = ring_surface(name, rings, [cloth], caps=(True, True))
    columns = len(outline)
    uv = part.data.uv_layers.active
    arclength = [0.0]
    for first, second in zip(outline, outline[1:] + outline[:1]):
        arclength.append(arclength[-1] + hypot(second[0] - first[0], second[1] - first[1]))
    for face in part.data.polygons:
        panel_face = abs(face.normal.y) > 0.63
        for loop in face.loop_indices:
            index = part.data.loops[loop].vertex_index
            row, col = divmod(index, columns)
            x, y, z = rings[row][col]
            if panel_face:
                uv.data[loop].uv = (0.5 + x / 0.31, z / 0.44)
            else:
                seam_col = columns if col == 0 and face.index % columns == columns - 1 else col
                uv.data[loop].uv = (arclength[seam_col] / 0.31, 0.5 + y / 0.33)
    return part, rings


def zipper(name, path, binding, teeth):
    track = tube(f"{name}_包边底带", path, 0.0031, binding, 12)
    verts, faces = [], []
    lengths = [0.0]
    for a, b in zip(path, path[1:]):
        lengths.append(lengths[-1] + (Vector(b) - Vector(a)).length)
    distance = 0.002
    for a, b, start, stop in zip(path, path[1:], lengths, lengths[1:]):
        direction = (Vector(b) - Vector(a)).normalized()
        across = Vector((-direction.z, 0, direction.x))
        while distance < stop:
            center = Vector(a) + (distance - start) * direction
            index = len(verts)
            for y in (-0.00365, -0.0022):
                for along, side in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    verts.append(center + 0.00078 * along * direction + 0.0021 * side * across + Vector((0, y, 0)))
            faces.extend(tuple(index + i for i in face) for face in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                                                                     (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))
            distance += 0.0028
    part = mesh_object(f"{name}_啮合齿", verts, faces, [teeth])
    uv = part.data.uv_layers.new(name="拉链UV")
    for loop in part.data.loops:
        co = verts[loop.vertex_index]
        uv.data[loop.index].uv = (co.x / 0.30, co.z / 0.44)
    return [track, part]


def zip_pull(name, x, y, z, material):
    tab = [(x - 0.006, y, z - 0.020), (x + 0.006, y, z - 0.020), (x + 0.0043, y + 0.002, z - 0.003),
           (x - 0.0043, y + 0.002, z - 0.003), (x - 0.006, y, z - 0.020)]
    return [rounded_box(f"{name}_滑块", (x, y + 0.003, z), (0.010, 0.007, 0.007), 0.0014, material),
            tube(f"{name}_中空拉片", tab, 0.00155, material)]


def shoulder_strap(sign, fabric, binding, hardware):
    def center(t):
        return sign * (0.047 + 0.055 * t ** 1.4), 0.068 + 0.062 * sin(pi * t) ** 0.93, 0.392 - 0.355 * t

    rings = []
    seams = [[], []]
    for i in range(41):
        t = i / 40
        x, y, z = center(t)
        width = 0.015 + 0.008 * sin(pi * t) ** 0.78
        thickness = 0.0025 + 0.0054 * sin(pi * t) ** 0.8
        rings.append([(x + width * cos(a), y - thickness * sin(a), z) for a in (tau * k / 32 for k in range(32))])
        for side, seam in zip((-1, 1), seams):
            seam.append((x + 0.78 * side * width, y + 0.64 * thickness, z))
    parts = [ring_surface("双肩包_独立软垫肩带", rings, [fabric], caps=(True, True)),
             *(tube("双肩包_肩带压线", seam, 0.00065, binding, 8) for seam in seams)]
    x, y, z = center(0.90)
    y += 0.0055
    frame = [(x - 0.016, y, z - 0.013), (x + 0.016, y, z - 0.013), (x + 0.016, y, z + 0.013),
             (x - 0.016, y, z + 0.013), (x - 0.016, y, z - 0.013)]
    parts.extend([tube("双肩包_肩带日字调节框", frame, 0.0020, hardware),
                  rod("双肩包_肩带调节横杠", (x - 0.016, y, z), (x + 0.016, y, z), 0.002, hardware),
                  rounded_box("双肩包_底角肩带车缝锚片", (sign * 0.102, 0.064, 0.039), (0.038, 0.013, 0.046), 0.003, fabric)])
    return parts


def daypack():
    canvas = waxed_canvas()
    webbing = textile("双肩包_橄榄织带", (0.074, 0.081, 0.041))
    thread = room_material("双肩包_棕褐车缝线", (0.30, 0.183, 0.071), 0.72)
    dark = room_material("双肩包_枪灰拉链与金属框", (0.106, 0.111, 0.088), 0.53, 0.62)
    outline = panel_outline(0.14, 0, 0.420, 0.023, 0.102)
    panels = ((0.12, 0.077), (0.56, 0.077), (0.84, 0.075), (0.97, 0.066), (1.00, 0.047),
              (1.00, -0.048), (0.975, -0.064), (0.912, -0.073), (0.73, -0.081), (0.48, -0.084), (0.10, -0.085))
    body, rings = cloth_panel("双肩包_有受力起伏的前后及侧片", outline, panels, 0.210, canvas, 0.0039)
    parts = [body]
    for border in (rings[3], rings[6]):
        parts.append(tube("双肩包_连续细滚边", [*border, border[0]], 0.0015, thread, 10))
    main_zip = [(x, y - 0.0038, z) for x, y, z in rings[7] if z > 0.164]
    parts.extend(zipper("双肩包_主舱双向拉链", main_zip, webbing, dark))
    for x in (-0.010, 0.010):
        parts.extend(zip_pull("双肩包_主舱拉片", x, -0.086, 0.405, dark))
    pocket = panel_outline(0.110, 0.033, 0.175, 0.018, 0.017)
    pouch, pocket_rings = cloth_panel("双肩包_前侧浅袋与上沿", pocket,
                                     ((0.98, -0.065), (1, -0.078), (0.96, -0.087), (0.83, -0.093), (0.12, -0.096)),
                                     0.104, canvas, 0.0028)
    parts.append(pouch)
    border = pocket_rings[2]
    parts.append(tube("双肩包_前袋缝边", [*border, border[0]], 0.0010, thread, 8))
    parts.extend(zipper("双肩包_前袋横链", [(-0.095, -0.095, 0.152), (0.095, -0.095, 0.152)], webbing, dark))
    parts.extend(zip_pull("双肩包_前袋拉片", -0.086, -0.101, 0.151, dark))
    for sign in (-1, 1):
        parts.extend(shoulder_strap(sign, webbing, thread, dark))
    handle_rings = []
    for i in range(37):
        p = pi * i / 36
        handle_rings.append([((0.058 + 0.0023 * cos(a)) * cos(p), 0.044 + 0.013 * sin(a),
                             0.402 + (0.070 + 0.0023 * cos(a)) * sin(p)) for a in (tau * k / 24 for k in range(24))])
    parts.append(ring_surface("双肩包_车缝织带提手", handle_rings, [webbing], caps=(True, True)))
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "cooking-tools/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "entry-daypack/house.blend")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    bench = scene.objects["entry-bench"]
    top = max((bench.matrix_world @ obj.matrix_world @ Vector(corner)).z
              for obj in bench.instance_collection.all_objects if obj.type == "MESH" for corner in obj.bound_box)
    place_new(ASSET, daypack(), (7.25, 2.39, top), pi / 2)
    scene.camera = scene_camera(scene, VIEW, (8.18, 2.06, 1.20), (7.26, 2.39, top + 0.215), 49)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if not args.build_only:
        scene.render.filepath = str(RENDERS / f"{VIEW}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
