"""按生成几何参照重建 A030 帆布袋的结构研究稿；尚未作为最终资产验收。"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S002" / "A030-study"
GUIDE = ROOT / "stages" / "S002" / "experiments" / "A030-hunyuan-textured.glb"
WIDTH, DEPTH, HEIGHT = 0.36, 0.12, 0.40


def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


def mesh_grid(name, u_count, v_count, fn, mat, thickness):
    vertices = [fn(i / u_count, j / v_count) for j in range(v_count + 1) for i in range(u_count + 1)]
    faces = []
    for j in range(v_count):
        for i in range(u_count):
            a = j * (u_count + 1) + i
            faces.append((a, a + 1, a + u_count + 2, a + u_count + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="fabric_uv")
    for loop in mesh.loops:
        row, column = divmod(loop.vertex_index, u_count + 1)
        uv.data[loop.index].uv = (column / u_count, row / v_count)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    solidify = obj.modifiers.new("fabric_thickness", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = 0
    subdiv = obj.modifiers.new("fabric_smoothing", "SUBSURF")
    subdiv.levels = 1
    return obj


def seam(name, points, mat, radius=0.00015):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    for start, end in zip(points, points[1:]):
        start, end = Vector(start), Vector(end)
        length = (end - start).length
        count = max(1, math.ceil(length / 0.0022))
        for i in range(count):
            t0 = i / count
            t1 = min(1.0, t0 + 0.0014 / length)
            spline = curve.splines.new("POLY")
            spline.points.add(1)
            spline.points[0].co = (*start.lerp(end, t0), 1)
            spline.points[1].co = (*start.lerp(end, t1), 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    if not GUIDE.is_file():
        raise FileNotFoundError(f"缺少几何参照 {GUIDE}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    bpy.ops.import_scene.gltf(filepath=str(GUIDE))
    guide = next(obj for obj in scene.objects if obj.type == "MESH")
    guide.name = "guide_generated_geometry_not_final"
    guide.dimensions = (WIDTH, DEPTH, 0.62)
    bpy.context.view_layer.update()
    points = [guide.matrix_world @ Vector(point) for point in guide.bound_box]
    guide.location.x -= (min(p.x for p in points) + max(p.x for p in points)) / 2
    guide.location.y -= (min(p.y for p in points) + max(p.y for p in points)) / 2
    guide.location.z -= min(p.z for p in points)
    guide.hide_render = True
    guide.hide_set(True)

    canvas = material("study_flax_canvas", (0.53, 0.44, 0.32), 0.84)
    handle = material("study_olive_webbing", (0.12, 0.15, 0.065), 0.81)
    thread = material("study_natural_thread", (0.64, 0.56, 0.42), 0.88)
    body = guide.copy()
    body.data = guide.data.copy()
    scene.collection.objects.link(body)
    body.name = "A030_generated_body"
    body.hide_set(False)
    body.hide_render = False
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    # glTF 会按 UV 接缝拆分顶点；合并共点并保留各面的 UV 环。
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    cut_height = HEIGHT - 0.06
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                           dist=0.00001, plane_co=(0, 0, cut_height), plane_no=(0, 0, 1),
                           clear_outer=True, clear_inner=False)
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    if not boundary or any(abs(vertex.co.z - cut_height) > 0.00003 for edge in boundary for vertex in edge.verts):
        raise RuntimeError("袋身存在不在切面上的边界，不能自动连接袋口")
    remaining = set(boundary)
    groups = 0
    while remaining:
        groups += 1
        stack = [remaining.pop()]
        while stack:
            edge = stack.pop()
            for vertex in edge.verts:
                for neighbor in vertex.link_edges:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        stack.append(neighbor)
    if groups != 2:
        raise RuntimeError(f"袋口边界应为两圈，实际为 {groups} 圈")
    uv = bm.loops.layers.uv.active
    if uv is None:
        raise RuntimeError("袋身缺少 UV")
    # 原网格上缘包含融合的提带残留，沿两圈边界重建袋口布边。
    extruded = bmesh.ops.extrude_edge_only(bm, edges=boundary)
    new_vertices = [element for element in extruded["geom"] if isinstance(element, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_vertices, vec=Vector((0, 0, HEIGHT - cut_height)))
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    bridge = bmesh.ops.bridge_loops(bm, edges=boundary)
    if not bridge["faces"]:
        raise RuntimeError("袋口连接没有生成面")
    # 袋身与新袋口使用同一套连续坐标，接缝放在背面中央。
    for face in bm.faces:
        us = [(math.atan2(loop.vert.co.x / WIDTH, -loop.vert.co.y / DEPTH) / (2 * math.pi) + 0.5) % 1.0
              for loop in face.loops]
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.5 else u for u in us]
        for loop, u in zip(face.loops, us):
            loop[uv].uv = (u, loop.vert.co.z / HEIGHT)
    if any(edge.is_boundary for edge in bm.edges):
        raise RuntimeError("袋口连接后仍有开放边界")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    body.data.materials.clear()
    body.data.materials.append(canvas)
    for y in (-0.064, 0.064):
        def strap(u, v, y_pos=y):
            angle = math.pi * u
            x = -0.095 * math.cos(angle)
            z = 0.36 + 0.235 * math.sin(angle)
            dx = 0.095 * math.pi * math.sin(angle)
            dz = 0.235 * math.pi * math.cos(angle)
            length = math.hypot(dx, dz)
            offset = (v - 0.5) * 0.028
            return (x - dz / length * offset, y_pos, z + dx / length * offset)
        mesh_grid("A030_handle", 48, 3, strap, handle, 0.0025)
    for side in (-1, 1):
        for anchor_x in (-0.095, 0.095):
            mesh_grid("A030_handle_tab", 4, 6,
                      lambda u, v, s=side, x=anchor_x: (x + (u - 0.5) * 0.029,
                          s * (DEPTH / 2 + 0.003), 0.348 + 0.05 * v), handle, 0.0015)
    for side in (-1, 1):
        for x in (-0.095, 0.095):
            y = side * (DEPTH / 2 + 0.0062)
            seam("A030_handle_stitch", [(x - 0.010, y, 0.356), (x - 0.010, y, 0.390),
                                         (x + 0.010, y, 0.390), (x + 0.010, y, 0.356),
                                         (x - 0.010, y, 0.356)], thread)
            for direction in (-1, 1):
                seam("A030_handle_stitch", [(x - 0.010, y, 0.357 if direction > 0 else 0.389),
                                             (x + 0.010, y, 0.389 if direction > 0 else 0.357)], thread)

    bpy.ops.object.camera_add(location=(1.0, -1.6, 1.05))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.87
    aim(camera, (0, 0, 0.30))
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(0.5, -0.8, 1.4))
    light = bpy.context.object
    light.data.energy = 45
    light.data.size = 1.2
    aim(light, (0, 0, 0.3))
    scene.world = bpy.data.worlds.new("study_world")
    scene.world.color = (0.5, 0.5, 0.5)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT / "preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "study.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
