# -*- coding: utf-8 -*-
"""检测类别定义：加载与校验 training/classes.yaml。

classes.yaml 是类别的唯一真源，训练侧（training/prepare_dataset.py）
与运行侧（core/recognizer.py、core/nutrition.py）共用，避免两处维护不同步。
"""
import yaml

import config

REQUIRED_FIELDS = ("id", "name", "zh", "ingredient", "unit", "default_weight_g")
UNITS = ("piece", "bulk")  # piece = 按个计数 × 单重；bulk = 整份取默认重量


def load_classes(path=None):
    """读取并校验类别文件。

    返回 {"version", "list"（按 id 排序）, "by_name", "by_id", "names"}。
    文件内容不合法时抛出 ValueError，并指出是哪一类出错。
    """
    with open(path or config.YOLO_CLASSES_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    items = data.get("classes") or []
    if not items:
        raise ValueError("classes.yaml 中没有任何类别")

    for c in items:
        missing = [k for k in REQUIRED_FIELDS if k not in c]
        if missing:
            raise ValueError(f"类别 {c.get('name', c)} 缺少字段：{missing}")
        if c["unit"] not in UNITS:
            raise ValueError(f"类别 {c['name']} 的 unit 必须是 {UNITS} 之一，实际为 {c['unit']!r}")
        if not c["default_weight_g"] > 0:
            raise ValueError(f"类别 {c['name']} 的 default_weight_g 必须大于 0")

    ordered = sorted(items, key=lambda c: c["id"])
    ids = [c["id"] for c in ordered]
    if ids != list(range(len(ordered))):
        raise ValueError(f"类别 id 必须从 0 开始连续且不重复，实际为 {ids}")

    names = [c["name"] for c in ordered]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError(f"类别名重复：{dup}")

    return {
        "version": data.get("version"),
        "list": ordered,
        "by_name": {c["name"]: c for c in ordered},
        "by_id": {c["id"]: c for c in ordered},
        "names": names,
    }


def validate(classes, ingredient_index):
    """返回 ingredient 字段在营养库索引（db.load_ingredients 的返回值）中找不到的类名。"""
    return [c["name"] for c in classes["list"] if c["ingredient"] not in ingredient_index]


def source_map(classes, source):
    """返回某个数据源的 {来源类名: 本项目类 id}，供数据集合并时做类别映射。

    同一个来源类名被映射到两个不同的类时抛出 ValueError。
    """
    mapping = {}
    for c in classes["list"]:
        for src_name in (c.get("sources") or {}).get(source, []):
            if mapping.get(src_name, c["id"]) != c["id"]:
                raise ValueError(f"来源 {source} 的类名 {src_name!r} 同时映射到了多个类别")
            mapping[src_name] = c["id"]
    return mapping
