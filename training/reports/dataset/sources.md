# 数据来源记录

对应总纲验收项 1.1。所有原始数据放在 `training/datasets/raw/<来源名>/`，该目录已被 git 忽略。来源名就是 `training/classes.yaml` 中 `sources` 下的键名。

最后更新：2026-10-12。各类最终的框数以 `training/reports/dataset/yolo/summary.json` 为准。

## 总表

| 来源名 | 数据集 | 下载日期 | 许可 | 原始规模 | 本项目用途 | 状态 |
|---|---|---|---|---|---|---|
| `lvis` | LVIS 果蔬子集（henningheyen） | 2026-10-12 | 代码 MIT；标注 CC BY 4.0（LVIS）；图片同 `lvis_full`，按 COCO（Flickr）原始许可 | 63 类；train 6721 / val 1500 / test 180 | 主数据集，可划入训练、验证、测试 | 已下载、已转换、已过滤 |
| `zenodo` | Multi-Class Fruit and Vegetable Detection Dataset | 2026-10-12 | CC BY 4.0 | 30 类，20216 张（train 15944 / valid 2582 / test 1690），1.0 GB | 主数据集 | 已下载、已解压、类名已映射 |
| `mendeley` | Vegetable Object Detection Dataset from Bangladesh v3 | 2026-10-12 | CC BY 4.0 | 22 类，3534 张，VOC 格式 | **只进训练集**的补充源 | 已下载、已解压 |
| `openimages` | Open Images V7 按类子集 | 2026-10-12 | 标注 CC BY 4.0；图片 CC BY 2.0 | 19 类，每类至多 600 张，共 7005 张 | 补充各类样本 | 已下载，0 张失败 |
| `vvrh5` | Roboflow ingredient-vvrh5（GitHub 副本） | 2026-10-12 | CC BY 4.0 | 40 类，4690 张（含 2 倍增强副本） | 鸡蛋、卷心菜等 | 已下载 |
| `eggdet` | Egg-Detection（afshin-dini） | 2026-10-12 | MIT | 51 张，白壳 229 框、褐壳 194 框 | 鸡蛋 | 已下载 |
| `fishmarket` | RF100 fish-market | 2026-10-12 | CC BY 4.0 | 19 个鱼种，18498 张，COCO 格式 | 鱼 | 已下载、已解压 |
| `hyunahko` | HYUNAHKO 韩国食材集（按类只取 4 个文件夹） | 2026-10-12 | **未声明** | 五花肉 860、鸡肉 558、鸡胸 1094、菠菜 970 张 | 猪肉、鸡肉、菠菜 | 已下载，已做生熟筛选 |
| `lvis_full` | LVIS v1 全量标注中的牛奶 | 2026-10-12 | 标注 CC BY 4.0；图片按 COCO（Flickr）原始许可 | 129 张，牛奶 157 框（另有牛肉 335 框，不采用） | 牛奶 | 已下载 |
| `web_raw_beef` | Openverse 爬取的生牛肉照片 | 2026-10-12 | CC0、PDM、CC BY、BY-SA、BY-NC、BY-NC-SA（逐张记录） | 两批下载 4700 张，人工复核后保留 218 张、271 框 | 牛肉 | 已下载、已画框、已人工复核 |
| `aicook` | AICook 冰箱数据集（GitHub 副本） | 2026-10-12 | MIT | 30 类，513 张；能映射到本项目的 15 类 | **只作真实场景测试集**，不进训练集 | 已生成 `fridge_test` |
| `web_ginger` | Openverse、Wikimedia Commons 爬取的生姜照片 | 2026-10-13 | CC0、公有领域、CC BY、BY-SA、BY-NC、BY-NC-SA（逐张记录） | 三批候选共约 3800 张，人工复核后保留 207 张、219 框 | 生姜 | 已下载、已画框、已人工复核 |
| `web_tofu` | Openverse、Wikimedia Commons 爬取的豆腐照片 | 2026-10-13 | 同上 | 五批候选共约 3900 张，人工复核后保留 79 张、95 框 | 豆腐 | 已下载、已画框、已人工复核 |
| `custom` | 用户自拍的生姜、豆腐（可选） | 未拍摄 | 自有 | — | 用户 2026-10-13 让我先自己去网上爬取，不再要求自拍；用户之后拍了仍可加入 | 暂不需要 |

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
  
  因此 Chicken、Fish、Egg 都不采用（Egg 改用 eggdet、vvrh5，用户决定）。
- **能映射的类别**：西红柿、黄瓜、土豆、胡萝卜、青椒、西兰花、南瓜、蘑菇、苹果、香蕉、橙子、梨、葡萄、草莓、柠檬、芒果、虾、牛奶、卷心菜，共 19 类。
- **实际下载**：运行 `python training/download_openimages.py --per-class 600 --classes <上述 19 个 Open Images 类名>`（类名顺序见 `raw/openimages/data.yaml`），选中并下载 7005 张，0 张失败，长边超过 1280 的已缩小，共约 1.9 GB，用时约 2 分钟（图片已在本地时跳过）。各类框数见 `raw/openimages/manifest.json`。只有芒果（230 框）和牛奶（242 框）偏少。
- **残留文件的处理（2026-10-13）**：补卷心菜时重新下载过一次，选图结果随类别列表而变，第一次下载（18 类，不含卷心菜）的 211 张图和标注留在目录里，并进入了第一版合并结果，按记录的命令无法复现。这些标注是在没有卷心菜类时写的，图中如有卷心菜会漏标。阶段 1 中期审查发现后，已删除这 211 对文件，并让下载脚本先清理不在本次选图结果中的旧文件；目录现在是 7005 张图、7005 个标注，与 manifest 一致。

### vvrh5：Roboflow ingredient-vvrh5 的 GitHub 副本

- **地址**：原集 https://universe.roboflow.com/ingredients-wzqqk/ingredient-vvrh5/dataset/1 （导出需登录）。实际下载的是 GitHub 仓库 https://github.com/Vaisakh-M-DS/AI-Based-Food-Ingredient-Detection-and-Dish-Recommendation-System 中的 `dataset/` 目录，用稀疏克隆只取该目录。
- **许可**：data.yaml 和 Roboflow 页面都写明 CC BY 4.0。
- **规模**：40 类，4690 张（训练 3439 / 验证 463 / 测试 788），每张原图做了 2 倍增强（水平翻转），图片缩到 300×300 以内。增强副本由 `prepare_dataset.py` 按原名归为一组。
- **能映射的类别**：鸡蛋、卷心菜，以及西红柿、黄瓜、茄子、土豆、胡萝卜、青椒、玉米、洋葱、大蒜、苹果、香蕉、橙子、梨、葡萄、草莓、柠檬、芒果等果蔬。场景是手机拍的家中台面，少量冰箱。

### eggdet：Egg-Detection

- **地址**：https://huggingface.co/datasets/afshin-dini/Egg-Detection ，经 hf-mirror 下载。
- **许可**：afshin-dini 的这一份标 MIT。另一个副本 https://huggingface.co/datasets/industoai/Egg-Detection 内容相同，却标 CC BY-NC 4.0，两处声明互相矛盾，不知哪一份是原始上传。**处理依据**：本毕设是非商业的学术用途，两种许可都允许（CC BY-NC 要求署名、禁止商用）；论文中同时注明两处声明和署名。如果导师或学院认为这个冲突不可接受，可以去掉 eggdet，鸡蛋仍有 vvrh5 的 1117 框（去掉增强副本后约 327 框）。
- **规模**：51 张，white-egg 229 框、brown-egg 194 框，都映射为鸡蛋。场景是木桌上打开的蛋盒，全是生鸡蛋。
- **注意**：标注文件带 UTF-8 BOM，`training/sources/yolo.py` 已改为按 utf-8-sig 读取，否则每个文件的首行会被当成坏框。

### fishmarket：RF100 fish-market

- **地址**：https://huggingface.co/datasets/Francesco/fish-market-ggjso 的 `dataset.tar.gz`（COCO 格式，1.09 GB）。属于 Roboflow 100 基准。
- **许可**：CC BY 4.0。
- **规模**：19 个孟加拉鱼种加一个总类 fish，18498 张（训练 14180 / 验证 1202 / 测试 3116），18591 框。全部映射为"鱼"。
- **场景**：鱼市台面、铁盘上的单条死鱼，抽样 6 张全是离水的生鱼。

### hyunahko：韩国食材集

- **地址**：https://huggingface.co/datasets/HYUNAHKO/ingredients_dataset 。仓库共 64 GB，原图压缩包 `images_original.zip` 有 28.5 GB。
- **获取方式**：`training/download_hyunahko.py` 用 HTTP 范围请求只读压缩包末尾的目录，再按文件夹单独取出需要的成员并校验 CRC，不下载整个压缩包。取了 4 个文件夹：삼겹살（五花肉）、닭고기（鸡肉）、닭가슴살（鸡胸）、시금치（菠菜），共 3482 张，0 张失败，用时约 19 分钟。
- **许可**：**未声明**。图片风格像商业图库。用户已知晓风险（2026-10-12 决定），论文中需注明。
- **生熟筛选**：图库里约有三分之一是烤肉、熟菜、菜肴，见下文"生熟筛选"。

### lvis_full：LVIS v1 全量标注中的牛奶

- **地址**：标注 https://dl.fbaipublicfiles.com/LVIS/lvis_v1_train.json.zip 和 https://dl.fbaipublicfiles.com/LVIS/lvis_v1_val.json.zip （LVIS v1，主页 https://www.lvisdataset.org/dataset ）；图片是 COCO 2017 的，地址取自标注里的 `coco_url` 字段，形如 http://images.cocodataset.org/train2017/{编号}.jpg。
- **获取方式**：`training/download_lvis_full.py` 用 ijson 流式解析 LVIS v1 的训练、验证标注（本机可用内存约 1 GB，不能整个读入），挑出含 `milk` 或 `beef_(food)` 的图，排除熟食场景（披萨、汉堡、牛排、刀叉等）和这两类未标全的图，从 COCO 下载图片。保留 129 张。
- **只映射牛奶**：牛奶 157 框，多为冰箱里的奶盒、奶桶。牛肉 335 框抽样 20 张，只有 2 张是生牛肉，其余是炖菜、牛排，不采用。

### aicook：真实场景测试集

- **地址**：Roboflow 上的 AICook 数据集（导出需登录），实际下载的是 GitHub 仓库 https://github.com/Leemone01/Recipe-Suggestion-over-Object-Detection-and-Word-Embeddings 中的 `Ingredient_Detection/datasets/refined/`（稀疏克隆）。类名取自同仓库 `Ingredient_Detection/training/dataset_kfold/iter_0/data_iter_0.yaml`。
- **许可**：MIT（在 Roboflow 页面源码中确认）。
- **规模**：30 类，513 张，6354 框。能映射到本项目的有 15 类。各类（图片数 / 框数）：西红柿 304 / 305、土豆 299 / 299、胡萝卜 202 / 226、洋葱 222 / 222、玉米 236 / 236、蘑菇 228 / 228、菠菜 207 / 207、苹果 172 / 182、香蕉 222 / 222、草莓 302 / 302、鸡蛋 220 / 220、鸡肉 305 / 356、牛肉 238 / 288、虾 237 / 237、牛奶 207 / 259（以 `fridge_test/summary.json` 的 `per_class_images.val` 为准；一张图可含多类，所以图片数之和大于 513）。
- **用途**：用户决定（2026-10-12）把它当作真实场景测试集，**不进训练集**，代替开题报告中的"自采国内冰箱照片"，偏离之处在论文中说明。生成命令是 `python training/prepare_dataset.py --sources aicook --no-split --out training/datasets/fridge_test`，固定的 50/50 划分在 `fridge_split.json`（微调 256 张、评估 257 张），**不得重新生成**。
- **局限**：同一台冰箱、固定机位，几盒肉和奶反复出现，多样性低；包装是欧洲超市的样式。

### custom：用户自拍的生姜、豆腐（可选，目前没有）

- **经过**：生姜、豆腐只有 LVIS 提供，过滤后只剩 57、116 框，其他免登录来源里也找不到许可清晰的数据。用户 2026-10-12 先决定自己拍照补充；2026-10-13 又说"你先自己去网上爬取"，所以改为 `web_ginger`、`web_tofu`（见下文）。用户以后拍了照片，仍可按下面的流程加入。
- **流程**：
  1. 把照片放到 `training/datasets/raw/custom_photos/`（iPhone 的 HEIC 原图本环境读不了，请改用"最兼容"格式或先转 JPG）。
  2. 运行 `python training/normalize_photos.py`，按 EXIF 转正、限制长边、统一命名为 `custom_NNNN.jpg`。
  3. 用 X-AnyLabeling（`uvx --from x-anylabeling-cvhub xanylabeling`）以 YOLO 格式标注，图片目录是 `raw/custom/images/all`，标注目录是 `raw/custom/labels/all`，类名直接用 `classes.yaml` 中的 `ginger`、`tofu`。
  4. 重新合并数据集时在 `--sources` 中加上 `custom`。

### rf_*：Roboflow Universe 补充集（未采用）

> 用户决定不注册 Roboflow 账号，数据改由免登录渠道获取（2026-10-12）。下面的调研只作记录：其中 ingredient-vvrh5、fish-market、AICook 已改用 GitHub 或 Hugging Face 上的副本（见上文 vvrh5、fishmarket、aicook），`training/download_roboflow.py` 不再使用。

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
5. **`training/data.yaml` 中的 `path` 是开发机上的绝对路径**。数据集拷到训练机后，需要把它改成训练机上的路径。在训练机上重新生成 fridge_test 会被"`fridge_split.json` 已存在"的保护拦下，所以交付时直接拷贝 `training/datasets/fridge_test/`，不要重新生成。
6. **`data_fridge.yaml` 的 `train`、`val`、`test` 都指向 `images/val`**，用它评估没有问题；阶段 5 的 E5 微调必须另建一个只含 `fridge_split.json` 里 ft 半集的 yaml，避免把 eval 半集带进训练。
7. **HYUNAHKO 没有按 EXIF 转正**：`download_hyunahko.py` 重新编码时去掉了 EXIF，但没有转正。输出数据集里所有图片都没有 Orientation≠1 的标记，不能排除原图有旋转标记而标注按显示方向画的情况；抽检的 20 张里有 1 张 hyunahko 图，框是对齐的。图库照片通常已经转正，风险较低，论文中不展开。

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

## 生熟筛选（2026-10-12，HYUNAHKO 与网上爬取的牛肉）

本项目识别的是生鲜食材，但图库型数据里混有大量烤肉、熟菜和菜肴。筛选分两步，结果都写成排除清单，原始数据不改动，清单入库：

1. **CLIP 自动筛选**（`training/clip_filter.py`，模型 openai/clip-vit-base-patch16，零样本）：每类写几句"生"和"熟"的英文描述，分别给整张图和每个目标框（四周留 15% 边距）打分，取"生"的概率最低的一项；低于 0.5 就整张排除。全部得分写在 `<来源>_clip_scores.csv`，排除的图写在 `<来源>_cooked.txt`。
2. **人工复核**：CLIP 保留、但"生"的概率在 0.5～0.8 之间的图逐张看，挑出熟食、菜肴，以及含有未标注的弱势类别（牛肉、鱼、豆腐）的图，写在 `<来源>_manual.txt`。这一段里熟食和生食大约各占一半，直接提高阈值会误删更多生食，所以改为人工判断。

### HYUNAHKO

调整过程如下，每一版都画出 KEEP 和 DROP 的抽检拼图看过：

| 版本 | 做法 | 排除 | 抽检发现的问题 |
|---|---|---|---|
| 1 | 只给目标框打分 | 1324 张 | 菠菜的 KEEP 里混有披萨、蛋饼、沙拉 |
| 2 | 菠菜的负类描述改为"沙拉、披萨、菜肴"（沙拉里的菠菜也是生的，所以负类不写"熟"） | 1421 张 | 菜肴上点缀的菠菜叶单独裁出来像生的，仍然漏判 |
| 3 | 再加整图打分，取整图与各框的最低值 | 1598 张 | KEEP 中 0.5～0.8 一段仍有约一半是熟食，改为人工复核 |

第 3 版各类的结果（总数 / CLIP 排除）：鸡肉 558 / 41，鸡胸 1094 / 659，五花肉 860 / 493，菠菜 970 / 405。鸡肉（닭고기）抽样全是生鸡，所以排除得少。

人工复核了五花肉 117 张、鸡胸 149 张、菠菜 131 张，又排除 67 张（`hyunahko_manual.txt`）：

- 五花肉 22 张：烤盘上已烤熟的、脆皮烤肉、水煮肉、生菜包肉、火锅。烤盘上还是生肉的保留。
- 鸡胸 11 张：熟鸡胸 5 张；另有 6 张同时出现生牛肉或三文鱼，但只标了鸡胸，会让模型把牛肉、鱼当作背景。
- 菠菜 34 张：沙拉、意面、汤、炒菠菜、菠菜饼、菠菜面 31 张；同时出现未标注的豆腐或三文鱼 3 张。

两步合计排除 1665 张，保留 1817 张。抽检中 CLIP 也误删了少量生食，例如烤盘上的生五花肉、锅里的生鸡胸；为了保证留下的都是生食，这部分损失可以接受。

**仍存在的问题**：HYUNAHKO 每张图只标了一个类别。图中同时出现的西红柿、西兰花、蘑菇等没有标注，训练时会被当作背景。这些类别在其他来源中数据充足，影响有限，论文中需要说明。

### 网上爬取的生牛肉（web_raw_beef）

许可清晰的免登录检测集里没有生牛肉：LVIS 的 beef_(food) 几乎全是熟的，AICook 只作测试集。用户决定从网上爬取（2026-10-12）。

1. **先试 Bing 图片搜索**（cn.bing.com）：爬到 324 张候选，抽样 48 张只有 1 张是生牛肉，其余是炖牛肉、母婴图表、飞机、山水等；而且图片版权不明。放弃，脚本未保留。
2. **改用 Openverse**（https://openverse.org ，开放许可媒体搜索，匿名 API 可直连）：`training/crawl_openverse.py`，只要 CC0、PDM、CC BY、BY-SA、BY-NC、BY-NC-SA 许可（不要 ND），每张图记录作者、许可和原始页面。分两批：
   - 第 1 批，18 个关键词（raw beef、raw steak、minced beef、ribeye steak、wagyu 等），每词最多 240 条：结果 3550 条，下载 3158 张。
   - 第 2 批，16 个关键词（ground beef、raw meat、chuck roast、porterhouse steak、beef shank 等），每词最多 120 条，跳过第 1 批已下载的图：结果 1671 条，下载 1542 张。
3. **CLIP 整图预筛**（`clip_filter.py --candidates raw_beef`，负类加上"活牛"）：第 1 批保留 800 张，第 2 批保留 252 张；排除清单 `candidates_raw_beef_cooked.txt`、`candidates_raw_beef2_cooked.txt`。抽检中预筛也误删了少量生牛排，但它的作用是减少后面画框的图片数，保留下来的已经够用。
4. **Grounding DINO 自动画框**（`training/auto_label.py`，模型 IDEA-Research/grounding-dino-tiny，提示词 "raw beef."，box_threshold 0.35，输入短边 512）：两批共 1016 张有检测结果。DINO 几乎在每张图上都能画出框，包括人物、街景和插画，所以它不能代替人工筛选。
5. **人工逐张复核**：1016 张连同框一起看，保留标准是画面主体为生牛肉（整块、切块、肉馅、薄片、超市盒装），框与牛肉基本对齐。保留 218 张，共 271 个框；排除 798 张，写在 `web_raw_beef_manual.txt`（其中 1 张 3D 渲染图是中期审查指出后补排除的），原因如下：

   | 原因 | 张数 |
   |---|---|
   | 无关（人物、街景、插画、海报、包装、3D 渲染图） | 278 |
   | 框不准（重叠、嵌套、漏框、框住整个柜台） | 212 |
   | 不是牛肉（鱼、猪肉、禽肉、羊肉、火腿、香肠） | 88 |
   | 看不清是否为生牛肉 | 96 |
   | 菜肴（生牛肉薄片、生拌、塔塔、炙烤） | 50 |
   | 熟肉 | 36 |
   | 近重复（同一块肉连拍） | 32 |
   | 图中有未标注的本项目类别（香蕉、胡萝卜、洋葱等） | 6 |

- **署名**：保留的 218 张逐张列在 `web_raw_beef_attribution.csv`（标题、作者、许可、原始页面），论文附录引用。202 张来自 Flickr；许可分布为 CC BY 80、BY-NC-SA 57、BY-SA 37、BY-NC 31、CC0 12、PDM 1。含 NC 的图只用于本毕设的非商业学术研究。
- **局限**：多是美食博客、超市、肉铺的照片，冰箱场景很少，只有几张是冰箱或展示冷柜里的生肉，另有一些超市盒装肉。框由模型画出、人工只做了取舍，没有逐个修正坐标。

### 网上爬取的生姜、豆腐（web_ginger、web_tofu）

用户 2026-10-13 的原话："阶段 1 仍在等你的生姜、豆腐照片。你先自己去网上爬取"。流程同生牛肉：爬取 → CLIP 整图预筛 → Grounding DINO 自动画框 → 人工逐张复核，每张保留的图都记录作者与许可。

- **地址**：Openverse https://openverse.org （API https://api.openverse.org/v1/images/）；Wikimedia Commons 的 https://commons.wikimedia.org/wiki/Category:Ginger 、https://commons.wikimedia.org/wiki/Category:Zingiber_officinale 、https://commons.wikimedia.org/wiki/Category:Tofu 及其两层子分类。每张图的原始页面在署名清单的 `foreign_landing_url` 列。
- **下载日期**：2026-10-13。

1. **Openverse**（`crawl_openverse.py`）：许可只要 CC0、PDM、CC BY、BY-SA、BY-NC、BY-NC-SA。
   - 生姜：2 批，共 30 个关键词，下载约 2500 张。
   - 豆腐：4 批，共 60 个关键词，每批跳过前几批已下载的图；下载约 3200 张。第三批以后新增的图已经很少（第四批只有 27 张），说明 Openverse 上的豆腐照片基本爬完了。
2. **Wikimedia Commons**（新增 `training/crawl_commons.py`，带离线测试）：Openverse 不够用，改从 Commons 的 `Category:Ginger`、`Category:Zingiber officinale`、`Category:Tofu` 向下取两层子分类，共约 1200、670 张。许可只要 CC0、公有领域、CC BY、CC BY-SA，脚本用正则过滤，测试里验证了 CC BY-ND、CC BY-NC 不会被放进来；请求之间停 1 秒，User-Agent 带联系方式，遇到 429 就停。
   - **写脚本时发现并修掉的 bug**：第一版正则 `cc by(-sa)?` 会把 `CC BY-ND 4.0` 和 `CC BY-NC 2.0` 也当成合格许可。改成显式排除带 NC、ND 的写法，并补了测试。已下载的 Commons 图片许可分布里没有 ND、NC 的（已核对）。
3. **CLIP 整图预筛**（`clip_filter.py --candidates`）：为生姜、豆腐新增了描述词。生姜的负类包括姜茶、姜饼、菜肴、人物、花草；豆腐的负类包括带酱汁的熟豆腐菜、炸豆腐、汤、人物、餐厅。阈值先用 0.5，抽检后发现 0.5 段混有不少无关图，后几批改用 0.8。
4. **Grounding DINO 自动画框**：提示词 "ginger."、"tofu."。
5. **人工逐张复核**：只复核 CLIP 整图得分不低于 0.8 的图（得分更低的抽样看过，几乎都是无关图，一律排除，原因记为"未复核"）。保留标准：画面主体是鲜的、整块或切块的食材本身，框与食材基本对齐，没有嵌套、重叠的多余框。
   - **生姜**：不要干姜片、姜粉、腌姜（Commons 里有大量中药材和香料图）、姜苗、盆栽，也不要同一块姜的连拍。保留 207 张、219 框。
   - **豆腐**：不要豆腐干、豆皮、腐竹、臭豆腐、豆腐乳、炸豆腐和各种菜肴；保留整块、切块、盒装的白豆腐。保留 79 张、95 框。
   - 排除清单：`web_ginger_manual.txt`（744 张）、`web_tofu_manual.txt`（408 张），每行有原因代码。
- **署名**：`web_ginger_attribution.csv`（207 行）、`web_tofu_attribution.csv`（79 行），与数据集中的图片逐一对应（`docs/acceptance/stage-1/1.11-web-ginger-tofu-attribution.txt`）。生姜 Wikimedia 106 张、Flickr 84 张；豆腐 Flickr 62 张、Wikimedia 17 张。含 NC 的图只用于本毕设的非商业学术研究。
- **局限**：
  - 豆腐图片少，进数据集的训练框 64 个，加上 LVIS 的 149 个才到 213，刚过 200；验证集、测试集里豆腐只有 44、9 个框，评估时很不稳定。
  - 生姜里很多是市场摊位上成堆的姜，框住整堆而不是单块；单块生姜的样本较少。
  - 这些来源多是美食博客、市场、百科类的照片，与冰箱场景差异大。

## 最终版构建结果（2026-10-13，十二个来源）

命令：`python training/prepare_dataset.py --sources lvis zenodo mendeley openimages vvrh5 eggdet fishmarket hyunahko lvis_full web_raw_beef web_ginger web_tofu --out training/datasets/yolo --split 0.8 0.1 0.1 --seed 42`。默认使用 lvis、hyunahko、web_raw_beef、web_ginger、web_tofu 的排除清单（见上文），mendeley 只进训练集。用时约 30 分钟。

这是第四次合并：四来源过渡版 → 十来源版（571fa1e）→ 清理 Open Images 残留、去重复框 → 近义类并入、加入网上爬取的生姜和豆腐。**以这一次为准。**

| 指标 | 结果 |
|---|---|
| 图片数 | 训练集 40900、验证集 4623、测试集 4649 |
| 框数 | 训练集 253144、验证集 23046、测试集 23576 |
| md5 去重 | 3444 张 |
| 映射后没有框而丢弃 | 6880 张 |
| 排除清单 | lvis 3757、hyunahko 1665、web_raw_beef 798、web_ginger 744、web_tofu 408；另有 LVIS 密集小框 591 |
| 同一张图里完全相同的框 | 去掉 57 个 |
| 原始标注中被丢弃的坏框 | 5 个：lvis 1 个（框中心在图片右边缘，一半在图外）、mendeley 4 个（零宽或零高）。输出数据集中没有这些框 |
| 独立校验 `training/verify_dataset.py` | `corrupt=0 unpaired=0 cross_split_md5=0 cross_split_ahash=0 against_md5=0 against_ahash=0`（与 AICook 测试集也没有相同的图片） |
| 各来源训练图片数 | fishmarket 14662, zenodo 8881, openimages 5562, mendeley 3519, vvrh5 3245, lvis 3085, hyunahko 1449, web_raw_beef 174, web_ginger 167, web_tofu 64, lvis_full 50, eggdet 42 |

**训练框数低于 200 的类别：没有**（验收项 1.8 达标）。最少的是 豆腐 213、牛肉 219、生姜 223、猪肉 285、牛奶 292、大蒜 323；最多的是 橙子 53015、苹果 43512、西红柿 28181，最多与最少相差约 249 倍，阶段 2 需要处理类别不均衡。

**验证集、测试集里的稀缺类别很少**，评估时不稳定：生姜 val 38、test 22 个框，豆腐 44、9，牛肉 28、24，猪肉 34、34，牛奶 37、35。论文里这几类的指标要注明样本数，或合并 val 与 test 一起报告。

**过程中修掉的问题**：

1. 第一次合并的坏框是 12 个，其中 LVIS 的 8 个其实是合法的框，只是坐标经浮点运算后超出 [0, 1] 约 0.000005，被过严的越界容差（1e-6）误删。容差改为 1e-3（约等于千像素宽图上的 1 个像素），越界部分随后裁剪，补了测试。
2. Open Images 的 211 对残留文件（见上文 openimages 一节）。
3. 同一张图里完全相同的框（mendeley、vvrh5、openimages 共 57 个）会让框数虚高，Ultralytics 加载时也会去重，现在合并时先去掉。
4. 近义类并入（用户决定，2026-10-13）：青柠（lvis lime、zenodo Lime、vvrh5 lime）并入柠檬，橘子（lvis mandarin orange、clementine）并入橙子，青香蕉（mendeley Green Banana）并入香蕉。柠檬增加了青柠的标注框（lvis、zenodo、vvrh5 的 lime 共 1920 框，按划分分布在三个子集），训练框现在是 11668。

**已知的残留问题**：

- **生熟筛选有残留**：CLIP 判为"生"的概率不低于 0.8 的五花肉里，随机看的 64 张有 2～3 张偏熟或腌制（红烧块、培根），约 4%；菠菜、鸡胸的残留比例没有逐一统计。
- **漏标**：LVIS、Open Images、HYUNAHKO 本来就只标了部分类别，图里的其他食材会被当作背景。1.9 两次抽检共 40 张，漏标 3 张（都在第一次抽检里），见 `docs/acceptance/stage-1/1.9-preview-review.md`。用户决定（2026-10-13）：只统计错框，漏标写进论文。
- **加工食材残留**：LVIS 中碗里的香蕉片、饮料里的柠檬片等没有被熟食场景规则排除。
- **lvis_full 的牛奶图**多是人物、厨房场景，牛奶只是画面角落的小物体，框很小。
