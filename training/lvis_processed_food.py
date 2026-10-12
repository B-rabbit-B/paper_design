# -*- coding: utf-8 -*-
"""生成 LVIS 子集中"熟食、加工食品场景"图片的排除清单，供 prepare_dataset.py 使用。

LVIS 的图片来自 COCO 2017，文件名主干就是 COCO 图片编号（例如 000000186476）。LVIS 本身没有
"切碎、熟制"这类属性，但 COCO 标注了披萨、热狗、三明治、蛋糕、甜甜圈等熟食类别，以及叉、勺等餐具。
一张图里出现这些类别时，被标注的西红柿、蘑菇、甜椒、草莓等大多是配料、装饰或盘中的熟菜，
而不是本项目要识别的完整生鲜食材，所以整张排除。

类别的选择依据 2026-10-12 的抽样核对（每组随机 10 张）：
- 含熟食类别的：10/10 是加工食材场景（三明治、披萨、拼盘、蛋糕等）；
- 不含熟食、但含叉或勺的：10/10 是熟菜餐盘、饭盒、餐厅场景；
- 只含刀的：混有案板上的整根胡萝卜、整个苹果等目标场景，因此"刀"不作为排除条件。

用法（项目根目录、venv 中）：
    1. 下载 COCO 2017 标注包（约 253 MB）到 training/datasets/raw/_coco_meta/：
       http://images.cocodataset.org/annotations/annotations_trainval2017.zip
    2. python training/lvis_processed_food.py
       可用 --categories 指定类别（COCO 英文类名），默认 sandwich "hot dog" pizza donut cake fork spoon
输出：training/reports/dataset/lvis_processed_food.txt（入库，保证可复现）
"""
import argparse
import json
import os
import time
import zipfile
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")
DEFAULT_ZIP = os.path.join(RAW, "_coco_meta", "annotations_trainval2017.zip")
DEFAULT_OUT = os.path.join(ROOT, "training", "reports", "dataset", "lvis_processed_food.txt")
DEFAULT_CATEGORIES = ["sandwich", "hot dog", "pizza", "donut", "cake", "fork", "spoon"]


def coco_categories_by_image(zip_path):
    """返回 ({图片编号: {COCO 类名, ...}}, {类名: 类别 id})，合并 train2017 与 val2017。"""
    by_image = defaultdict(set)
    names = {}
    with zipfile.ZipFile(zip_path) as z:
        for member in ("annotations/instances_train2017.json", "annotations/instances_val2017.json"):
            with z.open(member) as f:
                data = json.load(f)
            names.update({c["id"]: c["name"] for c in data["categories"]})
            for ann in data["annotations"]:
                by_image[ann["image_id"]].add(names[ann["category_id"]])
            del data
    return by_image, {v: k for k, v in names.items()}


def lvis_image_ids(lvis_dir):
    """LVIS 子集中文件名为 COCO 编号的图片：{编号: 文件名主干}。人工标注的测试图（非数字文件名）不在其中。"""
    ids = {}
    for split in os.listdir(os.path.join(lvis_dir, "images")):
        for fn in os.listdir(os.path.join(lvis_dir, "images", split)):
            stem = os.path.splitext(fn)[0]
            if stem.isdigit():
                ids[int(stem)] = stem
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--coco-zip", default=DEFAULT_ZIP)
    parser.add_argument("--lvis-dir", default=os.path.join(RAW, "lvis"))
    parser.add_argument("--categories", nargs="+", default=DEFAULT_CATEGORIES)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    by_image, name_to_id = coco_categories_by_image(args.coco_zip)
    unknown = [c for c in args.categories if c not in name_to_id]
    if unknown:
        raise SystemExit(f"COCO 中没有这些类别：{unknown}")
    lvis = lvis_image_ids(args.lvis_dir)
    wanted = set(args.categories)
    hits = sorted(stem for image_id, stem in lvis.items() if by_image.get(image_id, set()) & wanted)
    per_category = Counter(c for image_id in lvis for c in by_image.get(image_id, set()) & wanted)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# 由 training/lvis_processed_food.py 生成，{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 规则：COCO 2017 标注中含以下任一类别的 LVIS 图片整张排除：{', '.join(args.categories)}\n")
        f.write(f"# LVIS 中可对应到 COCO 编号的图片 {len(lvis)} 张，命中 {len(hits)} 张；各类别命中图片数："
                f"{dict(per_category.most_common())}\n")
        f.writelines(stem + "\n" for stem in hits)
    print(f"LVIS 可对应 COCO 的图片 {len(lvis)} 张，命中 {len(hits)} 张，各类别 {dict(per_category.most_common())}")
    print(f"清单已写入 {args.out}")


if __name__ == "__main__":
    main()
