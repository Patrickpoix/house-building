"""试验按原贴图颜色区分布料并换用实拍织物；保留原模型。"""
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tripo/outputs/reading-chair/tripo-original.glb"
TEXTURES = ROOT / "assets/materials/terlenka"
OUT = ROOT / "tripo/outputs/reading-chair/fabric-study"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mat = obj.active_material
nodes, links = mat.node_tree.nodes, mat.node_tree.links
original = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
base = original.inputs["Base Color"].links[0].from_node

# 原图木材比米色布料更偏红；这是试验掩码，边缘须实图检查。
separate = nodes.new("ShaderNodeSeparateColor")
links.new(base.outputs["Color"], separate.inputs["Color"])
diff = nodes.new("ShaderNodeMath")
diff.operation = "SUBTRACT"
links.new(separate.outputs["Red"], diff.inputs[0])
links.new(separate.outputs["Blue"], diff.inputs[1])
mask = nodes.new("ShaderNodeMapRange")
mask.clamp = True
mask.inputs["From Min"].default_value = 0.19
mask.inputs["From Max"].default_value = 0.30
links.new(diff.outputs[0], mask.inputs["Value"])

coord = nodes.new("ShaderNodeTexCoord")
scale = nodes.new("ShaderNodeVectorMath")
scale.operation = "SCALE"
scale.inputs[3].default_value = 1 / 0.3
links.new(coord.outputs["Object"], scale.inputs[0])
fabric = nodes.new("ShaderNodeBsdfPrincipled")
fabric.inputs["Metallic"].default_value = 0
fabric.inputs["Sheen Weight"].default_value = 0.22
for suffix, channel, color_space in (("diff", "Base Color", "sRGB"),
                                    ("rough", "Roughness", "Non-Color")):
    image = bpy.data.images.load(str(TEXTURES / f"terlenka_{suffix}_2k.jpg"), check_existing=True)
    image.colorspace_settings.name = color_space
    image.pack()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.projection = "BOX"
    tex.projection_blend = 0.25
    links.new(scale.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], fabric.inputs[channel])
normal_image = bpy.data.images.load(str(TEXTURES / "terlenka_nor_gl_2k.jpg"), check_existing=True)
normal_image.colorspace_settings.name = "Non-Color"
normal_image.pack()
normal_tex = nodes.new("ShaderNodeTexImage")
normal_tex.image = normal_image
normal_tex.projection = "BOX"
normal_tex.projection_blend = 0.25
links.new(scale.outputs["Vector"], normal_tex.inputs["Vector"])
normal_map = nodes.new("ShaderNodeNormalMap")
normal_map.inputs["Strength"].default_value = 0.45
links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
links.new(normal_map.outputs["Normal"], fabric.inputs["Normal"])
mix = nodes.new("ShaderNodeMixShader")
links.new(mask.outputs["Result"], mix.inputs[0])
links.new(fabric.outputs["BSDF"], mix.inputs[1])
links.new(original.outputs["BSDF"], mix.inputs[2])
links.new(mix.outputs[0], output.inputs["Surface"])

points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center, extent = (low + high) / 2, max(high - low)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.world = bpy.data.worlds.new("inspection world")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
bpy.ops.object.light_add(type="AREA")
light = bpy.context.object
light.data.energy = 400 * extent * extent
light.data.size = 4 * extent
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
scene.camera = camera
for name, direction, view_scale in (("front", (0, -1, 0.08), 1.25),
                                    ("close", (0.35, -1, 0.2), 0.65)):
    direction = Vector(direction).normalized()
    camera.location = center + direction * extent * 3
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = extent * view_scale
    light.location = center + direction * extent * 2 + Vector((0, 0, extent * 2))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "chair-fabric-study.blend"))
print("布料掩码试验已保存；边界、纹理和结构待验收。")
