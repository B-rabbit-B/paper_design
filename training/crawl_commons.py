# -*- coding: utf-8 -*-
"""从 Wikimedia Commons 的指定分类或全文搜索爬取开放许可图片（Openverse 的候选图不够用时的补充来源）。

背景：生姜、豆腐在 Openverse 上能爬到的新图已经很少（后几批的新增数量不到 100 张），
而 Commons 的 Ginger、Zingiber officinale、Tofu 等分类里有几百张图，每张都有明确的作者和许可。

做法：
- 从 --categories 指定的分类出发，向下取子分类最多 --depth 层，收集其中的图片文件（jpg、png）；
- 或用 --search 做全文搜索（只搜位图，每个关键词最多 --search-limit 条）：分类里没有收进来的图也能搜到，
  但相关度参差，更需要后面的 CLIP 预筛和人工复核；--skip-manifest 跳过之前批次已下载过的标题；
- 调用 MediaWiki API 取每张图的 1280 像素缩略图地址和 extmetadata（作者、许可、说明页）；
- 许可只要 CC0、公有领域、CC BY、CC BY-SA；缺少许可信息的跳过；
- 请求之间停 1 秒；API 或图片服务器返回 429 时停止，不绕过；User-Agent 带联系方式，符合 Wikimedia 的要求；
- 按 md5 和平均哈希去重；manifest.csv 记录标题、作者、许可、说明页，字段与 crawl_openverse.py 的 manifest 对齐，
  署名清单可以用同一段代码生成。
输出：training/datasets/raw/_web_candidates/<name>/ 下的 jpg 与 manifest.csv（不入库）。

用法（项目根目录、venv 中）：
    python training/crawl_commons.py --name commons_ginger --categories "Category:Ginger" "Category:Zingiber officinale" --depth 1
"""
import argparse
import csv
import hashlib
import io
import os
import re
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, "training", "datasets", "raw", "_web_candidates")
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "paperdesign-thesis/0.1 (undergraduate thesis, academic research; contact: owen@flycarclub.com)"}
EXTS = (".jpg", ".jpeg", ".png")
FIELDS = ("id", "title", "creator", "license", "license_version", "source", "foreign_landing_url", "url")
# 只要 CC0、公有领域、CC BY、CC BY-SA（后面可带版本号和地区，如 "CC BY-SA 4.0"、"CC BY 2.0 kr"）；
# 带 NC（非商业）或 ND（禁止演绎）的一律不要。Commons 本身不接受这两类，但这里不依赖这一点
ALLOWED = re.compile(r"^(cc0|public domain|pd\b|cc[ -]by(-sa)?(?![-\w]))", re.IGNORECASE)


class RateLimited(Exception):
    pass


def api(session, **params):
    resp = session.get(API, params={"format": "json", **params}, timeout=30)
    if resp.status_code == 429:
        raise RateLimited("MediaWiki API 返回 429")
    resp.raise_for_status()
    time.sleep(1)
    return resp.json()


def category_members(session, category, kind):
    """kind 为 'file' 或 'subcat'；返回标题列表。"""
    titles, cont = [], {}
    while True:
        data = api(session, action="query", list="categorymembers", cmtitle=category, cmtype=kind, cmlimit=500, **cont)
        titles += [m["title"] for m in data["query"]["categorymembers"]]
        if "continue" not in data:
            return titles
        cont = data["continue"]


def collect_files(session, categories, depth):
    seen_cats, files = set(), []
    frontier = [(c, 0) for c in categories]
    while frontier:
        cat, level = frontier.pop(0)
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        files += [t for t in category_members(session, cat, "file") if t.lower().endswith(EXTS)]
        if level < depth:
            frontier += [(s, level + 1) for s in category_members(session, cat, "subcat")]
        print(f"  {cat}：累计文件 {len(set(files))}，已访问分类 {len(seen_cats)}", flush=True)
    return sorted(set(files))


def search_files(session, queries, limit=300, skip=()):
    """全文搜索（File 命名空间、只要位图），返回图片文件标题；skip 里的标题不返回。每个关键词最多 limit 条。"""
    titles, seen = [], set(skip)
    for q in queries:
        got, cont = 0, {}
        while got < limit:
            data = api(session, action="query", list="search", srsearch=f"{q} filetype:bitmap", srnamespace=6,
                       srlimit=50, **cont)
            for hit in data["query"]["search"]:
                title = hit["title"]
                if title in seen or not title.lower().endswith(EXTS):
                    continue
                seen.add(title)
                titles.append(title)
                got += 1
                if got >= limit:
                    break
            if "continue" not in data:
                break
            cont = {"sroffset": data["continue"]["sroffset"]}
        print(f"  [{q}] 累计 {len(titles)} 个", flush=True)
    return titles


def file_infos(session, titles):
    """每 50 个标题一批，返回 [(标题, 缩略图地址, 作者, 许可, 许可版本, 说明页)]（只含许可合格的）。"""
    rows = []
    for i in range(0, len(titles), 50):
        data = api(session, action="query", prop="imageinfo", titles="|".join(titles[i:i + 50]),
                   iiprop="url|extmetadata", iiurlwidth=1280)
        for page in data["query"]["pages"].values():
            info = (page.get("imageinfo") or [None])[0]
            if not info:
                continue
            meta = info.get("extmetadata", {})
            license_name = meta.get("LicenseShortName", {}).get("value", "")
            if not ALLOWED.match(license_name):
                continue
            artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
            rows.append((page["title"], info.get("thumburl") or info["url"], artist, license_name,
                         meta.get("LicenseUrl", {}).get("value", ""), info["descriptionurl"]))
    return rows


def ahash(jpg):
    from PIL import Image

    with Image.open(io.BytesIO(jpg)) as im:
        pixels = list(im.convert("L").resize((8, 8), Image.BILINEAR).tobytes())
    mean = sum(pixels) / 64
    return sum(1 << i for i, p in enumerate(pixels) if p > mean)


def main():
    import requests
    from PIL import Image

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="输出子目录名，如 commons_ginger")
    parser.add_argument("--categories", nargs="*", default=[], help='如 "Category:Ginger"')
    parser.add_argument("--search", nargs="*", default=[], help="全文搜索关键词，如 \"tofu block\"")
    parser.add_argument("--search-limit", type=int, default=300, help="每个搜索关键词最多取多少条（默认 300）")
    parser.add_argument("--skip-manifest", nargs="*", default=[], help="之前批次的 manifest.csv；其中的标题不再下载")
    parser.add_argument("--depth", type=int, default=1, help="向下取几层子分类（默认 1）")
    args = parser.parse_args()
    if not args.categories and not args.search:
        parser.error("需要 --categories 或 --search")
    started = time.time()
    out = os.path.join(OUT_ROOT, args.name)
    os.makedirs(out, exist_ok=True)

    session = requests.Session()
    session.headers.update(UA)
    try:
        known = set()
        for path in args.skip_manifest:
            with open(path, encoding="utf-8") as f:
                known |= {row["title"] for row in csv.DictReader(f)}
        titles = collect_files(session, args.categories, args.depth) if args.categories else []
        titles += search_files(session, args.search, args.search_limit, skip=known | set(titles))
        titles = [t for t in titles if t not in known]
        infos = file_infos(session, titles)
    except RateLimited as e:
        raise SystemExit(f"{e}，停止（不绕过）")
    print(f"文件 {len(titles)} 个，许可合格 {len(infos)} 个", flush=True)

    seen_md5, seen_hash, rows = set(), set(), []
    for title, url, artist, license_name, license_url, page_url in infos:
        r = session.get(url, timeout=60)
        if r.status_code == 429:
            print("图片服务器返回 429，停止（不绕过）")
            break
        time.sleep(1)
        if r.status_code != 200:
            continue
        try:
            with Image.open(io.BytesIO(r.content)) as im:
                im = im.convert("RGB")
                if min(im.size) < 300:
                    continue
                im.thumbnail((1280, 1280))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=90)
        except Exception:
            continue
        jpg = buf.getvalue()
        md5, h = hashlib.md5(jpg).hexdigest(), ahash(jpg)
        if md5 in seen_md5 or h in seen_hash:
            continue
        seen_md5.add(md5)
        seen_hash.add(h)
        name = f"{args.name}_{len(rows):04d}.jpg"
        with open(os.path.join(out, name), "wb") as f:
            f.write(jpg)
        # 字段与 crawl_openverse.py 的 manifest 对齐：id、title、creator、license、license_version、source、foreign_landing_url、url
        rows.append((name, title, title, artist, license_name, license_url, "wikimedia", page_url, url, args.name))
    with open(os.path.join(out, "manifest.csv"), "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([("file", *FIELDS, "query"), *rows])
    print(f"完成：保存 {len(rows)} 张，用时 {time.time() - started:.0f} 秒，目录 {out}")


if __name__ == "__main__":
    main()
