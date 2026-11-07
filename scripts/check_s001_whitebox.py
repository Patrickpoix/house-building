"""核对 S001 实际工程的外轮廓及设计开口，不能代替家具和门扇通行检查。"""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_s001_whitebox import HEIGHT, WALLS


def main():
    scene = bpy.context.scene
    slab = bpy.data.objects["building_slab_10x10m"]
    for actual, expected in zip(slab.dimensions, (10, 10, 0.2)):
        if abs(actual - expected) > 0.001:
            raise AssertionError(f"建筑底板尺寸错误：{tuple(slab.dimensions)}")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    opening_count = 0
    for name, axis, fixed, start, end, thickness, openings in WALLS:
        for a, b, bottom, top in openings:
            along = (a + b) / 2
            z = (bottom + top) / 2
            if axis == "x":
                origin = Vector((along, fixed - thickness * 2, z))
                direction = Vector((0, 1, 0))
            else:
                origin = Vector((fixed - thickness * 2, along, z))
                direction = Vector((1, 0, 0))
            hit, _, _, _, obj, _ = scene.ray_cast(depsgraph, origin, direction, distance=thickness * 4)
            if hit:
                raise AssertionError(f"{name} 开口被 {obj.name} 阻挡")
            if bottom == 0 and (b - a < 0.9 - 1e-6 or top < 2.15 - 1e-6):
                raise AssertionError(f"{name} 门洞过小")
            opening_count += 1
        parts = [obj for obj in scene.objects if obj.name.startswith(f"wall_{name}")]
        if not parts:
            raise AssertionError(f"缺少墙体 {name}")
        if abs(max(obj.location.z + obj.dimensions.z / 2 for obj in parts) - HEIGHT) > 0.001:
            raise AssertionError(f"墙体 {name} 高度错误")
        points = sorted({start, end, *(v for a, b, _, _ in openings for v in (a, b))})
        spans = [(a, b) for a, b in zip(points, points[1:])
                 if not any(x <= a and b <= y for x, y, _, _ in openings)]
        if not spans:
            raise AssertionError(f"无法找到墙体 {name} 的实体区段")
        left, right = max(spans, key=lambda span: span[1] - span[0])
        along = (left + right) / 2
        if axis == "x":
            origin, direction = Vector((along, fixed - thickness * 2, 1)), Vector((0, 1, 0))
        else:
            origin, direction = Vector((fixed - thickness * 2, along, 1)), Vector((1, 0, 0))
        hit, _, _, _, obj, _ = scene.ray_cast(depsgraph, origin, direction, distance=thickness * 4)
        if not hit or not obj.name.startswith(f"wall_{name}"):
            raise AssertionError(f"墙体 {name} 实体区段未命中")
    print(f"白模检查通过：外轮廓 10×10 m；墙高 {HEIGHT} m；{len(WALLS)} 面墙的实体区段及 {opening_count} 个开口中心。")


if __name__ == "__main__":
    main()
