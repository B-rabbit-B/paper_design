# -*- coding: utf-8 -*-
"""training/crawl_commons.py 的离线单元测试：许可过滤和作者清洗（不联网）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "training"))

import crawl_commons as cc  # noqa: E402


class FakeSession:
    """按顺序返回预设的 API 结果，模拟 MediaWiki。"""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return FakeResponse(self.payloads.pop(0))


class FakeResponse:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


def page(title, license_name, artist="", url="http://x/y.jpg"):
    meta = {"LicenseShortName": {"value": license_name}, "Artist": {"value": artist}, "LicenseUrl": {"value": "http://lic"}}
    return {"title": title, "imageinfo": [{"thumburl": url, "url": url, "descriptionurl": "http://page/" + title, "extmetadata": meta}]}


class LicenseTest(unittest.TestCase):
    def setUp(self):
        cc.time.sleep = lambda s: None  # 测试里不真的等待

    def infos(self, pages):
        session = FakeSession([{"query": {"pages": {str(i): p for i, p in enumerate(pages)}}}])
        return cc.file_infos(session, [p["title"] for p in pages])

    def test_keeps_open_licenses(self):
        rows = self.infos([page("File:a.jpg", "CC BY 4.0"), page("File:b.jpg", "CC BY-SA 3.0"),
                           page("File:c.jpg", "CC0"), page("File:d.jpg", "Public domain")])
        self.assertEqual(len(rows), 4)

    def test_drops_non_open_or_unknown_licenses(self):
        rows = self.infos([page("File:a.jpg", "CC BY-NC 2.0"), page("File:b.jpg", "Fair use"),
                           page("File:c.jpg", ""), page("File:d.jpg", "CC BY-ND 4.0")])
        self.assertEqual(rows, [])

    def test_strips_html_from_artist(self):
        rows = self.infos([page("File:a.jpg", "CC BY 4.0", artist='<a href="http://u">Jane Doe</a>')])
        self.assertEqual(rows[0][2], "Jane Doe")

    def test_skips_files_without_image_info(self):
        session = FakeSession([{"query": {"pages": {"1": {"title": "File:gone.jpg"}}}}])
        self.assertEqual(cc.file_infos(session, ["File:gone.jpg"]), [])

    def test_rate_limit_stops_the_run(self):
        class Limited(FakeSession):
            def get(self, url, params=None, timeout=None):
                return FakeResponse({}, status=429)

        with self.assertRaises(cc.RateLimited):
            cc.api(Limited([]), action="query")


class CollectTest(unittest.TestCase):
    def setUp(self):
        cc.time.sleep = lambda s: None

    def test_collects_files_from_subcategories_up_to_depth(self):
        def members(titles):
            return {"query": {"categorymembers": [{"title": t} for t in titles]}}

        session = FakeSession([
            members(["File:a.jpg", "File:note.pdf"]), members(["Category:Sub"]),   # 根分类：文件、子分类
            members(["File:b.png"]), members(["Category:Deep"]),                   # Sub：文件、子分类（超过深度，不再展开）
        ])
        files = cc.collect_files(session, ["Category:Root"], depth=1)
        self.assertEqual(files, ["File:a.jpg", "File:b.png"])  # pdf 被过滤，Deep 没有展开


if __name__ == "__main__":
    unittest.main()
