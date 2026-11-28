"""按 S003 卫浴现有净空安装地排连体坐便器。"""

import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bathroom_vanity import area_light
from build_s003_bedroom import STAGES
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, cylinder, mesh_object, place_new, room_material
import texture_a019_study as textures


ASSET = "A115"
SEAT_PIVOT = 0.161
SEAT_Z = 0.473
LID_ANGLE = -pi * 0.494


def oval(rings, name, material, caps):
    # 前半圈平缓展开，后半圈收窄与水箱台座接合。
    steps = 80
    vertices = []
    for w, d, y, z in rings:
        for i in range(steps):
            angle = tau * i / steps
            side = sin(angle)
            vertices.append((cos(angle) * w / 2 * (1 - 0.105 * side), y + side * d / 2, z))
    faces = [tuple(reversed(range(steps)))] if caps else []
    for row in range(len(rings) - 1):
        for i in range(steps):
            a, b = row * steps + i, row * steps + (i + 1) % steps
            faces.append((a, b, b + steps, a + steps))
    if caps:
        faces.append(tuple(range(len(vertices) - steps, len(vertices))))
    obj = mesh_object(name, vertices, faces, [material])
    uv = obj.data.uv_layers.new(name="PorcelainUV")
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        axis = max(range(3), key=lambda k: abs(face.normal[k]))
        u, v = (j for j in range(3) if j != axis)
        for loop in face.loop_indices:
            point = vertices[obj.data.loops[loop].vertex_index]
            uv.data[loop].uv = (point[u] / 0.65 + 0.5, point[v] / 0.65 + 0.5)
    return obj


def ceramic():
    porcelain = room_material("坐便器_暖白釉陶瓷", (0.82, 0.82, 0.78), 0.255)
    textures.OUTPUT = LIBRARY / ASSET
    maps = textures.create_maps("porcelain", (0.82, 0.82, 0.78), 0.0, 0.255, 0.012, 115)
    textures.connect_maps(porcelain, maps)
    for image in maps.values():
        image.filepath = str(textures.OUTPUT / "textures" / bpy.path.basename(image.filepath))
        image.pack()
    return porcelain


def toilet():
    gloss = ceramic()
    seat_mat = room_material("坐便器_暖白座盖", (0.83, 0.815, 0.776), 0.33)
    fittings = room_material("坐便器_镀铬按键与铰轴", (0.50, 0.49, 0.465), 0.24, 0.76)
    buffer = room_material("坐便器_灰白缓冲垫", (0.42, 0.42, 0.39), 0.63)
    water = room_material("坐便器_盆底水面", (0.41, 0.52, 0.49), 0.125)
    water.node_tree.nodes.get("Principled BSDF").inputs["IOR"].default_value = 1.33
    body = oval((
        (0.296, 0.486, 0.047, 0.000), (0.305, 0.495, 0.045, 0.009),
        (0.310, 0.507, 0.041, 0.085), (0.316, 0.518, 0.030, 0.175),
        (0.343, 0.548, 0.009, 0.256), (0.380, 0.573, -0.011, 0.337),
        (0.389, 0.576, -0.019, 0.382), (0.383, 0.567, -0.019, 0.408),
        (0.367, 0.548, -0.020, 0.417), (0.305, 0.457, -0.043, 0.417),
        (0.286, 0.431, -0.047, 0.407), (0.259, 0.389, -0.050, 0.369),
        (0.223, 0.331, -0.046, 0.310), (0.172, 0.251, -0.020, 0.253),
        (0.133, 0.176, 0.009, 0.213), (0.109, 0.136, 0.024, 0.184),
    ), "坐便器_连续陶瓷外壳与盆腔", gloss, caps=True)
    seat_rings = (
        (0.357, 0.485, -0.066, 0.419), (0.371, 0.499, -0.066, 0.427),
        (0.371, 0.499, -0.066, 0.443), (0.361, 0.489, -0.066, 0.451),
        (0.285, 0.393, -0.062, 0.451), (0.270, 0.379, -0.062, 0.443),
        (0.270, 0.379, -0.062, 0.426), (0.282, 0.391, -0.062, 0.419),
    )
    seat = oval((*seat_rings, seat_rings[0]), "坐便器_独立座圈", seat_mat, caps=False)
    # 关闭姿态保留独立铰轴原点，在复验中可直接转开盖板。
    lid = oval((
        (0.356, 0.470, -0.074 - SEAT_PIVOT, 0.449 - SEAT_Z),
        (0.370, 0.484, -0.074 - SEAT_PIVOT, 0.455 - SEAT_Z),
        (0.367, 0.480, -0.074 - SEAT_PIVOT, 0.469 - SEAT_Z),
        (0.349, 0.458, -0.074 - SEAT_PIVOT, 0.477 - SEAT_Z),
    ), "坐便器_铰接上盖", seat_mat, caps=True)
    lid.location = (0, SEAT_PIVOT, SEAT_Z)
    wet = oval(((0.136, 0.196, 0.018, 0.222), (0.137, 0.196, 0.018, 0.225)), "坐便器_静态水面", water, caps=True)

    parts = [body, seat, lid, wet,
             rounded_box("坐便器_背部支承座", (0, 0.232, 0.255), (0.262, 0.171, 0.510), 0.031, gloss),
             rounded_box("坐便器_一体水箱", (0, 0.261, 0.580), (0.371, 0.172, 0.290), 0.029, gloss),
             rounded_box("坐便器_可拆水箱盖", (0, 0.259, 0.731), (0.374, 0.171, 0.024), 0.010, gloss)]
    for side in (-1, 1):
        pin = cylinder("坐便器_盖板铰轴", (side * 0.100, SEAT_PIVOT, SEAT_Z), 0.016, 0.037, fittings)
        pin.rotation_euler.y = pi / 2
        parts.extend((pin,
                      cylinder("坐便器_座圈后支座", (side * 0.100, SEAT_PIVOT, 0.414), 0.022, 0.017, buffer),
                      rounded_box("坐便器_铰轴底脚", (side * 0.100, SEAT_PIVOT, 0.442),
                                  (0.028, 0.023, 0.061), 0.006, seat_mat),
                      cylinder("坐便器_双冲水按键", (side * 0.011, 0.261, 0.745), 0.009, 0.006, fittings)))
    return parts


def render_glb(render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / ASSET / f"{ASSET}.glb"))
    lid = bpy.context.scene.objects["坐便器_铰接上盖"]
    # GLB 回导采用四元数，必须在实际生效的旋转模式下转动盖板。
    lid.rotation_mode = "XYZ"
    lid.rotation_euler.x += LID_ANGLE
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("坐便器回导照明")
    scene.world.color = (0.21, 0.21, 0.21)
    floor = room_material("坐便器回导地面", (0.22, 0.23, 0.24), 0.65)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
    bpy.context.object.data.materials.append(floor)
    area_light("坐便器回导主光", (-0.8, -1.6, 2.0), (0, 0, 0.46), 158, 1.55, (1, 1, 1))
    area_light("坐便器回导轮廓光", (1.5, 0.89, 1.6), (0, 0, 0.40), 100, 1.28, (1, 1, 1))
    scene.camera = scene_camera(scene, "toilet-open-glb", (0.84, -1.47, 1.49), (0, 0, 0.45), 53)
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 1.15
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 31
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 850
    scene.render.filepath = str(render_dir / "bathroom-toilet-glb-open.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bathroom-shower/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bathroom-toilet/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    previous = scene.objects["STUDY_toilet"]
    center = previous.location.x
    bpy.data.objects.remove(previous, do_unlink=True)
    north = next(w for w in WALLS if w[0] == "bath_north")
    north_face = north[2] - north[5] / 2
    floor = next(obj for obj in scene.objects if obj.name.startswith("卫浴_砂岩地砖"))
    tile_z = max((floor.matrix_world @ vertex.co).z for vertex in floor.data.vertices)
    place_new(ASSET, toilet(), (center, north_face - 0.365, tile_z))
    views = {
        "bathroom-complete": ((6.88, 1.23, 1.62), (4.91, 1.27, 1.03), 19),
        "bathroom-toilet": ((6.65, 1.32, 1.53), (5.38, 2.08, 0.71), 25),
        "bathroom-toilet-detail": ((6.48, 1.36, 1.18), (5.64, 2.10, 0.43), 41),
    }
    cameras = {name: scene_camera(scene, name, *cam) for name, cam in views.items()}
    scene.camera = cameras["bathroom-complete"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    render_dir = args.renders.resolve()
    render_dir.mkdir(parents=True, exist_ok=True)
    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    render_glb(render_dir)


if __name__ == "__main__":
    main()
