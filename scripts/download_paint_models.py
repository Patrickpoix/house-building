"""从官方仓库下载 Hunyuan 纹理模型，续传并核验大文件。

参数：两份官方 tree API JSON、输出根目录及仓库提交号。
上游自定义 UNet 硬编码读取 .bin，因此保留所有官方文件。
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import quote


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def git_blob_digest(path):
    hasher = hashlib.sha1(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paint_tree", type=Path)
    parser.add_argument("delight_tree", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("revision", help="官方仓库的完整提交号")
    args = parser.parse_args()
    if len(args.revision) != 40 or any(ch not in "0123456789abcdef" for ch in args.revision):
        raise ValueError("需要完整的小写十六进制提交号")
    entries = []
    for tree in (args.paint_tree, args.delight_tree):
        entries.extend(item for item in json.loads(tree.read_text(encoding="utf-8")) if item["type"] == "file")
    if not entries:
        raise ValueError("官方文件清单为空")
    names = {item["path"] for item in entries}
    if len(names) != len(entries):
        raise ValueError("官方文件清单包含重复路径")
    selected = []
    for item in entries:
        path = PurePosixPath(item["path"])
        if path.is_absolute() or ".." in path.parts or path.parts[0] not in {
            "hunyuan3d-paint-v2-0-turbo", "hunyuan3d-delight-v2-0"
        }:
            raise ValueError(f"无效文件路径：{path}")
        selected.append(item)
    print(f"待核对 {len(selected)} 个文件，合计 {sum(item['size'] for item in selected) / 1e9:.2f} GB", flush=True)
    for item in selected:
        path = PurePosixPath(item["path"])
        target = args.output.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        expected_size = item["size"]
        expected_hash = item.get("lfs", {}).get("oid")
        if target.exists() and target.stat().st_size > expected_size:
            raise RuntimeError(f"文件比官方尺寸大，需检查：{target}")
        if not target.exists() or target.stat().st_size < expected_size:
            url = f"https://huggingface.co/tencent/Hunyuan3D-2/resolve/{args.revision}/{quote(str(path))}"
            print(f"下载 {path}", flush=True)
            for attempt in range(3):
                previous_size = target.stat().st_size if target.exists() else 0
                completed = subprocess.run([
                    "curl", "-fsSL", "-C", "-", "--retry", "6", "--retry-all-errors",
                    "--retry-delay", "3", "--connect-timeout", "20", "--speed-time", "30",
                    "--speed-limit", "1024", "-o", str(target), url,
                ])
                if completed.returncode == 0:
                    break
                current_size = target.stat().st_size if target.exists() else 0
                if current_size <= previous_size or attempt == 2:
                    raise RuntimeError(f"下载失败（curl {completed.returncode}）：{path}")
                print(f"连接中断，已保存 {current_size} 字节，继续续传 {path}", flush=True)
        if target.stat().st_size != expected_size:
            raise RuntimeError(f"文件大小不符：{path}")
        if expected_hash and digest(target) != expected_hash:
            raise RuntimeError(f"SHA-256 不符：{path}")
        if not expected_hash and git_blob_digest(target) != item["oid"]:
            raise RuntimeError(f"Git 文件对象校验不符：{path}")
        print(f"完成 {path}", flush=True)


if __name__ == "__main__":
    main()
