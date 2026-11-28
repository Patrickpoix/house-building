"""检查门扇、把手与建筑及指定链接资产的网格表面相交。"""

import argparse
import math
import sys

import bpy
from mathutils.bvhtree import BVHTree


def tree(evaluated, world):
    mesh = evaluated.to_mesh()
    try:
        vertices = [world @ vertex.co for vertex in mesh.vertices]
        polygons = [tuple(p.vertices) for p in mesh.polygons]
        return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=0.000001)
    finally:
        evaluated.to_mesh_clear()


parser = argparse.ArgumentParser()
parser.add_argument("--assets", nargs="+", default=[], help="层级直接位于场景中的资产实例名称")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
scene = bpy.context.scene
for name in args.assets:
    if name not in scene.objects or scene.objects[name].instance_type != "COLLECTION":
        parser.error(f"找不到集合实例：{name}")
depsgraph = bpy.context.evaluated_depsgraph_get()
obstacles = [obj for obj in scene.objects if obj.type == "MESH" and
             (obj.name.startswith("wall_") or (obj.name.startswith("opening_") and ("_jamb" in obj.name or "_rail" in obj.name)))]
static = [(obj.name, tree(obj.evaluated_get(depsgraph), obj.matrix_world)) for obj in obstacles]
found = set()
for item in depsgraph.object_instances:
    if item.is_instance and item.object.type == "MESH" and item.parent and item.parent.original.name in args.assets:
        name = item.parent.original.name
        found.add(name)
        static.append((f"{name}/{item.object.name}", tree(item.object, item.matrix_world)))
if missing := set(args.assets) - found:
    parser.error(f"资产无评估网格：{', '.join(sorted(missing))}")
hinges = [obj for obj in scene.objects if obj.name.startswith("opening_") and obj.name.endswith("_hinge")]
collisions = []
for hinge in hinges:
    opened = hinge.rotation_euler.z
    for degrees in range(0, 91, 5):
        hinge.rotation_euler.z = math.copysign(math.radians(degrees), opened)
        bpy.context.view_layer.update()
        for obj in hinge.children:
            moving = tree(obj.evaluated_get(depsgraph), obj.matrix_world)
            for name, collider in static:
                if moving.overlap(collider):
                    collisions.append((hinge.name, degrees, obj.name, name))
    hinge.rotation_euler.z = opened
if collisions:
    for item in collisions[:30]:
        print("门扇与障碍相交：", *item)
    raise AssertionError(f"发现 {len(collisions)} 个离散角度的相交记录")
coverage = f"墙体、框体及 {len(found)} 个指定资产" if found else "墙体与框体"
print(f"{len(hinges)} 樘门每 5° 检查一次，门扇及把手与{coverage}的表面未检出相交。")
