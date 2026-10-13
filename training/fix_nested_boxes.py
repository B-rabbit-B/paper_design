# -*- coding: utf-8 -*-
"""去掉自动画框结果里"套在大框里面的小框"（Grounding DINO 常在同一块豆腐上画出好几层嵌套的框）。

规则：同一类别的两个框，如果小框有 80% 以上的面积落在大框里面，就去掉小框，只留大框；完全相同的框只留一个。
部分重叠但谁也没被包住的框都保留，由人工复核决定。

只改你指定的图片（--stems，或 --list 文件的第一列）。改之前把原标注备份到同来源目录下的
labels_orig/（已有备份就不再覆盖，所以重复运行是安全的，也随时可以恢复）。改完必须重新看图，
这个脚本只是减少人工画框的工作量，不保证框就对了。

用法（项目根目录、venv 中）：
    python training/fix_nested_boxes.py --source web_tofu --list training/reports/dataset/web_tofu_nested.txt
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")
INSIDE = 0.8  # 小框落在大框里面的面积占比达到这个值就算被包住


def _xyxy(b):
    _, cx, cy, w, h = b
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def _area(b):
    return b[3] * b[4]


def _inside_fraction(small, big):
    """small 有多大比例的面积落在 big 里面。"""
    sx1, sy1, sx2, sy2 = _xyxy(small)
    bx1, by1, bx2, by2 = _xyxy(big)
    iw, ih = min(sx2, bx2) - max(sx1, bx1), min(sy2, by2) - max(sy1, by1)
    return max(iw, 0) * max(ih, 0) / _area(small) if _area(small) > 0 else 0


def remove_nested(boxes):
    """boxes: [(类别, cx, cy, w, h)]（归一化）。返回去掉被包住的框和重复框之后的列表，保持原顺序。"""
    keep = []
    for i, b in enumerate(boxes):
        drop = False
        for j, other in enumerate(boxes):
            if i == j or other[0] != b[0]:
                continue
            if other == b:
                drop = j < i  # 完全相同的框只留第一个
            elif _area(other) > _area(b) and _inside_fraction(b, other) >= INSIDE:
                drop = True
            if drop:
                break
        if not drop:
            keep.append(b)
    return keep


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [(int(p[0]), *map(float, p[1:5])) for p in (l.split() for l in f if l.strip())]


def fix(source_dir, stems):
    """改写 source_dir/labels/<split>/<stem>.txt；返回 {stem: (改前框数, 改后框数)}（只含有变化的）。"""
    changed = {}
    for stem in stems:
        found = [(split, os.path.join(source_dir, "labels", split, stem + ".txt"))
                 for split in os.listdir(os.path.join(source_dir, "labels"))
                 if os.path.exists(os.path.join(source_dir, "labels", split, stem + ".txt"))]
        if not found:
            sys.exit(f"{source_dir} 里没有 {stem} 的标注")
        split, path = found[0]
        before = _read(path)
        after = remove_nested(before)
        if len(after) == len(before):
            continue
        backup = os.path.join(source_dir, "labels_orig", split, stem + ".txt")
        if not os.path.exists(backup):
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            shutil.copyfile(path, backup)
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n" for c, cx, cy, w, h in after)
        changed[stem] = (len(before), len(after))
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="training/datasets/raw 下的来源目录名，如 web_tofu")
    parser.add_argument("--list", required=True, help="要处理的图片清单（每行第一列是图片主干，# 开头为注释）")
    args = parser.parse_args()
    with open(args.list, encoding="utf-8") as f:
        stems = [l.split()[0] for l in f if l.strip() and not l.startswith("#")]
    changed = fix(os.path.join(RAW, args.source), stems)
    print(f"处理 {len(stems)} 张，其中 {len(changed)} 张去掉了嵌套的框，共去掉 {sum(a - b for a, b in changed.values())} 个框")


if __name__ == "__main__":
    main()
