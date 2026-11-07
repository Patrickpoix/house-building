"""检查本机纹理依赖扩展可导入，并让 CUDA 光栅器实际绘制一个三角形。"""

import sys
from pathlib import Path

import torch

root = Path(__file__).resolve().parent.parent / ".tools" / "Hunyuan3D-2" / "hy3dgen" / "texgen"
sys.path.insert(0, str(root / "custom_rasterizer"))
sys.path.insert(0, str(root / "differentiable_renderer"))

import custom_rasterizer
import mesh_processor

vertices = torch.tensor([[[-0.8, -0.8, 0.0, 1.0], [0.8, -0.8, 0.0, 1.0], [0.0, 0.8, 0.0, 1.0]]], device="cuda")
triangles = torch.tensor([[0, 1, 2]], dtype=torch.int32, device="cuda")
indices, weights = custom_rasterizer.rasterize(vertices, triangles, (32, 32), torch.empty(0, device="cuda"))
torch.cuda.synchronize()
covered = int((indices > 0).sum().item())
if covered <= 0 or not hasattr(mesh_processor, "meshVerticeInpaint"):
    raise RuntimeError("纹理扩展未通过最小检查")
print(f"CUDA 光栅器覆盖像素：{covered}；mesh_processor 导入成功")
