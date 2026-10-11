# -*- coding: utf-8 -*-
"""把 Hugging Face 上 LVIS 果蔬子集的 parquet 图片与单独下载的 YOLO 标注拼回标准目录。

背景：henningheyen/LVIS_Fruits_And_Vegetables 的散装图片逐个下载会被 hf-mirror 限流，
GitHub 仓库里又只有测试集。parquet（5 个文件，共约 1.4GB）里有全部图片和原始文件名，
但没有框标注；标注是 labels/ 下约 8400 个小 txt，需单独低并发下载。

    # 1. 下载 parquet（5 个文件）到 training/datasets/raw/lvis_parquet/
    # 2. 下载标注：HF_ENDPOINT=https://hf-mirror.com uvx --from "huggingface_hub[cli]" hf download \
    #      henningheyen/LVIS_Fruits_And_Vegetables --repo-type dataset \
    #      --local-dir training/datasets/raw/lvis_labels --include "labels/*" "data.yaml" --max-workers 2
    # 3. 拼装：
    python training/convert_lvis_parquet.py
"""
import argparse
import glob
import os
import shutil
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")
SPLIT_OF = {"train": "train", "validation": "val", "test": "test"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--parquet-dir", default=os.path.join(RAW, "lvis_parquet"))
    parser.add_argument("--labels-dir", default=os.path.join(RAW, "lvis_labels"))
    parser.add_argument("--out", default=os.path.join(RAW, "lvis"))
    args = parser.parse_args()

    import polars as pl

    os.makedirs(args.out, exist_ok=True)
    shutil.copyfile(os.path.join(args.labels_dir, "data.yaml"), os.path.join(args.out, "data.yaml"))
    stats = Counter()
    for path in sorted(glob.glob(os.path.join(args.parquet_dir, "*.parquet"))):
        split = SPLIT_OF[os.path.basename(path).split("-")[0]]
        for kind in ("images", "labels"):
            os.makedirs(os.path.join(args.out, kind, split), exist_ok=True)
        images = pl.read_parquet(path)["image"]
        for name, data in zip(images.struct.field("path").to_list(), images.struct.field("bytes").to_list()):
            stem = os.path.splitext(name)[0].strip()
            if not stem:
                stats[f"{split}:skipped_bad_name"] += 1
                continue
            label = os.path.join(args.labels_dir, "labels", split, stem + ".txt")
            if not os.path.exists(label):
                stats[f"{split}:skipped_no_label"] += 1
                continue
            with open(os.path.join(args.out, "images", split, name), "wb") as f:
                f.write(data)
            shutil.copyfile(label, os.path.join(args.out, "labels", split, stem + ".txt"))
            stats[f"{split}:pairs"] += 1
    for key in sorted(stats):
        print(f"{key}: {stats[key]}")


if __name__ == "__main__":
    main()
