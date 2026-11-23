"""按南窗和床侧的实际净空装配 S003 主卧窗帘与床头柜。"""

import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s001_whitebox import WALLS
from build_s003_bedroom import BED, BEDROOM_FLOOR, ROOM_BOUNDS, STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, cylinder, mesh_object, place_new, room_material, textile


CURTAIN, NIGHTSTAND = "A111", "A112"
RAIL_HEIGHT = 2.575
CLOTH_TOP = 2.535
CLOTH_BOTTOM = 0.026
PANEL_WIDTH = 0.445
PLEATS = 6
STAND_WIDTH, STAND_DEPTH, STAND_HEIGHT = 0.394, 0.355, 0.492


def curtain_point(center, side, u, v):
    # 上缘服从等距挂点，垂至下缘时褶宽、深度和下摆随布料重量放松。
    phase = tau * PLEATS * u
    spread = 0.92 + 0.08 * v
    x = center + side * (PANEL_WIDTH * spread * (u - 0.5) + 0.007 * v * sin(phase))
    y = (0.022 + 0.038 * sin(pi * v * 0.77)) * cos(phase + 0.31 * v * sin(7 * u))
    y += 0.010 * sin(8 * u + side) * v + 0.008 * sin(pi * v)
    z = CLOTH_TOP + v * (CLOTH_BOTTOM - CLOTH_TOP) + 0.004 * v**5 * (1 + sin(phase * 0.55))
    return x, y, z


def curtain_panel(center, side, cloth, hem):
    across, down = 120, 100
    stride = across + 1
    vertices = [curtain_point(center, side, i / across, j / down)
                for j in range(down + 1) for i in range(stride)]
    faces = []
    for j in range(down):
        for i in range(across):
            a = j * stride + i
            face = (a, a + 1, a + stride + 1, a + stride)
            faces.append(face if side > 0 else tuple(reversed(face)))
    obj = mesh_object("窗帘_垂褶布面", vertices, faces, [cloth, hem])
    uv = obj.data.uv_layers.new(name="FabricUV")
    distance = [0.0]
    midline = (down // 2) * stride
    for a, b in zip(vertices[midline:midline + across], vertices[midline + 1:midline + stride]):
        distance.append(distance[-1] + (Vector(a) - Vector(b)).length)
    for face in obj.data.polygons:
        face.use_smooth = True
        j, i = divmod(face.index, across)
        if i == 0 or i == across - 1 or j == 0 or j >= down - 2:
            face.material_index = 1
        for loop in face.loop_indices:
            row, column = divmod(obj.data.loops[loop].vertex_index, stride)
            uv.data[loop].uv = (distance[column] / 0.23, row / down * 2.51 / 0.23)
    solidify = obj.modifiers.new("窗帘包边厚度", "SOLIDIFY")
    solidify.thickness = 0.0022
    solidify.material_offset_rim = 1
    return obj


def curtain_parts(rail_width, panel_offset, wall_offset):
    cloth = textile("窗帘_暖灰亚麻混纺", (0.42, 0.365, 0.292))
    hem = cloth.copy()
    hem.name = "窗帘_折边"
    hem.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.39, 0.336, 0.269, 1)
    rail = room_material("窗帘_烟褐色导轨", (0.14, 0.117, 0.09), 0.39, 0.62)
    runner = room_material("窗帘_低光滑轮", (0.27, 0.229, 0.178), 0.43, 0.48)
    parts = [board("窗帘_滑轨", (0, 0, RAIL_HEIGHT), (rail_width, 0.040, 0.029), rail, 0, 0)]
    for x in (-rail_width * 0.42, 0, rail_width * 0.42):
        parts.extend((
            board("窗帘_背墙支座", (x, wall_offset + 0.007, RAIL_HEIGHT),
                  (0.044, 0.015, 0.067), rail, 2, 0),
            board("窗帘_导轨托臂", (x, (wall_offset - 0.015) / 2, RAIL_HEIGHT + 0.008),
                  (0.021, -wall_offset - 0.009, 0.014), rail, 1, 0),
        ))
    for side in (-1, 1):
        center = panel_offset * side
        parts.append(curtain_panel(center, side, cloth, hem))
        parts.append(board("窗帘_轨道端盖", (side * rail_width / 2, 0, RAIL_HEIGHT),
                           (0.014, 0.044, 0.033), rail, 2, 0))
        for index in range(PLEATS):
            x, y, _ = curtain_point(center, side, (index + 0.5) / PLEATS, 0)
            parts.append(board("窗帘_滑块", (x, 0, RAIL_HEIGHT - 0.013),
                               (0.012, 0.015, 0.011), runner, 2, 0))
            parts.append(board("窗帘_挂片", (x, y / 2, (CLOTH_TOP + RAIL_HEIGHT - 0.018) / 2),
                               (0.008, abs(y) + 0.003, RAIL_HEIGHT - 0.016 - CLOTH_TOP), runner, 2, 0))
    return parts


def nightstand_parts():
    wood, _ = white_oak_material("床头柜_白橡木皮", "WoodUV")
    inset = room_material("床头柜_抽屉退缝", (0.085, 0.057, 0.036), 0.65)
    metal = room_material("床头柜_缎面青铜", (0.27, 0.166, 0.086), 0.37, 0.69)
    w, d, h = STAND_WIDTH, STAND_DEPTH, STAND_HEIGHT
    parts = [
        board("床头柜_顶板", (0, 0, h - 0.014), (w, d, 0.028), wood, 0, 0.04),
        board("床头柜_下层板", (0, 0.009, 0.137), (w - 0.024, d - 0.034, 0.022), wood, 0, 0.32),
        board("床头柜_连续背板", (0, 0.151, 0.300), (w - 0.048, 0.012, 0.330), wood, 2, 0.27),
        board("床头柜_抽屉缝内箱", (0, -0.003, 0.375), (w - 0.062, d - 0.045, 0.157), inset, 0, 0),
        board("床头柜_独立抽面", (0, -0.163, 0.376), (w - 0.048, 0.021, 0.165), wood, 0, 0.21),
    ]
    for side in (-1, 1):
        parts.append(board("床头柜_侧围", (side * 0.178, 0.004, 0.300),
                           (0.019, d - 0.029, 0.328), wood, 2, 0.15 * side))
        for y in (-0.133, 0.133):
            leg = board("床头柜_收分实木脚", (side * 0.158, y, 0.067),
                        (0.042, 0.045, 0.134), wood, 2, 0.33 * side + y)
            for vertex in leg.data.vertices:
                if vertex.co.z < 0:
                    vertex.co.x *= 0.74
                    vertex.co.y *= 0.74
            parts.append(leg)
        peg = cylinder("床头柜_拉手底柱", (side * 0.048, -0.182, 0.382), 0.006, 0.019, metal)
        peg.rotation_euler.x = pi / 2
        parts.append(peg)
    pull = cylinder("床头柜_横拉手", (0, -0.193, 0.382), 0.0058, 0.124, metal)
    pull.rotation_euler.y = pi / 2
    parts.append(pull)
    return parts


def render_reimport(render_dir):
    for asset, view, angle, height, scale, size in (
        (CURTAIN, "curtain-glb", (2.5, -4.5, 2.9), 1.29, 3.3, (980, 940)),
        (NIGHTSTAND, "nightstand-glb", (0.75, -1.3, 0.85), 0.24, 0.74, (800, 800)),
    ):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(LIBRARY / asset / f"{asset}.glb"))
        scene = bpy.context.scene
        target = Vector((0, 0, height))
        scene.world = bpy.data.worlds.new("回导中性照明")
        scene.world.use_nodes = True
        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.24, 0.24, 0.24, 1)
        ground = room_material("检查底面", (0.205, 0.22, 0.23), 0.76)
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.003))
        bpy.context.object.data.materials.append(ground)
        camera = scene_camera(scene, view, angle, target, 45)
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = scale
        scene.camera = camera
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 24
        scene.cycles.use_denoising = True
        scene.render.resolution_x, scene.render.resolution_y = size
        for suffix, y in (("", -1), ("-reverse", 1)):
            camera.location.y = abs(angle[1]) * y
            camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
            for x, power in ((-1.3, 230), (1.4, 170)):
                bpy.ops.object.light_add(type="AREA", location=(x, y * 1.7, height + 1.25))
                light = bpy.context.object
                light.data.energy = power
                light.data.size = 1.8
                light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(render_dir / f"{view}{suffix}.png")
            bpy.ops.render.render(write_still=True)
            for obj in list(scene.objects):
                if obj.type == "LIGHT":
                    bpy.data.objects.remove(obj, do_unlink=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bedroom-wardrobe/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "bedroom-furnishings/house.blend")
    parser.add_argument("--renders", type=Path, default=ROOT / "renders/S003")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if any(scene.objects.get(asset) for asset in (CURTAIN, NIGHTSTAND)):
        raise RuntimeError("输入工程已装配待制作的资产")
    floor = scene.objects[BEDROOM_FLOOR].data.vertices[0].co.z
    south = next(wall for wall in WALLS if wall[0] == "south")
    left, right, _, _ = next(opening for opening in south[-1] if opening[1] < ROOM_BOUNDS[2])
    wall_y = south[2] + south[5] / 2
    offset = 0.146
    place_new(CURTAIN, curtain_parts(right - left + 1.05, (right - left) / 2 + 0.27, -offset),
              ((left + right) / 2, wall_y + offset, floor))
    place_new(NIGHTSTAND, nightstand_parts(),
              (ROOM_BOUNDS[0] + 0.254, scene.objects[BED].location.y + 0.407, floor), pi)

    views = {
        "bedroom-furnishings": ((2.89, 3.70, 1.63), (1.58, 0.94, 1.26), 24),
        "curtain-detail": ((1.33, 1.63, 2.08), (0.57, 0.36, 2.39), 54),
        "nightstand-detail": ((0.95, 1.64, 0.91), (0.52, 0.65, 0.38), 50),
    }
    cameras = {name: scene_camera(scene, name, *view) for name, view in views.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)

    render_dir = args.renders.resolve()
    render_dir.mkdir(parents=True, exist_ok=True)
    for name, camera in cameras.items():
        scene.camera = camera
        scene.render.filepath = str(render_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    render_reimport(render_dir)


if __name__ == "__main__":
    main()
