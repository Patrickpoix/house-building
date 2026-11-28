"""替换 S003 淋浴占位，安装低抬高底盘、固定玻璃及雨淋花洒。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bathroom_vanity import area_light
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board
from build_s003_cooktop import scene_camera
from build_s003_dining import rounded_rectangle
from build_s003_living import LIBRARY, cylinder, mesh_object, place_new, room_material
import texture_a019_study as textures


ASSET = "A114"
WIDTH, DEPTH = 0.986, 1.024
RAISED_EDGE = 0.071
GLASS_X = 0.464


def tray(material):
    profile = (
        (WIDTH - 0.012, DEPTH - 0.012, 0.000, 0.015),
        (WIDTH, DEPTH, 0.007, 0.017),
        (WIDTH, DEPTH, RAISED_EDGE - 0.006, 0.017),
        (WIDTH - 0.012, DEPTH - 0.012, RAISED_EDGE, 0.014),
        (WIDTH - 0.061, DEPTH - 0.061, RAISED_EDGE, 0.019),
        (WIDTH - 0.078, DEPTH - 0.078, RAISED_EDGE - 0.008, 0.019),
        (0.116, 0.116, 0.043, 0.008),
        (0.103, 0.103, 0.036, 0.006),
        (0.103, 0.103, 0.020, 0.006),
    )
    steps, ring_size = 10, 40
    vertices = [p for row in profile for p in rounded_rectangle(*row, steps)]
    faces = [tuple(reversed(range(ring_size)))]
    for row in range(len(profile) - 1):
        for i in range(ring_size):
            a, b = row * ring_size + i, row * ring_size + (i + 1) % ring_size
            faces.append((a, b, b + ring_size, a + ring_size))
    faces.append(tuple(range(len(vertices) - ring_size, len(vertices))))
    obj = mesh_object("淋浴_连续坡面底盘", vertices, faces, [material])
    uv = obj.data.uv_layers.new(name="TrayUV")
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        axis = max(range(3), key=lambda k: abs(face.normal[k]))
        u, v = (k for k in range(3) if k != axis)
        for loop in face.loop_indices:
            co = vertices[obj.data.loops[loop].vertex_index]
            uv.data[loop].uv = (co[u] / WIDTH + 0.5, co[v] / DEPTH + 0.5)
    return obj


def shower_parts():
    bowl = room_material("淋浴_浅砂防滑矿物树脂", (0.68, 0.663, 0.618), 0.57)
    textures.OUTPUT = LIBRARY / ASSET
    maps = textures.create_maps("shower-tray", (0.68, 0.663, 0.618), 0, 0.57, 0.037, 114)
    textures.connect_maps(bowl, maps)
    for image in maps.values():
        image.filepath = str(textures.OUTPUT / "textures" / bpy.path.basename(image.filepath))
        image.pack()

    steel = room_material("淋浴_拉丝不锈钢", (0.34, 0.335, 0.322), 0.29, 0.82)
    dark = room_material("淋浴_孔位与密封条", (0.065, 0.073, 0.073), 0.51)
    glass = room_material("淋浴_钢化净玻璃", (0.975, 0.99, 0.98), 0.045)
    shader = glass.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Transmission Weight"].default_value = 1.0
    shader.inputs["IOR"].default_value = 1.48
    parts = [tray(bowl)]
    parts.append(board("淋浴_排水槽内腔", (0, 0, 0.020), (0.099, 0.099, 0.005), dark, 0, 0))
    for side in (-1, 1):
        parts.extend((
            board("淋浴_排水盖长框", (side * 0.048, 0, 0.036), (0.012, 0.107, 0.009), steel, 1, 0),
            board("淋浴_排水盖短框", (0, side * 0.048, 0.036), (0.087, 0.012, 0.009), steel, 0, 0),
        ))
    for i in range(-4, 5):
        parts.append(board("淋浴_排水盖栅片", (0, i * 0.009, 0.036), (0.086, 0.0044, 0.008), steel, 0, 0))

    bottom = RAISED_EDGE + 0.008
    parts.append(rounded_box("淋浴_固定钢化玻璃", (GLASS_X, -0.024, bottom + 0.990),
                             (0.008, 0.945, 1.980), 0.0014, glass))
    parts.append(board("淋浴_玻璃底部密封条", (GLASS_X, -0.024, RAISED_EDGE + 0.004),
                       (0.012, 0.945, 0.009), dark, 1, 0))
    for y in (-0.382, 0.339):
        parts.append(board("淋浴_玻璃底部夹座", (GLASS_X, y, RAISED_EDGE + 0.015),
                           (0.035, 0.060, 0.035), steel, 1, 0))
    brace_y, brace_z = -0.318, 0.010 + bottom + 1.966
    brace = cylinder("淋浴_玻璃横向稳定杆", ((GLASS_X - WIDTH / 2) / 2, brace_y, brace_z),
                     0.010, GLASS_X + WIDTH / 2, steel)
    brace.rotation_euler.y = pi / 2
    parts.extend((brace,
                  board("淋浴_稳定杆墙座", (-WIDTH / 2 + 0.003, brace_y, brace_z),
                        (0.016, 0.058, 0.055), steel, 1, 0),
                  board("淋浴_稳定杆玻璃夹", (GLASS_X, brace_y, brace_z),
                        (0.035, 0.043, 0.046), steel, 1, 0)))

    # 墙阀连到外露立管，顶喷头的喷嘴独立位于盘底。
    y, valve_z, head_z = -0.159, 1.052, 2.115
    rear, head_x = -WIDTH / 2, -0.153
    outlet_x = rear + 0.055
    for z in (valve_z, 1.740):
        collar = cylinder("淋浴_花洒墙座", (rear + 0.015, y, z), 0.039, 0.033, steel)
        collar.rotation_euler.y = pi / 2
        connector = cylinder("淋浴_离墙接头", ((rear + outlet_x) / 2, y, z), 0.015, outlet_x - rear, steel)
        connector.rotation_euler.y = pi / 2
        parts.extend((collar, connector))
    valve = cylinder("淋浴_混水阀主体", (outlet_x, y, valve_z), 0.035, 0.141, steel)
    valve.rotation_euler.x = pi / 2
    arm = cylinder("淋浴_顶喷横臂", ((outlet_x + head_x) / 2, y, head_z + 0.031),
                   0.011, head_x - outlet_x + 0.022, steel)
    arm.rotation_euler.y = pi / 2
    top, base = head_z + 0.031, valve_z + 0.021
    parts.extend((
        valve, arm,
        cylinder("淋浴_混水阀拨柄", (outlet_x + 0.019, y - 0.082, valve_z + 0.023), 0.007, 0.059, steel),
        cylinder("淋浴_花洒立管", (outlet_x, y, (top + base) / 2), 0.010, top - base + 0.020, steel),
        cylinder("淋浴_顶喷万向接头", (head_x, y, head_z + 0.020), 0.015, 0.037, steel),
        cylinder("淋浴_圆形雨淋喷头", (head_x, y, head_z), 0.118, 0.019, steel, vertices=64),
        cylinder("淋浴_雨淋喷头面板", (head_x, y, head_z - 0.010), 0.105, 0.006, dark, vertices=64),
    ))
    for u in range(-4, 5):
        for v in range(-4, 5):
            if u * u + v * v <= 19:
                parts.append(cylinder("淋浴_雨淋硅胶喷嘴", (head_x + u * 0.022, y + v * 0.022, head_z - 0.014),
                                      0.0029, 0.005, steel, vertices=12))
    return parts


def wet_wall(west, south, north, center_x, center_y, window):
    original = bpy.data.materials["卫浴_墙砖釉色2"]
    alternating = bpy.data.materials["卫浴_墙砖釉色3"]
    column_w = (north - south) / 12
    for level in range(8, 12):
        z = (level + 0.5) * 0.195
        for col in range(6):
            end_y = min(south + (col + 1) * column_w, center_y + DEPTH / 2)
            start_y = south + col * column_w
            if end_y > start_y + 0.002:
                board("淋浴_西壁上沿釉砖", (west + 0.0045, (start_y + end_y) / 2, z),
                      (0.009, end_y - start_y - 0.0019, 0.1931), (original, alternating)[(col + level) % 2], 2, 0)
    east = center_x + WIDTH / 2
    # 窗台以下整墙铺砖，窗台之上每块砖停在实测窗洞左边。
    for level in range(12):
        z0, z1 = level * 0.195, (level + 1) * 0.195
        end = east if z1 <= window[2] else min(east, window[0] - 0.002)
        for col in range(6):
            x0, x1 = west + col * 0.185, min(west + (col + 1) * 0.185, end)
            if x1 > x0 + 0.002:
                board("淋浴_南壁釉砖", ((x0 + x1) / 2, south + 0.0045, (z0 + z1) / 2),
                      (x1 - x0 - 0.0019, 0.009, 0.1931), (original, alternating)[(col + level) % 2], 2, 0)


def render_glb(render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / ASSET / f"{ASSET}.glb"))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("淋浴回导中性世界")
    scene.world.color = (0.25, 0.25, 0.25)
    floor = room_material("淋浴回导地面", (0.23, 0.245, 0.25), 0.62)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.002))
    bpy.context.object.data.materials.append(floor)
    area_light("淋浴回导主光", (-1.2, 2.2, 2.9), (0, 0, 1.0), 180, 2.0, (1, 1, 1))
    area_light("淋浴回导玻璃边光", (2.0, -0.9, 2.46), (0, 0, 1.0), 115, 1.4, (1, 1, 1))
    scene.camera = scene_camera(scene, "shower-glb", (2.6, 3.5, 2.76), (0, 0, 1.03), 49)
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 2.75
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = (850, 980)
    scene.render.filepath = str(render_dir / "bathroom-shower-glb.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bathroom-vanity/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bathroom-shower/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")

    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    walls = {row[0]: row for row in WALLS}
    west = walls["bedroom_east"][2] + walls["bedroom_east"][5] / 2
    south = walls["south"][2] + walls["south"][5] / 2
    north = walls["bath_north"][2] - walls["bath_north"][5] / 2
    window = next(opening for opening in walls["south"][-1] if 4 < opening[0] < 6)
    for name in ("STUDY_shower_tray", "STUDY_shower_screen"):
        bpy.data.objects.remove(scene.objects[name], do_unlink=True)
    floor = next(obj for obj in scene.objects if obj.name.startswith("卫浴_砂岩地砖"))
    tile_z = max((floor.matrix_world @ vertex.co).z for vertex in floor.data.vertices)
    x = west + 0.009 + WIDTH / 2
    y = south + 0.009 + DEPTH / 2
    wet_wall(west, south, north, x, y, window)
    place_new(ASSET, shower_parts(), (x, y, tile_z))
    views = {
        "bathroom-shower": ((6.48, 1.40, 1.51), (4.63, 0.72, 1.10), 21),
        "shower-base-detail": ((4.96, 1.46, 1.16), (4.56, 0.74, 0.060), 34),
    }
    cameras = {name: scene_camera(scene, name, *cam) for name, cam in views.items()}
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
