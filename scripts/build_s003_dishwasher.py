"""制作可开门的柜下洗碗机，并在北台水槽右侧校核净空。"""

import argparse
from math import pi
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_a019_study import rounded_box
from build_s003_bedroom import OPEN_AREA_FLOOR, STAGES
from build_s003_cooking_station import satin_steel
from build_s003_cooktop import scene_camera
from build_s003_counter_seating_and_doors import hinge
from build_s003_kitchen_everyday import tube
from build_s003_kitchen_props import rod
from build_s003_living import LIBRARY, RENDERS, cylinder, place_new, room_material
from build_s003_reusable_openings import parent_parts

ASSET = "A205"
BODY_LIFT = 0.150
LOWER_RACK_TRAVEL = 0.235
VIEWS = {
    "kitchen-dishwasher": ((7.78, 7.86, 1.27), (8.64, 9.15, 0.55), 38),
    "kitchen-dishwasher-open": ((7.87, 7.75, 1.44), (8.70, 8.98, 0.48), 34),
}


def dish_basket(name, z, width, depth, steel, polymer, full):
    x_edge, y_edge = width / 2, depth / 2
    corners = [(-x_edge, -y_edge + 0.009), (-x_edge + 0.009, -y_edge), (x_edge - 0.009, -y_edge),
               (x_edge, -y_edge + 0.009), (x_edge, y_edge - 0.009), (x_edge - 0.009, y_edge),
               (-x_edge + 0.009, y_edge), (-x_edge, y_edge - 0.009), (-x_edge, -y_edge + 0.009)]
    bottom, lip, cage = z, z + 0.078, []
    for height in (bottom, lip):
        cage.append(tube(f"{name}_连续外沿", [(x, y, height) for x, y in corners], 0.0038, polymer))
    rows = 12
    for i in range(rows):
        x = (i / (rows - 1) - 0.5) * (width - 0.040)
        cage.append(tube(f"{name}_沿深度折弯排架", [(x, -y_edge, lip), (x, -y_edge, bottom + 0.014),
                        (x, -y_edge + 0.015, bottom), (x, y_edge - 0.015, bottom),
                        (x, y_edge, bottom + 0.014), (x, y_edge, lip)], 0.0023, polymer))
    for i in range(8):
        y = (i / 7 - 0.5) * (depth - 0.035)
        cage.append(rod(f"{name}_横向底部钢网", (-x_edge, y, bottom), (x_edge, y, bottom), 0.0026, polymer))
    if full:
        for x in (-0.141, -0.027, 0.091, 0.167):
            for y in (-0.149, -0.107, -0.065, -0.023, 0.019, 0.061, 0.103, 0.145):
                cage.append(rod(f"{name}_可立盘隔齿", (x, y, bottom), (x + 0.015, y + 0.004, lip - 0.013), 0.0025, polymer))
    for side in (-1, 1):
        x = side * (x_edge + 0.003)
        for y in (-0.138, 0.138):
            cage.append(rod(f"{name}_滚轮", (x, y, bottom + 0.014), (x + side * 0.009, y, bottom + 0.014), 0.013, steel))
        cage.append(rod(f"{name}_侧挂防跳杆", (x, -y_edge, lip), (x, y_edge, lip), 0.0039, steel))
    cage.append(rounded_box(f"{name}_前沿塑胶拉把", (0, -y_edge - 0.006, lip), (0.143, 0.017, 0.022), 0.0045, polymer))
    return cage


def dishwasher():
    steel = satin_steel(ASSET)
    chassis = room_material("洗碗机_消音外壳镀层", (0.158, 0.185, 0.175), 0.62, 0.46)
    glass = room_material("洗碗机_烟青按钮观察面", (0.043, 0.072, 0.062), 0.24)
    rubber = room_material("洗碗机_门周耐热密封条", (0.035, 0.046, 0.041), 0.79)
    spray = room_material("洗碗机_灰绿耐热尼龙件", (0.22, 0.30, 0.268), 0.66)
    rack_coat = room_material("洗碗机_雾灰保护涂层钢丝", (0.425, 0.459, 0.419), 0.53, 0.13)
    panel = room_material("洗碗机_暖灰珐琅门板", (0.38, 0.414, 0.395), 0.46, 0.28)
    fixed = [rounded_box("洗碗机_不锈钢内胆顶板", (0, 0.004, 0.708), (0.565, 0.537, 0.025), 0.005, steel),
             rounded_box("洗碗机_不锈钢内胆背板", (0, 0.268, 0.389), (0.563, 0.024, 0.63), 0.008, steel),
             rounded_box("洗碗机_独立泵仓和底部隔水盘", (0, 0.008, 0.052), (0.581, 0.551, 0.063), 0.012, chassis),
             rounded_box("洗碗机_倾斜导水槽内胆底板", (0, 0.012, 0.106), (0.565, 0.523, 0.024), 0.009, steel),
             cylinder("洗碗机_底部可拆细滤芯", (0, 0.015, 0.127), 0.043, 0.017, chassis, vertices=64),
             cylinder("洗碗机_喷臂独立轴座", (0.014, 0.040, 0.143), 0.029, 0.025, steel, vertices=48),
             rounded_box("洗碗机_出口喷淋长臂", (0.014, 0.040, 0.162), (0.431, 0.039, 0.017), 0.008, spray)]
    for x in (-0.21, -0.154, -0.093, -0.031, 0.042, 0.121, 0.197):
        fixed.append(cylinder("洗碗机_独立喷嘴", (x + 0.014, 0.042, 0.172), 0.0025, 0.004, chassis, vertices=16))
    for side in (-1, 1):
        x = side * 0.285
        fixed.extend([rounded_box("洗碗机_反折成型外侧板", (x, 0.006, 0.388), (0.022, 0.548, 0.654), 0.005, chassis),
                      rounded_box("洗碗机_成型钢胆侧壁", (side * 0.265, 0.006, 0.401), (0.015, 0.524, 0.601), 0.0045, steel),
                      rounded_box("洗碗机_贯通门封立边", (side * 0.276, -0.263, 0.398), (0.012, 0.015, 0.623), 0.004, rubber)])
        for z in (0.192, 0.464):
            fixed.append(rounded_box("洗碗机_胆壁固定导轨", (side * 0.259, 0.006, z), (0.017, 0.492, 0.020), 0.003, steel))
        fixed.append(rod("洗碗机_门铰销和轴套", (side * 0.263, -0.271, 0.088),
                         (side * 0.292, -0.271, 0.088), 0.012, steel))
    for z in (0.091, 0.707):
        fixed.append(rounded_box("洗碗机_贯通门封横边", (0, -0.264, z), (0.559, 0.012, 0.011), 0.003, rubber))
    upper = dish_basket("洗碗机_上碗篮", 0.476, 0.473, 0.459, steel, rack_coat, False)
    lower = dish_basket("洗碗机_下盘篮", 0.204, 0.473, 0.459, steel, rack_coat, True)
    for side in (-1, 1):
        upper.append(rounded_box("洗碗机_上篮里轨", (side * 0.244, 0.003, 0.473), (0.018, 0.479, 0.008), 0.003, steel))
        lower.append(rounded_box("洗碗机_下篮伸缩里轨", (side * 0.244, 0.003, 0.201), (0.018, 0.479, 0.008), 0.003, steel))
    rail = hinge("洗碗机_下篮伸出轴", (0, 0, 0))
    anchor = hinge("洗碗机_门下翻轴", (0, -0.271, 0.088))
    door = [rounded_box("洗碗机_暖灰独立门外板", (0, -0.291, 0.401), (0.595, 0.031, 0.626), 0.0075, panel),
            rounded_box("洗碗机_拉丝不锈内侧门皮", (0, -0.271, 0.401), (0.563, 0.015, 0.581), 0.007, steel),
            rounded_box("洗碗机_控制面板黑玻嵌条", (0, -0.308, 0.661), (0.536, 0.006, 0.038), 0.0025, glass),
            tube("洗碗机_前拉手压弯金属杆", [(-0.155, -0.302, 0.595), (-0.155, -0.323, 0.595),
                 (-0.143, -0.331, 0.595), (0.143, -0.331, 0.595), (0.155, -0.323, 0.595), (0.155, -0.302, 0.595)], 0.0065, steel),
            rounded_box("洗碗机_洗涤块及漂洗剂盒", (-0.160, -0.253, 0.501), (0.109, 0.025, 0.091), 0.009, chassis),
            rounded_box("洗碗机_弹按小盒盖", (-0.167, -0.239, 0.508), (0.064, 0.007, 0.063), 0.005, spray)]
    for x in (-0.215, 0.140, 0.171, 0.202, 0.233):
        button = cylinder("洗碗机_微凹圆控制键", (x, -0.313, 0.661), 0.007, 0.005, steel, vertices=24)
        button.rotation_euler.x = pi / 2
        door.append(button)
    lifted = [*fixed, *upper, parent_parts(rail, lower), parent_parts(anchor, door)]
    for part in lifted:
        part.location.z += BODY_LIFT
    base = [rounded_box("洗碗机_退缩可拆检修盖", (0, -0.234, 0.109), (0.564, 0.029, 0.119), 0.006, chassis)]
    for side in (-1, 1):
        for y in (-0.198, 0.219):
            center = (side * 0.245, y)
            base.extend([
                cylinder("洗碗机_可调防滑底脚", (*center, 0.008), 0.021, 0.016, rubber, vertices=36),
                cylinder("洗碗机_高度调节螺杆", (*center, 0.046), 0.009, 0.072, steel, vertices=36),
                rounded_box("洗碗机_脚座承重立柱", (*center, 0.118), (0.048, 0.046, 0.113), 0.005, chassis),
            ])
    return [*lifted, *lower, *door, *base]


def shorten_cabinet_board(part, cut_x):
    transform = part.matrix_world.inverted()
    mesh = bmesh.new()
    try:
        mesh.from_mesh(part.data)
        cut = bmesh.ops.bisect_plane(mesh, geom=[*mesh.verts, *mesh.edges, *mesh.faces],
                                    plane_co=transform @ Vector((cut_x, 0, 0)),
                                    plane_no=part.matrix_world.to_3x3().transposed() @ Vector((1, 0, 0)),
                                    dist=1e-6, clear_outer=True)
        rim = [element for element in cut["geom_cut"] if isinstance(element, bmesh.types.BMEdge) and element.is_boundary]
        bmesh.ops.holes_fill(mesh, edges=rim, sides=0)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(part.data)
        part.data.update()
    finally:
        mesh.free()


def install(scene):
    sink_x = scene.objects["A123"].location.x
    doors = [part for part in scene.objects if part.name.startswith("北柜_门板") and part.location.x > sink_x + 0.4]
    if len(doors) != 1:
        raise RuntimeError("水槽右侧未找到唯一安装柜舱")
    door = doors[0]
    floor = scene.objects[OPEN_AREA_FLOOR]
    support_z = max((floor.matrix_world @ Vector(point)).z for point in floor.bound_box)
    front = door.location.y - door.dimensions.y / 2
    center = Vector((door.location.x, front + 0.303, support_z))
    left_divider = max((part for part in scene.objects if part.name.startswith("北柜_隔板")
                        and part.location.x < center.x), key=lambda part: part.location.x)
    for name in ("北柜_底板", "北柜_背板", "北柜_退缩踢脚"):
        shorten_cabinet_board(scene.objects[name], left_divider.location.x)
    for part in [door, *(part for part in scene.objects if part.name.startswith("北柜_拉手") and abs(part.location.x - center.x) < 0.01)]:
        bpy.data.objects.remove(part, do_unlink=True)
    place_new(ASSET, dishwasher(), center)


def show_open(scene):
    with bpy.data.libraries.load(str(LIBRARY / ASSET / f"{ASSET}.blend")) as (_, target):
        target.collections = [ASSET]
    collection = target.collections[0]
    parts = {part.name.rsplit(".", 1)[0]: part for part in collection.objects}
    parts["洗碗机_门下翻轴"].rotation_euler.x = pi / 2
    parts["洗碗机_下篮伸出轴"].location.y -= LOWER_RACK_TRAVEL
    scene.objects[ASSET].instance_collection = collection
    bpy.context.view_layer.update()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STAGES / "fixture-details/house.blend")
    parser.add_argument("--output", type=Path, default=STAGES / "dishwasher/house.blend")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--render-only", action="store_true", help="重开输出工程并渲染闭门与开门视图")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        parser.error("输出工程需与输入工程分开")
    if args.render_only and args.build_only:
        parser.error("--render-only 与 --build-only 互斥")
    bpy.ops.wm.open_mainfile(filepath=str(output if args.render_only else source))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    if not args.render_only:
        install(scene)
        for name, view in VIEWS.items():
            scene_camera(scene, name, *view)
        scene.camera = scene.objects["kitchen-dishwasher"]
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=True, compress=True)
    if args.build_only:
        return
    for name in VIEWS:
        if name == "kitchen-dishwasher-open":
            show_open(scene)
        scene.camera = scene.objects[name]
        scene.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
