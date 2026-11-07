"""在离散角度检查门扇、把手与墙体和门窗框的网格表面相交。"""

import math
import bpy
from mathutils.bvhtree import BVHTree


def tree(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        polygons = [tuple(p.vertices) for p in mesh.polygons]
        return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=0.000001)
    finally:
        evaluated.to_mesh_clear()


scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()
obstacles = [obj for obj in scene.objects if obj.type == "MESH" and
             (obj.name.startswith("wall_") or (obj.name.startswith("opening_") and ("_jamb" in obj.name or "_rail" in obj.name)))]
static = [(obj.name, tree(obj, depsgraph)) for obj in obstacles]
hinges = [obj for obj in scene.objects if obj.name.startswith("opening_") and obj.name.endswith("_hinge")]
collisions = []
for hinge in hinges:
    opened = hinge.rotation_euler.z
    for degrees in range(0, 91, 5):
        hinge.rotation_euler.z = math.copysign(math.radians(degrees), opened)
        bpy.context.view_layer.update()
        for obj in hinge.children:
            moving = tree(obj, depsgraph)
            for name, collider in static:
                if moving.overlap(collider):
                    collisions.append((hinge.name, degrees, obj.name, name))
    hinge.rotation_euler.z = opened
if collisions:
    for item in collisions[:30]:
        print("门扇与障碍相交：", *item)
    raise AssertionError(f"发现 {len(collisions)} 个离散角度的相交记录")
print(f"{len(hinges)} 樘门每 5° 检查一次，门扇及把手与墙体、框体表面未检出相交；未覆盖家具和连续角度。")
