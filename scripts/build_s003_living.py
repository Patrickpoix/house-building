"""打包现有起居资产并装配 S003 正式起居场景。"""

from math import pi
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_s003_bookshelf_study import board
from build_s001_whitebox import material


SOURCE = ROOT / "stages/S003/chair-fabric-room-study/house-chair-fabric-study.blend"
LIBRARY = ROOT / "assets"
RENDERS = ROOT / "renders/S003"
VIEWS = {
    "living": ((4.86, 5.02, 1.48), (1.37, 7.83, 1.20), 25),
    "reading-corner": ((3.05, 7.33, 1.38), (1.08, 8.94, 1.10), 31),
    "living-reverse": ((1.55, 9.44, 1.46), (1.63, 6.72, 0.74), 26),
    "kitchen": ((6.43, 6.80, 1.58), (9.15, 8.73, 1.39), 29),
    "entry": ((9.10, 1.46, 1.37), (7.37, 2.53, 0.68), 32),
}
# 20261121 为本批验收抽样种子，镜头从实际房间一侧观察。
REVIEW_VIEWS = {
    "living-side-table": ((1.98, 7.05, 1.04), (0.87, 8.16, 0.40), 55),
    "A031": ((8.35, 8.13, 1.53), (9.75, 8.86, 1.52), 51),
    "entry-bench": ((8.91, 1.78, 0.95), (7.30, 2.72, 0.34), 40),
    "living-bookshelf": ((2.57, 7.84, 1.55), (0.43, 9.075, 1.06), 30),
    "A030": ((8.43, 2.21, 1.04), (7.30, 2.99, 0.77), 56),
}


def own_collection(asset, objects, origin, angle=0):
    collection = bpy.data.collections.new(asset)
    bpy.context.scene.collection.children.link(collection)
    inverse = (Matrix.Translation(origin) @ Matrix.Rotation(angle, 4, "Z")).inverted()
    roots = {obj: obj.matrix_world.copy() for obj in objects if obj.parent not in objects}
    for obj in objects:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    for obj, world in roots.items():
        obj.matrix_world = inverse @ world
    bpy.context.view_layer.update()
    return collection


def publish_asset(asset, objects, origin, angle=0, placement=None):
    if not objects:
        raise RuntimeError(f"{asset} 缺少来源对象")
    folder = LIBRARY / asset
    folder.mkdir(parents=True, exist_ok=True)
    collection = own_collection(asset, objects, origin, angle)
    collection.asset_mark()
    bpy.ops.file.pack_all()
    blend_path = folder / f"{asset}.blend"
    bpy.data.libraries.write(str(blend_path), {collection}, fake_user=True, compress=True)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(folder / f"{asset}.glb"), export_format="GLB",
        use_selection=True, export_apply=True,
    )
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)
    with bpy.data.libraries.load(str(blend_path), link=True, relative=True) as (source, target):
        target.collections = [asset]
    instance = bpy.data.objects.new(asset, None)
    instance.instance_type = "COLLECTION"
    instance.instance_collection = target.collections[0]
    instance.empty_display_size = 0.2
    instance.location = placement if placement is not None else origin
    instance.rotation_euler.z = angle
    bpy.context.scene.collection.objects.link(instance)
    return instance


def load_study(path, prefix, exclude=()):
    study = ROOT / path
    with bpy.data.libraries.load(str(study)) as (source, target):
        target.objects = [name for name in source.objects if name.startswith(prefix) and name not in exclude]
    objects = target.objects
    for obj in objects:
        bpy.context.scene.collection.objects.link(obj)
        for material in obj.data.materials if obj.type in {"MESH", "CURVE"} else ():
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and not node.image.packed_file:
                    image = node.image
                    image.filepath = str(study.parent / "textures" / Path(image.filepath).name)
                    image.reload()
                    image.pack()
    bpy.context.view_layer.update()
    return objects


def publish_chair():
    chair = bpy.data.objects["STUDY_reading_chair_fabric_v2"]
    mat = chair.active_material
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    output = next(node for node in nodes if node.type == "OUTPUT_MATERIAL")
    shader_mix = output.inputs["Surface"].links[0].from_node
    fabric, original = [shader_mix.inputs[i].links[0].from_node for i in (1, 2)]
    factor = shader_mix.inputs[0].links[0].from_socket
    emission = nodes.new("ShaderNodeEmission")
    links.new(emission.outputs[0], output.inputs["Surface"])
    baked = {}
    scene = bpy.context.scene
    previous_samples = scene.cycles.samples
    scene.cycles.samples = 1
    bpy.ops.object.select_all(action="DESELECT")
    chair.select_set(True)
    bpy.context.view_layer.objects.active = chair
    for channel, color_space in (("Base Color", "sRGB"), ("Roughness", "Non-Color"), ("Normal", "Non-Color")):
        blend = nodes.new("ShaderNodeMixRGB")
        links.new(factor, blend.inputs[0])
        if channel == "Normal":
            # 布面使用平坦切线法线，木框留用原 2K 法线。
            blend.inputs[1].default_value = (0.5, 0.5, 1, 1)
            normal_map = original.inputs[channel].links[0].from_node
            source = normal_map.inputs["Color"].links[0].from_socket
        else:
            links.new(fabric.inputs[channel].links[0].from_socket, blend.inputs[1])
            source = original.inputs[channel].links[0].from_socket
        links.new(source, blend.inputs[2])
        links.new(blend.outputs[0], emission.inputs["Color"])
        name = f"ReadingChair_{channel.replace(' ', '')}_2K"
        image = bpy.data.images.new(name, width=2048, height=2048, alpha=False)
        image.colorspace_settings.name = color_space
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        nodes.active = texture
        bpy.ops.object.bake(type="EMIT", margin=10)
        image.pack()
        baked[channel] = texture
    scene.cycles.samples = previous_samples
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 0
    normal = nodes.new("ShaderNodeNormalMap")
    links.new(baked["Normal"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    for channel in ("Base Color", "Roughness"):
        links.new(baked[channel].outputs["Color"], shader.inputs[channel])
    links.new(shader.outputs[0], output.inputs["Surface"])
    for node in list(nodes):
        if node not in (shader, normal, output, *baked.values()):
            nodes.remove(node)
    publish_asset("reading-chair", [chair], chair.location.copy())


def room_material(name, color, roughness, metallic=0):
    mat = material(name, color, roughness)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = metallic
    return mat


def mesh_object(name, vertices, faces, materials):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for material in materials:
        mesh.materials.append(material)
    return obj


def textile(name, color):
    mat = room_material(name, color, 0.8)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Sheen Weight"].default_value = 0.25
    for suffix, channel in (("rough", "Roughness"), ("nor_gl", "Normal")):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(
            str(LIBRARY / "materials/terlenka" / f"terlenka_{suffix}_2k.jpg"),
            check_existing=True,
        )
        tex.image.colorspace_settings.name = "Non-Color"
        socket = tex.outputs["Color"]
        if channel == "Normal":
            normal = nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = 0.32
            links.new(socket, normal.inputs["Color"])
            socket = normal.outputs["Normal"]
        links.new(socket, shader.inputs[channel])
    return mat


def upholstered(name, center, size, mat, radius, tilt=0, repeats=(2, 2)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    uv = obj.data.uv_layers.active
    for loop in uv.data:
        loop.uv.x *= repeats[0] * 4
        loop.uv.y *= repeats[1] * 3
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("软包圆边", "BEVEL")
    bevel.width = radius
    bevel.segments = 8
    obj.modifiers.new("软包法线", "WEIGHTED_NORMAL").keep_sharp = True
    for face in obj.data.polygons:
        face.use_smooth = True
    obj.rotation_euler.x = tilt
    return obj


def cylinder(name, center, radius, height, mat, narrow=None, vertices=48):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius,
        radius2=radius if narrow is None else narrow, depth=height, location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("触边倒圆", "BEVEL")
    bevel.width = min(radius * 0.15, height * 0.25, 0.008)
    bevel.segments = 3
    obj.modifiers.new("边缘法线", "WEIGHTED_NORMAL")
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


def place_new(asset, objects, origin, angle=0):
    transform = Matrix.Translation(origin) @ Matrix.Rotation(angle, 4, "Z")
    bpy.context.view_layer.update()
    transforms = {obj: obj.matrix_world.copy() for obj in objects if obj.parent not in objects}
    for obj, world in transforms.items():
        obj.matrix_world = transform @ world
    bpy.context.view_layer.update()
    publish_asset(asset, objects, origin, angle)


def build_sofa(wood):
    olive = textile("沙发_橄榄绿织物", (0.19, 0.22, 0.123))
    seat = textile("沙发_坐垫织物", (0.235, 0.255, 0.155))
    sage = textile("沙发_靠垫织物", (0.26, 0.29, 0.19))
    parts = [
        upholstered("软包底座", (0, 0, 0.225), (2.20, 0.90, 0.25), olive, 0.065, repeats=(6, 4)),
        upholstered("连续背框", (0, 0.34, 0.50), (2.19, 0.21, 0.64), olive, 0.073, -0.07),
    ]
    for side in (-1, 1):
        parts.extend([
            upholstered("扶手", (side * 1.012, -0.024, 0.432), (0.176, 0.79, 0.398), olive, 0.08),
            upholstered("坐垫", (side * 0.464, -0.113, 0.36), (0.927, 0.692, 0.181), seat, 0.081, repeats=(3, 3)),
            upholstered("背垫", (side * 0.464, 0.222, 0.622), (0.934, 0.221, 0.456), sage, 0.105, -0.18),
        ])
        for y in (-0.31, 0.30):
            parts.append(cylinder("收分木脚", (side * 0.93, y, 0.063), 0.024, 0.126, wood, 0.04))
    place_new("living-sofa", parts, Vector((0.747, 6.70, 0.0)), pi / 2)


def stage_living(wood):
    cloth = textile("地毯_燕麦色", (0.40, 0.354, 0.275))
    rug = upholstered("短绒地毯", (0, 0, 0.010), (2.11, 2.63, 0.020), cloth, 0.009, repeats=(9, 11))
    place_new("living-rug", [rug], Vector((2.07, 6.80, 0)))
    coffee = cylinder("茶几圆台面", (0, 0, 0.376), 0.366, 0.035, wood, vertices=96)
    # 圆台面以立面和顶面各自的 UV 投影保持木纹尺度。
    for face in coffee.data.polygons:
        if len(face.vertices) == 4:
            continue
        for loop_id in face.loop_indices:
            vertex = coffee.data.vertices[coffee.data.loops[loop_id].vertex_index].co
            coffee.data.uv_layers.active.data[loop_id].uv = (vertex.x / 0.5, vertex.y / 0.5)
    parts = [coffee, cylinder("茶几支撑圈", (0, 0, 0.327), 0.253, 0.063, wood)]
    for x, y in ((0.164, -0.105), (-0.158, -0.10), (0, 0.184)):
        parts.append(cylinder("茶几木脚", (x, y, 0.165), 0.026, 0.33, wood, 0.038))
    place_new("living-coffee-table", parts, Vector((2.01, 6.68, 0.02)))
    bowl = load_study("stages/S002/A103-study/study.blend", "A103_bowl")
    place_new("A103", bowl, Vector((2.075, 6.73, 0.4135)))

    covers = [
        room_material("封面_铁锈红", (0.24, 0.095, 0.065), 0.62),
        room_material("封面_灰蓝", (0.11, 0.16, 0.19), 0.62),
        room_material("封面_牛皮纸", (0.47, 0.348, 0.216), 0.74),
    ]
    paper = room_material("书页_本白", (0.73, 0.66, 0.52), 0.83)

    def book(y, z, width, height, color):
        jacket = board("书封", (0.397, y, z + height / 2), (0.202, width, height), color, 2, 0)
        pages = board(
            "书口", (0.403, y, z + height / 2),
            (0.194, width - 0.005, height - 0.006), paper, 2, 0,
        )
        # 书脊朝向房间，书口从两侧书封之间露出。
        pages.location.x -= 0.013
        return jacket, pages

    parts = []
    for y, z in ((8.72, 0.749), (9.38, 1.429)):
        for width, height, color in zip((0.031, 0.043, 0.026, 0.037), (0.235, 0.264, 0.214, 0.253),
                                        (covers[0], covers[2], covers[1], covers[2])):
            parts.extend(book(y + width / 2, z, width, height, color))
            y += width + 0.004
    bookshelf = bpy.data.collections.new("S003 陈设")
    bpy.context.scene.collection.children.link(bookshelf)
    for obj in parts:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        bookshelf.objects.link(obj)


def stage_entry_and_kitchen(wood):
    dark = room_material("五金_深青铜", (0.062, 0.049, 0.035), 0.39, 0.72)
    bench = [board("换鞋凳_面板", (7.30, 2.72, 0.447), (0.41, 1.08, 0.046), wood, 1, 0)]
    for y in (2.28, 3.16):
        bench.append(board("换鞋凳_板脚", (7.30, y, 0.212), (0.36, 0.035, 0.424), wood, 2, 0))
    bench.append(board("换鞋凳_撑板", (7.18, 2.72, 0.274), (0.035, 0.88, 0.112), wood, 1, 0))
    publish_asset("entry-bench", bench, Vector((7.30, 2.72, 0)))
    bag = load_study("stages/S002/A030-study/continuous-study.blend", "A030_")
    place_new("A030", bag, Vector((7.30, 2.99, 0.467)), pi / 2)

    apron = load_study("stages/S002/A031-study/reconstructed-v2.blend", "A031_", ("A031_tripo_guide",))
    place_new("A031", apron, Vector((9.753, 8.86, 0.978)), -pi / 2)
    hook = cylinder("东墙_围裙挂钩", (9.765, 8.86, 2.076), 0.010, 0.069, dark, 0.013)
    hook.rotation_euler.y = -pi / 2
    cooker = load_study("stages/S002/A019-study/study-textured.blend", "A019_")
    place_new("A019", cooker, Vector((9.45, 7.78, 0.94)), -pi / 2)

    source = bpy.data.objects["STUDY_kitchen_base"]
    source.name = "餐厨_东侧柜箱"
    source.location.x += 0.012
    source.dimensions.x -= 0.024
    source.location.z += 0.045
    source.dimensions.z -= 0.09
    bpy.data.objects["STUDY_kitchen_worktop"].name = "餐厨_东侧台面"
    paint = room_material("餐厨_鼠尾草烤漆", (0.24, 0.295, 0.236), 0.47)
    board("餐厨_东侧退缩踢脚", (9.50, 7.15, 0.045), (0.64, 4.88, 0.09), dark, 1, 0)
    for i in range(8):
        width = 4.90 / 8
        y = 4.70 + width * (i + 0.5)
        board("餐厨_东侧门板", (9.113, y, 0.49), (0.022, width - 0.006, 0.773), paint, 2, i / 7)
        board("餐厨_东侧拉手", (9.088, y, 0.815), (0.028, 0.125, 0.017), dark, 1, 0)
    build_sink_run(paint, dark)


def build_sink_run(paint, dark):
    worktop = bpy.data.objects["STUDY_north_worktop"]
    surface = worktop.active_material
    for obj in (worktop, bpy.data.objects["STUDY_north_counter"]):
        bpy.data.objects.remove(obj, do_unlink=True)
    for name, x0, x1, y0, y1 in (
        ("左", 7.15, 7.66, 9.10, 9.80),
        ("右", 8.29, 9.05, 9.10, 9.80),
        ("前", 7.66, 8.29, 9.10, 9.29),
        ("后", 7.66, 8.29, 9.66, 9.80),
    ):
        board(f"北侧操作台_{name}", ((x0 + x1) / 2, (y0 + y1) / 2, 0.91),
              (x1 - x0, y1 - y0, 0.06), surface, 0, 0)
    board("北柜_底板", (8.10, 9.47, 0.103), (1.88, 0.64, 0.026), paint, 0, 0)
    board("北柜_背板", (8.10, 9.765, 0.49), (1.88, 0.025, 0.78), paint, 2, 0)
    for i in range(4):
        x = 7.162 + i * 0.625
        board("北柜_隔板", (x, 9.47, 0.485), (0.024, 0.64, 0.79), paint, 2, 0)
        if i < 3:
            board("北柜_门板", (x + 0.31, 9.123, 0.49), (0.613, 0.022, 0.773), paint, 2, i)
            board("北柜_拉手", (x + 0.31, 9.098, 0.815), (0.125, 0.028, 0.017), dark, 0, 0)
    board("北柜_退缩踢脚", (8.10, 9.47, 0.045), (1.88, 0.60, 0.09), dark, 0, 0)

    steel = room_material("水槽_缎面不锈钢", (0.51, 0.51, 0.48), 0.31, 0.78)
    x, y = 7.975, 9.475
    for part, cx, cy, w, d in (
        ("前", x, 9.300, 0.646, 0.024), ("后", x, 9.650, 0.646, 0.024),
        ("左", 7.672, y, 0.040, 0.347), ("右", 8.278, y, 0.040, 0.347),
    ):
        board(f"水槽压边_{part}", (cx, cy, 0.941), (w, d, 0.004), steel, 0, 0)
    floor = board("水槽内底", (x, y, 0.757), (0.575, 0.320, 0.008), steel, 0, 0)
    for side in (-1, 1):
        board("盆壁_纵向", (x + side * 0.286, y, 0.847), (0.009, 0.322, 0.182), steel, 2, 0)
        board("盆壁_横向", (x, y + side * 0.159, 0.847), (0.578, 0.009, 0.182), steel, 2, 0)
    cylinder("水槽滤盖", (x, y, floor.location.z + 0.006), 0.043, 0.005, dark, vertices=32)
    cylinder("龙头底座", (x, 9.725, 0.953), 0.028, 0.026, steel)
    data = bpy.data.curves.new("龙头弯管", "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = 0.011
    data.bevel_resolution = 5
    spline = data.splines.new("BEZIER")
    path = [(x, 9.725, 0.961), (x, 9.725, 1.139), (x, 9.685, 1.202),
            (x, 9.598, 1.205), (x, 9.535, 1.16)]
    spline.bezier_points.add(len(path) - 1)
    for point, position in zip(spline.bezier_points, path, strict=True):
        point.co = position
        point.handle_left_type = point.handle_right_type = "AUTO"
    tap = bpy.data.objects.new("龙头弯管", data)
    bpy.context.collection.objects.link(tap)
    data.materials.append(steel)


def lamp_cord(lamp):
    cord = bpy.data.objects["STUDY_lamp_cord"]
    positions = (
        (0.87, 8.16, 0.554), (0.72, 8.22, 0.546), (0.665, 8.22, 0.527),
        (0.64, 8.25, 0.47), (0.622, 8.25, 0.145), (0.563, 8.25, 0.018),
        (0.42, 8.25, 0.011), (0.26, 8.24, 0.018), (0.224, 8.18, 0.116), (0.222, 8.18, 0.27),
    )
    for point, position in zip(cord.data.splines[0].bezier_points, positions, strict=True):
        point.co = position
        point.handle_left_type = point.handle_right_type = "AUTO"
    cord.name = "台灯电线"
    bpy.data.objects["STUDY_socket_plate"].name = "起居插座"
    bpy.data.objects["STUDY_lamp_plug"].name = "台灯插头"
    light = bpy.data.lights.new("台灯_2700K", "POINT")
    light.energy = 6
    light.color = (1, 0.67, 0.38)
    light.shadow_soft_size = 0.08
    fixture = bpy.data.objects.new(light.name, light)
    bpy.context.scene.collection.objects.link(fixture)
    x, y, z = lamp.location
    fixture.location = (x, y, z + 0.29)


def lighting(scene):
    data = bpy.data.lights.new("起居半吸顶灯", "AREA")
    data.energy = 42
    data.shape = "DISK"
    data.size = 0.37
    data.color = (1.0, 0.86, 0.70)
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = (2.06, 6.94, 2.83)
    ceiling = room_material("吸顶灯_乳白玻璃", (0.9, 0.83, 0.72), 0.29)
    shader = ceiling.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Emission Color"].default_value = (1, 0.85, 0.66, 1)
    shader.inputs["Emission Strength"].default_value = 0.42
    cylinder("起居吸顶灯_底盘", (2.06, 6.94, 2.975), 0.165, 0.05, ceiling)
    cylinder("起居吸顶灯_漫射罩", (2.06, 6.94, 2.90), 0.222, 0.12, ceiling)


def render_views(scene):
    RENDERS.mkdir(parents=True, exist_ok=True)
    old_camera = scene.camera
    bpy.data.objects.remove(old_camera, do_unlink=True)
    review_dir = RENDERS / "asset-review"
    review_dir.mkdir(exist_ok=True)
    cameras = {**VIEWS, **{f"review-{name}": view for name, view in REVIEW_VIEWS.items()}}
    for name, (location, target, lens) in cameras.items():
        data = bpy.data.cameras.new(name)
        data.lens = lens
        camera = bpy.data.objects.new(name, data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = bpy.data.objects["living"]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D" and area.spaces.active.region_3d:
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    scene.render.filepath = "//renders/S003/living.png"
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "house.blend"), compress=True, relative_remap=True)
    for name in cameras:
        scene.camera = bpy.data.objects[name]
        output = review_dir if name.startswith("review-") else RENDERS
        scene.render.filepath = str(output / f"{name.removeprefix('review-')}.png")
        bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    bpy.context.view_layer.update()
    wood = bpy.data.materials["书架_白橡木皮_试验"]
    # 通用 UV 使用活动层，书架 WoodUV 和圆件默认 UV 均可导出 glTF。
    for node in wood.node_tree.nodes:
        if node.type == "UVMAP":
            node.uv_map = ""
    shelf = [obj for obj in scene.objects if obj.name.startswith("书架")]
    table = [obj for obj in scene.objects if obj.name.startswith("STUDY_side_table_")]
    publish_asset("living-bookshelf", shelf, Vector((0.385, 9.075, 0)))
    publish_asset("living-side-table", table, Vector((1.52, 7.95, 0)), placement=(0.87, 8.16, 0))
    lamp = publish_asset(
        "living-table-lamp", [bpy.data.objects["STUDY_table_lamp_original"]],
        Vector((1.52, 7.95, 0.54)), placement=(0.87, 8.16, 0.54),
    )
    lamp_cord(lamp)
    publish_chair()
    for name in ("STUDY_sofa_base", "STUDY_sofa_back"):
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    build_sofa(wood)
    stage_living(wood)
    stage_entry_and_kitchen(wood)
    lighting(scene)
    scene.cycles.samples = 30
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 720
    render_views(scene)


if __name__ == "__main__":
    main()
