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


class BatchTest(unittest.TestCase):
    def test_batches_stay_within_the_url_length_budget(self):
        # 全文搜索得到的文件名可能很长，50 个标题拼进 URL 会超过服务器的上限（实测返回 414），要按总长度分批
        titles = [f"File:{'x' * 180}{i}.jpg" for i in range(30)]
        batches = cc.batch_titles(titles, budget=2000)
        self.assertEqual([t for b in batches for t in b], titles)  # 不丢、不重、不乱序
        self.assertGreater(len(batches), 1)
        self.assertTrue(all(len("|".join(b)) <= 2000 for b in batches))
        self.assertTrue(all(len(b) <= 50 for b in batches))

    def test_many_short_titles_are_capped_at_50_per_batch(self):
        batches = cc.batch_titles([f"File:{i}.jpg" for i in range(120)], budget=100000)
        self.assertEqual([len(b) for b in batches], [50, 50, 20])

    def test_single_oversized_title_still_gets_its_own_batch(self):
        batches = cc.batch_titles(["File:" + "y" * 3000 + ".jpg", "File:a.jpg"], budget=2000)
        self.assertEqual(len(batches), 2)


class SearchTest(unittest.TestCase):
    def setUp(self):
        cc.time.sleep = lambda s: None

    @staticmethod
    def hits(titles, more=False):
        data = {"query": {"search": [{"title": t} for t in titles]}}
        if more:
            data["continue"] = {"sroffset": 50}
        return data

    def test_search_collects_images_only_and_pages_until_limit(self):
        session = FakeSession([self.hits(["File:a.jpg", "File:b.pdf"], more=True), self.hits(["File:c.png", "File:d.jpg"])])
        files = cc.search_files(session, ["tofu block"], limit=100)
        self.assertEqual(files, ["File:a.jpg", "File:c.png", "File:d.jpg"])
        self.assertIn("filetype:bitmap", session.calls[0]["srsearch"])  # 只搜位图，不要 svg、pdf、视频
        self.assertEqual(session.calls[1]["sroffset"], 50)

    def test_search_stops_at_limit(self):
        session = FakeSession([self.hits(["File:a.jpg", "File:b.jpg"], more=True), self.hits(["File:c.jpg"])])
        self.assertEqual(cc.search_files(session, ["x"], limit=2), ["File:a.jpg", "File:b.jpg"])
        self.assertEqual(len(session.calls), 1)

    def test_known_titles_are_skipped(self):
        session = FakeSession([self.hits(["File:a.jpg", "File:b.jpg"])])
        files = cc.search_files(session, ["x"], limit=10, skip={"File:a.jpg"})
        self.assertEqual(files, ["File:b.jpg"])


if __name__ == "__main__":
    unittest.main()
