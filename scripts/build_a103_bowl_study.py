"""生成 A103 陶碗结构和 PBR 贴图研究稿；尚非验收资产。"""

import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S002" / "A103-study"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import texture_a019_study as textures

PROFILE = [(0.035, 0.000), (0.050, 0.000), (0.055, 0.003), (0.058, 0.009),
           (0.067, 0.012), (0.080, 0.019), (0.092, 0.030), (0.102, 0.046),
           (0.110, 0.065), (0.114, 0.082), (0.114, 0.087), (0.112, 0.090),
           (0.108, 0.090), (0.106, 0.086), (0.104, 0.078), (0.098, 0.063),
           (0.090, 0.049), (0.079, 0.037), (0.065, 0.028), (0.049, 0.023),
           (0.030, 0.021)]


def make_maps(name, color, roughness, seed):
    n = textures.RESOLUTION
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((n, n), dtype=np.float32)
    speck = (rng.random((n, n), dtype=np.float32) < 0.00025).astype(np.float32)
    for axis in (0, 1):
        for shift in (-2, -1, 1, 2):
            speck = np.maximum(speck, np.roll(speck, shift, axis=axis) * 0.8)
    bands = np.sin(np.arange(n, dtype=np.float32)[:, None] * 0.028) * 0.012
    surface = noise * 0.012 + bands
    pigment = np.asarray(color, dtype=np.float32)[None, None, :] * (1 + surface[:, :, None])
    pigment *= 1 - speck[:, :, None] * 0.35
    rough = np.clip(roughness + surface * 0.45 + speck * 0.05, 0.05, 0.95)
    dy, dx = np.gradient(surface)
    normal = np.empty((n, n, 3), dtype=np.float32)
    normal[:, :, 0] = np.clip(0.5 - dx * 0.08, 0, 1)
    normal[:, :, 1] = np.clip(0.5 - dy * 0.08, 0, 1)
    normal[:, :, 2] = 1.0
    return {"BaseColor": textures.save_image(name + "_BaseColor", np.clip(pigment, 0, 1), False),
            "Roughness": textures.save_image(name + "_Roughness", rough, True),
            "Metallic": textures.save_image(name + "_Metallic", np.zeros((n, n), dtype=np.float32), True),
            "Normal": textures.save_image(name + "_Normal", normal, True)}


def material(name, color, roughness, seed):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    textures.connect_maps(mat, make_maps(name, color, roughness, seed))
    return mat


def bowl(glaze, clay):
    sides = 128
    vertices = [(0, 0, 0.000)]
    for radius, z in PROFILE:
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            irregularity = 1 + 0.004 * math.sin(3 * angle + 0.6) + 0.002 * math.sin(7 * angle)
            vertices.append((radius * math.cos(angle) * irregularity, radius * math.sin(angle) * irregularity, z))
    top_center = len(vertices)
    vertices.append((0, 0, 0.021))
    faces = [(0, 1 + (i + 1) % sides, 1 + i) for i in range(sides)]
    for row in range(len(PROFILE) - 1):
        for i in range(sides):
            a = 1 + row * sides + i
            b = 1 + row * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    last = 1 + (len(PROFILE) - 1) * sides
    faces.extend((last + i, last + (i + 1) % sides, top_center) for i in range(sides))
    mesh = bpy.data.meshes.new("A103_bowl_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="ceramic_uv")
    lengths = [0.0]
    for current, previous in zip(PROFILE[1:], PROFILE):
        lengths.append(lengths[-1] + math.dist(current, previous))
    for face in mesh.polygons:
        coords = []
        quad_row = (face.index - sides) // sides
        # 较陡的内壁使用弧长坐标，内底与胎土底使用平面坐标。
        is_planar = face.center.z < 0.006 or top_center in face.vertices or quad_row >= 17
        for loop_index in face.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            v = mesh.vertices[vertex_index].co
            if is_planar:
                coords.append((0.5 + v.x / 0.25, 0.5 + v.y / 0.25))
            else:
                row = (vertex_index - 1) // sides
                coords.append(((math.atan2(v.y, v.x) / (2 * math.pi)) % 1, lengths[row] / 0.23))
        us = [p[0] for p in coords]
        if not is_planar and max(us) - min(us) > 0.5:
            coords = [(u + 1 if u < 0.5 else u, v) for u, v in coords]
        if not is_planar:
            coords = [(u * 3, v) for u, v in coords]
        for loop_index, coord in zip(face.loop_indices, coords):
            uv.data[loop_index].uv = coord
        face.use_smooth = True
        face.material_index = 1 if face.center.z < 0.006 else 0
    obj = bpy.data.objects.new("A103_bowl", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(glaze)
    obj.data.materials.append(clay)
    sub = obj.modifiers.new("ceramic_smoothing", "SUBSURF")
    sub.levels = 2
    return obj


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    textures.OUTPUT = OUTPUT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    glaze = material("A103_glaze", (0.78, 0.72, 0.61), 0.29, 3101)
    clay = material("A103_foot_clay", (0.60, 0.49, 0.35), 0.64, 3102)
    bowl(glaze, clay)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "preview_floor_not_asset"
    floor_mat = bpy.data.materials.new("preview_floor")
    floor_mat.diffuse_color = (0.60, 0.62, 0.59, 1)
    floor.data.materials.append(floor_mat)
    for location, energy, size in [((0.35, -0.42, 0.65), 18, 0.55), ((-0.4, 0.05, 0.4), 8, 0.4)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.size = size
        light.rotation_euler = (Vector((0, 0, 0.04)) - light.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(location=(0.36, -0.50, 0.36))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 0.045)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.34
    scene.camera = camera
    scene.world = bpy.data.worlds.new("preview_world")
    scene.world.color = (0.4, 0.4, 0.4)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT / "preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "study.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
