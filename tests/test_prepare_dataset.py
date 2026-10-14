# -*- coding: utf-8 -*-
"""training/prepare_dataset.py 与 training/sources 的单元测试。

用临时目录造出很小的 YOLO 源和 VOC 源，验证类别映射、坏标签统计、去重、
近重复分组、划分、输出文件与 summary.json 字段。

用法：在项目根目录执行  python -m unittest discover -s tests -v
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "training"))

import yaml  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import prepare_dataset as pd  # noqa: E402
from sources import coco as coco_adapter  # noqa: E402
from sources import detect_format, voc, yolo  # noqa: E402

CLASSES_YAML = {
    "version": 1,
    "classes": [
        {"id": 0, "name": "tomato", "zh": "西红柿", "ingredient": "西红柿", "unit": "piece",
         "default_weight_g": 150, "sources": {"src_yolo": ["Tomato", "tomato"], "src_voc": ["tomato"]}},
        {"id": 1, "name": "carrot", "zh": "胡萝卜", "ingredient": "胡萝卜", "unit": "piece",
         "default_weight_g": 120, "sources": {"src_yolo": ["carrot"], "src_voc": ["carrot"]}},
    ],
}


def _image(path, seed, size=(64, 48)):
    """生成内容互不相同的小图（seed 不同 → 像素不同 → md5 与平均哈希都不同）。"""
    rng = random.Random(seed)
    img = Image.new("RGB", size, (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
    draw = ImageDraw.Draw(img)
    for _ in range(6):
        x, y = rng.randint(0, size[0] - 10), rng.randint(0, size[1] - 10)
        draw.rectangle([x, y, x + rng.randint(4, 30), y + rng.randint(4, 20)],
                       fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Fixture(unittest.TestCase):
    """临时目录：raw/src_yolo（YOLO 格式）、raw/src_voc（VOC 格式）、classes.yaml。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.raw = os.path.join(self.tmp, "raw")
        self.classes_path = os.path.join(self.tmp, "classes.yaml")
        with open(self.classes_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(CLASSES_YAML, f, allow_unicode=True)

        # --- YOLO 源：names 0=Tomato 1=carrot 2=watermelon（未映射）
        y = os.path.join(self.raw, "src_yolo")
        _write(os.path.join(y, "data.yaml"), "names:\n  0: Tomato\n  1: carrot\n  2: watermelon\n")
        for i in range(20):
            _image(os.path.join(y, "images", "train", f"y{i}.jpg"), seed=i)
            _write(os.path.join(y, "labels", "train", f"y{i}.txt"), "0 0.5 0.5 0.2 0.2\n1 0.3 0.3 0.1 0.1\n")
        # 只含未映射类别的图 → 映射后没有框，应被丢弃
        _image(os.path.join(y, "images", "train", "only_watermelon.jpg"), seed=100)
        _write(os.path.join(y, "labels", "train", "only_watermelon.txt"), "2 0.5 0.5 0.2 0.2\n")
        # 坏标签：坐标越界、宽高为 0、类别越界、字段数不对 → 4 个坏框，好框保留
        _image(os.path.join(y, "images", "train", "bad.jpg"), seed=101)
        _write(os.path.join(y, "labels", "train", "bad.txt"),
               "0 1.5 0.5 0.2 0.2\n0 0.5 0.5 0 0.2\n9 0.5 0.5 0.2 0.2\n0 0.5\n1 0.5 0.5 0.2 0.2\n")
        # 与 y0 字节完全相同的副本 → md5 去重
        shutil.copy(os.path.join(y, "images", "train", "y0.jpg"), os.path.join(y, "images", "train", "dup.jpg"))
        shutil.copy(os.path.join(y, "labels", "train", "y0.txt"), os.path.join(y, "labels", "train", "dup.txt"))

        # --- VOC 源：两张图，像素坐标
        v = os.path.join(self.raw, "src_voc")
        for i in range(2):
            _image(os.path.join(v, f"v{i}.jpg"), seed=200 + i, size=(100, 50))
            _write(os.path.join(v, f"v{i}.xml"),
                   "<annotation><filename>v%d.jpg</filename><size><width>100</width><height>50</height></size>"
                   "<object><name>tomato</name><bndbox><xmin>10</xmin><ymin>5</ymin><xmax>30</xmax><ymax>25</ymax></bndbox></object>"
                   "<object><name>pumpkin</name><bndbox><xmin>1</xmin><ymin>1</ymin><xmax>9</xmax><ymax>9</ymax></bndbox></object>"
                   "</annotation>" % i)

        self.out = os.path.join(self.tmp, "out")
        self.reports = os.path.join(self.tmp, "reports")

    def build(self, **kw):
        args = dict(sources=["src_yolo", "src_voc"], raw_root=self.raw, out=self.out,
                    classes_path=self.classes_path, split=(0.8, 0.1, 0.1), seed=42,
                    yaml_path=os.path.join(self.tmp, "data.yaml"), reports_dir=self.reports)
        args.update(kw)
        return pd.build_dataset(**args)


class AdapterTest(Fixture):
    def test_yolo_adapter_returns_pixel_boxes(self):
        samples = {os.path.basename(s.image): s for s in yolo.iter_samples(os.path.join(self.raw, "src_yolo"))}
        s = samples["y1.jpg"]
        self.assertEqual((s.width, s.height), (64, 48))
        name, x1, y1, x2, y2 = s.boxes[0]
        self.assertEqual(name, "Tomato")
        self.assertAlmostEqual(x1, 0.4 * 64)
        self.assertAlmostEqual(y2, 0.6 * 48)

    def test_yolo_adapter_counts_bad_lines(self):
        s = next(s for s in yolo.iter_samples(os.path.join(self.raw, "src_yolo")) if s.image.endswith("bad.jpg"))
        self.assertEqual(len(s.boxes), 1)
        self.assertEqual(s.corrupt, 4)

    def test_yolo_adapter_keeps_boxes_with_rounding_overshoot(self):
        # LVIS 的标注里有 cy - h/2 = -2.6e-6 这样的浮点误差，框本身是合法的，应裁剪到边界后保留
        d = os.path.join(self.tmp, "overshoot")
        _image(os.path.join(d, "images", "a.jpg"), seed=501)
        _write(os.path.join(d, "data.yaml"), "names: [onion]\n")
        _write(os.path.join(d, "labels", "a.txt"),
               "0 0.38580555555555557 0.10069270833333334 0.3271574074074074 0.20139062500000002\n"
               "0 0.5198333333333333 0.952234375 0.14780555555555555 0.09553645833333334\n"
               "0 0.5 0.5 0.2 0.2\n0 0.95 0.5 0.2 0.2\n")  # 最后一行越界 0.05，仍是坏框
        s = next(yolo.iter_samples(d))
        self.assertEqual((len(s.boxes), s.corrupt), (3, 1))
        _, x1, y1, x2, y2 = s.boxes[0]
        self.assertEqual(y1, 0.0)
        self.assertEqual(s.boxes[1][4], s.height)

    def test_yolo_adapter_handles_utf8_bom(self):
        # 有的数据集（如 HF afshin-dini/Egg-Detection）标注文件带 BOM，首行类别号会读成 '﻿0'
        d = os.path.join(self.tmp, "bom")
        _image(os.path.join(d, "images", "a.jpg"), seed=500)
        _write(os.path.join(d, "data.yaml"), "names: [egg]\n")
        os.makedirs(os.path.join(d, "labels"), exist_ok=True)
        with open(os.path.join(d, "labels", "a.txt"), "w", encoding="utf-8-sig") as f:  # 写入时带 BOM
            f.write("0 0.5 0.5 0.2 0.2\n0 0.3 0.3 0.1 0.1\n")
        s = next(yolo.iter_samples(d))
        self.assertEqual((len(s.boxes), s.corrupt), (2, 0))

    def test_coco_adapter_and_format_detection(self):
        d = os.path.join(self.tmp, "coco_src", "train")
        _image(os.path.join(d, "c0.jpg"), seed=600, size=(100, 50))
        coco = {"images": [{"id": 7, "file_name": "c0.jpg", "width": 100, "height": 50}],
                "categories": [{"id": 1, "name": "rui"}, {"id": 2, "name": "katla"}],
                "annotations": [{"image_id": 7, "category_id": 1, "bbox": [10, 5, 20, 20]},
                                {"image_id": 7, "category_id": 2, "bbox": [50, 10, 0, 5]}]}  # 第二个框宽度为 0
        _write(os.path.join(d, "_annotations.coco.json"), json.dumps(coco))
        root = os.path.join(self.tmp, "coco_src")
        self.assertEqual(detect_format(root), "coco")
        s = next(coco_adapter.iter_samples(root))
        self.assertEqual(s.boxes, [("rui", 10.0, 5.0, 30.0, 25.0)])
        self.assertEqual(s.corrupt, 1)

    def test_voc_adapter(self):
        samples = list(voc.iter_samples(os.path.join(self.raw, "src_voc")))
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0].boxes[0], ("tomato", 10.0, 5.0, 30.0, 25.0))


class BuildTest(Fixture):
    def test_summary_fields_and_counts(self):
        summary = self.build()
        for key in ("images", "per_class", "per_class_images", "sources", "corrupt",
                    "duplicates_removed", "cross_split_duplicates"):
            self.assertIn(key, summary)
        # 20 张 y* + bad + 2 张 voc = 23；dup 被 md5 去重，only_watermelon 映射后无框被丢弃
        self.assertEqual(sum(summary["images"].values()), 23)
        self.assertEqual(summary["duplicates_removed"], 1)
        self.assertEqual(summary["dropped_no_boxes"], 1)
        self.assertEqual(summary["corrupt"], 4)
        self.assertEqual(summary["corrupt_by_source"], {"src_yolo": 4})  # 原始标注中被丢弃的坏框出自哪个来源
        self.assertEqual(summary["cross_split_duplicates"], 0)
        total_tomato = sum(summary["per_class"][s].get("tomato", 0) for s in ("train", "val", "test"))
        self.assertEqual(total_tomato, 20 + 2)  # 每张 y* 1 个，voc 每张 1 个；bad.jpg 只剩 carrot

    def test_outputs_are_valid_yolo(self):
        self.build()
        for split in ("train", "val", "test"):
            imgs = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(self.out, "images", split)))
            lbls = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(self.out, "labels", split)))
            self.assertEqual(imgs, lbls)
            for name in lbls:
                with open(os.path.join(self.out, "labels", split, name + ".txt"), encoding="utf-8") as f:
                    for line in f:
                        cls, *xywh = line.split()
                        self.assertIn(int(cls), (0, 1))
                        self.assertTrue(all(0 <= float(v) <= 1 for v in xywh))

    def test_data_yaml_names_match_classes(self):
        self.build()
        with open(os.path.join(self.tmp, "data.yaml"), encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["names"], ["tomato", "carrot"])
        self.assertEqual(os.path.normcase(data["path"]), os.path.normcase(os.path.abspath(self.out)))

    def test_split_is_deterministic(self):
        first = self.build()
        shutil.rmtree(self.out)
        second = self.build()
        self.assertEqual(first["split_files"], second["split_files"])

    def test_near_duplicates_stay_in_same_split(self):
        # 同一张图另存为 png：md5 不同、平均哈希相同 → 必须落在同一个 split
        y = os.path.join(self.raw, "src_yolo")
        Image.open(os.path.join(y, "images", "train", "y3.jpg")).save(os.path.join(y, "images", "train", "y3copy.png"))
        shutil.copy(os.path.join(y, "labels", "train", "y3.txt"), os.path.join(y, "labels", "train", "y3copy.txt"))
        summary = self.build()
        where = {f: s for s, files in summary["split_files"].items() for f in files}
        self.assertEqual(where["src_yolo_y3.jpg"], where["src_yolo_y3copy.png"])

    def test_no_split_puts_everything_in_val_and_freezes_halves(self):
        split_json = os.path.join(self.reports, "fridge_split.json")
        summary = self.build(sources=["src_yolo"], no_split=True, split_json=split_json)
        self.assertEqual(set(summary["images"]), {"val"})
        with open(split_json, encoding="utf-8") as f:
            halves = json.load(f)
        self.assertEqual(len(set(halves["ft"]) & set(halves["eval"])), 0)
        self.assertEqual(len(halves["ft"]) + len(halves["eval"]), summary["images"]["val"])
        # 已存在的划分文件不允许被覆盖
        shutil.rmtree(self.out)
        with self.assertRaises(SystemExit):
            self.build(sources=["src_yolo"], no_split=True, split_json=split_json)

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.build(sources=["not_a_source"])

    def _add_dense_and_pile_images(self):
        """dense：5 个极小的番茄框（每个面积占比 0.0004）；pile：5 个大框（每个 0.09）。"""
        y = os.path.join(self.raw, "src_yolo")
        _image(os.path.join(y, "images", "train", "dense.jpg"), seed=300)
        _write(os.path.join(y, "labels", "train", "dense.txt"),
               "".join(f"0 {0.1 + i * 0.15:.2f} 0.5 0.02 0.02\n" for i in range(5)))
        _image(os.path.join(y, "images", "train", "pile.jpg"), seed=301)
        _write(os.path.join(y, "labels", "train", "pile.txt"),
               "".join(f"0 {0.2 + i * 0.15:.2f} 0.5 0.3 0.3\n" for i in range(5)))

    def test_dense_small_filter_drops_only_dense_small_images(self):
        self._add_dense_and_pile_images()
        summary = self.build(dense_sources=["src_yolo"], dense_min_boxes=5, dense_max_median_area=0.002)
        files = {f for fs in summary["split_files"].values() for f in fs}
        self.assertNotIn("src_yolo_dense.jpg", files)
        self.assertIn("src_yolo_pile.jpg", files)
        self.assertEqual(summary["filtered"]["dense"], {"src_yolo": 1})

    def test_dense_filter_only_applies_to_listed_sources(self):
        self._add_dense_and_pile_images()
        summary = self.build(dense_sources=["src_voc"], dense_min_boxes=5, dense_max_median_area=0.002)
        files = {f for fs in summary["split_files"].values() for f in fs}
        self.assertIn("src_yolo_dense.jpg", files)

    def test_identical_boxes_in_one_image_are_written_once(self):
        # 有的来源（mendeley、vvrh5、openimages）一张图里有完全相同的框，Ultralytics 加载时会去重，
        # 这里先去掉，统计里的框数才不会虚高
        _write(os.path.join(self.raw, "src_yolo", "labels", "train", "y2.txt"),
               "0 0.5 0.5 0.2 0.2\n0 0.5 0.5 0.2 0.2\n1 0.3 0.3 0.1 0.1\n0 0.5 0.5 0.2 0.2\n")
        summary = self.build()
        split = next(s for s, files in summary["split_files"].items() if "src_yolo_y2.jpg" in files)
        with open(os.path.join(self.out, "labels", split, "src_yolo_y2.txt"), encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 2)  # tomato 一个、carrot 一个
        self.assertEqual(summary["duplicate_boxes_removed"], 2)

    def test_low_classes_uses_the_shared_threshold(self):
        # 1.8 的门槛只定义在一处（MIN_TRAIN_BOXES），统计输出、分布图的虚线、验收命令都用它
        per_class = {"train": {"a": pd.MIN_TRAIN_BOXES - 1, "b": pd.MIN_TRAIN_BOXES, "c": 0}}
        self.assertEqual(pd.low_classes(per_class), {"a": pd.MIN_TRAIN_BOXES - 1, "c": 0})

    def test_preview_draws_requested_number_of_samples(self):
        self.build()
        out_dir = os.path.join(self.tmp, "preview")
        pd.preview(self.out, 5, out_dir, classes_path=self.classes_path)
        files = os.listdir(out_dir)
        self.assertEqual(len(files), 5)
        self.assertTrue(all(f.split("_")[0] in pd.SPLITS and f.endswith(".jpg") for f in files))
        self.assertEqual(sorted(files), sorted(os.listdir(self._preview_again())))  # 固定种子，两次抽到同样的图

    def _preview_again(self):
        out_dir = os.path.join(self.tmp, "preview2")
        pd.preview(self.out, 5, out_dir, classes_path=self.classes_path)
        return out_dir

    def test_preview_of_empty_dataset_is_an_error(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(os.path.join(empty, "labels", "train"))
        with self.assertRaises(SystemExit):
            pd.preview(empty, 3, os.path.join(self.tmp, "p"), classes_path=self.classes_path)

    def test_exclude_list_drops_listed_images(self):
        listing = os.path.join(self.tmp, "exclude.txt")
        _write(listing, "# 注释行\ny1\ny2\n\n")
        summary = self.build(exclude_lists={"src_yolo": [listing]})
        files = {f for fs in summary["split_files"].values() for f in fs}
        self.assertNotIn("src_yolo_y1.jpg", files)
        self.assertNotIn("src_yolo_y2.jpg", files)
        self.assertIn("src_yolo_y5.jpg", files)
        self.assertEqual(summary["filtered"]["excluded_list"], {"src_yolo": 2})

    def test_exclude_list_uses_first_column_only(self):
        # clip_filter.py 写出的清单每行是"图片主干<TAB>概率"
        listing = os.path.join(self.tmp, "cooked.txt")
        _write(listing, "# 注释\ny3\t0.120\ny4\t0.300\n")
        summary = self.build(exclude_lists={"src_yolo": [listing]})
        files = {f for fs in summary["split_files"].values() for f in fs}
        self.assertNotIn("src_yolo_y3.jpg", files)
        self.assertNotIn("src_yolo_y4.jpg", files)

    def test_multiple_exclude_lists_for_one_source_are_merged(self):
        # 同一来源可有多份清单：CLIP 自动生成的一份，人工复核的一份（重跑 CLIP 不会覆盖人工结果）
        auto, manual = os.path.join(self.tmp, "auto.txt"), os.path.join(self.tmp, "manual.txt")
        _write(auto, "y1\t0.1\n")
        _write(manual, "y2  熟肉\ny1  重复也没关系\n")
        summary = self.build(exclude_lists={"src_yolo": [auto, manual]})
        files = {f for fs in summary["split_files"].values() for f in fs}
        self.assertNotIn("src_yolo_y1.jpg", files)
        self.assertNotIn("src_yolo_y2.jpg", files)
        self.assertEqual(summary["filtered"]["excluded_list"], {"src_yolo": 2})

    def test_missing_exclude_list_is_an_error(self):
        with self.assertRaises(SystemExit):
            self.build(exclude_lists={"src_yolo": [os.path.join(self.tmp, "nope.txt")]})

    def test_train_only_source_never_reaches_val_or_test(self):
        summary = self.build(train_only=["src_voc"])
        for split in ("val", "test"):
            self.assertFalse(any(f.startswith("src_voc_") for f in summary["split_files"][split]))
        self.assertEqual(summary["sources"]["train"].get("src_voc"), 2)


class GroupKeyTest(unittest.TestCase):
    def test_roboflow_augmented_copies_share_a_group(self):
        a = pd.group_key("src", "apple_1_png.rf.0a1b.jpg")
        b = pd.group_key("src", "apple_1_png.rf.9f8e.jpg")
        self.assertEqual(a, b)
        self.assertNotEqual(a, pd.group_key("src", "apple_2_png.rf.0a1b.jpg"))

    def test_frames_of_one_video_share_a_group(self):
        a = pd.group_key("src", "VID_20250228_124329_mp4-0010_jpg.rf.eefb.jpg")
        b = pd.group_key("src", "VID_20250228_124329_mp4-0057_jpg.rf.97a9.jpg")
        self.assertEqual(a, b)
        self.assertNotEqual(a, pd.group_key("src", "VID_20250301_090000_mp4-0010_jpg.rf.eefb.jpg"))

    def test_groups_are_per_source(self):
        self.assertNotEqual(pd.group_key("a", "x.jpg"), pd.group_key("b", "x.jpg"))


if __name__ == "__main__":
    unittest.main()
