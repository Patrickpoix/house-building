"""沿 S001 净尺寸建模并装配 S003 家政间。"""

import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_a019_study import rounded_box
from build_s001_whitebox import WALLS
from build_s003_bathroom_vanity import area_light
from build_s003_bedroom import STAGES
from build_s003_bookshelf_study import board, white_oak_material
from build_s003_cooktop import scene_camera
from build_s003_living import LIBRARY, RENDERS, cylinder, mesh_object, place_new, room_material
import texture_a019_study as textures


WASHER = "A116"
CABINET = "A117"
FLOOR_TOP = 0.010
WASHER_WIDTH = 0.598
WASHER_DEPTH = 0.590
WASHER_HEIGHT = 0.848
DOOR_CENTER = 0.449
DOOR_PIVOT = (-0.195, -0.291, DOOR_CENTER)
DOOR_OPEN_ANGLE = -105 * pi / 180
VIEWS = {
    "utility-folding": ((5.24, 3.88, 1.53), (4.97, 2.82, 1.20), 18),
    "utility-washer-detail": ((5.18, 3.83, 0.91), (4.43, 3.20, 0.51), 29),
}


def profile(name, rings, material, caps=False, sides=96):
    """沿 -Y 的同轴截面从半径与深度构造门圈、滚筒或玻璃。"""
    closed = rings[0] == rings[-1]
    if closed:
        rings = rings[:-1]
    vertices = [(radius * cos(tau * index / sides), y, radius * sin(tau * index / sides))
                for radius, y in rings for index in range(sides)]
    faces = []
    for row in range(len(rings) if closed else len(rings) - 1):
        for index in range(sides):
            a = row * sides + index
            b = row * sides + (index + 1) % sides
            faces.append((a, b, (b + sides) % len(vertices), (a + sides) % len(vertices)))
    if caps:
        faces += [tuple(reversed(range(sides))), tuple(range(len(vertices) - sides, len(vertices)))]
    obj = mesh_object(name, vertices, faces, [material])
    if closed or caps:
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        mesh.free()
    uv = obj.data.uv_layers.new(name="门圈UV")
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
        for loop in face.loop_indices:
            x, _, z = vertices[obj.data.loops[loop].vertex_index]
            uv.data[loop].uv = (x / 0.45 + 0.5, z / 0.45 + 0.5)
    return obj


def axial_cylinder(name, center, radius, thickness, material, sides=48):
    part = cylinder(name, center, radius, thickness, material, vertices=sides)
    part.rotation_euler.x = pi / 2
    return part


def washer_parts():
    enamel = room_material("洗衣机_暖白搪瓷", (0.79, 0.80, 0.77), 0.36)
    textures.OUTPUT = LIBRARY / WASHER
    maps = textures.create_maps("enamel", (0.79, 0.80, 0.77), 0, 0.36, 0.011, 116)
    textures.connect_maps(enamel, maps)
    for image in maps.values():
        image.filepath = str(textures.OUTPUT / "textures" / Path(bpy.path.basename(image.filepath)).name)
        image.pack()
    bezel = room_material("洗衣机_烟灰门圈", (0.104, 0.115, 0.114), 0.30)
    rubber = room_material("洗衣机_橡胶门封", (0.046, 0.050, 0.049), 0.68)
    steel = room_material("洗衣机_缎面不锈钢", (0.47, 0.47, 0.45), 0.33, 0.88)
    lettering = room_material("洗衣机_指示刻度", (0.105, 0.135, 0.14), 0.44)
    display = room_material("洗衣机_显示窗", (0.035, 0.043, 0.041), 0.19)
    glass = room_material("洗衣机_浅灰观察玻璃", (0.83, 0.89, 0.88), 0.10)
    shader = glass.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Transmission Weight"].default_value = 1.0
    shader.inputs["IOR"].default_value = 1.46

    # 前围板由顶部、底部和左右钣金围出真圆孔，机门开启后仍能看到门封及滚筒。
    front = -WASHER_DEPTH / 2
    half = WASHER_WIDTH / 2
    cut = 0.187
    pts = []
    for i in range(96):
        angle = tau * i / 96 + pi / 4
        x, z = cos(angle), sin(angle)
        reach = min(half / max(abs(x), 1e-9),
                    (0.706 - DOOR_CENTER if z > 0 else DOOR_CENTER - 0.048) / max(abs(z), 1e-9))
        pts.extend(((x * reach, front, DOOR_CENTER + z * reach),
                    (x * cut, front, DOOR_CENTER + z * cut)))
    quads = [(i, (i + 2) % len(pts), (i + 3) % len(pts), i + 1) for i in range(0, len(pts), 2)]
    fascia = mesh_object("洗衣机_开孔前围板", pts, quads, [enamel])
    uv = fascia.data.uv_layers.new(name="前板UV")
    for loop in fascia.data.loops:
        x, _, z = pts[loop.vertex_index]
        uv.data[loop.index].uv = (x / WASHER_WIDTH + 0.5, z / WASHER_HEIGHT)
    fascia.modifiers.new("钢板厚度", "SOLIDIFY").thickness = 0.002
    parts = [fascia,
             rounded_box("洗衣机_控制面板", (0, -0.277, 0.766), (0.596, 0.037, 0.125), 0.010, enamel),
             rounded_box("洗衣机_机顶", (0, 0.003, 0.835), (0.598, 0.581, 0.026), 0.008, enamel),
             rounded_box("洗衣机_背板", (0, 0.281, 0.436), (0.594, 0.028, 0.780), 0.010, enamel),
             rounded_box("洗衣机_底部检修板", (0, -0.269, 0.032), (0.595, 0.053, 0.039), 0.006, enamel),
             rounded_box("洗衣机_泵滤检修盖", (0.214, -0.296, 0.040), (0.104, 0.005, 0.031), 0.002, enamel),
             rounded_box("洗衣机_投料抽盒", (-0.196, -0.298, 0.772), (0.184, 0.008, 0.079), 0.004, enamel),
             rounded_box("洗衣机_投料抽盒扣位", (-0.196, -0.303, 0.747), (0.115, 0.006, 0.009), 0.002, bezel),
             rounded_box("洗衣机_显示外屏", (0.148, -0.298, 0.774), (0.226, 0.006, 0.054), 0.003, display),
             axial_cylinder("洗衣机_旋钮背环", (0, -0.301, 0.770), 0.033, 0.008, bezel),
             axial_cylinder("洗衣机_选择旋钮", (0, -0.311, 0.770), 0.028, 0.018, steel)]
    for side in (-1, 1):
        parts += [rounded_box("洗衣机_侧壁", (side * (half - 0.009), 0, 0.428),
                              (0.018, 0.587, 0.798), 0.005, enamel)]
        for y in (-0.229, 0.227):
            parts += [cylinder("洗衣机_可调橡胶脚", (side * 0.234, y, 0.010), 0.025, 0.020, rubber)]
    for angle in (i * pi / 6 for i in range(12)):
        mark = rounded_box("洗衣机_程序标记", (0.043 * cos(angle), -0.298, 0.770 + 0.043 * sin(angle)),
                           (0.002, 0.0015, 0.006), 0.0004, lettering)
        mark.rotation_euler.y = pi / 2 - angle
        parts.append(mark)
    for x in (0.087, 0.121, 0.155, 0.189, 0.231):
        parts.append(axial_cylinder("洗衣机_触控指示", (x, -0.302, 0.761), 0.0031, 0.0017, steel, 16))

    for name, rings, mat, caps in (
        ("洗衣机_折叠橡胶门封", ((0.187, front), (0.189, -0.302), (0.177, -0.306),
                                (0.164, -0.293), (0.166, -0.279), (0.175, -0.267), (0.185, -0.257),
                                (0.187, front)), rubber, False),
        ("洗衣机_不锈钢滚筒", ((0.180, -0.268), (0.201, -0.250), (0.220, -0.221),
                              (0.220, 0.157), (0.208, 0.195), (0.175, 0.210)), steel, False),
        ("洗衣机_滚筒背冲压板", ((0.175, 0.210), (0.147, 0.202), (0.122, 0.186),
                                (0.086, 0.188), (0.071, 0.200)), steel, False),
    ):
        part = profile(name, rings, mat, caps)
        part.location.z = DOOR_CENTER
        parts.append(part)
    parts.append(axial_cylinder("洗衣机_滚筒轮毂", (0, 0.197, DOOR_CENTER), 0.074, 0.023, steel, 64))
    for angle in (0, tau / 3, 2 * tau / 3):
        paddle = rounded_box("洗衣机_滚筒提升筋",
                             (0.197 * cos(angle), -0.034, DOOR_CENTER + 0.197 * sin(angle)),
                             (0.023, 0.286, 0.037), 0.009, enamel)
        paddle.rotation_euler.y = -angle
        parts.append(paddle)
    parts.append(drum_perforations(lettering))
    for x in (-0.152, 0.138):
        parts.append(axial_cylinder("洗衣机_背部供排水接头", (x, 0.301, 0.718), 0.013, 0.021, steel, 24))
    return parts + washer_door(bezel, steel, rubber, glass)


def drum_perforations(dark):
    vertices, faces = [], []
    for row in range(12):
        center_y = -0.200 + row * 0.030
        for column in range(60):
            angle = tau * (column + (row % 2) / 2) / 60
            start = len(vertices)
            for i in range(8):
                step = tau * i / 8
                a = angle + 0.010 * cos(step)
                vertices.append((0.219 * cos(a), center_y + 0.0022 * sin(step),
                                 DOOR_CENTER + 0.219 * sin(a)))
            faces.append(tuple(range(start, start + 8)))
    part = mesh_object("洗衣机_滚筒孔纹", vertices, faces, [dark])
    uv = part.data.uv_layers.new(name="冲孔UV")
    for loop in part.data.loops:
        i = loop.vertex_index % 8
        uv.data[loop.index].uv = (0.5 + 0.5 * cos(tau * i / 8), 0.5 + 0.5 * sin(tau * i / 8))
    return part


def washer_door(bezel, steel, rubber, glass):
    outer_glass = ((0.151, -0.320), (0.150, -0.308), (0.129, -0.274),
                   (0.108, -0.251), (0.049, -0.247), (0.001, -0.248))
    glass_profile = (*reversed(outer_glass), *((r, y + 0.0035) for r, y in outer_glass))
    parts = [profile("洗衣机_外侧门圈", ((0.148, -0.325), (0.198, -0.325), (0.207, -0.320),
                                      (0.209, -0.309), (0.203, -0.294), (0.192, -0.291),
                                      (0.152, -0.297), (0.148, -0.325)), bezel),
             profile("洗衣机_门圈内金属嵌条", ((0.148, -0.326), (0.155, -0.327), (0.158, -0.325),
                                            (0.154, -0.321), (0.148, -0.322), (0.148, -0.326)), steel),
             profile("洗衣机_曲面观察玻璃", glass_profile, glass, caps=True)]
    for part in parts:
        part.location.z = DOOR_CENTER
    parts += [rounded_box("洗衣机_门扣拉手", (0.183, -0.323, DOOR_CENTER), (0.048, 0.014, 0.061), 0.006, bezel),
              rounded_box("洗衣机_门钩", (0.192, -0.285, DOOR_CENTER), (0.017, 0.022, 0.024), 0.003, steel)]
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=DOOR_PIVOT)
    pivot = bpy.context.object
    pivot.name = "洗衣机_门铰"
    bpy.context.view_layer.update()
    for part in parts:
        previous_world = part.matrix_world.copy()
        part.parent = pivot
        part.matrix_world = previous_world
    parts.append(pivot)
    # 轴座留在机身，门圈、玻璃及门钩作为一个组件旋转。
    for z in (DOOR_CENTER - 0.052, DOOR_CENTER + 0.052):
        parts.append(cylinder("洗衣机_铰链轴座", (DOOR_PIVOT[0], DOOR_PIVOT[1], z), 0.012, 0.030, rubber))
    return parts


def folding_cabinet():
    oak, _ = white_oak_material("家政柜_白橡木皮", "WoodUV")
    paint = room_material("家政柜_苔灰防潮漆", (0.225, 0.258, 0.220), 0.48)
    shadow = room_material("家政柜_踢脚板", (0.101, 0.116, 0.098), 0.61)
    metal = room_material("家政柜_深锡拉手", (0.184, 0.187, 0.162), 0.33, 0.73)
    stone = room_material("家政柜_暖白耐污台面", (0.68, 0.65, 0.57), 0.40)
    parts = []

    def panel(name, loc, size, mat, grain=2):
        parts.append(board(name, loc, size, mat, grain, sum(loc) * 0.21))

    panel("家政柜_连续折叠台面", (0.887, 0.315, 0.912), (1.774, 0.630, 0.031), stone)
    panel("家政柜_挡水后沿", (0.887, 0.012, 0.953), (1.774, 0.024, 0.053), stone)
    for x in (0.015, 0.707, 1.207, 1.757):
        panel("家政柜_承重侧板", (x, 0.313, 0.449), (0.022, 0.594, 0.898), oak)
    for x, width in ((0.957, 0.478), (1.482, 0.528)):
        panel("家政柜_柜背", (x, 0.029, 0.485), (width, 0.018, 0.810), oak)
        panel("家政柜_底板", (x, 0.317, 0.102), (width, 0.558, 0.019), oak)
        panel("家政柜_退进式踢脚", (x, 0.535, 0.049), (width, 0.022, 0.098), shadow)
    panel("家政柜_开放分隔层板", (0.957, 0.305, 0.522), (0.478, 0.551, 0.021), oak, 0)
    for z in (0.236, 0.502, 0.767):
        panel("家政柜_齐平抽面", (1.482, 0.607, z), (0.522, 0.020, 0.260), paint)
        panel("家政柜_抽身背口", (1.482, 0.546, z + 0.030), (0.456, 0.062, 0.172), oak, 0)
        panel("家政柜_抽屉拉手", (1.482, 0.623, z + 0.081), (0.156, 0.017, 0.013), metal)
    panel("家政柜_吊柜底板", (0.886, 0.162, 1.555), (1.751, 0.322, 0.022), oak, 0)
    panel("家政柜_吊柜顶板", (0.886, 0.162, 2.355), (1.751, 0.322, 0.022), oak, 0)
    for x in (0.016, 0.599, 1.181, 1.756):
        panel("家政柜_吊柜立板", (x, 0.166, 1.955), (0.021, 0.312, 0.784), oak)
    for x in (0.307, 0.889, 1.470):
        panel("家政柜_吊柜背板", (x, 0.018, 1.955), (0.551, 0.018, 0.784), oak)
        panel("家政柜_吊柜搁板", (x, 0.152, 1.960), (0.551, 0.261, 0.020), oak, 0)
        panel("家政柜_吊柜门板", (x, 0.330, 1.957), (0.577, 0.023, 0.783), paint)
        panel("家政柜_吊柜拉手", (x + 0.223, 0.347, 1.668), (0.014, 0.017, 0.098), metal)
    return parts


def utility_floor(west, east, south, north):
    grout = room_material("家政间_地砖缝", (0.277, 0.269, 0.243), 0.85)
    tile = room_material("家政间_细灰石砖", (0.38, 0.377, 0.339), 0.64)
    board("家政间_地砖底层", ((west + east) / 2, (south + north) / 2, 0.003),
          (east - west, north - south, 0.005), grout, 0, 0)
    for i in range(7):
        for j in range(3):
            dx, dy = (east - west) / 7, (north - south) / 3
            board("家政间_细灰石砖", (west + (i + 0.5) * dx, south + (j + 0.5) * dy, FLOOR_TOP - 0.004),
                  (dx - 0.002, dy - 0.002, 0.008), tile, 0, 0)


def reflect_door_swing(scene, north_axis):
    hinge = scene.objects["opening_utility_north_0_hinge"]
    hinge.rotation_euler.z = 0.0
    bpy.context.view_layer.update()
    closed = {part: part.matrix_world.copy() for part in hinge.children}
    hinge.location.y = 2 * north_axis - hinge.location.y
    bpy.context.view_layer.update()
    for part, matrix in closed.items():
        part.matrix_world = matrix
    hinge.rotation_euler.z = pi / 2
    bpy.context.view_layer.update()


def make_utility(source, output):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    walls = {name: (fixed, thickness) for name, _, fixed, _, _, thickness, _ in WALLS}
    west = walls["bedroom_east"][0] + walls["bedroom_east"][1] / 2
    east = walls["bath_east"][0] - walls["bath_east"][1] / 2
    south = walls["bath_north"][0] + walls["bath_north"][1] / 2
    north = walls["utility_north"][0] - walls["utility_north"][1] / 2
    utility_floor(west, east, south, north)
    reflect_door_swing(scene, walls["utility_north"][0])
    bpy.data.objects.remove(scene.objects["STUDY_washer"], do_unlink=True)
    cabinet_x, cabinet_y = west + 0.003, south + 0.005
    place_new(WASHER, washer_parts(), Vector((cabinet_x + 0.359, cabinet_y + 0.351, FLOOR_TOP)), pi)
    place_new(CABINET, folding_cabinet(), Vector((cabinet_x, cabinet_y, FLOOR_TOP)))

    metal = room_material("家政间_吸顶灯灯座", (0.69, 0.69, 0.66), 0.44)
    diffuser = room_material("家政间_磨砂灯罩", (0.92, 0.88, 0.80), 0.43)
    shader = diffuser.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Emission Color"].default_value = (1.0, 0.91, 0.79, 1.0)
    shader.inputs["Emission Strength"].default_value = 2.1
    for x in (west + 0.77, east - 0.78):
        y = (south + north) / 2 + 0.15
        cylinder("家政间_吸顶灯灯座", (x, y, 2.974), 0.12, 0.051, metal)
        cylinder("家政间_吸顶灯灯罩", (x, y, 2.945), 0.111, 0.010, diffuser)
        area_light("家政间_吸顶灯", (x, y, 2.934), (x, y, 0.0), 53, 0.32, (1, 0.91, 0.80))
    board("家政间_折叠台线性灯槽", (cabinet_x + 0.89, cabinet_y + 0.256, 1.550),
          (1.51, 0.031, 0.008), diffuser, 0, 0)
    area_light("家政间_折叠台工作灯", (cabinet_x + 0.89, cabinet_y + 0.253, 1.543),
               (cabinet_x + 0.89, cabinet_y + 0.36, 0.95), 17, 0.75, (1, 0.88, 0.76))
    for name, view in VIEWS.items():
        scene_camera(scene, name, *view)
    scene.camera = scene.objects["utility-folding"]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)


def render_glb(asset, render_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(LIBRARY / asset / f"{asset}.glb"))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("家政资产回导照明")
    scene.world.color = (0.28, 0.28, 0.28)
    floor = room_material("检查地面", (0.30, 0.30, 0.28), 0.70)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
    bpy.context.object.data.materials.append(floor)
    area_light("回导面光", (0.60, -3.8, 3.2), (0, 0, 0.65), 240, 3.0, (1, 0.97, 0.93))
    area_light("回导侧光", (-2.0, -0.90, 2.3), (0, 0, 0.70), 83, 1.7, (1, 1, 1))
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = (1000, 1000)
    if asset == WASHER:
        hinge = scene.objects["洗衣机_门铰"]
        hinge.rotation_mode = "XYZ"
        hinge.rotation_euler.z += DOOR_OPEN_ANGLE
        camera = scene_camera(scene, "washer-open", (0.55, -1.60, 1.22), (-0.13, -0.15, 0.40), 46)
        camera.data.type, camera.data.ortho_scale = "ORTHO", 1.22
        output = "utility-washer-glb-open.png"
    else:
        camera = scene_camera(scene, "folding-cabinet", (2.9, 3.72, 2.98), (0.88, 0.25, 1.18), 43)
        camera.data.type, camera.data.ortho_scale = "ORTHO", 2.67
        output = "utility-folding-glb.png"
    scene.camera = camera
    scene.render.filepath = str(render_dir / output)
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "bathroom-toilet/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "utility-folding/house.blend")
    parser.add_argument("--renders", type=Path, default=RENDERS)
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    make_utility(source, output)
    if not args.no_render:
        scene = bpy.context.scene
        args.renders.mkdir(parents=True, exist_ok=True)
        for name in VIEWS:
            scene.camera = scene.objects[name]
            if name == "utility-folding":
                scene.render.resolution_x, scene.render.resolution_y = (1160, 1240)
            scene.render.filepath = str(args.renders.resolve() / f"{name}.png")
            bpy.ops.render.render(write_still=True)
        for asset in (WASHER, CABINET):
            render_glb(asset, args.renders.resolve())


if __name__ == "__main__":
    main()
