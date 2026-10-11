# -*- coding: utf-8 -*-
"""自采照片标注前的预处理：按 EXIF 转正、限制长边、统一重命名，并生成 labelImg 用的类别表。

为什么要先做：手机竖拍照片的像素通常是横的，只在 EXIF 里记了"需要旋转"。有的标注工具按 EXIF
显示、有的不按，训练时读取方式又可能不同，框就会错位。这里把旋转真正应用到像素上并去掉 EXIF，
之后所有工具看到的都是同一个方向。

用法（项目根目录、venv 中）：
    1. 把手机照片拷到 training/datasets/raw/custom_photos/（可含子目录）
    2. python training/normalize_photos.py
    3. 用 labelImg 打开 training/datasets/raw/custom/images/all，保存目录选
       training/datasets/raw/custom/labels/all，格式选 YOLO（该目录下已有 33 类的 classes.txt）
输出的原文件名对照表在 training/datasets/raw/custom/rename_map.csv。
"""
import argparse
import csv
import os
import sys

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import food_classes  # noqa: E402

RAW = os.path.join(ROOT, "training", "datasets", "raw")
EXTS = (".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp")


def normalize(src, out, max_side=1920, prefix="fridge"):
    """处理 src 下所有图片，写入 out/images/all，返回 [(原路径, 新文件名)]。out 已有图片时拒绝覆盖。"""
    image_dir = os.path.join(out, "images", "all")
    label_dir = os.path.join(out, "labels", "all")
    if os.path.isdir(image_dir) and os.listdir(image_dir):
        sys.exit(f"{image_dir} 已有图片，为避免打乱已完成的标注，拒绝覆盖。追加新照片请换一个 --prefix 并输出到新目录")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)

    sources = []
    for dirpath, dirnames, files in os.walk(src):
        dirnames.sort()
        sources += [os.path.join(dirpath, f) for f in sorted(files) if f.lower().endswith(EXTS)]

    mapping = []
    for i, path in enumerate(sources, 1):
        name = f"{prefix}_{i:04d}.jpg"
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((max_side, max_side))
            im.save(os.path.join(image_dir, name), "JPEG", quality=92)  # 不带 exif 保存，方向信息被去掉
        mapping.append((os.path.relpath(path, src), name))

    with open(os.path.join(label_dir, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(food_classes.load_classes()["names"]) + "\n")
    with open(os.path.join(out, "rename_map.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([("original", "renamed"), *mapping])
    return mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", default=os.path.join(RAW, "custom_photos"))
    parser.add_argument("--out", default=os.path.join(RAW, "custom"))
    parser.add_argument("--max-side", type=int, default=1920)
    parser.add_argument("--prefix", default="fridge")
    args = parser.parse_args()
    mapping = normalize(args.src, args.out, args.max_side, args.prefix)
    print(f"已处理 {len(mapping)} 张照片，输出到 {os.path.join(args.out, 'images', 'all')}")


if __name__ == "__main__":
    main()
