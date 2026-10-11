# -*- coding: utf-8 -*-
"""Pascal VOC XML 适配器（Mendeley 孟加拉蔬菜检测数据集）。

每个 .xml 对应一张同目录的图片：优先用 <filename>，找不到时按同名不同扩展名查找。
"""
import os
import xml.etree.ElementTree as ET

from PIL import Image

from . import IMAGE_EXTS, Sample


def _image_for(xml_path, filename):
    folder = os.path.dirname(xml_path)
    if filename and os.path.exists(os.path.join(folder, filename)):
        return os.path.join(folder, filename)
    stem = os.path.splitext(xml_path)[0]
    for ext in IMAGE_EXTS + tuple(e.upper() for e in IMAGE_EXTS):
        if os.path.exists(stem + ext):
            return stem + ext
    return None


def iter_samples(raw_dir):
    """遍历 raw_dir 下所有 VOC 标注，按路径排序以保证结果可复现。"""
    for dirpath, dirnames, files in os.walk(raw_dir):
        dirnames.sort()
        for fn in sorted(files):
            if not fn.lower().endswith(".xml"):
                continue
            xml_path = os.path.join(dirpath, fn)
            root = ET.parse(xml_path).getroot()
            image = _image_for(xml_path, root.findtext("filename"))
            if image is None:
                continue
            width = int(float(root.findtext("size/width") or 0))
            height = int(float(root.findtext("size/height") or 0))
            if width <= 0 or height <= 0:
                with Image.open(image) as im:
                    width, height = im.size
            sample = Sample(image=image, width=width, height=height)
            for obj in root.iter("object"):
                try:
                    name = obj.findtext("name").strip()
                    x1, y1, x2, y2 = (float(obj.findtext(f"bndbox/{k}")) for k in ("xmin", "ymin", "xmax", "ymax"))
                except (AttributeError, TypeError, ValueError):
                    sample.corrupt += 1
                    continue
                x1, y1 = max(x1, 0.0), max(y1, 0.0)
                x2, y2 = min(x2, float(width)), min(y2, float(height))
                if x2 <= x1 or y2 <= y1:
                    sample.corrupt += 1
                    continue
                sample.boxes.append((name, x1, y1, x2, y2))
            yield sample
