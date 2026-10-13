# -*- coding: utf-8 -*-
"""training/fix_nested_boxes.py 的单元测试：嵌套框的去除规则，以及原标注的备份。"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "training"))

import fix_nested_boxes as fnb  # noqa: E402


def box(cx, cy, w, h, cls=0):
    return (cls, cx, cy, w, h)


class RemoveNestedTest(unittest.TestCase):
    def test_drops_box_mostly_inside_a_larger_one(self):
        big, small = box(0.5, 0.5, 0.6, 0.6), box(0.5, 0.5, 0.3, 0.3)
        self.assertEqual(fnb.remove_nested([small, big]), [big])

    def test_keeps_separate_boxes(self):
        a, b = box(0.25, 0.5, 0.3, 0.3), box(0.75, 0.5, 0.3, 0.3)
        self.assertEqual(fnb.remove_nested([a, b]), [a, b])

    def test_partially_overlapping_boxes_are_both_kept(self):
        a, b = box(0.4, 0.5, 0.4, 0.4), box(0.6, 0.5, 0.4, 0.4)  # 各有一半重叠，谁也没被包住
        self.assertEqual(fnb.remove_nested([a, b]), [a, b])

    def test_identical_boxes_keep_one(self):
        a = box(0.5, 0.5, 0.4, 0.4)
        self.assertEqual(fnb.remove_nested([a, a]), [a])

    def test_only_boxes_of_the_same_class_nest(self):
        big, small = box(0.5, 0.5, 0.6, 0.6, cls=0), box(0.5, 0.5, 0.2, 0.2, cls=1)
        self.assertEqual(fnb.remove_nested([big, small]), [big, small])


class FixFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        os.makedirs(os.path.join(self.tmp, "labels", "train"))
        self.label = os.path.join(self.tmp, "labels", "train", "a.txt")
        with open(self.label, "w", encoding="utf-8") as f:
            f.write("0 0.5 0.5 0.6 0.6\n0 0.5 0.5 0.2 0.2\n")

    def test_rewrites_label_and_backs_up_the_original(self):
        changed = fnb.fix(self.tmp, ["a"])
        self.assertEqual(changed, {"a": (2, 1)})
        with open(self.label, encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 1)
        with open(os.path.join(self.tmp, "labels_orig", "train", "a.txt"), encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 2)

    def test_second_run_does_not_overwrite_the_backup(self):
        fnb.fix(self.tmp, ["a"])
        fnb.fix(self.tmp, ["a"])  # 标注已经只剩 1 个框，没有变化，备份仍是最初的 2 个框
        with open(os.path.join(self.tmp, "labels_orig", "train", "a.txt"), encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 2)

    def test_unknown_stem_is_an_error(self):
        with self.assertRaises(SystemExit):
            fnb.fix(self.tmp, ["nope"])


if __name__ == "__main__":
    unittest.main()
