# -*- coding: utf-8 -*-
"""YOLO 格式适配器。

目录约定：标注在某个 labels/ 目录下，图片在把该路径中的 labels 换成 images 的位置，
例如 labels/train/a.txt ↔ images/train/a.jpg，或 train/labels/a.txt ↔ train/images/a.jpg。
类别名取自从标注目录向上找到的第一个 data.yaml（names 为列表或字典）或 classes.txt（labelImg 导出）。
每行支持两种写法：检测框 `cls cx cy w h`，以及分割多边形 `cls x1 y1 x2 y2 ...`（取外接框）。
"""
import os

import yaml
from PIL import Image

from . import IMAGE_EXTS, Sample

_EPS = 1e-3  # 越界容差：约等于千像素宽图上的 1 个像素，容纳 LVIS 等标注中的浮点误差（越界部分随后裁剪）


def _read_names(directory):
    y = os.path.join(directory, "data.yaml")
    if os.path.exists(y):
        with open(y, encoding="utf-8-sig") as f:
            names = (yaml.safe_load(f) or {}).get("names")
        if isinstance(names, dict):
            return {int(k): str(v) for k, v in names.items()}
        if isinstance(names, list):
            return {i: str(v) for i, v in enumerate(names)}
    t = os.path.join(directory, "classes.txt")
    if os.path.exists(t):
        with open(t, encoding="utf-8-sig") as f:
            return {i: line.strip() for i, line in enumerate(f.read().splitlines()) if line.strip()}
    return None


def _find_names(label_dir, raw_dir, cache):
    d = os.path.abspath(label_dir)
    top = os.path.normcase(os.path.abspath(raw_dir))
    while True:
        if d not in cache:
            cache[d] = _read_names(d)
        if cache[d] is not None:
            return cache[d]
        parent = os.path.dirname(d)
        if os.path.normcase(d) == top or parent == d:
            return None
        d = parent


def _image_for(label_path):
    parts = os.path.normpath(label_path).split(os.sep)
    idx = len(parts) - 1 - parts[::-1].index("labels")
    parts[idx] = "images"
    stem = os.path.splitext(os.sep.join(parts))[0]
    for ext in IMAGE_EXTS + tuple(e.upper() for e in IMAGE_EXTS):
        if os.path.exists(stem + ext):
            return stem + ext
    return None


def _parse_line(line, names, width, height):
    """返回 (类名, x1, y1, x2, y2)；格式或数值不合法时返回 None。"""
    parts = line.split()
    if len(parts) < 5 or (len(parts) > 5 and (len(parts) - 1) % 2 != 0):
        return None
    try:
        cls = int(parts[0])
        vals = [float(v) for v in parts[1:]]
    except ValueError:
        return None
    if cls not in names:
        return None
    if len(vals) == 4:
        cx, cy, w, h = vals
        if w <= 0 or h <= 0:
            return None
        x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    else:  # 分割多边形 → 外接框
        xs, ys = vals[0::2], vals[1::2]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        if x2 <= x1 or y2 <= y1:
            return None
    if x1 < -_EPS or y1 < -_EPS or x2 > 1 + _EPS or y2 > 1 + _EPS:
        return None
    x1, y1, x2, y2 = (min(max(v, 0.0), 1.0) for v in (x1, y1, x2, y2))
    return names[cls], x1 * width, y1 * height, x2 * width, y2 * height


def iter_samples(raw_dir):
    """遍历 raw_dir 下所有 YOLO 标注，按路径排序以保证结果可复现。没有对应图片的标注被跳过。"""
    cache = {}
    for dirpath, dirnames, files in os.walk(raw_dir):
        dirnames.sort()
        if "labels" not in os.path.normpath(dirpath).split(os.sep):
            continue
        names = _find_names(dirpath, raw_dir, cache)
        for fn in sorted(files):
            if not fn.endswith(".txt") or fn == "classes.txt":
                continue
            label_path = os.path.join(dirpath, fn)
            image = _image_for(label_path)
            if image is None or names is None:
                continue
            with Image.open(image) as im:
                width, height = im.size
            sample = Sample(image=image, width=width, height=height)
            with open(label_path, encoding="utf-8-sig") as f:  # utf-8-sig：兼容带 BOM 的标注文件
                for line in f:
                    if not line.strip():
                        continue
                    box = _parse_line(line, names, width, height)
                    if box is None:
                        sample.corrupt += 1
                    else:
                        sample.boxes.append(box)
            yield sample
