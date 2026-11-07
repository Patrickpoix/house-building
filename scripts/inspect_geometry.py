"""记录 GLB 网格的基本拓扑指标；不代替模型外观和 PBR 人工验收。"""

import argparse
import json
from pathlib import Path

import trimesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    mesh = trimesh.load(str(args.mesh), force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise RuntimeError("未找到有效三角网格")
    result = {
        "source": args.mesh.name,
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "watertight": bool(mesh.is_watertight),
        "connected_components": int(mesh.body_count),
        "visual_kind": mesh.visual.kind,
        "bounds": mesh.bounds.tolist(),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
