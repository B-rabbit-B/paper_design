# training/：数据集构建与模型训练

阶段 1（数据集）、阶段 2（训练评估）的工作都在这里。先读根目录 `CLAUDE.md` 和总纲对应阶段。

## 目录

| 路径 | 内容 | 入库 |
|---|---|---|
| `classes.yaml` | 33 类定义的唯一真源，含各来源的类名映射（`sources`） | 是 |
| `prepare_dataset.py` | 合并主脚本：映射、去重、分组、划分、排除清单、统计 | 是 |
| `sources/` | 数据源适配器：`yolo.py`、`voc.py`、`coco.py` | 是 |
| `verify_dataset.py` | 输出数据集的独立校验（1.4、1.6 的检查命令） | 是 |
| `download_*.py`、`convert_lvis_parquet.py`、`lvis_processed_food.py` | 各来源的下载与转换 | 是 |
| `crawl_openverse.py`、`crawl_commons.py`、`auto_label.py`、`clip_filter.py` | 爬取（Openverse 取 CC0、PDM、BY、BY-SA、BY-NC、BY-NC-SA；Wikimedia Commons 只取 CC0、公有领域、BY、BY-SA）、自动画框、生熟筛选（自动结果必须人工复核） | 是 |
| `make_attribution.py` | 以合并后的数据集为准生成网图来源的署名清单（被去重的图不列入，找不到来源记录就报错） | 是 |
| `fix_nested_boxes.py` | 去掉自动画框结果里套在大框里的小框（原标注备份在 `labels_orig/`，改完必须重新看图） | 是 |
| `normalize_photos.py` | 自拍照片按 EXIF 转正、重命名，供标注 | 是 |
| `check_env.py` | 训练机环境自检（阶段 0 的 0.8–0.13） | 是 |
| `reports/dataset/` | 统计、来源记录、排除清单、署名清单、抽检样图 | 是 |
| `datasets/raw/<来源名>/` | 原始数据；来源名就是 `classes.yaml` 里 `sources` 下的键 | **否** |
| `datasets/yolo/`、`datasets/fridge_test/` | 合并产物 | **否** |
| `data.yaml`、`data_fridge.yaml` | 生成的数据集配置，`path` 是本机绝对路径，换机器要重新生成或修改 | 是 |

## 常用命令（项目根目录，用 `.venv/Scripts/python`）

```bash
python training/prepare_dataset.py --check-classes          # 类别与营养库对得上（1.2）
python training/prepare_dataset.py --sources lvis zenodo mendeley openimages vvrh5 eggdet fishmarket hyunahko lvis_full web_raw_beef web_ginger web_tofu --out training/datasets/yolo   # 合并，约 30 分钟，放后台；用户拍了照片再加 custom
python training/verify_dataset.py training/datasets/yolo --against training/datasets/fridge_test   # 独立校验
python training/prepare_dataset.py --preview 20 --out training/reports/dataset/samples            # 抽检样图
```

需要 transformers 的脚本（`clip_filter.py`、`auto_label.py`）用临时环境，不进项目 venv：
`HF_ENDPOINT=https://hf-mirror.com uv run --no-project --with torch --with transformers --with pillow --with pyyaml python training/clip_filter.py ...`

## 约定

- **排除清单**在 `reports/dataset/`：`*_cooked.txt` 由 `clip_filter.py` 生成，`*_manual.txt` 是人工复核写的，**重跑 CLIP 不会覆盖人工清单**。每行第一列是图片主干，后面的列只给人看。合并时默认使用，`--no-filters` 可关闭用于对比实验。
- 改了 `classes.yaml`（含只加映射）：重跑总纲 0.4、0.6、1.2，并重新合并；改了类别名、编号或顺序，数据集要重建、模型要重训。
- `reports/dataset/fridge_split.json` 一经入库不得修改，`prepare_dataset.py` 检测到它已存在会拒绝重建测试集。
- 所有网上爬取、图库来源的图片都要在 `sources.md` 记录地址、日期、许可；CC 许可的要逐张留署名清单（`web_*_attribution.csv`，必须与数据集里的图片逐一对应）。爬取脚本的许可过滤是版权相关的逻辑，必须有测试，不能放进 ND、未知许可。许可未声明的来源（`hyunahko`）只用于本毕设，论文中注明。
- 署名清单用 `make_attribution.py` 重新生成，不要手工改；每次合并后都要重新生成并确认与数据集逐一对应。
- 测试集 AICook（`aicook`）**只作测试，不进训练集**。
- **自动画框的结果不能在缩略图上过一眼就算复核**：阶段 1 最终审查在原图上发现，我在 320 像素的拼图里漏看了干姜、姜苗、烤豆腐、熟牛肉。复核时放大看（每页 18 张、格子 320 像素以上、带署名清单里的标题），可疑的单独看原图，保留标准要具体写出来（鲜的、整块、框对齐、没有嵌套重叠）；复核完再对数据集里的图随机抽 30 张独立验证一遍。这个来源做了三轮审查才清干净，不要指望一轮复核就够。

## 已知的坑

- 数据集很大（合并后约 5 万张图、近 30 万个框），不要整体读入内存；本机可用内存只有约 1–3 GB。
- Windows 路径长度有限：Zenodo 的长文件名在解压时被截断，对照表在 `raw/zenodo/extracted/long_name_map.csv`。
- 同一来源的 Roboflow 增强副本、视频帧、近重复图会被归为一组，保证同组只进同一个子集；新增来源时先看 `group_key`。近重复指平均哈希相同，或 256 位差异哈希汉明距离不超过 `NEAR_DUP_DISTANCE`（12，跨来源也算）；`verify_dataset.py` 的 `cross_split_dhash`、`against_dhash` 用同一个阈值检查。
- 单个脚本不超过 800 行；`prepare_dataset.py` 现在约 540 行，再往里加功能前先想是否该拆。
