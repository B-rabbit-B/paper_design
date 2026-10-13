# -*- coding: utf-8 -*-
"""training/normalize_photos.py 的单元测试。"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "training"))

from PIL import Image  # noqa: E402

import normalize_photos as npz  # noqa: E402

ORIENTATION = 0x0112


class NormalizeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.src = os.path.join(self.tmp, "photos")
        self.out = os.path.join(self.tmp, "custom")
        os.makedirs(os.path.join(self.src, "sub"))
        # 竖拍手机照：像素 400x300，EXIF 方向 6（需顺时针转 90°）→ 转正后应为 300x400
        exif = Image.Exif()
        exif[ORIENTATION] = 6
        Image.new("RGB", (400, 300), (200, 30, 30)).save(os.path.join(self.src, "IMG_0001.JPG"), exif=exif)
        Image.new("RGB", (4000, 1000), (30, 200, 30)).save(os.path.join(self.src, "sub", "big.png"))
        with open(os.path.join(self.src, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("not an image")

    def test_rotates_by_exif_and_strips_orientation(self):
        npz.normalize(self.src, self.out, max_side=1920)
        out = os.path.join(self.out, "images", "all", "custom_0001.jpg")
        with Image.open(out) as im:
            self.assertEqual(im.size, (300, 400))
            self.assertNotIn(ORIENTATION, im.getexif())

    def test_resizes_long_side_and_skips_non_images(self):
        mapping = npz.normalize(self.src, self.out, max_side=1920)
        self.assertEqual(len(mapping), 2)
        with Image.open(os.path.join(self.out, "images", "all", "custom_0002.jpg")) as im:
            self.assertEqual(max(im.size), 1920)

    def test_writes_classes_txt_in_label_dir(self):
        npz.normalize(self.src, self.out, max_side=1920)
        with open(os.path.join(self.out, "labels", "all", "classes.txt"), encoding="utf-8") as f:
            names = f.read().split()
        self.assertEqual(len(names), 33)
        self.assertEqual(names[0], "tomato")

    def test_heic_files_stop_the_run_before_anything_is_written(self):
        # 项目 venv 里没有 HEIC 插件，PIL 打不开 iPhone 原图；处理到一半才报错会留下半份输出，所以一开始就拒绝
        with open(os.path.join(self.src, "IMG_0002.HEIC"), "wb") as f:
            f.write(b"not really heic")
        with self.assertRaises(SystemExit) as ctx:
            npz.normalize(self.src, self.out, max_side=1920)
        self.assertIn("HEIC", str(ctx.exception))
        self.assertFalse(os.path.exists(os.path.join(self.out, "images", "all")))

    def test_refuses_to_overwrite_existing_output(self):
        npz.normalize(self.src, self.out, max_side=1920)
        with self.assertRaises(SystemExit):
            npz.normalize(self.src, self.out, max_side=1920)


if __name__ == "__main__":
    unittest.main()
