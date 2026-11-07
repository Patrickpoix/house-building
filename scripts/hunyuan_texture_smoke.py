"""验证 Hunyuan 单张颜色纹理流程；输出不等同于完整 PBR 资产。"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".tools" / "Hunyuan3D-2"
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE / "hy3dgen" / "texgen" / "custom_rasterizer"))

import trimesh
from hy3dgen.texgen.pipelines import Hunyuan3DPaintPipeline, Hunyuan3DTexGenConfig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    model_root = ROOT / ".tools" / "models" / "tencent" / "Hunyuan3D-2"
    config = Hunyuan3DTexGenConfig(
        str(model_root / "hunyuan3d-delight-v2-0"),
        str(model_root / "hunyuan3d-paint-v2-0-turbo"),
        "hunyuan3d-paint-v2-0-turbo",
    )
    # 两个模型先装入 CPU，避免加载阶段同时占满 8 GB 显存，再按官方接口卸载。
    config.device = "cpu"
    pipeline = Hunyuan3DPaintPipeline(config)
    pipeline.enable_model_cpu_offload(device="cuda")
    mesh = trimesh.load(str(args.mesh), force="mesh")
    textured = pipeline(mesh, str(args.image))
    if textured is None or len(textured.faces) == 0:
        raise RuntimeError("纹理管线未返回有效网格")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    textured.export(str(args.output))
    print(f"纹理试验写入 {args.output}")


if __name__ == "__main__":
    main()
