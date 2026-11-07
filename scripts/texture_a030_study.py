"""为 A030 研究稿生成织物贴图；不代表接缝和 PBR 已通过验收。"""

import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texture_a019_study as textures

OUTPUT = Path(__file__).resolve().parent.parent / "stages" / "S002" / "A030-study"
N = textures.RESOLUTION
MATERIALS = {
    "study_flax_canvas": ((0.76, 0.68, 0.56), 0.84, 240, 260, 2001),
    "study_olive_webbing": ((0.30, 0.33, 0.19), 0.81, 170, 310, 2002),
    "study_natural_thread": ((0.83, 0.76, 0.63), 0.88, 120, 120, 2003),
}


def create_weave(name, color, roughness, warp_frequency, weft_frequency, seed):
    rng = np.random.default_rng(seed)
    x = np.arange(N, dtype=np.float32)[None, :] / N
    y = np.arange(N, dtype=np.float32)[:, None] / N
    warp = np.sin(2 * np.pi * warp_frequency * x)
    weft = np.sin(2 * np.pi * weft_frequency * y)
    noise = rng.standard_normal((N, N), dtype=np.float32)
    height = 0.5 * warp + 0.5 * weft + 0.20 * warp * weft + 0.06 * noise
    pigment = np.asarray(color, dtype=np.float32)[None, None, :] * (1 + height[:, :, None] * 0.018)
    rough = np.clip(roughness + height * 0.025, 0.05, 0.98)
    dy, dx = np.gradient(height)
    normal = np.empty((N, N, 3), dtype=np.float32)
    normal[:, :, 0] = np.clip(0.5 - dx * 0.045, 0, 1)
    normal[:, :, 1] = np.clip(0.5 - dy * 0.045, 0, 1)
    normal[:, :, 2] = 1.0
    return {
        "BaseColor": textures.save_image(f"{name}_BaseColor", np.clip(pigment, 0, 1), False),
        "Roughness": textures.save_image(f"{name}_Roughness", rough, True),
        "Metallic": textures.save_image(f"{name}_Metallic", np.zeros((N, N), dtype=np.float32), True),
        "Normal": textures.save_image(f"{name}_Normal", normal, True),
    }


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT / "study.blend"))
    bpy.context.preferences.filepaths.save_version = 0
    textures.OUTPUT = OUTPUT
    for name, params in MATERIALS.items():
        textures.connect_maps(bpy.data.materials[name], create_weave(name, *params))
    bpy.context.scene.render.filepath = str(OUTPUT / "textured-preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "study-textured.blend"))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
