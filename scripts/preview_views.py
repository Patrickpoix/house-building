r"""Make compact previews for AI review; never modify the source images.

Usage:
    D:\Python\python.exe scripts\preview_views.py stages\S002\A031-study\reconstructed-v2-views
    D:\Python\python.exe scripts\preview_views.py tripo\outputs\reading-chair\views\close.png
    D:\Python\python.exe scripts\preview_views.py tripo\outputs\reading-chair\views\close.png --crop 100 100 512 512

Open the printed JPEG for an overview or a lossless PNG crop for focused detail.
The original render remains untouched and available for definitive inspection.
"""

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ORDER = ("front", "back", "left", "right", "top", "close")


def source_fingerprint(paths: list[Path]) -> str:
    """Invalidate previews when views are added/removed, or input files change."""
    entries = [
        f"{str(path.resolve()).casefold()}:{path.stat().st_size}:{path.stat().st_mtime_ns}"
        for path in paths
    ]
    return hashlib.sha1("|".join(entries).encode("utf-8")).hexdigest()[:12]


def review_rgb(image: Image.Image) -> Image.Image:
    """Use a white matte for transparent assets, not an implicit black matte."""
    if "A" in image.getbands() or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def create_preview(source: Path) -> Path:
    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"Not a render directory: {source}")
    files = [p for p in source.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS]
    if not files:
        raise ValueError(f"No images in: {source}")
    files.sort(key=lambda p: (ORDER.index(p.stem.lower()) if p.stem.lower() in ORDER else len(ORDER), p.name.lower()))

    digest = source_fingerprint([source, *files])
    destination = ROOT / ".tools" / "view-previews" / f"{source.name}-{digest}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
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
            image = review_rgb(ImageOps.exif_transpose(original))
            image.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            sheet.paste(image, (x + (tile_w - image.width) // 2, y + title_h + (tile_h - image.height) // 2))

    sheet.save(destination, "JPEG", quality=90, subsampling=0, optimize=True)
    return destination


def create_image_preview(source: Path, crop: tuple[int, int, int, int] | None = None) -> Path:
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
        raise ValueError(f"Not a supported image file: {source}")

    digest = hashlib.sha1(f"{source_fingerprint([source])}|{crop}".encode("utf-8")).hexdigest()[:12]
    suffix = ".png" if crop is not None else ".jpg"
    destination = ROOT / ".tools" / "view-previews" / f"{source.stem}-{digest}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original)
        if crop is not None:
            x, y, width, height = crop
            if min(x, y) < 0 or min(width, height) <= 0 or x + width > image.width or y + height > image.height:
                raise ValueError(f"Crop {crop} outside source dimensions {image.size}")
        if destination.exists():
            return destination
        if crop is not None:
            # Lossless original-pixel region, without downsampling.
            image.crop((x, y, x + width, y + height)).save(destination, "PNG", optimize=True)
        else:
            image = review_rgb(image)
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            image.save(destination, "JPEG", quality=95, subsampling=0, optimize=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Render directory or single image")
    parser.add_argument("--crop", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="Lossless pixel crop from a single image")
    args = parser.parse_args()
    try:
        if args.source.is_dir():
            if args.crop:
                raise ValueError("--crop requires a single image file")
            result = create_preview(args.source)
        else:
            result = create_image_preview(args.source, tuple(args.crop) if args.crop else None)
        print(result)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
