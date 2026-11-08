r"""Make one small contact sheet for AI review; never modify source renders.

Usage:
    D:\Python\python.exe scripts\preview_views.py stages\S002\A031-study\reconstructed-v2-views

Open the printed JPEG for an overview. Inspect an original render or a cropped
detail only when necessary to judge fabric, UV, topology, or PBR quality.
"""

import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ORDER = ("front", "back", "left", "right", "top", "close")


def create_preview(source: Path) -> Path:
    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"Not a render directory: {source}")
    files = [p for p in source.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS]
    if not files:
        raise ValueError(f"No images in: {source}")
    files.sort(key=lambda p: (ORDER.index(p.stem.lower()) if p.stem.lower() in ORDER else len(ORDER), p.name.lower()))

    digest = hashlib.sha1(str(source).casefold().encode("utf-8")).hexdigest()[:12]
    destination = ROOT / ".tools" / "view-previews" / f"{source.name}-{digest}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_mtime_ns >= max(p.stat().st_mtime_ns for p in files):
        return destination

    tile_w, tile_h, margin, title_h = 460, 320, 14, 30
    columns = 2 if len(files) <= 4 else 3
    rows = (len(files) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (tile_w + margin) + margin, rows * (tile_h + title_h + margin) + margin), "#efefef")
    draw = ImageDraw.Draw(sheet)

    for index, path in enumerate(files):
        column, row = index % columns, index // columns
        x = margin + column * (tile_w + margin)
        y = margin + row * (tile_h + title_h + margin)
        draw.text((x + 5, y + 5), path.stem, fill="#222222")
        with Image.open(path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            sheet.paste(image, (x + (tile_w - image.width) // 2, y + title_h + (tile_h - image.height) // 2))

    sheet.save(destination, "JPEG", quality=84, optimize=True)
    return destination


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/preview_views.py <render-image-directory>")
    try:
        print(create_preview(Path(sys.argv[1])))
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
