# -*- coding: utf-8 -*-
"""training/make_attribution.py 的单元测试：署名清单必须与合并后的数据集中的图片逐一对应。"""
import csv
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "training"))

import make_attribution as ma  # noqa: E402

FIELDS = ["file", "title", "creator", "license", "license_version", "source", "foreign_landing_url", "url", "id", "query"]


def write_manifest(path, files):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "id", "title", "creator", "license", "license_version", "source", "foreign_landing_url", "url", "query"])
        for name in files:
            w.writerow([name, "id-" + name, "title " + name, "me", "by", "4.0", "flickr", "http://x/" + name, "http://u", "q"])


class MakeAttributionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cand = os.path.join(self.tmp, "cand")
        self.dataset = os.path.join(self.tmp, "yolo")
        write_manifest(os.path.join(self.cand, "raw_a", "manifest.csv"), ["raw_a_0001.jpg", "raw_a_0002.jpg", "raw_a_0003.jpg"])
        write_manifest(os.path.join(self.cand, "other_b", "manifest.csv"), ["other_b_0001.jpg"])
        for split, name in (("train", "web_x_raw_a_0001.jpg"), ("val", "web_x_raw_a_0003.jpg"), ("train", "web_x_other_b_0001.jpg"),
                            ("train", "web_other_raw_a_0002.jpg")):
            os.makedirs(os.path.join(self.dataset, "images", split), exist_ok=True)
            open(os.path.join(self.dataset, "images", split, name), "w").close()

    def run_it(self, **kw):
        out = os.path.join(self.tmp, "att.csv")
        n = ma.make(self.dataset, "web_x", self.cand, out, **kw)
        with open(out, encoding="utf-8") as f:
            return n, list(csv.DictReader(f))

    def test_lists_exactly_the_images_in_the_dataset(self):
        n, rows = self.run_it()
        self.assertEqual(n, 3)
        self.assertEqual(sorted(r["file"] for r in rows), ["other_b_0001.jpg", "raw_a_0001.jpg", "raw_a_0003.jpg"])

    def test_images_removed_by_dedup_are_not_listed(self):
        # raw_a_0002 在候选目录里有记录，但数据集里没有（合并时被去重），署名清单里不应该有它
        _, rows = self.run_it()
        self.assertNotIn("raw_a_0002.jpg", [r["file"] for r in rows])

    def test_other_sources_are_ignored(self):
        _, rows = self.run_it()
        self.assertEqual(len(rows), 3)  # web_other_* 属于另一个来源

    def test_missing_manifest_entry_is_an_error(self):
        os.makedirs(os.path.join(self.dataset, "images", "test"), exist_ok=True)
        open(os.path.join(self.dataset, "images", "test", "web_x_raw_a_9999.jpg"), "w").close()
        with self.assertRaises(SystemExit):
            self.run_it()

    def test_output_has_license_columns(self):
        _, rows = self.run_it()
        self.assertEqual(set(["file", "title", "creator", "license", "license_version", "source", "foreign_landing_url"]), set(rows[0]))


if __name__ == "__main__":
    unittest.main()
