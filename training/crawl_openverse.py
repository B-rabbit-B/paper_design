# -*- coding: utf-8 -*-
"""从 Openverse 爬取开放许可（CC）图片，作为公开检测集中缺少的类别（例如生牛肉）的候选图。

用户于 2026-10-12 决定：生牛肉在免登录、许可清晰的公开检测集里找不到，改为从网上爬取。
先试过 Bing 图片搜索，结果相关度很低（抽样 48 张只有 1 张是生牛肉），版权也不明，所以改用
Openverse（https://openverse.org，WordPress 维护的开放许可媒体搜索，图片主要来自 Flickr、Wikimedia）。
每张图都记下作者、许可和原始页面，论文中可以逐张注明出处。

做法：
- 多个英文关键词，逐页调用 Openverse 匿名 API（每页 20 条，每个关键词最多 12 页）。不按"照片"类别过滤：
  Flickr 上大部分照片没有标类别，加上这个条件结果会少约三分之二，插画等非照片交给后面的人工核对剔除；
- 许可只要 CC0、PDM、BY、BY-SA、BY-NC、BY-NC-SA，不要 ND（禁止演绎，标注后的数据集可能算演绎作品）；
- 每页之间停 1 秒；API 返回 429（限流）时停止，不绕过；
- 跳过短边小于 300 像素的图，长边超过 1280 的缩小；按 md5 和 64 位平均哈希去重；
- manifest.csv 记录每张图的 Openverse id、标题、作者、许可、来源站点、原始页面和关键词。
输出：training/datasets/raw/_web_candidates/<name>/ 下的 jpg 与 manifest.csv（不入库）。

用法（项目根目录、venv 中）：
    python training/crawl_openverse.py --name raw_beef --queries "raw beef" "raw steak" "raw ground beef"
"""
import argparse
import csv
import hashlib
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, "training", "datasets", "raw", "_web_candidates")
API = "https://api.openverse.org/v1/images/"
UA = {"User-Agent": "paperdesign-thesis/0.1 (undergraduate thesis, academic research)"}
LICENSES = "cc0,pdm,by,by-sa,by-nc,by-nc-sa"
FIELDS = ("id", "title", "creator", "license", "license_version", "source", "foreign_landing_url", "url")


def search(session, query, max_pages):
    """返回该关键词的结果列表（Openverse 的原始字典）；遇到限流或没有更多结果时提前结束。"""
    results = []
    for page in range(1, max_pages + 1):
        resp = session.get(API, timeout=30, params={"q": query, "page": page, "page_size": 20, "license": LICENSES})
        if resp.status_code == 429:
            print(f"  [{query}] 第 {page} 页被限流（429），停止该关键词")
            return results, True
        if resp.status_code != 200:
            break
        data = resp.json()
        results += [dict(r, query=query) for r in data["results"]]
        if page >= data.get("page_count", 0):
            break
        time.sleep(1)
    return results, False


def fetch(item):
    """下载并校验一张图；返回 (jpg 字节, 结果字典) 或 None。"""
    import requests
    from PIL import Image

    try:
        r = requests.get(item["url"], headers=UA, timeout=30)
        if r.status_code != 200:
            return None
        with Image.open(io.BytesIO(r.content)) as im:
            im = im.convert("RGB")
            if min(im.size) < 300:
                return None
            im.thumbnail((1280, 1280))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=90)
        return buf.getvalue(), item
    except Exception:
        return None


def ahash(jpg):
    from PIL import Image

    with Image.open(io.BytesIO(jpg)) as im:
        pixels = list(im.convert("L").resize((8, 8), Image.BILINEAR).tobytes())
    mean = sum(pixels) / 64
    return sum(1 << i for i, p in enumerate(pixels) if p > mean)


def main():
    import requests

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="输出子目录名，如 raw_beef")
    parser.add_argument("--queries", nargs="+", required=True)
    parser.add_argument("--max-pages", type=int, default=12, help="每个关键词最多翻几页（每页 20 条）")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--skip-manifest", nargs="*", default=[],
                        help="之前批次的 manifest.csv；其中的 Openverse id 不再下载（分批爬取同一类别时用）")
    args = parser.parse_args()
    started = time.time()
    out = os.path.join(OUT_ROOT, args.name)
    os.makedirs(out, exist_ok=True)

    session = requests.Session()
    session.headers.update(UA)
    items, seen_ids = [], set()
    for path in args.skip_manifest:
        with open(path, encoding="utf-8") as f:
            seen_ids |= {row["id"] for row in csv.DictReader(f)}
    for q in args.queries:
        results, limited = search(session, q, args.max_pages)
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                items.append(r)
        print(f"  [{q}] 本词 {len(results)} 条，累计不重复 {len(items)} 条", flush=True)
        if limited:
            break

    seen_md5, seen_hash, rows = set(), set(), []
    skipped = 0  # 下载失败、过小、无法解码的图（fetch 返回 None，没有区分原因）
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(fetch, items):
            if result is None:
                skipped += 1
                continue
            jpg, item = result
            md5, h = hashlib.md5(jpg).hexdigest(), ahash(jpg)
            if md5 in seen_md5 or h in seen_hash:
                continue
            seen_md5.add(md5)
            seen_hash.add(h)
            name = f"{args.name}_{len(rows):04d}.jpg"
            with open(os.path.join(out, name), "wb") as f:
                f.write(jpg)
            rows.append((name, *(item.get(k) or "" for k in FIELDS), item["query"]))
    with open(os.path.join(out, "manifest.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([("file", *FIELDS, "query"), *rows])
    print(f"完成：结果 {len(items)} 条，保存 {len(rows)} 张（下载失败或过小 {skipped} 张，重复 {len(items) - len(rows) - skipped} 张），"
          f"用时 {time.time() - started:.0f} 秒，目录 {out}")


if __name__ == "__main__":
    main()
