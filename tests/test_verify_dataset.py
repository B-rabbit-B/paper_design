# -*- coding: utf-8 -*-
"""training/verify_dataset.py 的单元测试：用 prepare_dataset 在临时目录里合出一个小数据集，再故意弄坏它。"""
import os
import shutil
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "training"))

import verify_dataset as vd  # noqa: E402
from test_prepare_dataset import Fixture, _cropped_copy, _image, _smooth_image, _write  # noqa: E402


class VerifyTest(Fixture):
    def setUp(self):
        super().setUp()
        self.summary = self.build()

    def verify(self, **kw):
        return vd.verify(self.out, num_classes=2, **kw)

    def some_file(self, split, kind):
        return os.path.join(self.out, kind, split, sorted(os.listdir(os.path.join(self.out, kind, split)))[0])

    def test_clean_dataset_has_no_problems(self):
        r = self.verify()
        self.assertEqual(sum(r["images"].values()), 23)
        self.assertEqual((r["unpaired_files"], r["bad_label_lines"], r["cross_split_md5"], r["cross_split_ahash"],
                          r["cross_split_dhash"]), (0, 0, 0, 0, 0))

    def test_detects_bad_label_lines(self):
        label = self.some_file("train", "labels")
        with open(label, "a", encoding="utf-8") as f:
            # 类别越界、宽度为 0、字段数不对、框超出图片
            f.write("5 0.5 0.5 0.2 0.2\n0 0.5 0.5 0 0.2\n0 0.5 0.5\n0 0.95 0.5 0.2 0.2\n")
        self.assertEqual(self.verify()["bad_label_lines"], 4)

    def test_detects_unpaired_files(self):
        os.remove(self.some_file("train", "labels"))
        self.assertEqual(self.verify()["unpaired_files"], 1)

    def test_detects_same_image_in_two_splits(self):
        src_image, src_label = self.some_file("train", "images"), self.some_file("train", "labels")
        shutil.copyfile(src_image, os.path.join(self.out, "images", "test", "copy.jpg"))
        shutil.copyfile(src_label, os.path.join(self.out, "labels", "test", "copy.txt"))
        r = self.verify()
        self.assertEqual((r["cross_split_md5"], r["cross_split_ahash"]), (1, 1))

    def test_detects_cropped_copy_in_another_split(self):
        train_image = os.path.join(self.out, "images", "train", "photo.jpg")
        test_image = os.path.join(self.out, "images", "test", "photo_crop.jpg")
        _smooth_image(train_image, seed=1)
        _cropped_copy(train_image, test_image)
        for path in (os.path.join(self.out, "labels", "train", "photo.txt"),
                     os.path.join(self.out, "labels", "test", "photo_crop.txt")):
            _write(path, "0 0.5 0.5 0.2 0.2\n")
        r = self.verify()
        self.assertEqual((r["cross_split_md5"], r["cross_split_ahash"], r["cross_split_dhash"]), (0, 0, 1))

    def test_detects_same_image_in_another_dataset(self):
        other = os.path.join(self.tmp, "other")
        _image(os.path.join(other, "images", "val", "z.jpg"), seed=900)
        _write(os.path.join(other, "labels", "val", "z.txt"), "0 0.5 0.5 0.2 0.2\n")
        r = self.verify(against=other)
        self.assertEqual((r["against_md5"], r["against_ahash"], r["against_dhash"]), (0, 0, 0))
        shutil.copyfile(self.some_file("train", "images"), os.path.join(other, "images", "val", "copy.jpg"))
        _write(os.path.join(other, "labels", "val", "copy.txt"), "0 0.5 0.5 0.2 0.2\n")
        r = self.verify(against=other)
        self.assertEqual((r["against_md5"], r["against_ahash"], r["against_dhash"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
