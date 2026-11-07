"""运行单图生成几何的环境试验；结果不是最终资产或 PBR 贴图。"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".tools" / "Hunyuan3D-2"))

import torch
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA 不可用")
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        "tencent/Hunyuan3D-2mini", subfolder="hunyuan3d-dit-v2-mini", device="cuda"
    )
    mesh = pipeline(
        image=str(args.image), num_inference_steps=30, octree_resolution=256,
        num_chunks=10000, generator=torch.manual_seed(12345), output_type="trimesh"
    )[0]
    if mesh is None or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise RuntimeError("未生成有效网格")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(args.output))
    print(f"试验网格：{len(mesh.vertices)} 顶点，{len(mesh.faces)} 面；{args.output}")


if __name__ == "__main__":
    main()
