"""Focused regression checks for the non-destructive AI preview helper."""

import hashlib
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
