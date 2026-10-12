# -*- coding: utf-8 -*-
"""从 HF 数据集 HYUNAHKO/ingredients_dataset 中只下载指定食材的图片与标注（YOLO 格式）。

该数据集是 155 类韩国食材的检测集，原图打包成一个 28.5 GB 的 images_original.zip。
zip 的文件目录在包的末尾，这里用 HTTP 范围请求只读目录，再逐个取出需要的图片，
因此只需下载目标食材的部分（4 类约 3500 张）。

**许可：数据集未声明许可，图片风格像商业图库。** 用户已知晓这一风险，决定用于补齐
猪肉、鸡肉、菠菜（2026-10-12），论文中需如实注明。

标注包 labels_original.zip（68 MB）需事先下载到 training/datasets/raw/_hyunahko_meta/：
    https://hf-mirror.com/datasets/HYUNAHKO/ingredients_dataset/resolve/main/labels_original.zip
包内路径为 labels/<split>/<韩文食材名>/<编号>.txt，每个文件夹只有一种食材、一个类别编号。
zip 用 CP437 记录了 UTF-8 的韩文文件夹名，读取时需要还原。

用法（项目根目录、venv 中）：
    python training/download_hyunahko.py
    python training/download_hyunahko.py --folders 삼겹살 시금치
"""
import argparse
import io
import json
import os
import struct
import sys
import time
import unicodedata
import zipfile
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "training", "datasets", "raw")
IMAGES_URL = "https://hf-mirror.com/datasets/HYUNAHKO/ingredients_dataset/resolve/main/images_original.zip"
# 韩文文件夹名 → 本数据源中使用的类名（写入 data.yaml，再由 classes.yaml 的 sources.hyunahko 映射到 33 类）
TAGS = {"삼겹살": "pork_belly", "닭고기": "chicken", "닭가슴살": "chicken_breast", "시금치": "spinach"}
HEADERS = {"User-Agent": "Mozilla/5.0"}


def korean(name):
    """把 zip 按 CP437 解码出来的乱码文件夹名还原成韩文。"""
    try:
        return unicodedata.normalize("NFC", name.encode("cp437").decode("utf-8"))
    except (UnicodeEncodeError, UnicodeDecodeError):
        return unicodedata.normalize("NFC", name)


def split_path(name):
    """'images/train/<文件夹>/<文件名>' → (split, 韩文文件夹, 文件名主干)；不符合时返回 None。"""
    parts = name.split("/")
    if name.startswith("__MACOSX") or len(parts) != 4 or not parts[3]:
        return None
    return parts[1], korean(parts[2]), os.path.splitext(parts[3])[0]


class RangeFile(io.RawIOBase):
    """把远程文件包装成可随机读取的文件对象，供 zipfile 读取末尾的文件目录。"""

    def __init__(self, url, session):
        self.url, self.session, self.pos = url, session, 0
        head = session.head(url, allow_redirects=True, timeout=60)
        head.raise_for_status()
        self.size = int(head.headers["Content-Length"])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: 0, 1: self.pos, 2: self.size}[whence] + offset
        return self.pos

    def readinto(self, buffer):
        if self.pos >= self.size or not len(buffer):
            return 0
        data = fetch(self.session, self.url, self.pos, min(self.pos + len(buffer), self.size) - 1)
        buffer[:len(data)] = data
        self.pos += len(data)
        return len(data)


def fetch(session, url, start, end, retries=5):
    for attempt in range(retries):
        try:
            r = session.get(url, headers={**HEADERS, "Range": f"bytes={start}-{end}"}, timeout=120)
            if r.status_code == 206:
                return r.content
            raise IOError(f"HTTP {r.status_code}")
        except Exception:  # 网络抖动重试
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def read_member(session, info):
    """按本地文件头取出一个 zip 成员的内容并校验 CRC。"""
    header = fetch(session, IMAGES_URL, info.header_offset, info.header_offset + 29)
    signature, *_, name_len, extra_len = struct.unpack("<4s5H3L2H", header)
    if signature != b"PK\x03\x04":
        raise IOError("本地文件头签名不对")
    start = info.header_offset + 30 + name_len + extra_len
    raw = fetch(session, IMAGES_URL, start, start + info.compress_size - 1)
    if info.compress_type == zipfile.ZIP_STORED:
        data = raw
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompressobj(-15).decompress(raw)
    else:
        raise IOError(f"不支持的压缩方式 {info.compress_type}")
    if zlib.crc32(data) & 0xFFFFFFFF != info.CRC:
        raise IOError("CRC 校验失败")
    return data


def main():
    import requests
    from PIL import Image

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--folders", nargs="+", default=list(TAGS), help="韩文食材文件夹名（默认：五花肉、鸡肉、鸡胸、菠菜）")
    parser.add_argument("--labels-zip", default=os.path.join(RAW, "_hyunahko_meta", "labels_original.zip"))
    parser.add_argument("--out", default=os.path.join(RAW, "hyunahko"))
    parser.add_argument("--max-side", type=int, default=1280)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    unknown = [f for f in args.folders if f not in TAGS]
    if unknown:
        sys.exit(f"没有为这些文件夹定义类名：{unknown}，请先在 TAGS 中补充")
    wanted = set(args.folders)
    started = time.time()

    # 1. 标注：收集目标文件夹的标注内容与类别编号
    labels, ids = {}, defaultdict(Counter)
    with zipfile.ZipFile(args.labels_zip) as z:
        for info in z.infolist():
            key = split_path(info.filename)
            if key and key[1] in wanted and info.filename.endswith(".txt"):
                text = z.read(info).decode("utf-8-sig")
                labels[key] = text
                ids[key[1]].update(int(line.split()[0]) for line in text.splitlines() if line.strip())
    class_id = {folder: c.most_common(1)[0][0] for folder, c in ids.items()}
    print(f"标注：{len(labels)} 个；类别编号 {class_id}", flush=True)

    # 2. 图片：只读远程大包末尾的文件目录，挑出有标注的目标图片
    session = requests.Session()
    session.headers.update(HEADERS)
    with zipfile.ZipFile(io.BufferedReader(RangeFile(IMAGES_URL, session), buffer_size=8 << 20)) as z:
        members = [(split_path(i.filename), i) for i in z.infolist() if not i.is_dir()]
    jobs = [(key, info) for key, info in members if key and key in labels]
    print(f"远程包共 {len(members)} 个文件，其中目标图片 {len(jobs)} 张", flush=True)

    def work(job):
        (split, folder, stem), info = job
        name = f"{TAGS[folder]}_{stem}"
        image_path = os.path.join(args.out, "images", split, name + ".jpg")
        if not os.path.exists(image_path):
            try:
                data = read_member(session, info)
            except Exception as exc:
                return name, f"{type(exc).__name__}: {exc}"
            with Image.open(io.BytesIO(data)) as im:
                im = im.convert("RGB")
                im.thumbnail((args.max_side, args.max_side))
                im.save(image_path + ".part", "JPEG", quality=90)
            os.replace(image_path + ".part", image_path)
        with open(os.path.join(args.out, "labels", split, name + ".txt"), "w", encoding="utf-8") as f:
            f.write(labels[(split, folder, stem)].strip() + "\n")
        return name, None

    for split in {key[0] for key, _ in jobs}:
        for kind in ("images", "labels"):
            os.makedirs(os.path.join(args.out, kind, split), exist_ok=True)
    failures = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for n, (name, error) in enumerate(pool.map(work, jobs), 1):
            if error:
                failures[name] = error
            if n % 200 == 0 or n == len(jobs):
                print(f"  已处理 {n}/{len(jobs)}，失败 {len(failures)}", flush=True)

    with open(os.path.join(args.out, "data.yaml"), "w", encoding="utf-8") as f:
        f.write("# 由 training/download_hyunahko.py 生成；编号是原数据集的类别编号\nnames:\n")
        f.writelines(f"  {class_id[folder]}: {TAGS[folder]}\n" for folder in sorted(class_id, key=class_id.get))
    counts = Counter(TAGS[key[1]] for key, _ in jobs)
    manifest = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "https://huggingface.co/datasets/HYUNAHKO/ingredients_dataset",
                "folders": {TAGS[f]: f for f in args.folders}, "class_ids": {TAGS[f]: i for f, i in class_id.items()},
                "images_per_class": dict(counts), "downloaded_images": len(jobs) - len(failures), "failures": failures,
                "license": "未声明（用户已知晓风险，论文中需注明）", "max_side": args.max_side,
                "elapsed_seconds": round(time.time() - started, 1)}
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"完成：下载 {manifest['downloaded_images']} 张，失败 {len(failures)} 张，用时 {manifest['elapsed_seconds']} 秒")


if __name__ == "__main__":
    main()
