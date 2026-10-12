# -*- coding: utf-8 -*-
"""COCO JSON 适配器（如 Roboflow 导出的 _annotations.coco.json、RF100 fish-market）。

目录下每个含 "images" 和 "annotations" 的 .json 都按 COCO 格式读取，图片在 JSON 所在目录下，
路径为 images[].file_name。框为像素坐标 [x, y, w, h]。
"""
import json
import os

from PIL import Image

from . import Sample


def is_coco_json(path):
    """只读取文件开头判断，避免为了识别格式把大文件整个解析一遍。"""
    with open(path, encoding="utf-8-sig") as f:
        head = f.read(4096)
    return '"images"' in head or '"annotations"' in head or '"categories"' in head


def iter_samples(raw_dir):
    """遍历 raw_dir 下所有 COCO JSON，按路径和图片 id 排序以保证结果可复现。"""
    for dirpath, dirnames, files in os.walk(raw_dir):
        dirnames.sort()
        for fn in sorted(files):
            if not fn.lower().endswith(".json") or not is_coco_json(os.path.join(dirpath, fn)):
                continue
            with open(os.path.join(dirpath, fn), encoding="utf-8-sig") as f:
                data = json.load(f)
            names = {c["id"]: c["name"] for c in data.get("categories", [])}
            anns = {}
            for a in data.get("annotations", []):
                anns.setdefault(a["image_id"], []).append(a)
            for img in sorted(data.get("images", []), key=lambda i: i["id"]):
                path = os.path.join(dirpath, img["file_name"])
                if not os.path.exists(path):
                    continue
                width, height = img.get("width"), img.get("height")
                if not width or not height:
                    with Image.open(path) as im:
                        width, height = im.size
                sample = Sample(image=path, width=int(width), height=int(height))
                for a in anns.get(img["id"], []):
                    try:
                        x, y, w, h = (float(v) for v in a["bbox"])
                        name = names[a["category_id"]]
                    except (KeyError, TypeError, ValueError):
                        sample.corrupt += 1
                        continue
                    x1, y1 = max(x, 0.0), max(y, 0.0)
                    x2, y2 = min(x + w, float(width)), min(y + h, float(height))
                    if x2 <= x1 or y2 <= y1:
                        sample.corrupt += 1
                        continue
                    sample.boxes.append((name, x1, y1, x2, y2))
                yield sample
