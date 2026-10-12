# -*- coding: utf-8 -*-
"""用 Grounding DINO 按文字提示给候选图片自动画框，输出 YOLO 格式的数据源。

用于网上爬取的图片（training/crawl_openverse.py 的输出）：它们没有标注。先用
clip_filter.py --candidates 整图预筛掉熟食（CPU 上画框较慢，先减少图片数），再按文字提示自动检测，
最后人工逐张连同框一起核对，把熟食、无关图和框不准的图写入排除清单。
**自动标注会有误差，进训练前必须经过人工核对。**

模型：IDEA-Research/grounding-dino-tiny（Apache-2.0，经 hf-mirror 下载）。

用法（项目根目录；transformers 用 uv 临时安装，不进项目 venv）：
    set HF_ENDPOINT=https://hf-mirror.com
    uv run --no-project --with torch --with transformers --with pillow \
        python training/auto_label.py --name raw_beef --prompt "raw beef." --class-name raw_beef \
        --skip-list training/reports/dataset/candidates_raw_beef_cooked.txt
输出：training/datasets/raw/web_<name>/（images/train、labels/train、data.yaml、auto_label_<name>.csv）
"""
import argparse
import csv
import os
import shutil
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")


def detect(model, processor, image, prompt, box_threshold, text_threshold):
    import torch

    inputs = processor(images=image, text=prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    kwargs = dict(text_threshold=text_threshold, target_sizes=[image.size[::-1]])
    try:  # 新版 transformers 的参数名是 threshold，旧版是 box_threshold
        result = processor.post_process_grounded_object_detection(outputs, inputs.input_ids, threshold=box_threshold, **kwargs)
    except TypeError:
        result = processor.post_process_grounded_object_detection(outputs, inputs.input_ids, box_threshold=box_threshold, **kwargs)
    r = result[0]
    return [(float(s), [float(v) for v in b]) for s, b in zip(r["scores"], r["boxes"])]


def main():
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="候选目录名（_web_candidates 下）")
    parser.add_argument("--prompt", required=True, help='文字提示，英文小写并以句点结尾，如 "raw beef."')
    parser.add_argument("--class-name", required=True, help="写入 data.yaml 的类名")
    parser.add_argument("--out", help="输出的数据源目录名（默认 web_<name>）；同一类别分批爬取时可指向同一目录，"
                                      "各批文件名前缀不同，不会互相覆盖")
    parser.add_argument("--box-threshold", type=float, default=0.35)
    parser.add_argument("--text-threshold", type=float, default=0.25)
    parser.add_argument("--short-side", type=int, default=512,
                        help="输入短边（模型默认 800）；CPU 上 512 约快一倍半，牛肉这类大目标影响不大")
    parser.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                        help="PyTorch 线程数（默认逻辑核数的一半，约等于物理核数）")
    parser.add_argument("--skip-list", help="不处理的图片清单（每行第一列为图片主干，# 开头为注释），如 CLIP 预筛判为熟的图")
    parser.add_argument("--model", default="IDEA-Research/grounding-dino-tiny")
    args = parser.parse_args()
    started = time.time()

    src = os.path.join(RAW, "_web_candidates", args.name)
    out = os.path.join(RAW, args.out or f"web_{args.name}")
    for kind in ("images", "labels"):
        os.makedirs(os.path.join(out, kind, "train"), exist_ok=True)
    import torch

    torch.set_num_threads(args.threads)
    processor = AutoProcessor.from_pretrained(args.model)
    processor.image_processor.size = {"shortest_edge": args.short_side, "longest_edge": args.short_side * 1333 // 800}
    model = AutoModelForZeroShotObjectDetection.from_pretrained(args.model).eval()

    rows, kept = [], 0
    skip = set()
    if args.skip_list:
        with open(args.skip_list, encoding="utf-8") as f:
            skip = {line.split()[0] for line in f if line.strip() and not line.startswith("#")}
    files = sorted(f for f in os.listdir(src) if f.endswith(".jpg") and f[:-4] not in skip)
    print(f"候选 {len(files)} 张（跳过清单中的 {len(skip)} 张）", flush=True)
    for n, fn in enumerate(files, 1):
        with Image.open(os.path.join(src, fn)) as im:
            image = im.convert("RGB")
        dets = detect(model, processor, image, args.prompt, args.box_threshold, args.text_threshold)
        w, h = image.size
        rows.append((fn, len(dets), ";".join(f"{s:.2f}" for s, _ in dets)))
        if dets:
            kept += 1
            shutil.copyfile(os.path.join(src, fn), os.path.join(out, "images", "train", fn))
            with open(os.path.join(out, "labels", "train", fn[:-4] + ".txt"), "w", encoding="utf-8") as f:
                for _, (x1, y1, x2, y2) in dets:
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
                    f.write(f"0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}\n")
        if n % 50 == 0 or n == 10:
            print(f"  已处理 {n}/{len(files)}，有检测结果 {kept}", flush=True)

    with open(os.path.join(out, "data.yaml"), "w", encoding="utf-8") as f:
        f.write(f"# 由 training/auto_label.py 生成；提示词 {args.prompt!r}，box_threshold={args.box_threshold}，短边 {args.short_side}，"
                f"跳过清单 {args.skip_list}\n")
        f.write(f"names:\n  0: {args.class_name}\n")
    with open(os.path.join(out, f"auto_label_{args.name}.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([("file", "num_boxes", "scores"), *rows])
    print(f"完成：{len(files)} 张候选，{kept} 张有检测结果，用时 {time.time() - started:.0f} 秒，输出 {out}")


if __name__ == "__main__":
    main()
