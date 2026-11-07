"""提取指定帧并记录来源，供人工核对视频资产；不推断视频中不可读的文字。"""

import argparse
import json
from pathlib import Path

import cv2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("frames", type=int, nargs="+")
    args = parser.parse_args()

    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"无法打开视频：{args.video}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or count <= 0:
        raise RuntimeError("视频帧率或帧数不可用")
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for frame_index in args.frames:
        if not 0 <= frame_index < count:
            raise ValueError(f"帧号超出范围：{frame_index}")
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"无法读取帧 {frame_index}")
        name = f"frame_{frame_index:04d}.png"
        if not cv2.imwrite(str(args.output / name), frame):
            raise RuntimeError(f"无法保存帧 {frame_index}")
        records.append({"frame": frame_index, "seconds": round(frame_index / fps, 3), "file": name})
    capture.release()
    manifest = {"source": args.video.name, "fps": fps, "frame_count": count, "frames": records}
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
