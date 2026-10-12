# -*- coding: utf-8 -*-
"""多源数据集合并：类别映射 → md5 去重 → 近重复分组 → 分层划分 → 写出 YOLO 格式与统计。

设计见 docs/plan/01 §7 与总纲阶段 1。在项目根目录、venv 中运行：

    python training/prepare_dataset.py --check-classes
    python training/prepare_dataset.py --sources lvis zenodo mendeley openimages
    python training/prepare_dataset.py --sources custom --no-split --out training/datasets/fridge_test
    python training/prepare_dataset.py --preview 20 --out training/reports/dataset/samples

数据源 = training/datasets/raw/ 下的一个子目录，格式（YOLO / VOC）自动识别；
它的类名在 training/classes.yaml 各类的 sources.<子目录名> 中声明。

防止数据泄漏的做法：
- 同一张原图的 Roboflow 增强副本、同一段视频抽出的帧、平均哈希相同的近重复图，归为一组，同组只进同一个子集；
- --train-only 指定的来源（默认 mendeley：3534 张图只来自 10 段视频）全部放入训练集，不参与验证和测试。
"""
import argparse
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import config  # noqa: E402
from core import food_classes  # noqa: E402
from sources import detect_format, voc, yolo  # noqa: E402

ADAPTERS = {"yolo": yolo.iter_samples, "voc": voc.iter_samples}
SPLITS = ("train", "val", "test")
MARKER = ".prepare_dataset"  # 本脚本生成的目录里才有这个文件；没有它的非空目录拒绝清空
DEGENERATE_HASHES = {0, (1 << 64) - 1}  # 纯色图的平均哈希，不能用来判定近重复

DEFAULT_RAW = os.path.join(ROOT, "training", "datasets", "raw")
DEFAULT_OUT = os.path.join(ROOT, "training", "datasets", "yolo")
DEFAULT_REPORTS = os.path.join(ROOT, "training", "reports", "dataset")
# LVIS 中含熟食场景的图片清单（由 training/lvis_processed_food.py 依据 COCO 标注生成）
DEFAULT_LVIS_EXCLUDE = os.path.join(DEFAULT_REPORTS, "lvis_processed_food.txt")

_RF_SUFFIX = re.compile(r"\.rf\.[0-9a-fA-F]+$")
_VIDEO_FRAME = re.compile(r"^(.*_(?:mp4|mov|avi))-\d+(?:_jpe?g|_png)?$", re.IGNORECASE)


def group_key(source, filename):
    """近重复分组键：去掉 Roboflow 增强后缀 .rf.<hash>，视频帧只保留视频名。分组按来源隔离。"""
    stem = _RF_SUFFIX.sub("", os.path.splitext(filename)[0])
    match = _VIDEO_FRAME.match(stem)
    if match:
        stem = match.group(1)
    return f"{source}:{stem}"


def _hashes(path):
    """返回 (md5, 64 位平均哈希)。JPEG 用 draft 按比例解码，大图也很快。"""
    with open(path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    with Image.open(path) as im:
        im.draft("RGB", (64, 64))
        pixels = list(im.convert("L").resize((8, 8), Image.BILINEAR).tobytes())
    mean = sum(pixels) / len(pixels)
    return md5, sum(1 << i for i, p in enumerate(pixels) if p > mean)


# ---------------------------------------------------------------- 收集与映射
def _is_dense_small(sample, min_boxes, max_median_area):
    """某个来源类别在图中有至少 min_boxes 个框，且这些框面积占整图比例的中位数小于 max_median_area。

    用全部来源类别判断（包括没有映射到 33 类的），因为它衡量的是这张图的标注方式：
    切碎、加工后的食材（沙拉里的胡萝卜丝、披萨上的配料）和远景市场，都表现为同类框又多又小。
    """
    image_area = float(sample.width * sample.height)
    areas = defaultdict(list)
    for name, x1, y1, x2, y2 in sample.boxes:
        areas[name].append((x2 - x1) * (y2 - y1) / image_area)
    return any(len(v) >= min_boxes and statistics.median(v) < max_median_area for v in areas.values())


def _display_path(path):
    """项目内的路径记成相对路径；跨盘符（Windows 上 relpath 会报错）时保留原样。"""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def _read_exclude_list(path):
    if not os.path.exists(path):
        sys.exit(f"排除清单不存在：{path}")
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip() and not line.startswith("#")}


def _collect(sources, raw_root, classes, train_only, dense=None, excludes=None):
    """dense = {"sources": 集合, "min_boxes": N, "max_median_area": T}；excludes = {来源: 图片文件名主干集合}。"""
    dense = dense or {"sources": set()}
    excludes = excludes or {}
    records = []
    stats = {"corrupt": 0, "dropped_no_boxes": 0, "unmapped_boxes": defaultdict(Counter),
             "filtered_dense": Counter(), "filtered_excluded": Counter()}
    for source in sources:
        src_dir = os.path.join(raw_root, source)
        if not os.path.isdir(src_dir):
            sys.exit(f"数据源目录不存在：{src_dir}")
        fmt = detect_format(src_dir)
        if fmt is None:
            sys.exit(f"无法识别 {src_dir} 的标注格式（既没有 .xml，也没有 labels/ 下的 .txt）")
        smap = food_classes.source_map(classes, source)
        if not smap:
            sys.exit(f"classes.yaml 中还没有任何类别声明来源 {source!r} 的类名，请先在各类的 sources.{source} 下填写")
        used = set()
        for sample in ADAPTERS[fmt](src_dir):
            stats["corrupt"] += sample.corrupt
            if os.path.splitext(os.path.basename(sample.image))[0] in excludes.get(source, ()):
                stats["filtered_excluded"][source] += 1
                continue
            if source in dense["sources"] and _is_dense_small(sample, dense["min_boxes"], dense["max_median_area"]):
                stats["filtered_dense"][source] += 1
                continue
            boxes = []
            for name, x1, y1, x2, y2 in sample.boxes:
                if name in smap:
                    boxes.append((smap[name], x1, y1, x2, y2))
                else:
                    stats["unmapped_boxes"][source][name] += 1
            if not boxes:
                stats["dropped_no_boxes"] += 1
                continue
            base = os.path.basename(sample.image)
            out_name, stem, ext, k = f"{source}_{base}", f"{source}_{os.path.splitext(base)[0]}", os.path.splitext(base)[1], 1
            while out_name.lower() in used:
                out_name, k = f"{stem}_{k}{ext}", k + 1
            used.add(out_name.lower())
            records.append({"source": source, "image": sample.image, "width": sample.width,
                            "height": sample.height, "boxes": boxes, "name": out_name,
                            "train_only": source in train_only, "group": group_key(source, base)})
    return records, stats


def _dedupe(records):
    with ThreadPoolExecutor(max_workers=8) as pool:
        hashes = list(pool.map(_hashes, [r["image"] for r in records]))
    seen, kept = set(), []
    for record, (md5, ahash) in zip(records, hashes):
        if md5 in seen:
            continue
        seen.add(md5)
        record["md5"], record["ahash"] = md5, ahash
        kept.append(record)
    return kept, len(records) - len(kept)


def _groups(records):
    """并查集：共享分组键或（非纯色的）平均哈希的图片归为同一组。"""
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first = {}
    for i, r in enumerate(records):
        keys = [r["group"]] + ([("ahash", r["ahash"])] if r["ahash"] not in DEGENERATE_HASHES else [])
        for key in keys:
            if key in first:
                parent[find(i)] = find(first[key])
            else:
                first[key] = i
    groups = defaultdict(list)
    for i, r in enumerate(records):
        groups[find(i)].append(r)
    return list(groups.values())


# ---------------------------------------------------------------- 划分
def _split(groups, ratios, seed):
    """以组为单位、按组内最稀有类别分层划分；含 train_only 图片的组整组进训练集。"""
    rng = random.Random(seed)
    freq = Counter(b[0] for g in groups for r in g for b in r["boxes"])
    assign, buckets = {}, defaultdict(list)
    for g in groups:
        if any(r["train_only"] for r in g):
            assign.update({r["name"]: "train" for r in g})
            continue
        rarest = min({b[0] for r in g for b in r["boxes"]}, key=lambda c: (freq[c], c))
        buckets[rarest].append(g)
    for cls in sorted(buckets):
        bucket = sorted(buckets[cls], key=lambda g: min(r["name"] for r in g))
        rng.shuffle(bucket)
        n_test, n_val = round(len(bucket) * ratios[2]), round(len(bucket) * ratios[1])
        for i, g in enumerate(bucket):
            split = "test" if i < n_test else "val" if i < n_test + n_val else "train"
            assign.update({r["name"]: split for r in g})
    return assign


def _halves(groups, seed):
    """自采集 50/50 固定划分（微调半集 ft / 评估半集 eval），以组为单位、按图片数贪心平衡。"""
    rng = random.Random(seed)
    ordered = sorted(groups, key=lambda g: min(r["name"] for r in g))
    rng.shuffle(ordered)
    halves = {"ft": [], "eval": []}
    for g in ordered:
        target = "ft" if len(halves["ft"]) <= len(halves["eval"]) else "eval"
        halves[target].extend(sorted(r["name"] for r in g))
    return halves


# ---------------------------------------------------------------- 写出
def _prepare_out(out):
    if os.path.exists(out):
        if os.listdir(out) and not os.path.exists(os.path.join(out, MARKER)):
            sys.exit(f"{out} 不是本脚本生成的目录，拒绝清空")
        shutil.rmtree(out)
    for kind in ("images", "labels"):
        for split in SPLITS:
            os.makedirs(os.path.join(out, kind, split))
    with open(os.path.join(out, MARKER), "w", encoding="utf-8") as f:
        f.write("generated by training/prepare_dataset.py\n")


def _write_record(record, split, out):
    shutil.copyfile(record["image"], os.path.join(out, "images", split, record["name"]))
    w, h = record["width"], record["height"]
    lines = []
    for cls, x1, y1, x2, y2 in record["boxes"]:
        cx, cy, bw, bh = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h
        lines.append(f"{cls} {min(max(cx, 0), 1):.6f} {min(max(cy, 0), 1):.6f} {min(bw, 1):.6f} {min(bh, 1):.6f}")
    stem = os.path.splitext(record["name"])[0]
    with open(os.path.join(out, "labels", split, stem + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _plot_distribution(per_class, names, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, max(4, len(names) * 0.32)))
    left = [0] * len(names)
    for split, color in zip(SPLITS, ("#4C78A8", "#F58518", "#54A24B")):
        values = [per_class[split].get(n, 0) for n in names]
        ax.barh(names, values, left=left, color=color, label=split)
        left = [a + b for a, b in zip(left, values)]
    for y, (name, total) in enumerate(zip(names, left)):  # 标出训练集框数，0 框类别标红
        train = per_class["train"].get(name, 0)
        ax.text(max(total, 1) * 1.05, y, str(train), va="center", fontsize=7,
                color="#D62728" if train < 200 else "#333333")
    ax.axvline(200, color="#D62728", linestyle="--", linewidth=1, label="200 (train threshold)")
    ax.set_xscale("symlog", linthresh=10)  # 对数刻度：类别间相差几百倍时，少数类也看得清
    ax.invert_yaxis()
    ax.set_xlabel("boxes (symlog scale; number = train boxes)")
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def build_dataset(sources, raw_root=DEFAULT_RAW, out=DEFAULT_OUT, classes_path=None, split=(0.8, 0.1, 0.1),
                  seed=42, yaml_path=None, reports_dir=DEFAULT_REPORTS, no_split=False, split_json=None,
                  train_only=(), dense_sources=(), dense_min_boxes=20, dense_max_median_area=0.002,
                  exclude_lists=None):
    """合并 sources 到 out，返回 summary 字典（同时写入 out/summary.json）。

    dense_sources 中的来源启用"密集小框"过滤；exclude_lists = {来源: 清单文件}，清单中的图片整张排除。
    """
    if no_split and split_json and os.path.exists(split_json):
        sys.exit(f"{split_json} 已存在。自采集的 50/50 划分一旦生成就不得修改（总纲 1.12），如确需重建请手动处理")
    started = time.time()
    classes = food_classes.load_classes(classes_path)
    names = classes["names"]
    excludes = {src: _read_exclude_list(path) for src, path in (exclude_lists or {}).items()}
    dense = {"sources": set(dense_sources), "min_boxes": dense_min_boxes, "max_median_area": dense_max_median_area}

    records, stats = _collect(sources, raw_root, classes, set(train_only), dense, excludes)
    records, duplicates_removed = _dedupe(records)
    groups = _groups(records)
    assign = {r["name"]: "val" for r in records} if no_split else _split(groups, split, seed)

    _prepare_out(out)
    for r in records:
        _write_record(r, assign[r["name"]], out)

    per_class = {s: {n: 0 for n in names} for s in SPLITS}
    per_class_images = {s: {n: 0 for n in names} for s in SPLITS}
    by_source = {s: Counter() for s in SPLITS}
    split_of_md5, split_of_ahash = defaultdict(set), defaultdict(set)
    for r in records:
        s = assign[r["name"]]
        for cls in (b[0] for b in r["boxes"]):
            per_class[s][names[cls]] += 1
        for cls in {b[0] for b in r["boxes"]}:
            per_class_images[s][names[cls]] += 1
        by_source[s][r["source"]] += 1
        split_of_md5[r["md5"]].add(s)
        if r["ahash"] not in DEGENERATE_HASHES:
            split_of_ahash[r["ahash"]].add(s)

    images = Counter(assign.values())
    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sources_used": list(sources),
        "train_only": sorted(train_only),
        "split_ratios": None if no_split else list(split),
        "seed": seed,
        "classes_version": classes["version"],
        "images": {s: images[s] for s in SPLITS if images[s]},
        "per_class": per_class,
        "per_class_images": per_class_images,
        "sources": {s: dict(by_source[s]) for s in SPLITS},
        "corrupt": stats["corrupt"],
        "duplicates_removed": duplicates_removed,
        "dropped_no_boxes": stats["dropped_no_boxes"],
        "filtered": {"dense": dict(stats["filtered_dense"]), "excluded_list": dict(stats["filtered_excluded"])},
        "filter_params": {"dense_sources": sorted(dense_sources), "dense_min_boxes": dense_min_boxes,
                          "dense_max_median_area": dense_max_median_area,
                          "exclude_lists": {s: _display_path(p) for s, p in (exclude_lists or {}).items()}},
        "cross_split_duplicates": sum(1 for v in split_of_md5.values() if len(v) > 1),
        "cross_split_near_duplicates": sum(1 for v in split_of_ahash.values() if len(v) > 1),
        "groups": len(groups),
        "unmapped_boxes": {src: dict(c.most_common()) for src, c in stats["unmapped_boxes"].items()},
        "elapsed_seconds": round(time.time() - started, 1),
        "split_files": {s: sorted(n for n, sp in assign.items() if sp == s) for s in SPLITS},
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    report_dir = os.path.join(reports_dir, os.path.basename(os.path.normpath(out)))
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in summary.items() if k != "split_files"}, f, ensure_ascii=False, indent=2)
    _plot_distribution(per_class, names, f"{os.path.basename(os.path.normpath(out))}: boxes per class",
                       os.path.join(report_dir, "class_distribution.png"))

    if yaml_path:
        rel = {s: ("images/val" if no_split else f"images/{s}") for s in SPLITS}
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("# 由 training/prepare_dataset.py 生成，请勿手改。path 是生成时的绝对路径，换机器后需重新生成。\n")
            yaml.safe_dump({"path": os.path.abspath(out), **rel, "names": names}, f, allow_unicode=True, sort_keys=False)

    if no_split and split_json:
        os.makedirs(os.path.dirname(split_json), exist_ok=True)
        with open(split_json, "w", encoding="utf-8") as f:
            json.dump({"seed": seed, **_halves(groups, seed)}, f, ensure_ascii=False, indent=2)
    return summary


# ---------------------------------------------------------------- 预览与类别校验
def preview(dataset, n, out_dir, seed=0, classes_path=None):
    """随机抽 n 张已生成的样本，画框后输出，用于人工抽检（总纲 1.9、1.11）。"""
    names = food_classes.load_classes(classes_path)["names"]
    labels = sorted(
        (split, f) for split in SPLITS if os.path.isdir(os.path.join(dataset, "labels", split))
        for f in os.listdir(os.path.join(dataset, "labels", split)) if f.endswith(".txt"))
    if not labels:
        sys.exit(f"{dataset} 下没有标注文件")
    os.makedirs(out_dir, exist_ok=True)
    for split, fn in random.Random(seed).sample(labels, min(n, len(labels))):
        stem = os.path.splitext(fn)[0]
        image = next(os.path.join(dataset, "images", split, f) for f in os.listdir(os.path.join(dataset, "images", split))
                     if os.path.splitext(f)[0] == stem)
        with Image.open(image) as im:
            canvas = im.convert("RGB")
        draw, (w, h) = ImageDraw.Draw(canvas), canvas.size
        with open(os.path.join(dataset, "labels", split, fn), encoding="utf-8") as f:
            for line in f:
                cls, cx, cy, bw, bh = line.split()
                cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
                draw.rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], outline=(255, 0, 0), width=3)
                draw.text((cx - bw / 2 + 3, cy - bh / 2 + 2), names[int(cls)], fill=(255, 255, 0))
        canvas.save(os.path.join(out_dir, f"{split}_{stem}.jpg"), quality=90)
    print(f"已输出 {min(n, len(labels))} 张抽检图到 {out_dir}")


def check_classes(classes_path=None):
    import database.db as db
    missing = food_classes.validate(food_classes.load_classes(classes_path), db.load_ingredients(db.get_connection()))
    print(f"missing: {missing}")
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-classes", action="store_true", help="只校验 classes.yaml 与营养库是否一致")
    parser.add_argument("--sources", nargs="+", help="要合并的数据源（training/datasets/raw 下的子目录名）")
    parser.add_argument("--raw-root", default=DEFAULT_RAW)
    parser.add_argument("--out", help="输出目录；--preview 时为抽检图输出目录")
    parser.add_argument("--split", nargs=3, type=float, default=(0.8, 0.1, 0.1), metavar=("TRAIN", "VAL", "TEST"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-only", nargs="*", default=["mendeley"], help="只进训练集的来源（默认 mendeley）")
    parser.add_argument("--no-split", action="store_true", help="不划分，全部放入 val（用于自采集 fridge_test）")
    parser.add_argument("--split-json", default=os.path.join(DEFAULT_REPORTS, "fridge_split.json"),
                        help="--no-split 时生成的 50/50 固定划分文件")
    parser.add_argument("--yaml", help="data.yaml 输出路径（默认 training/data.yaml；--no-split 时为 training/data_fridge.yaml）")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS)
    parser.add_argument("--classes", default=config.YOLO_CLASSES_YAML)
    parser.add_argument("--dense-sources", nargs="*", default=["lvis"],
                        help="启用密集小框过滤的来源（默认 lvis）")
    parser.add_argument("--dense-min-boxes", type=int, default=20, help="同类框数达到此值才算密集（默认 20）")
    parser.add_argument("--dense-max-median-area", type=float, default=0.002,
                        help="同类框面积占比中位数低于此值才算小框（默认 0.002，即 0.2%%）")
    parser.add_argument("--exclude-list", action="append", metavar="SOURCE=PATH",
                        help=f"排除清单，可多次指定；默认 lvis={os.path.relpath(DEFAULT_LVIS_EXCLUDE, ROOT)}")
    parser.add_argument("--no-filters", action="store_true", help="关闭密集小框过滤和排除清单（用于对比实验）")
    parser.add_argument("--preview", type=int, metavar="N", help="从 --dataset 抽 N 张画框，输出到 --out")
    parser.add_argument("--dataset", default=DEFAULT_OUT, help="--preview 读取的数据集目录")
    args = parser.parse_args()

    if args.check_classes:
        sys.exit(1 if check_classes(args.classes) else 0)
    if args.preview:
        if not args.out:
            parser.error("--preview 需要用 --out 指定抽检图输出目录")
        preview(args.dataset, args.preview, args.out, classes_path=args.classes)
        return
    if not args.sources:
        parser.error("需要 --sources，或使用 --check-classes / --preview")
    if abs(sum(args.split) - 1) > 1e-6:
        parser.error("--split 三个比例之和必须为 1")
    out = args.out or (os.path.join(ROOT, "training", "datasets", "fridge_test") if args.no_split else DEFAULT_OUT)
    yaml_path = args.yaml or os.path.join(ROOT, "training", "data_fridge.yaml" if args.no_split else "data.yaml")
    if args.no_filters:
        dense_sources, exclude_lists = [], {}
    else:
        dense_sources = [s for s in args.dense_sources if s in args.sources]
        pairs = args.exclude_list or [f"lvis={DEFAULT_LVIS_EXCLUDE}"]
        exclude_lists = {}
        for pair in pairs:
            source, _, path = pair.partition("=")
            if source in args.sources:
                exclude_lists[source] = path if os.path.isabs(path) else os.path.join(ROOT, path)
    summary = build_dataset(args.sources, raw_root=args.raw_root, out=out, classes_path=args.classes,
                            split=tuple(args.split), seed=args.seed, yaml_path=yaml_path,
                            reports_dir=args.reports_dir, no_split=args.no_split,
                            split_json=args.split_json if args.no_split else None,
                            train_only=args.train_only, dense_sources=dense_sources,
                            dense_min_boxes=args.dense_min_boxes, dense_max_median_area=args.dense_max_median_area,
                            exclude_lists=exclude_lists)
    print(json.dumps({k: summary[k] for k in ("images", "corrupt", "duplicates_removed", "dropped_no_boxes", "filtered",
                                             "cross_split_duplicates", "cross_split_near_duplicates", "groups",
                                             "elapsed_seconds")}, ensure_ascii=False, indent=2))
    low = {n: c for n, c in summary["per_class"]["train"].items() if c < 200}
    print(f"train 框数 < 200 的类别（{len(low)} 个）：{low}")


if __name__ == "__main__":
    main()
