# tests/：单元测试

只用标准库 `unittest`，不依赖 pytest。先读根目录 `CLAUDE.md`。

```bash
.venv/Scripts/python -m unittest discover -s tests           # 全部，提交前必须通过
.venv/Scripts/python -m unittest discover -s tests -p "test_make_attribution.py"   # 单个文件
```

## 文件

| 文件 | 测什么 |
|---|---|
| `test_food_classes.py` | 33 类定义的加载与校验、来源映射 |
| `test_model_path.py` | 兜底权重路径在下载脚本与识别器之间一致（防止权重下载到 A 处、识别器去 B 处找） |
| `test_prepare_dataset.py` | 合并脚本：适配器、去重、分组、划分、排除清单、预览 |
| `test_verify_dataset.py` | 输出数据集的独立校验 |
| `test_fix_nested_boxes.py`、`test_make_attribution.py` | 嵌套框去除、署名清单与数据集逐一对应 |
| `test_crawl_commons.py`、`test_download_openimages.py` | 爬取与下载脚本的离线部分（许可过滤、分批、选图、清理旧文件），不联网 |
| `test_normalize_photos.py`、`test_lvis_processed_food.py` | 照片预处理、LVIS 熟食排除清单 |

## 约定

- **测试不联网、不加载大模型、不依赖本机的数据集和数据库**：用 `tempfile` 在临时目录里造数据。需要读真实 `classes.yaml` 的测试是例外，因为它是仓库里的文件。
- 版权相关的逻辑（爬取的许可过滤）必须有测试，不能放进 ND、未知许可。
- 修 bug 先写能复现它的测试，看它失败，再修。
- 脚本在 `training/`、`scripts/` 里，测试通过 `sys.path` 引入，注意脚本里不要在导入时就执行副作用。
- 项目还没有接 CI，所以这一步靠自觉；加 CI 要等用户同意。
