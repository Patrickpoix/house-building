#!/usr/bin/env bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_CUDA="${HOUSE_CUDA_BUILD:-$HOME/.cache/house-building-mamba/cuda-build}"
TASK_PYTHON="$TASK_ROOT/.tools/hunyuan-linux-uv/bin/python"
TASK_NVIDIA="$TASK_ROOT/.tools/hunyuan-linux-uv/lib/python3.11/site-packages/nvidia"
TASK_MAMBA="$TASK_ROOT/.tools/bin/micromamba"
TASK_SOURCE="$TASK_ROOT/.tools/Hunyuan3D-2/hy3dgen/texgen"
TASK_INCLUDES="$TASK_NVIDIA/cusparse/include:$TASK_NVIDIA/cublas/include:$TASK_NVIDIA/cusolver/include:$TASK_NVIDIA/curand/include:$TASK_NVIDIA/cufft/include"

cd "$TASK_SOURCE/custom_rasterizer"
"$TASK_MAMBA" run -p "$TASK_CUDA" env \
    CUDA_HOME="$TASK_CUDA" \
    CC="$TASK_CUDA/bin/x86_64-conda-linux-gnu-gcc" \
    CXX="$TASK_CUDA/bin/x86_64-conda-linux-gnu-g++" \
    CUDAHOSTCXX="$TASK_CUDA/bin/x86_64-conda-linux-gnu-g++" \
    CPLUS_INCLUDE_PATH="$TASK_INCLUDES" \
    TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=2 \
    "$TASK_PYTHON" setup.py build_ext --inplace

cd "$TASK_SOURCE/differentiable_renderer"
"$TASK_MAMBA" run -p "$TASK_CUDA" env \
    CC="$TASK_CUDA/bin/x86_64-conda-linux-gnu-gcc" \
    CXX="$TASK_CUDA/bin/x86_64-conda-linux-gnu-g++" \
    "$TASK_PYTHON" setup.py build_ext --inplace
