# -*- coding: utf-8 -*-
"""从 Open Images V7 按类别下载检测子集，输出为 YOLO 格式（可直接作为 prepare_dataset 的数据源）。

标注 CSV 放在 --meta 目录（training/datasets/raw/_openimages_meta），需事先下载：
    class-descriptions-boxable.csv   https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions-boxable.csv
    train-annotations-bbox.csv       https://storage.googleapis.com/openimages/v6/oidv6-train-annotations-bbox.csv
    validation-annotations-bbox.csv  https://storage.googleapis.com/openimages/v5/validation-annotations-bbox.csv
    test-annotations-bbox.csv        https://storage.googleapis.com/openimages/v5/test-annotations-bbox.csv
图片从 https://open-images-dataset.s3.amazonaws.com/<split>/<ImageID>.jpg 下载（国内可直连）。

选图规则：
- 含"群组框"（IsGroupOf=1，一个框框住一群物体）或"非实物描绘"（IsDepiction=1，画作/卡通）的图整张不要；
- 每个类别按固定种子随机抽取至多 --per-class 张；被选中的图里所有目标类别的框都写入标注。

用法（项目根目录、venv 中）：
    python training/download_openimages.py --classes Egg Mango Milk Shrimp --per-class 800
    python training/download_openimages.py --classes Egg --per-class 800 --dry-run
"""
import argparse
import csv
import io
import json
import os
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_META = os.path.join(ROOT, "training", "datasets", "raw", "_openimages_meta")
DEFAULT_OUT = os.path.join(ROOT, "training", "datasets", "raw", "openimages")
SPLIT_FILES = {"train": "train-annotations-bbox.csv",
               "validation": "validation-annotations-bbox.csv",
               "test": "test-annotations-bbox.csv"}
IMAGE_URL = "https://open-images-dataset.s3.amazonaws.com/{split}/{image_id}.jpg"


def _class_mids(meta, names):
    with open(os.path.join(meta, "class-descriptions-boxable.csv"), encoding="utf-8") as f:
        by_name = {row[1]: row[0] for row in csv.reader(f) if len(row) >= 2}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        sys.exit(f"Open Images 中没有这些可框选类别：{unknown}（类名区分大小写，见 class-descriptions-boxable.csv）")
    return {by_name[n]: n for n in names}


def select_images(meta, names, per_class, seed):
    """返回 {ImageID: {"split": ..., "boxes": [(类名, XMin, YMin, XMax, YMax), ...]}}。"""
    mids = _class_mids(meta, names)
    images, excluded = {}, set()
    for split, fn in SPLIT_FILES.items():
        path = os.path.join(meta, fn)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            col = {name: i for i, name in enumerate(next(reader))}
            i_id, i_lab = col["ImageID"], col["LabelName"]
            i_box = [col[k] for k in ("XMin", "YMin", "XMax", "YMax")]
            i_grp, i_dep = col["IsGroupOf"], col["IsDepiction"]
            for row in reader:
                name = mids.get(row[i_lab])
                if name is None:
                    continue
                image_id = row[i_id]
                if row[i_grp] == "1" or row[i_dep] == "1":
                    excluded.add(image_id)
                    continue
                entry = images.setdefault(image_id, {"split": split, "boxes": []})
                entry["boxes"].append((name, *(float(row[i]) for i in i_box)))
    for image_id in excluded:
        images.pop(image_id, None)

    by_class = defaultdict(list)
    for image_id, entry in images.items():
        for name in {b[0] for b in entry["boxes"]}:
            by_class[name].append(image_id)
    chosen = set()
    for name in names:
        candidates = sorted(by_class[name])
        random.Random(f"{seed}:{name}").shuffle(candidates)
        chosen.update(candidates[:per_class])
    return {i: images[i] for i in sorted(chosen)}


def yolo_lines(boxes, names):
    index = {n: i for i, n in enumerate(names)}
    lines = []
    for name, x1, y1, x2, y2 in boxes:
        lines.append(f"{index[name]} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}")
    return lines


def _download(job):
    """下载一张图（已存在则跳过），长边超过 max_side 时缩小后保存。返回 (ImageID, 错误信息或 None)。"""
    import requests
    from PIL import Image

    image_id, split, target, max_side = job
    if os.path.exists(target):
        return image_id, None
    url = IMAGE_URL.format(split=split, image_id=image_id)
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with Image.open(io.BytesIO(resp.content)) as im:
                if max(im.size) > max_side:
                    im = im.convert("RGB")
                    im.thumbnail((max_side, max_side))
                    im.save(target + ".part", "JPEG", quality=90)
                else:
                    with open(target + ".part", "wb") as f:
                        f.write(resp.content)
            os.replace(target + ".part", target)
            return image_id, None
        except Exception as exc:  # 网络抖动重试，最终失败记入清单
            error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
    return image_id, error


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--classes", nargs="+", required=True, help="Open Images 类名（区分大小写），如 Egg Mango")
    parser.add_argument("--per-class", type=int, default=800)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--meta", default=DEFAULT_META)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--max-side", type=int, default=1280)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--dry-run", action="store_true", help="只统计将要下载的图片数，不下载")
    args = parser.parse_args()

    started = time.time()
    chosen = select_images(args.meta, args.classes, args.per_class, args.seed)
    per_class = {n: sum(1 for e in chosen.values() if any(b[0] == n for b in e["boxes"])) for n in args.classes}
    boxes = {n: sum(1 for e in chosen.values() for b in e["boxes"] if b[0] == n) for n in args.classes}
    print(f"选中 {len(chosen)} 张图；各类图片数 {per_class}；各类框数 {boxes}")
    if args.dry_run:
        return

    jobs = []
    for image_id, entry in chosen.items():
        for kind in ("images", "labels"):
            os.makedirs(os.path.join(args.out, kind, entry["split"]), exist_ok=True)
        with open(os.path.join(args.out, "labels", entry["split"], image_id + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(yolo_lines(entry["boxes"], args.classes)) + "\n")
        jobs.append((image_id, entry["split"], os.path.join(args.out, "images", entry["split"], image_id + ".jpg"),
                     args.max_side))

    failures = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for n, (image_id, error) in enumerate(pool.map(_download, jobs), 1):
            if error:
                failures[image_id] = error
            if n % 200 == 0 or n == len(jobs):
                print(f"  已处理 {n}/{len(jobs)}，失败 {len(failures)}", flush=True)
    for image_id in failures:  # 下载失败的图删除其标注，避免出现没有图片的标注
        split = chosen[image_id]["split"]
        os.remove(os.path.join(args.out, "labels", split, image_id + ".txt"))

    with open(os.path.join(args.out, "data.yaml"), "w", encoding="utf-8") as f:
        f.write("# 由 training/download_openimages.py 生成；names 为 Open Images 原始类名\nnames:\n")
        f.writelines(f"  {i}: {n}\n" for i, n in enumerate(args.classes))
    manifest = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "classes": args.classes,
                "per_class_limit": args.per_class, "seed": args.seed, "max_side": args.max_side,
                "selected_images": len(chosen), "downloaded_images": len(chosen) - len(failures),
                "images_per_class": per_class, "boxes_per_class": boxes, "failures": failures,
                "excluded_rule": "IsGroupOf=1 或 IsDepiction=1 的图片整张排除",
                "license": "标注 CC BY 4.0；图片 CC BY 2.0（Open Images V7）",
                "elapsed_seconds": round(time.time() - started, 1)}
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"完成：下载 {manifest['downloaded_images']} 张，失败 {len(failures)} 张，清单见 {args.out}\\manifest.json")


if __name__ == "__main__":
    main()
