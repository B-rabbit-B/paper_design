# -*- coding: utf-8 -*-
"""独立校验合并后的数据集（只读）：不依赖 prepare_dataset.py 自己写出的统计，直接扫描输出目录。

检查三件事：
1. 图片与标注一一对应；
2. 标注行合法：恰好 5 个字段、类别号在 0..n-1、中心与宽高都在 [0, 1]、宽高大于 0、框不超出图片；
3. 各 split 之间（以及与 --against 指定的另一个数据集之间）没有重复图片：md5 相同，或 64 位平均哈希相同。
   平均哈希按 prepare_dataset.py 的规则计算，纯色图（哈希全 0 或全 1）不参与比较。

总纲验收项 1.4、1.6 的检查命令；有任何一项不为 0 时退出码为 1。
用法（项目根目录、venv 中）：
    python training/verify_dataset.py training/datasets/yolo
    python training/verify_dataset.py training/datasets/yolo --against training/datasets/fridge_test
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "training"))

import prepare_dataset as pd  # noqa: E402

EPS = 1e-6


def _bad_label_lines(path, num_classes):
    """返回这个标注文件中不合法的行数。"""
    bad = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split()
            try:
                cls, (cx, cy, w, h) = int(parts[0]), (float(v) for v in parts[1:])
            except ValueError:
                bad += 1
                continue
            ok = (len(parts) == 5 and 0 <= cls < num_classes and 0 <= cx <= 1 and 0 <= cy <= 1
                  and w > 0 and h > 0 and cx - w / 2 >= -EPS and cx + w / 2 <= 1 + EPS
                  and cy - h / 2 >= -EPS and cy + h / 2 <= 1 + EPS)
            bad += not ok
    return bad


def _scan(dataset, num_classes):
    """返回 ({split: [图片路径]}, 不成对的文件数, 不合法的标注行数)。"""
    images, unpaired, bad = {}, 0, 0
    for split in pd.SPLITS:
        image_dir, label_dir = (os.path.join(dataset, kind, split) for kind in ("images", "labels"))
        if not os.path.isdir(image_dir):
            continue
        stems = {os.path.splitext(f)[0]: f for f in os.listdir(image_dir)}
        labels = {os.path.splitext(f)[0] for f in os.listdir(label_dir)} if os.path.isdir(label_dir) else set()
        unpaired += len(stems.keys() ^ labels)
        images[split] = [os.path.join(image_dir, f) for f in stems.values()]
        for stem in stems.keys() & labels:
            bad += _bad_label_lines(os.path.join(label_dir, stem + ".txt"), num_classes)
    return images, unpaired, bad


def _hash_all(paths):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(pd._hashes, paths))


def _collisions(groups):
    """groups: {标签: [(md5, ahash)]}；返回 (跨标签 md5 相同的值数, 跨标签平均哈希相同的值数)。"""
    md5_labels, hash_labels = defaultdict(set), defaultdict(set)
    for label, hashes in groups.items():
        for md5, ahash in hashes:
            md5_labels[md5].add(label)
            if ahash not in pd.DEGENERATE_HASHES:
                hash_labels[ahash].add(label)
    return (sum(len(v) > 1 for v in md5_labels.values()), sum(len(v) > 1 for v in hash_labels.values()))


def verify(dataset, against=None, num_classes=None):
    if num_classes is None:
        from core import food_classes
        num_classes = len(food_classes.load_classes()["names"])
    images, unpaired, bad = _scan(dataset, num_classes)
    groups = {split: _hash_all(paths) for split, paths in images.items()}
    md5_dup, hash_dup = _collisions(groups)
    result = {"images": {s: len(p) for s, p in images.items()}, "unpaired_files": unpaired, "bad_label_lines": bad,
              "cross_split_md5": md5_dup, "cross_split_ahash": hash_dup}
    if against:
        other, _, _ = _scan(against, num_classes)
        other_hashes = _hash_all([p for paths in other.values() for p in paths])
        result["against_md5"], result["against_ahash"] = _collisions(
            {"main": [h for hs in groups.values() for h in hs], "against": other_hashes})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", help="prepare_dataset.py 的输出目录")
    parser.add_argument("--against", help="再与另一个数据集（如 fridge_test）比较，确认没有相同的图片")
    args = parser.parse_args()
    result = verify(args.dataset, args.against)
    print(json.dumps(result, ensure_ascii=False))
    print("corrupt={} unpaired={} cross_split_md5={} cross_split_ahash={}".format(
        result["bad_label_lines"], result["unpaired_files"], result["cross_split_md5"], result["cross_split_ahash"])
        + (" against_md5={} against_ahash={}".format(result["against_md5"], result["against_ahash"]) if args.against else ""))
    problems = [v for k, v in result.items() if k != "images"]
    sys.exit(1 if any(problems) else 0)


if __name__ == "__main__":
    main()
