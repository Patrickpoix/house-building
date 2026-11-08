"""Focused regression checks for the non-destructive AI preview helper."""

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, JpegImagePlugin


MODULE_PATH = Path(__file__).with_name("preview_views.py")
SPEC = importlib.util.spec_from_file_location("preview_views", MODULE_PATH)
assert SPEC and SPEC.loader
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old_root = preview.ROOT
        preview.ROOT = self.root
        self.addCleanup(setattr, preview, "ROOT", self.old_root)

    def test_contact_sheet_reuses_unchanged_inputs_and_tracks_view_changes(self):
        source = self.root / "views"
        source.mkdir()
        Image.new("RGB", (300, 240), "red").save(source / "front.png")
        Image.new("RGB", (300, 240), "green").save(source / "back.png")
        initial = preview.create_preview(source)
        self.assertEqual(initial, preview.create_preview(source))
        self.assertTrue(initial.is_file())
        front = source / "front.png"
        old_stat = front.stat()
        Image.new("RGB", (300, 240), "purple").save(front)
        os.utime(front, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 2_000_000_000))
        changed = preview.create_preview(source)
        self.assertNotEqual(initial, changed)
        Image.new("RGB", (300, 240), "blue").save(source / "left.png")
        added = preview.create_preview(source)
        self.assertNotEqual(changed, added)
        (source / "left.png").unlink()
        removed = preview.create_preview(source)
        self.assertNotEqual(added, removed)

    def test_lossless_crop_and_high_quality_single_preview(self):
        source = self.root / "texture.png"
        image = Image.new("RGB", (360, 300))
        for y in range(300):
            for x in range(360):
                image.putpixel((x, y), ((x * 7) % 256, (y * 11) % 256, (x + y) % 256))
        image.save(source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        cropped = preview.create_image_preview(source, (20, 30, 140, 130))
        overview = preview.create_image_preview(source)
        with Image.open(cropped) as small:
            self.assertEqual(small.size, (140, 130))
            self.assertIsNone(ImageChops.difference(image.crop((20, 30, 160, 160)), small).getbbox())
        with Image.open(overview) as jpeg:
            self.assertEqual(jpeg.size, image.size)
            self.assertEqual(JpegImagePlugin.get_sampling(jpeg), 0)  # 4:4:4 chroma
        self.assertEqual(digest, hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(overview, preview.create_image_preview(source))

    def test_transparency_and_crop_validation(self):
        source = self.root / "alpha.png"
        Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(source)
        overview = preview.create_image_preview(source)
        with Image.open(overview) as jpeg:
            self.assertEqual(jpeg.getpixel((5, 5)), (255, 255, 255))
        for crop in ((-1, 0, 10, 10), (0, 0, 100, 10), (0, 0, 0, 10)):
            with self.subTest(crop=crop), self.assertRaises(ValueError):
                preview.create_image_preview(source, crop)

    def test_generated_images_newest_and_paged_source_manifest(self):
        generated = self.root / "generated_images"
        generated.mkdir()
        for index in range(12):
            path = generated / f"exec-{index:02d}.png"
            Image.new("RGB", (100, 80), (index * 12, 50, 70)).save(path)
            os.utime(path, ns=(1_700_000_000_000_000_000 + index * 1_000_000_000,) * 2)
        newest = preview.image_files(generated, newest=8)
        self.assertEqual([p.stem for p in newest], [f"exec-{i:02d}" for i in range(11, 3, -1)])
        pages = preview.create_review_pages(newest, "recent")
        self.assertEqual(len(pages), 2)
        contents = []
        for page in pages:
            self.assertTrue(page.exists())
            manifest = json.loads(page.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["kind"], "reference")
            contents.extend(manifest["sources"])
        self.assertEqual(len(contents), 8)
        self.assertEqual(Path(contents[0]["source"]).stem, "exec-11")
        self.assertEqual(pages, preview.create_review_pages(newest, "recent"))
        with self.assertRaises(ValueError):
            preview.create_review_pages(newest + newest, "repeated")
        with self.assertRaises(ValueError):
            preview.create_review_pages(preview.image_files(generated) * 3, "overlarge")

    def test_before_after_is_paired_and_never_drops_missing_views(self):
        before, after = self.root / "before", self.root / "after"
        before.mkdir()
        after.mkdir()
        for view in ("front", "back", "left", "right", "close"):
            Image.new("RGB", (90, 100), "white").save(before / f"{view}.png")
            Image.new("RGB", (90, 100), "black").save(after / f"{view}.png")
        pages = preview.create_comparison_pages(before, after)
        self.assertEqual(len(pages), 2)
        first = json.loads(pages[0].with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(first["kind"], "before-after")
        self.assertEqual([x["side"] for x in first["sources"]], ["before", "after"] * 3)
        self.assertEqual({x["view"] for x in first["sources"]}, {"front", "back", "left"})
        self.assertEqual(pages, preview.create_comparison_pages(before, after))
        (after / "right.png").unlink()
        with self.assertRaisesRegex(ValueError, "Unmatched views"):
            preview.create_comparison_pages(before, after)

    def test_cross_folder_reference_selection_preserves_real_paths(self):
        one = self.root / "wood.png"
        folder = self.root / "fabric"
        folder.mkdir()
        two = folder / "fabric.png"
        Image.new("RGB", (300, 300), "brown").save(one)
        Image.new("RGB", (300, 300), "blue").save(two)
        pages = preview.create_review_pages([one, two], "mixed")
        data = json.loads(pages[0].with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual([Path(x["source"]) for x in data["sources"]], [one.resolve(), two.resolve()])
        self.assertTrue(all(Path(x["source"]).exists() for x in data["sources"]))
        self.assertFalse(list((self.root / ".tools").rglob("*.tmp.*")))

    def test_detailed_old_new_comparison_preserves_decoded_rgb_pixels(self):
        old = self.root / "old.png"
        new = self.root / "new.png"
        a, b = Image.new("RGB", (200, 180)), Image.new("RGB", (200, 180))
        for y in range(180):
            for x in range(200):
                a.putpixel((x, y), (x % 256, y % 256, 37))
                b.putpixel((x, y), (x % 256, y % 256, 91))
        a.save(old)
        b.save(new)
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (old, new)]
        cropped = preview.create_comparison_crop(old, new, (30, 40, 80, 70))
        details = json.loads(cropped.with_suffix(".json").read_text(encoding="utf-8"))["sources"]
        with Image.open(cropped) as page:
            for original, entry in zip((a, b), details):
                px, py = entry["pixel_roi_origin"]
                tile = page.crop((px, py, px + 80, py + 70))
                expected = original.crop((30, 40, 110, 110))
                self.assertIsNone(ImageChops.difference(expected.convert("RGBA"), tile.convert("RGBA")).getbbox())
        self.assertEqual(hashes, [hashlib.sha256(p.read_bytes()).hexdigest() for p in (old, new)])
        with self.assertRaisesRegex(ValueError, "outside"):
            preview.create_comparison_crop(old, new, (150, 140, 100, 100))
        alpha = self.root / "alpha.png"
        Image.new("RGBA", (200, 180), (0, 1, 2, 0)).save(alpha)
        rgba_result = preview.create_comparison_crop(alpha, new, (1, 1, 50, 50))
        rgba_map = json.loads(rgba_result.with_suffix(".json").read_text(encoding="utf-8"))
        px, py = rgba_map["sources"][0]["pixel_roi_origin"]
        with Image.open(rgba_result) as rgba_sheet:
            self.assertEqual(rgba_sheet.getpixel((px + 5, py + 5)), (0, 1, 2, 0))
        high_depth = self.root / "16bit.png"
        Image.new("I;16", (200, 180), 1000).save(high_depth)
        with self.assertRaisesRegex(ValueError, "8-bit RGB/RGBA"):
            preview.create_comparison_crop(high_depth, new, (1, 1, 50, 50))


if __name__ == "__main__":
    unittest.main()
