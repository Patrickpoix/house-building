#!/usr/bin/env bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ $# -lt 1 || ( "$1" != "shape" && "$1" != "texture" ) ]]; then
    echo "用法: bash scripts/run_hunyuan.sh {shape|texture} 参数..." >&2
    exit 2
fi
TASK_MODE="$1"
shift

# pymeshlab 的插件在导入时加载 OpenGL，必须在 Python 启动前设置搜索路径。
export LD_LIBRARY_PATH="$TASK_ROOT/.tools/opengl-local/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME="${HF_HOME:-$TASK_ROOT/.tools/huggingface}"
export HY3DGEN_MODELS="${HY3DGEN_MODELS:-$TASK_ROOT/.tools/models}"
if [[ "$TASK_MODE" == "shape" ]]; then
    TASK_SCRIPT="$TASK_ROOT/scripts/hunyuan_smoke.py"
else
    TASK_SCRIPT="$TASK_ROOT/scripts/hunyuan_texture_smoke.py"
fi
exec "$TASK_ROOT/.tools/hunyuan-linux-uv/bin/python" "$TASK_SCRIPT" "$@"
