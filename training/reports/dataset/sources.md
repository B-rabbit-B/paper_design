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

## 过渡版构建结果（2026-10-12，四个公开来源）

Roboflow 数据和自采照片到位之前，先用 lvis、zenodo、mendeley、openimages 四个来源合并出一版，目的是把整条流程跑通。命令是 `python training/prepare_dataset.py --sources lvis zenodo mendeley openimages`，其中 mendeley 默认只进训练集。

| 指标 | 结果 |
|---|---|
| 图片数 | 训练集 23678、验证集 2519、测试集 2584 |
| 训练框数 | 303054 |
| md5 去重 | 3416 张 |
| 映射后没有框而丢弃 | 6825 张 |
| 坏标注 | 12 个 |
| 跨子集的重复、近重复 | 0、0 |
| 耗时 | 约 10 分钟 |
| ultralytics 标注扫描 | 三个子集全部 0 损坏、0 背景图 |
| CPU 试训练 | 1% 数据、1 轮，263 秒，流程跑通 |

各类框数见 `yolo/summary.json` 和 `yolo/class_distribution.png`。训练框数低于 200 的有：

- **0 框，等 Roboflow**：白菜、菠菜、鸡蛋、鸡肉、猪肉、牛肉、鱼。
- **生姜**：60 框。只有 LVIS 有这一类，需另找来源或补拍。
- **牛奶**：188 框。Roboflow 的冰箱数据集可补。
- **豆腐**：210 框，刚好过线；验证集、测试集各只有 13 框，评估会很不稳定，Roboflow 可补。

## 已知问题（训练前需要处理或在论文中说明）

1. **类别极不均衡**。橙子、苹果、香蕉各有 4 万到 5.6 万个训练框，豆腐只有 210 个，相差两百多倍。主要原因是 LVIS 把成串、成堆的果实逐个标注，单张图最多有 458 个框。阶段 2 训练前，需要考虑按类限制框数或对少数类过采样。
2. **LVIS 标注了切碎和加工后的食材**。抽检中看到热狗上的洋葱碎、沙拉里的胡萝卜丝、烤番茄片都被当作整类标注。本项目要识别的是完整的生鲜食材，这类样本是噪声，也是胡萝卜、洋葱框数虚高的原因之一。可以考虑过滤极小的框，或单图同类框数过多的图。是否过滤由用户决定。
3. **LVIS 是联合标注数据集**，每张图只保证部分类别标全，存在漏标，训练时漏标的物体会被当作背景。
4. **拍摄场景与冰箱差异大**。Zenodo 多是田间和果树上的果蔬，Mendeley 是孟加拉的街边菜摊，Open Images 是各种生活照。这正是实验 E4（域偏移）要量化的内容。
5. **`training/data.yaml` 中的 `path` 是开发机上的绝对路径**。数据集拷到训练机后，需要把它改成训练机上的路径。

## LVIS 过滤（2026-10-12，按用户要求去掉加工食材和密集小框）

过滤只对 lvis 来源生效，原始数据不改动。传入 `--no-filters` 可以关闭过滤，便于在论文中做"过滤与否"的对比实验。两条规则都按整张图排除，不删除单个框。原因是：如果只删框、保留图片，图中的物体就成了未标注的背景，反而会误导训练。

1. **熟食场景**：LVIS 的图片来自 COCO 2017。COCO 标注中含三明治、热狗、披萨、甜甜圈、蛋糕、叉、勺任一类别的图片，整张排除。
   - 清单由 `training/lvis_processed_food.py` 生成，写在 `lvis_processed_food.txt`，共 3757 张，占 LVIS 中能对应到 COCO 的 8221 张的 46%。
   - 规则的依据是每组随机抽 10 张核对：
     - 含熟食类别的，10 张全是加工食材场景。
     - 含叉或勺的，10 张全是熟菜。
     - 只含刀的，混有案板上的整根胡萝卜、整个苹果，所以刀不作为排除条件。
2. **密集小框**：某个类别在一张图中有 20 个以上的框，且这些框面积占整图比例的中位数小于 0.2%，整张排除。
   - 这条规则主要清除胡萝卜丝沙拉、披萨配料和远景市场。
   - 在 3757 张熟食图之外，又排除了 591 张。
   - 阈值依据：LVIS 的框面积中位数是 0.25%，Open Images 是 3.18%。在这个阈值下，用 11% 的图片去掉了 43% 的框。抽样核对时，被排除的图片都是加工食材或远景，正常的整果堆、成堆胡萝卜都被保留了下来。

**过滤效果**：

| 指标 | 过滤前 | 过滤后 |
|---|---|---|
| LVIS 训练图片 | 6215 | 3078 |
| 全部训练图片 | 23678 | 20520 |
| 训练框总数 | 30.3 万 | 21.1 万 |

降幅最大的类别是洋葱 88%、生菜 77%、玉米 74%、蘑菇 69%、葡萄 64%、香蕉 58%，与抽检中看到的配料类加工食材相符。

**过滤后仍需处理**：

- 大蒜、豆腐、生姜主要靠 LVIS 提供数据，过滤后降到 183、116、57 框，需要另找来源。
- 从留下的 LVIS 训练图中随机抽 15 张，仍有约 4 张是碗里或盘里的熟菜、饮料里的柠檬片。这些图在 COCO 中没有标注叉、勺或熟食类别。如果把"碗"也加入排除条件，可以再清掉一部分，但会误伤碗里的整颗生西兰花这类正常样本，目前没有加入。
- 类别不均衡仍然严重：橙子 4.9 万框、苹果 4 万框，主要来自 Zenodo 的果树图片；非零类别中，最多与最少相差约 860 倍。需要在阶段 2 处理。
