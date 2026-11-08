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
import json
import os
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ORDER = ("front", "back", "left", "right", "top", "close")
PAGE_SIZE = 6
COMPARISON_PAIRS_PER_PAGE = 3
MAX_REVIEW_INPUTS = 24
CACHE_VERSION = "quality-review-v4"


def source_fingerprint(paths: list[Path]) -> str:
    """Invalidate previews when views are added/removed, or input files change."""
    entries = [
        f"{str(path.resolve()).casefold()}:{path.stat().st_size}:{path.stat().st_mtime_ns}"
        for path in paths
    ]
    return hashlib.sha1((CACHE_VERSION + "|" + "|".join(entries)).encode("utf-8")).hexdigest()[:12]


def review_rgb(image: Image.Image) -> Image.Image:
    """Use a white matte for transparent assets, not an implicit black matte."""
    if "A" in image.getbands() or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def image_files(source: Path, newest: int | None = None) -> list[Path]:
    """List only local originals; do not duplicate or modify source images."""
    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"Not an image directory: {source}")
    files = [p for p in source.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS]
    if not files:
        raise ValueError(f"No images in: {source}")
    if newest is not None:
        if newest < 1:
            raise ValueError("--newest must be positive")
        files.sort(key=lambda p: (-p.stat().st_mtime_ns, p.name.lower()))
        return files[:newest]
    files.sort(key=lambda p: (ORDER.index(p.stem.lower()) if p.stem.lower() in ORDER else len(ORDER), p.name.lower()))
    return files


def _save_atomic(image: Image.Image, destination: Path, fmt: str, **kwargs) -> None:
    """Avoid publishing partial JPEG/PNG when a process is interrupted."""
    temp = destination.with_name(f".{destination.stem}-{os.getpid()}-{uuid.uuid4().hex}.tmp{destination.suffix}")
    try:
        image.save(temp, fmt, **kwargs)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def _save_manifest(destination: Path, sources: list[dict], kind: str) -> None:
    path = destination.with_suffix(".json")
    if path.exists():
        return
    payload = {
        "schema": 1,
        "kind": kind,
        "preview": str(destination),
        "note": "Preview only; source image files are authoritative for modeling and quality inspection.",
        "sources": sources,
    }
    temp = path.with_name(f".{path.stem}-{os.getpid()}-{uuid.uuid4().hex}.tmp.json")
    try:
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _contact_sheet(files: list[Path], prefix: str, kind: str = "overview") -> Path:
    if not files or len(files) > PAGE_SIZE:
        raise ValueError(f"Expected 1-{PAGE_SIZE} images per contact page")
    digest = source_fingerprint(files)
    destination = ROOT / ".tools" / "view-previews" / f"{prefix}-{digest}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    tile_w, tile_h, margin, title_h = 460, 320, 14, 30
    columns = 2 if len(files) <= 4 else 3
    rows = (len(files) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (tile_w + margin) + margin, rows * (tile_h + title_h + margin) + margin), "#efefef")
    draw = ImageDraw.Draw(sheet)
    metadata: list[dict] = []
    for index, path in enumerate(files):
        column, row = index % columns, index // columns
        x = margin + column * (tile_w + margin)
        y = margin + row * (tile_h + title_h + margin)
        label = f"{index + 1:02d} {path.stem[:35]}"
        # ASCII fallback is for Pillow installs without an international font;
        # the adjacent manifest always retains the exact original path/name.
        label = label.encode("ascii", "replace").decode("ascii")
        draw.text((x + 5, y + 5), label, fill="#222222")
        with Image.open(path) as original:
            image = review_rgb(ImageOps.exif_transpose(original))
            source_dimensions = list(image.size)
            image.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            sheet.paste(image, (x + (tile_w - image.width) // 2, y + title_h + (tile_h - image.height) // 2))
        metadata.append({
            "index": index + 1,
            "source": str(path.resolve()),
            "source_pixels": source_dimensions,
            "source_bytes": path.stat().st_size,
            "tile_origin": [x, y],
        })
    if not destination.exists():
        _save_atomic(sheet, destination, "JPEG", quality=90, subsampling=0, optimize=True)
    _save_manifest(destination, metadata, kind)
    return destination


def create_review_pages(files: list[Path], prefix: str = "review") -> list[Path]:
    """Bound each page to six views; keep a machine-readable source mapping."""
    if not files:
        raise ValueError("No images selected")
    if len(files) > MAX_REVIEW_INPUTS:
        raise ValueError(f"Too many images ({len(files)}); select at most {MAX_REVIEW_INPUTS}, or use --newest")
    if len({str(p.resolve()).casefold() for p in files}) != len(files):
        raise ValueError("The same source image was selected more than once")
    if any(not p.is_file() or p.suffix.lower() not in EXTENSIONS for p in files):
        raise ValueError("Every selected source must be a supported image file")
    return [
        _contact_sheet(files[start:start + PAGE_SIZE], f"{prefix}-p{start // PAGE_SIZE + 1:02d}", "reference")
        for start in range(0, len(files), PAGE_SIZE)
    ]


def create_comparison_pages(before: Path, after: Path) -> list[Path]:
    """Pair like-for-like views; never silently omit an unmatched angle."""
    before, after = before.resolve(), after.resolve()
    if before.is_dir() and after.is_dir():
        left, right = image_files(before), image_files(after)
        left_by_name = {p.stem.lower(): p for p in left}
        right_by_name = {p.stem.lower(): p for p in right}
        if len(left_by_name) != len(left) or len(right_by_name) != len(right):
            raise ValueError("Duplicate view stems with different file extensions; rename before comparing")
        if left_by_name.keys() != right_by_name.keys():
            missing_left = sorted(right_by_name.keys() - left_by_name.keys())
            missing_right = sorted(left_by_name.keys() - right_by_name.keys())
            raise ValueError(f"Unmatched views (before missing {missing_left}; after missing {missing_right})")
        pairs = [(p, right_by_name[p.stem.lower()]) for p in left]
    elif before.is_file() and after.is_file():
        pairs = [(before, after)]
    else:
        raise ValueError("Compare two files or two directories, not a mixed pair")
    if not pairs:
        raise ValueError("No comparable views")
    if len(pairs) > MAX_REVIEW_INPUTS:
        raise ValueError(f"Too many comparison views ({len(pairs)}); split the review into smaller groups")

    results: list[Path] = []
    for start in range(0, len(pairs), COMPARISON_PAIRS_PER_PAGE):
        batch = pairs[start:start + COMPARISON_PAIRS_PER_PAGE]
        digest = source_fingerprint([p for pair in batch for p in pair])
        destination = ROOT / ".tools" / "view-previews" / f"comparison-p{start // COMPARISON_PAIRS_PER_PAGE + 1:02d}-{digest}.jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        tile_w, tile_h, margin, title_h = 460, 320, 14, 36
        sheet = Image.new("RGB", (2 * (tile_w + margin) + margin, len(batch) * (tile_h + title_h + margin) + margin), "#efefef")
        draw = ImageDraw.Draw(sheet)
        metadata: list[dict] = []
        for row, (older, newer) in enumerate(batch):
            for column, path in enumerate((older, newer)):
                x = margin + column * (tile_w + margin)
                y = margin + row * (tile_h + title_h + margin)
                caption = f"{'BEFORE' if column == 0 else 'AFTER'} {row + start + 1:02d} {path.stem[:26]}"
                draw.text((x + 4, y + 4), caption.encode("ascii", "replace").decode("ascii"), fill="#222222")
                with Image.open(path) as original:
                    image = review_rgb(ImageOps.exif_transpose(original))
                    dimensions = list(image.size)
                    image.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
                    sheet.paste(image, (x + (tile_w - image.width) // 2, y + title_h + (tile_h - image.height) // 2))
                metadata.append({"view": path.stem, "side": "before" if column == 0 else "after",
                                 "source": str(path), "source_pixels": dimensions, "source_bytes": path.stat().st_size,
                                 "tile_origin": [x, y]})
        if not destination.exists():
            _save_atomic(sheet, destination, "JPEG", quality=95, subsampling=0, optimize=True)
        _save_manifest(destination, metadata, "before-after")
        results.append(destination)
    return results


def create_comparison_crop(before: Path, after: Path, crop: tuple[int, int, int, int]) -> Path:
    """A lossless, equal-coordinate, side-by-side ROI. Does not resample pixels."""
    before, after = before.resolve(), after.resolve()
    if not before.is_file() or not after.is_file():
        raise ValueError("Detailed --compare --crop requires two individual image files")
    if before.suffix.lower() not in EXTENSIONS or after.suffix.lower() not in EXTENSIONS:
        raise ValueError("Both inputs must be supported images")
    x, y, width, height = crop
    if min(x, y) < 0 or min(width, height) <= 0:
        raise ValueError("Crop coordinates must be nonnegative and dimensions positive")
    digest = hashlib.sha1(f"{source_fingerprint([before, after])}|{crop}".encode("utf-8")).hexdigest()[:12]
    destination = ROOT / ".tools" / "view-previews" / f"detail-comparison-{digest}.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    margin, title_h = 12, 34
    metadata: list[dict] = []
    sheet = Image.new("RGBA", (width * 2 + margin * 3, height + margin * 2 + title_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for column, path in enumerate((before, after)):
        with Image.open(path) as original:
            image = ImageOps.exif_transpose(original)
            if image.mode not in ("RGB", "RGBA"):
                raise ValueError("Pixel-identical comparison needs 8-bit RGB/RGBA inputs; use single --crop for 16-bit/PBR maps")
            if x + width > image.width or y + height > image.height:
                raise ValueError(f"Crop {crop} outside {path.name} dimensions {image.size}")
            # RGBA output keeps every decoded source color/alpha sample.
            detail = image.crop((x, y, x + width, y + height)).convert("RGBA")
            px = margin + column * (width + margin)
            sheet.paste(detail, (px, margin + title_h))
            metadata.append({
                "side": "before" if column == 0 else "after", "source": str(path),
                "source_pixels": list(image.size), "crop": list(crop),
                "pixel_roi_origin": [px, margin + title_h],
            })
        draw.text((margin + column * (width + margin), margin),
                  "BEFORE (original pixels)" if column == 0 else "AFTER (original pixels)", fill="#222222")
    if not destination.exists():
        _save_atomic(sheet, destination, "PNG", optimize=True)
    _save_manifest(destination, metadata, "lossless-before-after-roi")
    return destination


def create_preview(source: Path) -> Path:
    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"Not a render directory: {source}")
    files = image_files(source)
    if len(files) > PAGE_SIZE:
        raise ValueError("More than six images; use create_review_pages() or the CLI for paged previews")

    return _contact_sheet(files, source.name, "render")


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
            _save_atomic(image.crop((x, y, x + width, y + height)), destination, "PNG", optimize=True)
        else:
            image = review_rgb(image)
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            _save_atomic(image, destination, "JPEG", quality=95, subsampling=0, optimize=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", help="Render/reference directory or single image")
    parser.add_argument("--crop", nargs=4, type=int, metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="Lossless pixel crop from a single image")
    parser.add_argument("--newest", type=int, metavar="COUNT",
                        help="Preview only the newest COUNT images in a directory (e.g. Codex generated_images)")
    parser.add_argument("--files", nargs="+", type=Path, metavar="IMAGE",
                        help="Review images selected from different folders without copying originals")
    parser.add_argument("--compare", type=Path, metavar="OTHER",
                        help="Pair original and revised views from two directories or two image files")
    args = parser.parse_args()
    try:
        if args.files is not None:
            if args.source or args.crop or args.newest or args.compare:
                raise ValueError("--files cannot be combined with a positional source or other modes")
            results = create_review_pages([p.resolve() for p in args.files], "selected")
        elif args.source is None:
            raise ValueError("Provide a directory, image file, or --files list")
        elif args.compare is not None:
            if args.newest is not None:
                raise ValueError("--compare cannot be combined with --newest")
            results = ([create_comparison_crop(args.source, args.compare, tuple(args.crop))]
                       if args.crop else create_comparison_pages(args.source, args.compare))
        elif args.source.is_dir():
            if args.crop:
                raise ValueError("--crop requires a single image file")
            files = image_files(args.source, args.newest)
            results = [create_preview(args.source)] if args.newest is None and len(files) <= PAGE_SIZE else create_review_pages(files, "recent" if args.newest is not None else args.source.name)
        else:
            if args.newest is not None:
                raise ValueError("--newest requires a directory")
            results = [create_image_preview(args.source, tuple(args.crop) if args.crop else None)]
        for result in results:
            print(result)
        if len(results) > 1:
            print(f"Contact pages: {len(results)}. Each has a matching .json source map.")
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
