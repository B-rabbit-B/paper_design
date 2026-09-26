# -*- coding: utf-8 -*-
"""兜底权重路径的一致性测试。

防止再次出现：下载脚本把权重写到 A 处，而识别器去 B 处找，导致 YOLO 兜底静默失效。
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config  # noqa: E402


def _load_download_script():
    path = os.path.join(ROOT, "scripts", "download_model.py")
    spec = importlib.util.spec_from_file_location("download_model", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModelPathTest(unittest.TestCase):
    def test_yolo_model_is_absolute(self):
        self.assertTrue(os.path.isabs(config.YOLO_MODEL))

    def test_download_target_matches_config(self):
        self.assertEqual(os.path.normcase(_load_download_script().OUT),
                         os.path.normcase(config.YOLO_MODEL))


if __name__ == "__main__":
    unittest.main()
