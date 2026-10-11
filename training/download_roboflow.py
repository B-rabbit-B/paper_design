# -*- coding: utf-8 -*-
"""下载 Roboflow Universe 上补齐稀缺类别用的公开检测数据集（YOLOv8 格式）。

需要你自己的 Roboflow 账号（建议邮箱注册）。API Key 在 Roboflow 网页右上角
Settings → API Keys 中查看，只通过环境变量传给本脚本，不要写进任何文件或提交到仓库：

    PowerShell:  $env:ROBOFLOW_API_KEY = "你的key"
    运行:        uv run --with roboflow python training/download_roboflow.py
    只下其中几个: uv run --with roboflow python training/download_roboflow.py --only rf_ingredients rf_chicken

每个数据集下载到 training/datasets/raw/<目录名>/，目录名就是 classes.yaml 中 sources 的键名；
已存在的目录会跳过。也可以在网页上手动选 "YOLOv8" 导出 zip，解压到同名目录，效果相同。
数据集清单来自 2026-10-12 的调研（见 training/reports/dataset/sources.md）。
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")

# (目录名, workspace, project, version, 许可, 主要用途)
DATASETS = [
    ("rf_ingredients", "yolov5-rznzw", "food-ingredients-7txer", 5, "CC BY 4.0",
     "猪肉、牛肉、鸡肉、鱼（鲭鱼）、大白菜（baechu）、鸡蛋、虾、豆腐（dubu）"),
    ("rf_chicken", "france-7awpa", "chicken-mx39r", 2, "CC BY 4.0", "生鸡肉各部位"),
    ("rf_meat", "meat-detection", "meat-detection-8z18t", 2, "CC BY 4.0", "牛肉、猪肉、鸡肉"),
    ("rf_beef", "sju", "beef-detection1_0630", 4, "CC BY 4.0", "牛肉"),
    ("rf_fish", "sages", "meat-a9qkz", 1, "CC BY 4.0", "盘装或市场里的整条鱼、鱼块"),
    ("rf_napa", "jericho-cskol", "vegetable-detection-fmlst", 3, "CC BY 4.0", "大白菜（chinese cabbage - good）"),
    # 调研时该项目有 4 个版本（大小未能核实），取 v4；若下载失败，请在网页上确认版本号后修改
    ("rf_fridge_kitchen", "kevins-workspace-fwyve", "refrigerator-and-kitchen-objects", 4, "CC BY 4.0",
     "菠菜（espinaca）等冰箱和厨房物品"),
    ("rf_spinach", "andyzhang", "foods-f07qs", 4, "CC BY 4.0", "菠菜"),
    ("rf_fridge_egg_milk", "gracelearning", "hien_fridge-tathx", 12, "CC BY 4.0", "冰箱里的鸡蛋、牛奶盒"),
    ("rf_thesis_ingredients", "thesis-101", "ingredients-99akx", 7, "CC BY 4.0", "生鸡蛋、猪肉、鸡肉、鱼、虾、豆腐"),
    ("rf_tofu", "sages", "tofu-47uo2", 1, "CC BY 4.0", "豆腐"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", help="只下载这些目录名对应的数据集")
    parser.add_argument("--list", action="store_true", help="只列出清单，不下载")
    args = parser.parse_args()

    selected = [d for d in DATASETS if not args.only or d[0] in args.only]
    if args.list:
        for folder, ws, project, version, license_, use in selected:
            print(f"{folder:24s} https://universe.roboflow.com/{ws}/{project}  v{version}  {license_}  {use}")
        return

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        sys.exit("请先设置环境变量 ROBOFLOW_API_KEY（见本文件开头的说明）")
    from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    for folder, ws, project, version, _, use in selected:
        target = os.path.join(RAW, folder)
        if os.path.isdir(target) and os.listdir(target):
            print(f"[跳过] {folder} 已存在")
            continue
        print(f"[下载] {folder} ← {ws}/{project} v{version}（{use}）", flush=True)
        try:
            rf.workspace(ws).project(project).version(version).download("yolov8", location=target)
        except Exception as exc:  # 单个失败不影响其余，最后汇总
            print(f"[失败] {folder}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
