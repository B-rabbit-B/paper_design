# -*- coding: utf-8 -*-
"""用 CLIP 零样本分类区分"生"与"熟"，生成排除清单，供 prepare_dataset.py 的 --exclude-list 使用。

背景：HYUNAHKO 等图库型数据里，五花肉、鸡胸、菠菜约有一半是烤肉、熟菜、菜肴配菜，
而本项目识别的是生鲜食材。做法是把每个目标框（四周留 15% 边距）裁出来，让 CLIP 在
"生"和"熟"两组文字描述之间打分；整张图也打一次分（菜肴上点缀的菠菜叶单独裁出来像生的，
整图才看得出是菜肴）。整图或任一目标框判为熟，整张图写入排除清单。
原始数据不改动，清单入库，结果可复现；阈值可调，便于抽检后修正。

模型：openai/clip-vit-base-patch16（通过 hf-mirror 下载）。本机可用内存有限，没有用 large 版本。

用法（项目根目录；transformers 用 uv 临时安装，不进项目 venv）：
    set HF_ENDPOINT=https://hf-mirror.com
    uv run --no-project --with torch --with transformers --with pillow --with pyyaml \
        python training/clip_filter.py --source hyunahko
    爬取的候选图（未标注）先整图预筛，再交给 auto_label.py 画框：
        python training/clip_filter.py --source raw_beef --candidates raw_beef --threshold 0.5
输出：training/reports/dataset/<source>_cooked.txt（被判为熟的图片清单，含每张图的最低"生"概率）
      与 <source>_clip_scores.csv（全部图片的得分）；--candidates 模式下文件名前加 candidates_
"""
import argparse
import os
import sys
import time

import yaml
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")
REPORTS = os.path.join(ROOT, "training", "reports", "dataset")

# 来源类名 → (生的描述, 熟的描述)
PROMPTS = {
    "pork_belly": (["a photo of raw uncooked pork belly", "a photo of fresh raw pork meat"],
                   ["a photo of grilled pork belly", "a photo of a cooked braised pork dish"]),
    "chicken": (["a photo of raw uncooked chicken meat", "a photo of a raw whole chicken"],
                ["a photo of cooked grilled chicken", "a photo of a cooked chicken dish"]),
    "chicken_breast": (["a photo of raw uncooked chicken breast", "a photo of fresh raw chicken meat"],
                       ["a photo of grilled chicken breast", "a photo of sliced cooked chicken on a plate"]),
    # 沙拉里的菠菜也是生的，所以负类写成"菜肴"而不是"熟"：本项目要的是整把、整袋的生菠菜
    "spinach": (["a photo of a bunch of fresh raw spinach", "a photo of fresh spinach leaves in a bowl or a bag",
                 "a photo of raw spinach on a cutting board"],
                ["a photo of a salad on a plate", "a photo of a pizza or a cooked dish",
                 "a photo of a meal with spinach as garnish"]),
    # 爬取的候选图里还有活牛、餐厅等无关图，负类加上"活牛"
    "raw_beef": (["a photo of raw uncooked beef", "a photo of fresh raw red meat", "a photo of raw beef at a butcher shop"],
                 ["a photo of cooked steak", "a photo of a cooked beef dish", "a photo of live cattle"]),
}


def _features(output):
    """旧版 transformers 的 get_*_features 直接返回张量；5.x 返回输出对象，投影后的特征在 pooler_output。"""
    return output if hasattr(output, "norm") else output.pooler_output


def iter_boxes(src_dir, names):
    """遍历 YOLO 来源中的 (标注文件主干, 图片路径, 类名, 像素框)。"""
    for split in sorted(os.listdir(os.path.join(src_dir, "labels"))):
        for fn in sorted(os.listdir(os.path.join(src_dir, "labels", split))):
            stem = os.path.splitext(fn)[0]
            image = os.path.join(src_dir, "images", split, stem + ".jpg")
            if not os.path.exists(image):
                continue
            with Image.open(image) as im:
                w, h = im.size
            with open(os.path.join(src_dir, "labels", split, fn), encoding="utf-8-sig") as f:
                for line in f:
                    p = line.split()
                    if len(p) < 5 or int(p[0]) not in names:
                        continue
                    cx, cy, bw, bh = (float(v) for v in p[1:5])
                    yield stem, image, names[int(p[0])], ((cx - bw / 2) * w, (cy - bh / 2) * h,
                                                          (cx + bw / 2) * w, (cy + bh / 2) * h)


def main():
    import torch
    from transformers import CLIPModel, CLIPProcessor

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="training/datasets/raw 下的来源目录名")
    parser.add_argument("--candidates", metavar="TAG",
                        help="改为处理 raw/_web_candidates/<source>/ 中未标注的爬取候选图，只做整图打分，"
                             "TAG 是 PROMPTS 中的类名；用于 auto_label.py 画框之前先筛掉熟食")
    parser.add_argument("--threshold", type=float, default=0.5, help="'生'的概率低于此值判为熟（默认 0.5）")
    parser.add_argument("--thresholds", nargs="*", default=[], metavar="TAG=VALUE",
                        help="按类覆盖阈值，如 spinach=0.7")
    parser.add_argument("--model", default="openai/clip-vit-base-patch16")
    args = parser.parse_args()
    started = time.time()

    if args.candidates:
        if args.candidates not in PROMPTS:
            sys.exit(f"{args.candidates} 没有定义生熟描述，请先在 PROMPTS 中补充")
        src_dir = os.path.join(RAW, "_web_candidates", args.source)
        items = ((f[:-4], os.path.join(src_dir, f), args.candidates, None)
                 for f in sorted(os.listdir(src_dir)) if f.endswith(".jpg"))
        report = f"candidates_{args.source}"
    else:
        src_dir = os.path.join(RAW, args.source)
        with open(os.path.join(src_dir, "data.yaml"), encoding="utf-8-sig") as f:
            names = {int(k): v for k, v in (yaml.safe_load(f)["names"]).items()}
        unknown = sorted(set(names.values()) - set(PROMPTS))
        if unknown:
            sys.exit(f"这些类名没有定义生熟描述：{unknown}，请先在 PROMPTS 中补充")
        items = iter_boxes(src_dir, names)
        report = args.source

    model = CLIPModel.from_pretrained(args.model).eval()
    processor = CLIPProcessor.from_pretrained(args.model)
    text_inputs, raw_counts = {}, {}
    for tag, (raw, cooked) in PROMPTS.items():
        text_inputs[tag] = processor(text=raw + cooked, return_tensors="pt", padding=True)
        raw_counts[tag] = len(raw)

    thresholds = {tag: args.threshold for tag in PROMPTS}
    thresholds.update({k: float(v) for k, v in (item.split("=") for item in args.thresholds)})
    worst, whole, tag_of = {}, {}, {}  # 图片主干 → 整图与各目标框"生"概率的最小值、整图的"生"概率、类名
    with torch.no_grad():
        text_features = {t: _features(model.get_text_features(**ti)) for t, ti in text_inputs.items()}
        text_features = {t: f / f.norm(dim=-1, keepdim=True) for t, f in text_features.items()}

        def p_raw_of(img, tag):
            img_f = _features(model.get_image_features(**processor(images=img, return_tensors="pt")))
            img_f = img_f / img_f.norm(dim=-1, keepdim=True)
            probs = (100.0 * img_f @ text_features[tag].T).softmax(dim=-1)[0]
            return float(probs[:raw_counts[tag]].sum())

        for n, (stem, image, tag, box) in enumerate(items, 1):
            with Image.open(image) as im:
                im = im.convert("RGB")
                if stem not in whole:
                    whole[stem] = p_raw_of(im, tag)
                p_raw = whole[stem]
                if box:  # 目标框四周留 15% 边距裁出来单独打分
                    x1, y1, x2, y2 = box
                    mx, my = (x2 - x1) * 0.15, (y2 - y1) * 0.15
                    crop = im.crop((max(0, x1 - mx), max(0, y1 - my), min(im.width, x2 + mx), min(im.height, y2 + my)))
                    p_raw = min(p_raw, p_raw_of(crop, tag))
            worst[stem] = min(worst.get(stem, 1.0), p_raw)
            tag_of[stem] = tag
            if n % 500 == 0:
                print(f"  已处理 {n} 个框（或候选图）", flush=True)

    cooked = sorted((s, p) for s, p in worst.items() if p < thresholds[tag_of[s]])
    with open(os.path.join(REPORTS, f"{report}_clip_scores.csv"), "w", encoding="utf-8") as f:
        f.write("stem,tag,min_p_raw,whole_p_raw\n")  # 全部图片的得分，供抽检和调整阈值
        f.writelines(f"{s},{tag_of[s]},{p:.3f},{whole[s]:.3f}\n" for s, p in sorted(worst.items()))
    out = os.path.join(REPORTS, f"{report}_cooked.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# 由 training/clip_filter.py 生成，{time.strftime('%Y-%m-%d %H:%M:%S')}，模型 {args.model}\n")
        f.write(f"# 规则：整图或任一目标框'生'的概率低于该类阈值即整张排除；阈值 {thresholds}；共 {len(worst)} 张，排除 {len(cooked)} 张\n")
        f.write("# 每行：图片主干 [制表符] 该图最低的'生'概率（排除清单读取时只用第一列）\n")
        f.writelines(f"{s}\t{p:.3f}\n" for s, p in cooked)
    by_tag = {}
    for s, p in worst.items():
        by_tag.setdefault(tag_of[s], [0, 0])
        by_tag[tag_of[s]][0] += 1
        by_tag[tag_of[s]][1] += p < thresholds[tag_of[s]]
    print(f"共 {len(worst)} 张，判为熟 {len(cooked)} 张；按类（总数, 熟）：{by_tag}；用时 {time.time() - started:.0f} 秒")
    print(f"清单：{out}")


if __name__ == "__main__":
    main()
