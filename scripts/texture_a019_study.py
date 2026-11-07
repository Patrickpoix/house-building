"""为 A019 研究稿制作可重跑的程序化试验贴图；不代表成品验收。"""

from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "stages" / "S002" / "A019-study"
RESOLUTION = 2048
MATERIALS = {
    "study_ivory_enamel": ((0.86, 0.84, 0.78), 0.0, 0.32, 0.015, 1001),
    "study_brushed_steel": ((0.73, 0.74, 0.73), 1.0, 0.28, 0.012, 1002),
    "study_graphite_polymer": ((0.23, 0.24, 0.24), 0.0, 0.42, 0.025, 1003),
    "study_rubber": ((0.17, 0.18, 0.17), 0.0, 0.66, 0.035, 1004),
}


def save_image(name, data, noncolor):
    target = OUTPUT / "textures" / f"{name}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = bpy.data.images.new(name, width=RESOLUTION, height=RESOLUTION, alpha=True)
    image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    rgba = np.ones((RESOLUTION, RESOLUTION, 4), dtype=np.float32)
    if data.ndim == 2:
        rgba[:, :, :3] = data[:, :, None]
    else:
        rgba[:, :, :3] = data
    image.pixels.foreach_set(rgba.reshape(-1))
    image.filepath_raw = str(target)
    image.file_format = "PNG"
    image.save()
    image.filepath = f"//textures/{name}.png"
    return image


def create_maps(name, base, metallic, roughness, variation, seed):
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((RESOLUTION, RESOLUTION), dtype=np.float32)
    if metallic:
        streaks = rng.standard_normal((RESOLUTION, 1), dtype=np.float32)
        surface = np.clip(streaks * 0.60 + noise * 0.16, -2.5, 2.5)
    else:
        surface = np.clip((noise + np.roll(noise, 1, axis=0) + np.roll(noise, 1, axis=1)) / 3, -2.0, 2.0)
    color = np.clip(np.asarray(base, dtype=np.float32)[None, None, :] * (1 + surface[:, :, None] * variation * 0.22), 0, 1)
    rough_map = np.clip(roughness + surface * variation, 0.03, 0.98)
    metal_map = np.full((RESOLUTION, RESOLUTION), metallic, dtype=np.float32)
    dy, dx = np.gradient(surface)
    normal = np.empty((RESOLUTION, RESOLUTION, 3), dtype=np.float32)
    normal[:, :, 0] = np.clip(0.5 - dx * variation * 0.20, 0, 1)
    normal[:, :, 1] = np.clip(0.5 - dy * variation * 0.20, 0, 1)
    normal[:, :, 2] = 1.0
    return {
        "BaseColor": save_image(f"{name}_BaseColor", color, False),
        "Roughness": save_image(f"{name}_Roughness", rough_map, True),
        "Metallic": save_image(f"{name}_Metallic", metal_map, True),
        "Normal": save_image(f"{name}_Normal", normal, True),
    }


def connect_maps(mat, maps):
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    for key, socket in (("BaseColor", "Base Color"), ("Roughness", "Roughness"), ("Metallic", "Metallic")):
        node = tree.nodes.new("ShaderNodeTexImage")
        node.name = f"PBR_{key}"
        node.image = maps[key]
        tree.links.new(node.outputs["Color"], shader.inputs[socket])
    node = tree.nodes.new("ShaderNodeTexImage")
    node.name = "PBR_Normal"
    node.image = maps["Normal"]
    normal = tree.nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.15
    tree.links.new(node.outputs["Color"], normal.inputs["Color"])
    tree.links.new(normal.outputs["Normal"], shader.inputs["Normal"])


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / "study.blend"))
    bpy.context.preferences.filepaths.save_version = 0
    for name, params in MATERIALS.items():
        connect_maps(bpy.data.materials[name], create_maps(name, *params))
    bpy.context.scene.render.filepath = str(OUTPUT / "textured-preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "study-textured.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
