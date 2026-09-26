# -*- coding: utf-8 -*-
"""core/food_classes.py 的单元测试。

用法：在项目根目录执行  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest

# 确保项目根目录在 sys.path 中，便于 `import core` / `import config`
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import food_classes  # noqa: E402

VALID_CLASS = {
    "id": 0, "name": "tomato", "zh": "西红柿", "ingredient": "西红柿",
    "unit": "piece", "default_weight_g": 150,
}


def _ingredient_index_from_json():
    """用 data/ingredients.json 构建 {主名或别名: 条目} 索引，与 db.load_ingredients 的键规则一致。"""
    with open(os.path.join(ROOT, "data", "ingredients.json"), encoding="utf-8") as f:
        items = json.load(f)
    index = {}
    for it in items:
        index[it["name"]] = it
        for alias in it.get("aliases", []):
            index[alias] = it
    return index


class RealClassesTest(unittest.TestCase):
    """针对仓库里真实的 training/classes.yaml。"""

    def setUp(self):
        self.classes = food_classes.load_classes()

    def test_has_33_contiguous_ids(self):
        ids = [c["id"] for c in self.classes["list"]]
        self.assertEqual(ids, list(range(33)))

    def test_names_follow_id_order(self):
        self.assertEqual(self.classes["names"], [c["name"] for c in self.classes["list"]])
        self.assertEqual(self.classes["by_id"][0]["name"], self.classes["names"][0])

    def test_every_ingredient_resolves(self):
        missing = food_classes.validate(self.classes, _ingredient_index_from_json())
        self.assertEqual(missing, [])


class LoadClassesErrorTest(unittest.TestCase):
    """用临时 yaml 构造各种错误，都应抛出 ValueError。"""

    def _load(self, classes):
        import yaml
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.safe_dump({"version": 1, "classes": classes}, f, allow_unicode=True)
            path = f.name
        self.addCleanup(os.remove, path)
        return food_classes.load_classes(path)

    def _cls(self, **overrides):
        c = dict(VALID_CLASS)
        c.update(overrides)
        return c

    def test_valid_minimal_file_loads(self):
        result = self._load([self._cls()])
        self.assertEqual(result["names"], ["tomato"])
        self.assertEqual(result["by_name"]["tomato"]["zh"], "西红柿")
        self.assertEqual(result["version"], 1)

    def test_empty_class_list(self):
        with self.assertRaises(ValueError):
            self._load([])

    def test_duplicate_id(self):
        with self.assertRaises(ValueError):
            self._load([self._cls(), self._cls(name="egg")])

    def test_non_contiguous_ids(self):
        with self.assertRaises(ValueError):
            self._load([self._cls(), self._cls(id=2, name="egg")])

    def test_duplicate_name(self):
        with self.assertRaises(ValueError):
            self._load([self._cls(), self._cls(id=1)])

    def test_missing_required_field(self):
        c = self._cls()
        del c["ingredient"]
        with self.assertRaises(ValueError):
            self._load([c])

    def test_bad_unit(self):
        with self.assertRaises(ValueError):
            self._load([self._cls(unit="kg")])

    def test_non_positive_weight(self):
        with self.assertRaises(ValueError):
            self._load([self._cls(default_weight_g=0)])

    def test_list_sorted_by_id(self):
        result = self._load([self._cls(id=1, name="egg"), self._cls()])
        self.assertEqual(result["names"], ["tomato", "egg"])


class ValidateAndSourceMapTest(unittest.TestCase):
    def setUp(self):
        self.classes = {
            "list": [
                {**VALID_CLASS, "sources": {"lvis": ["tomato"], "openimages": ["Tomato"]}},
                {**VALID_CLASS, "id": 1, "name": "egg", "zh": "鸡蛋", "ingredient": "鸡蛋",
                 "sources": {"openimages": ["Egg (Food)"]}},
            ]
        }

    def test_validate_reports_missing_ingredient(self):
        self.assertEqual(food_classes.validate(self.classes, {"西红柿": {}}), ["egg"])

    def test_source_map(self):
        self.assertEqual(food_classes.source_map(self.classes, "openimages"),
                         {"Tomato": 0, "Egg (Food)": 1})
        self.assertEqual(food_classes.source_map(self.classes, "lvis"), {"tomato": 0})
        self.assertEqual(food_classes.source_map(self.classes, "zenodo"), {})

    def test_source_map_conflict(self):
        self.classes["list"][1]["sources"]["openimages"].append("Tomato")
        with self.assertRaises(ValueError):
            food_classes.source_map(self.classes, "openimages")


if __name__ == "__main__":
    unittest.main()
