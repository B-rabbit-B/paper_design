# -*- coding: utf-8 -*-
"""数据源适配器：把各种标注格式统一成 Sample（绝对像素坐标的框）。

- yolo.py：images/ 与 labels/ 平行目录（LVIS 子集、Zenodo、Roboflow 导出、labelImg 自采、Open Images 下载结果）
- voc.py：Pascal VOC XML（Mendeley 孟加拉蔬菜）
"""
import os
from dataclasses import dataclass, field
from typing import List, Tuple

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

Box = Tuple[str, float, float, float, float]  # (来源类名, x1, y1, x2, y2)，像素坐标


@dataclass
class Sample:
    image: str                      # 图片绝对路径
    width: int
    height: int
    boxes: List[Box] = field(default_factory=list)
    corrupt: int = 0                # 本图被丢弃的坏标注数（坐标越界、类别越界、格式错误）


def detect_format(raw_dir):
    """按目录内容判断格式：有 .xml → voc；有 labels/ 下的 .txt → yolo；否则返回 None。"""
    has_yolo = False
    for dirpath, _, files in os.walk(raw_dir):
        if any(f.lower().endswith(".xml") for f in files):
            return "voc"
        if "labels" in os.path.normpath(dirpath).split(os.sep) and any(f.endswith(".txt") for f in files):
            has_yolo = True
    return "yolo" if has_yolo else None
