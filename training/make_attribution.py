# -*- coding: utf-8 -*-
"""根据合并后的数据集生成网络爬取来源的署名清单（作者、许可、原始页面）。

署名清单必须与数据集里的图片**逐一对应**：只列实际进入数据集的图。候选图在合并时可能因为与别的图
内容相同（md5 一致）被去重丢掉，这些图不能出现在署名清单里。所以这里以数据集为准，而不是以人工复核
保留的图为准。

做法：列出 <数据集>/images/{train,val,test} 下以 `<来源名>_` 开头的图片，去掉前缀得到候选图文件名，
到 raw/_web_candidates/*/manifest.csv 里查作者与许可；找不到记录就报错（说明图片来历不明）。

用法（项目根目录、venv 中；数据集合并完之后运行）：
    python training/make_attribution.py --source web_ginger --out training/reports/dataset/web_ginger_attribution.csv
"""
import argparse
import csv
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATASET = os.path.join(ROOT, "training", "datasets", "yolo")
DEFAULT_CANDIDATES = os.path.join(ROOT, "training", "datasets", "raw", "_web_candidates")
FIELDS = ["file", "title", "creator", "license", "license_version", "source", "foreign_landing_url"]


def make(dataset, source, candidates, out):
    """生成署名清单，返回行数。"""
    meta = {}
    for manifest in sorted(glob.glob(os.path.join(candidates, "*", "manifest.csv"))):
        with open(manifest, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                meta[row["file"]] = row
    files = sorted(f[len(source) + 1:] for split in ("train", "val", "test")
                   if os.path.isdir(os.path.join(dataset, "images", split))
                   for f in os.listdir(os.path.join(dataset, "images", split)) if f.startswith(source + "_"))
    unknown = [f for f in files if f not in meta]
    if unknown:
        sys.exit(f"{len(unknown)} 张图在候选目录的 manifest.csv 里找不到来源记录，例如 {unknown[:3]}")
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows([meta[name][k] for k in FIELDS] for name in files)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="来源名，如 web_ginger")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    args = parser.parse_args()
    print(f"{args.source}：写出 {make(args.dataset, args.source, args.candidates, args.out)} 行到 {args.out}")


if __name__ == "__main__":
    main()
