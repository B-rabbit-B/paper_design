# -*- coding: utf-8 -*-
"""training/download_openimages.py 的离线单元测试（只测选图与写标注，不联网）。"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "training"))

import download_openimages as oi  # noqa: E402

CLASSES_CSV = "/m/egg,Egg\n/m/mango,Mango\n/m/cat,Cat\n"
HEADER = "ImageID,Source,LabelName,Confidence,XMin,XMax,YMin,YMax,IsOccluded,IsTruncated,IsGroupOf,IsDepiction,IsInside\n"


def row(image, label, xmin=0.1, xmax=0.5, ymin=0.2, ymax=0.6, group=0, depiction=0):
    return f"{image},xclick,{label},1,{xmin},{xmax},{ymin},{ymax},0,0,{group},{depiction},0\n"


class SelectTest(unittest.TestCase):
    def setUp(self):
        self.meta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.meta, ignore_errors=True)
        with open(os.path.join(self.meta, "class-descriptions-boxable.csv"), "w", encoding="utf-8") as f:
            f.write(CLASSES_CSV)
        rows = [row(f"e{i}", "/m/egg") for i in range(5)]
        rows += [row("both", "/m/egg"), row("both", "/m/mango", 0.6, 0.9, 0.1, 0.4)]
        rows += [row("grp", "/m/egg", group=1)]           # 群组框 → 整张图不要
        rows += [row("draw", "/m/mango", depiction=1)]    # 非实物描绘 → 整张图不要
        rows += [row("cat", "/m/cat")]                    # 无关类别
        with open(os.path.join(self.meta, "train-annotations-bbox.csv"), "w", encoding="utf-8") as f:
            f.write(HEADER + "".join(rows))

    def select(self, per_class=100, seed=0):
        return oi.select_images(self.meta, ["Egg", "Mango"], per_class, seed)

    def test_excludes_group_and_depiction_images(self):
        chosen = self.select()
        self.assertNotIn("grp", chosen)
        self.assertNotIn("draw", chosen)
        self.assertNotIn("cat", chosen)

    def test_keeps_all_target_boxes_of_a_chosen_image(self):
        chosen = self.select()
        self.assertEqual(sorted(b[0] for b in chosen["both"]["boxes"]), ["Egg", "Mango"])
        self.assertEqual(chosen["both"]["split"], "train")

    def test_per_class_limit_and_determinism(self):
        a = self.select(per_class=2, seed=7)
        b = self.select(per_class=2, seed=7)
        self.assertEqual(sorted(a), sorted(b))
        egg_images = [i for i, v in a.items() if any(n == "Egg" for n, *_ in v["boxes"])]
        self.assertLessEqual(len(egg_images), 3)  # Egg 最多抽 2 张，另外可能因 Mango 被选中的 both 也含 Egg

    def test_unknown_class_name_is_rejected(self):
        with self.assertRaises(SystemExit):
            oi.select_images(self.meta, ["Dragonfruit"], 10, 0)

    def test_yolo_label_lines(self):
        chosen = self.select()
        lines = oi.yolo_lines(chosen["both"]["boxes"], ["Egg", "Mango"])
        self.assertEqual(lines[0], "0 0.300000 0.400000 0.400000 0.400000")
        self.assertTrue(lines[1].startswith("1 0.750000 0.250000"))


class StaleFilesTest(unittest.TestCase):
    def test_removes_files_of_images_that_are_no_longer_selected(self):
        # 第二次下载换了类别列表，选图结果变了；上一次留下的图和标注必须清掉，否则输出目录无法由命令复现
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        for kind, ext in (("images", ".jpg"), ("labels", ".txt")):
            os.makedirs(os.path.join(out, kind, "train"))
            for image_id in ("keep", "old"):
                open(os.path.join(out, kind, "train", image_id + ext), "w").close()
        removed = oi.remove_stale(out, {"keep": {"split": "train"}})
        self.assertEqual(removed, 2)
        self.assertEqual(os.listdir(os.path.join(out, "images", "train")), ["keep.jpg"])
        self.assertEqual(os.listdir(os.path.join(out, "labels", "train")), ["keep.txt"])

    def test_missing_output_directory_is_fine(self):
        self.assertEqual(oi.remove_stale(os.path.join(tempfile.gettempdir(), "no-such-dir-oi"), {}), 0)


if __name__ == "__main__":
    unittest.main()
