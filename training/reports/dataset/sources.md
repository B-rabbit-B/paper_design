# 数据来源记录

对应总纲验收项 1.1。所有原始数据放在 `training/datasets/raw/<来源名>/`，该目录已被 git 忽略。来源名就是 `training/classes.yaml` 中 `sources` 下的键名。

最后更新：2026-10-12。各类最终的框数以 `training/reports/dataset/yolo/summary.json` 为准。

## 总表

| 来源名 | 数据集 | 下载日期 | 许可 | 原始规模 | 本项目用途 | 状态 |
|---|---|---|---|---|---|---|
| `lvis` | LVIS 果蔬子集（henningheyen） | 2026-10-12 | 代码 MIT；标注 CC BY 4.0（LVIS） | 63 类；train 6721 / val 1500 / test 180 | 主数据集，可划入训练、验证、测试 | 下载中 |
| `zenodo` | Multi-Class Fruit and Vegetable Detection Dataset | 2026-10-12 | CC BY 4.0 | 30 类，20216 张（train 15944 / valid 2582 / test 1690），1.0 GB | 主数据集 | 已下载、已解压、类名已映射 |
| `mendeley` | Vegetable Object Detection Dataset from Bangladesh v3 | 2026-10-12 | CC BY 4.0 | 22 类，3534 张，VOC 格式 | **只进训练集**的补充源 | 已下载、已解压 |
| `openimages` | Open Images V7 按类子集 | 2026-10-12 | 标注 CC BY 4.0；图片 CC BY 2.0 | 18 类，每类至多 600 张，共 6872 张 | 补充各类样本 | 已下载，0 张失败 |
| `custom` | 自采国内冰箱、菜篮、案板照片 | 待拍摄 | 自有 | 计划 300–500 张 | 独立测试集，其中一半用于微调实验 | 待拍摄 |
| `rf_*` | Roboflow Universe 上的 11 个公开检测集 | 待下载 | 均为 CC BY 4.0 | 见下文 | 补齐肉、鱼、大白菜、菠菜、鸡蛋、牛奶等公开集缺少的类别 | 需用户用自己的账号下载 |

## 各来源说明

### lvis：LVIS 果蔬子集

- **地址**：https://huggingface.co/datasets/henningheyen/LVIS_Fruits_And_Vegetables ，国内通过 https://hf-mirror.com 镜像访问。原作者的 GitHub 仓库：https://github.com/henningheyen/Fruits-And-Vegetables-Detection-Dataset 。
- **获取方式**：直接逐个下载散装图片会被镜像站限流，GitHub 仓库里又只有 180 张测试图，所以分两步拼装：
  1. 下载 5 个 parquet 文件，共约 1.4 GB，里面有全部图片和原始文件名，但没有框标注。
  2. 以 2 个并发下载约 8400 个标注 txt。

  然后用 `training/convert_lvis_parquet.py` 把图片和标注拼回标准目录。已验证 parquet 中的 180 张测试图与 GitHub 原图按 md5 逐一相同。
- **能映射的类别**：23 类。白菜、菠菜、芒果、鸡蛋、鸡肉、猪肉、牛肉、鱼、虾、牛奶不在其中。原始类名里 `Tomato` 与 `tomato`、`Strawberry` 与 `strawberry` 各是两个重复类，都映射到同一类。
- **注意**：文件名带有 `.rf.<hash>`，说明经过 Roboflow 导出。同一原图的增强副本由 `prepare_dataset.py` 归为一组，只会进入同一个子集。

### zenodo：多类果蔬检测数据集

- **地址**：https://zenodo.org/records/18904638 ，DOI 10.5281/zenodo.18904638。开题报告参考文献 [15] 就是它。
- **获取方式**：`curl -L -o AgricultureDataset.zip https://zenodo.org/api/records/18904638/files/AgricultureDataset.zip/content`。用 Python urllib 访问 Zenodo API 会返回 403，用 curl 正常。
- **说明**：由 62 个 Roboflow 公开项目清洗合并而成，Roboflow 项目地址 https://universe.roboflow.com/vision-rzoan/datasettfg-2502 。
- **解压**：有 944 个文件名过长，超过了 Windows 的路径长度上限。解压时把它们缩短为"前 80 个字符 + `~` + 原名 md5 前 8 位 + 原 `.rf.<hash>` 后缀"，图片和标注同步改名，对照表在 `raw/zenodo/extracted/long_name_map.csv`。
- **能映射的类别**：13 类，分别是西红柿、茄子（原名 Aubegine）、胡萝卜、青椒（原名 Pepper）、生菜（原名 Salad）、苹果、香蕉、橙子、梨、葡萄、草莓、柠檬、芒果。Pepper 和 Salad 各抽 6 张核实过：Pepper 是田间的红、黄、绿甜椒，Salad 是生菜等叶菜，但混有部分混合沙拉叶。
- **重复较多**：用 Zenodo 和 Mendeley 试合并时，按 md5 去掉了 3416 张完全相同的图。这是因为它由多个 Roboflow 项目合并而来，项目之间互有重复。
- **场景**：大多是田间、果树上的果蔬，与冰箱场景差异大，这是实验 E4 要量化的域偏移。

### mendeley：孟加拉蔬菜检测数据集

- **地址**：https://data.mendeley.com/datasets/gnc4s3z2mf/3 ，DOI 10.17632/gnc4s3z2mf.3。
- **获取方式**：`curl -L -o gnc4s3z2mf-3.zip https://data.mendeley.com/public-api/zip/gnc4s3z2mf/download/3`。这个地址会跳转到一个带签名的 S3 链接，只能用 GET 下载，用 HEAD 检查会返回 403。压缩包 217 MB，共 3534 张 jpg 和 3534 个 VOC xml。
- **为什么只进训练集**：3534 张图全部是从 **10 段**视频里抽出的帧，相邻帧几乎一样。按视频分组之后，测试集最多只能分到 1 段视频，评估结果会被这段视频严重带偏。所以它只用来扩充训练样本，不参与验证和测试。
- **能映射的类别**：西红柿、黄瓜、茄子、土豆、胡萝卜（原名 Carrots）、青椒（原名 Capsicum）、南瓜、菜花、柠檬，共 9 类。
  - 原始的 `Cabbage` 有 1678 个框，但它是卷心菜不是大白菜，等用户决定后再处理。
  - 绿辣椒、香菜、四季豆、苦瓜等不在 33 类中，不映射。
  - 当地的柠檬是绿色的小青柠，和国内常见的黄柠檬外观不同。因为只进训练集，影响有限，论文中需要说明。

### openimages：Open Images V7 子集

- **地址**：https://storage.googleapis.com/openimages/web/download_v7.html 。
- **获取方式**：实测**国内可以直连**，不需要代理。
  - 框标注 CSV 在 storage.googleapis.com 上，训练集标注约 2.3 GB，下载速度约 0.9 MB/s。
  - 图片在 open-images-dataset.s3.amazonaws.com 上。
  - 用 `training/download_openimages.py` 按类别抽取图片，含群组框或非实物描绘的图片整张排除。
- **类别抽检**：从验证集各随机抽 6 张，结论如下。
  - `Chicken`：6 张全是活鸡，不能作为"鸡肉"。
  - `Fish`：4 张是水中的活鱼，只有 2 张是盘中或烤架上的鱼。
  - `Egg`：3 张是彩绘复活节蛋，另有沙拉里的蛋片和一盒生鸡蛋。
  
  因此 Chicken 和 Fish 不采用，Egg 是否采用等用户决定。
- **能映射的类别**：西红柿、黄瓜、土豆、胡萝卜、青椒、西兰花、南瓜、蘑菇、苹果、香蕉、橙子、梨、葡萄、草莓、柠檬、芒果、虾、牛奶，共 18 类。
- **实际下载**：运行 `python training/download_openimages.py --per-class 600 --classes <上述 18 个类名>`，选中并下载 6872 张，0 张失败，长边超过 1280 的已缩小，共 1.9 GB，用时约 18 分钟。各类框数见 `raw/openimages/manifest.json`。只有芒果（230 框）和牛奶（242 框）偏少。

### custom：自采数据

- **拍摄规范**：见 docs/plan/01 §5。
- **流程**：
  1. 把照片放到 `training/datasets/raw/custom_photos/`。
  2. 运行 `python training/normalize_photos.py`，按 EXIF 转正、限制长边、统一重命名。
  3. 用 labelImg 以 YOLO 格式标注，图片目录是 `raw/custom/images/all`，标注目录是 `raw/custom/labels/all`，类别表已自动生成。
  4. 运行 `python training/prepare_dataset.py --sources custom --no-split`，生成独立测试集和 50/50 固定划分。

### rf_*：Roboflow Universe 补充集

- **为什么需要**：猪肉、牛肉、鸡肉、鱼、大白菜、菠菜，在上面几个来源中都没有合格数据。Open Images 的 Chicken、Fish 是活鸡、活鱼，Cabbage 是卷心菜，Egg 约一半是彩绘蛋。
- **调研结论**（2026-10-12）：每一类都能在 Roboflow 上凑到 200 个以上的训练框，清单见 `training/download_roboflow.py` 中的 `DATASETS`，全部为 CC BY 4.0。
  - 覆盖面最广的是 `yolov5-rznzw/food-ingredients-7txer`，一次覆盖猪、牛、鸡、鱼、大白菜、蛋、虾、豆腐。
  - 真正的冰箱场景只有 `gracelearning/hien_fridge-tathx`，标注了鸡蛋和牛奶盒。
  - 菠菜只有网络图，最弱，建议另外补拍。
- **获取方式**：导出必须登录 Roboflow 账号，需要用户用自己的账号下载。可以把 API Key 设到环境变量后运行 `uv run --no-project --with roboflow python training/download_roboflow.py`，也可以在网页上选 YOLOv8 格式导出，解压到同名目录。
- **注意**：很多版本做过 2～3 倍增强。增强副本的文件名是 `原名_jpg.rf.<hash>`，由 `prepare_dataset.py` 按原名分组，保证不会跨子集。但它们会让框数虚高，论文中需要说明。
- **未采用**：
  - `halal-*` 系列（pork-only、beef-only、chicken-only）：标为 Public Domain，但图上有图库水印，版权声明不可信。
  - `food-w4zm1/recipe-ingredients-cn`：许可是 CC BY-NC-SA，禁止商用；另外几个 CC BY 数据集已经够用。

## 未采用的来源

| 来源 | 原因 |
|---|---|
| Kaggle 上的各镜像 | 下载需要登录账号，国内访问还要代理；内容与上面的来源重复 |
| FoodSeg103、UEC、Nutrition5k 等 | 菜品级或分割数据，不适用于生鲜食材检测，只在论文综述中引用（见 docs/plan/01 §2） |
| CSDN、面包多等平台上的打包数据 | 来源和许可不明，论文中无法引用 |
