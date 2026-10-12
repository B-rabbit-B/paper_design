# -*- coding: utf-8 -*-
"""从 LVIS v1 全量标注中提取指定类别（默认牛肉、牛奶），下载对应的 COCO 图片，输出 YOLO 格式。

LVIS 果蔬子集里没有牛肉和牛奶，而 LVIS v1 全量标注（CC BY 4.0）里有。标注 JSON 解压后超过 1 GB，
这里用 ijson 流式解析，只保留需要的条目，内存占用很小。

排除规则（与 lvis_processed_food.py 的思路一致）：
- 熟食场景：图中标有 PROCESSED 中任一类别（披萨、三明治、汉堡、香肠、各种蛋糕、甜甜圈、叉、勺、
  熟牛排、牛排刀等）的，整张排除；
- 漏标：LVIS 是联合标注，每张图会列出"没有标全"的类别（not_exhaustive_category_ids）。
  目标类别在其中的图整张排除，避免未标出的同类物体在训练时被当作背景。

用法（项目根目录；需要 ijson，用 uv 临时安装，不进项目 venv）：
    1. 下载 https://dl.fbaipublicfiles.com/LVIS/lvis_v1_train.json.zip 和 lvis_v1_val.json.zip
       到 training/datasets/raw/_lvis_full_meta/
    2. uv run --no-project --with ijson --with requests python training/download_lvis_full.py
"""
import argparse
import json
import os
import sys
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")
META = os.path.join(RAW, "_lvis_full_meta")
# LVIS v1 的实际类名（与 COCO 不同：没有 hotdog，蛋糕、勺子分成多个类）。
# steak_(food) 在 LVIS 中基本是熟牛排，steak_knife 也提示正在吃牛排，所以一并作为熟食场景排除。
PROCESSED = ["pizza", "sandwich", "hamburger", "sausage", "burrito", "taco",
             "cake", "birthday_cake", "chocolate_cake", "wedding_cake", "cupcake", "doughnut",
             "fork", "spoon", "soupspoon", "steak_(food)", "steak_knife"]


def stream(zip_path, prefix):
    import ijson

    with zipfile.ZipFile(zip_path) as z, z.open(z.namelist()[0]) as f:
        yield from ijson.items(f, prefix, use_float=True)


def main():
    import requests

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--categories", nargs="+", default=["beef_(food)", "milk"], help="LVIS 类名")
    parser.add_argument("--out", default=os.path.join(RAW, "lvis_full"))
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    started = time.time()

    for split, zip_name in (("train", "lvis_v1_train.json.zip"), ("val", "lvis_v1_val.json.zip")):
        zip_path = os.path.join(META, zip_name)
        cats = {c["name"]: c["id"] for c in stream(zip_path, "categories.item")}
        missing = [c for c in args.categories + PROCESSED if c not in cats]
        if missing:
            sys.exit(f"LVIS 中没有这些类别：{missing}")
        target = {cats[c]: i for i, c in enumerate(args.categories)}
        processed_ids = {cats[c] for c in PROCESSED}

        boxes, processed_images = defaultdict(list), set()
        for a in stream(zip_path, "annotations.item"):
            if a["category_id"] in target:
                boxes[a["image_id"]].append((target[a["category_id"]], a["bbox"]))
            elif a["category_id"] in processed_ids:
                processed_images.add(a["image_id"])

        stats = Counter()
        jobs = []
        for img in stream(zip_path, "images.item"):
            if img["id"] not in boxes:
                continue
            if img["id"] in processed_images:
                stats["excluded_processed"] += 1
                continue
            if set(img.get("not_exhaustive_category_ids", [])) & set(target):
                stats["excluded_not_exhaustive"] += 1
                continue
            jobs.append((img, boxes[img["id"]]))
        print(f"[{split}] 含目标类别的图 {len(boxes)}，排除熟食场景 {stats['excluded_processed']}，"
              f"排除未标全 {stats['excluded_not_exhaustive']}，保留 {len(jobs)}", flush=True)

        for kind in ("images", "labels"):
            os.makedirs(os.path.join(args.out, kind, split), exist_ok=True)

        def work(job):
            img, items = job
            stem = f"{img['id']:012d}"
            path = os.path.join(args.out, "images", split, stem + ".jpg")
            if not os.path.exists(path):
                for attempt in range(3):
                    try:
                        r = requests.get(img["coco_url"], timeout=60)
                        r.raise_for_status()
                        with open(path + ".part", "wb") as f:
                            f.write(r.content)
                        os.replace(path + ".part", path)
                        break
                    except Exception as exc:
                        if attempt == 2:
                            return stem, f"{type(exc).__name__}: {exc}"
                        time.sleep(2 * (attempt + 1))
            w, h = float(img["width"]), float(img["height"])
            with open(os.path.join(args.out, "labels", split, stem + ".txt"), "w", encoding="utf-8") as f:
                for cls, (x, y, bw, bh) in items:
                    f.write(f"{cls} {(x + bw / 2) / w:.6f} {(y + bh / 2) / h:.6f} {bw / w:.6f} {bh / h:.6f}\n")
            return stem, None

        failures = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for stem, error in pool.map(work, jobs):
                if error:  # 图片下载失败的，删掉其标注，避免出现没有图片的标注
                    failures[stem] = error
                    label = os.path.join(args.out, "labels", split, stem + ".txt")
                    if os.path.exists(label):
                        os.remove(label)
        per_class = Counter(args.categories[c] for _, items in jobs for c, _ in items)
        print(f"[{split}] 下载 {len(jobs) - len(failures)} 张，失败 {len(failures)}；各类框数 {dict(per_class)}", flush=True)
        with open(os.path.join(args.out, f"manifest_{split}.json"), "w", encoding="utf-8") as f:
            json.dump({"categories": args.categories, "processed_rule": PROCESSED, "kept_images": len(jobs),
                       "boxes_per_class": dict(per_class), "excluded": dict(stats), "failures": failures,
                       "license": "LVIS 标注 CC BY 4.0；COCO 图片按 Flickr 原始许可"}, f, ensure_ascii=False, indent=2)

    with open(os.path.join(args.out, "data.yaml"), "w", encoding="utf-8") as f:
        f.write("# 由 training/download_lvis_full.py 生成；names 为 LVIS 原始类名\nnames:\n")
        f.writelines(f"  {i}: {c}\n" for i, c in enumerate(args.categories))
    print(f"完成，用时 {time.time() - started:.0f} 秒")


if __name__ == "__main__":
    main()
