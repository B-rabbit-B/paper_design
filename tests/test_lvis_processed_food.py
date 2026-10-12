# -*- coding: utf-8 -*-
"""training/lvis_processed_food.py 的单元测试（用伪造的小型 COCO 标注包，不联网）。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "training", "lvis_processed_food.py")
CATEGORIES = [{"id": 1, "name": "pizza"}, {"id": 2, "name": "fork"}, {"id": 3, "name": "knife"},
              {"id": 4, "name": "carrot"}, {"id": 5, "name": "sandwich"}, {"id": 6, "name": "hot dog"},
              {"id": 7, "name": "donut"}, {"id": 8, "name": "cake"}, {"id": 9, "name": "spoon"}]


def _coco(annotations):
    return json.dumps({"categories": CATEGORIES,
                       "annotations": [{"image_id": i, "category_id": c} for i, c in annotations]})


class ProcessedFoodListTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.zip_path = os.path.join(self.tmp, "ann.zip")
        with zipfile.ZipFile(self.zip_path, "w") as z:
            # 101 披萨、102 叉、103 只有刀、104 只有胡萝卜；105 在 val 中含披萨
            z.writestr("annotations/instances_train2017.json",
                       _coco([(101, 1), (101, 4), (102, 2), (103, 3), (103, 4), (104, 4)]))
            z.writestr("annotations/instances_val2017.json", _coco([(105, 1)]))
        self.lvis = os.path.join(self.tmp, "lvis")
        for split, stems in {"train": [101, 102, 103], "val": [104, 105], "test": ["20240326_manual_1"]}.items():
            os.makedirs(os.path.join(self.lvis, "images", split))
            for s in stems:
                name = f"{s:012d}.jpg" if isinstance(s, int) else f"{s}.jpg"
                open(os.path.join(self.lvis, "images", split, name), "wb").close()
        self.out = os.path.join(self.tmp, "list.txt")

    def run_script(self, *extra):
        subprocess.run([sys.executable, SCRIPT, "--coco-zip", self.zip_path, "--lvis-dir", self.lvis,
                        "--out", self.out, *extra], check=True, capture_output=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        with open(self.out, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

    def test_default_categories_exclude_food_and_fork_but_not_knife(self):
        self.assertEqual(self.run_script(), ["000000000101", "000000000102", "000000000105"])

    def test_custom_categories(self):
        self.assertEqual(self.run_script("--categories", "knife"), ["000000000103"])

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_script("--categories", "dragonfruit")


if __name__ == "__main__":
    unittest.main()
