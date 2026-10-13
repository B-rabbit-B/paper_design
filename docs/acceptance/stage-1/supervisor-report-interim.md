# 阶段 1 审查报告（中期）

- 审查时间：2026-10-13
- 分支：`stage-1-dataset`
- 被审查提交：`571fa1ec85718ae3f06f8e1a3b9fe1ee6ab473e4`（HEAD，`571fa1e`）
- 未提交改动：无（审查开始和结束时 `git status --porcelain` 均为空）
- 审查范围（调用方指定）：1.1、1.2、1.3、1.4、1.5、1.6、1.7、1.8、1.10、1.12、1.13，以及本分支相对 master 的代码改动
- 未审查项：1.9（抽检 3/20 漏标，处理方式待用户决定）、1.11（用户自拍的生姜、豆腐照片尚未提供）
- 审查方式说明：
  - 没有重新生成任何数据集、清单或证据文件，也没有运行 `database/init_db.py`，没有加载 CLIP 或 Grounding DINO，没有启动 Web 应用。
  - 下文中的独立核对脚本放在系统临时目录，只读取 `training/datasets/` 下的文件。读取 Ultralytics 的 `labels/*.cache` 时只用 `np.load` 读出，没有改写。
  - `docs/acceptance/stage-1/` 原来不存在，本报告是该目录下的第一个文件。

## 进入条件

**结论：符合 §1.6 例外，可以继续阶段 1。合并前仍有前置条件未满足。**

- `git tag -l "stage-*"` 输出为空，说明 `stage-0-pass` 还没有打。
- §1.6 门禁例外表中有 2026-10-11 的记录：用户决定，阶段 0 只剩训练机检查时，可以从 `stage-0-env` 切出 `stage-1-dataset`。分支图与记录一致：merge-base 是 `958daac`（`stage-0-env` 的最新提交），`f75e47d` 把 `stage-0-env` 合并进了本分支。
- 按例外的补救条件，**阶段 1 合并回 master 之前，阶段 0 必须先合并并打上 `stage-0-pass`**。最终审查时需要复核这一点。

## 验收清单逐项复核

**共性问题：`docs/acceptance/stage-1/` 下没有任何证据文件。** 总纲中阶段 1 的清单项全部未勾选，验收记录也没有自查行。因为这些项还没有勾选，所以不算违反 §1.2。下表的结论依据是本审查员自己重新执行的结果；最终审查之前，每一项都必须按 §1.2 生成以编号开头的证据文件。

| 编号 | 结论 | 依据（实际执行的命令与关键输出，或核对的证据文件） |
|---|---|---|
| 1.1 | **不通过** | 逐行核对了 `training/reports/dataset/sources.md` 中 11 个来源的地址、下载日期、许可和图片数，发现以下问题：① **`lvis_full` 没有写下载地址**，该节只写了"用 download_lvis_full.py 流式解析 LVIS v1 标注，从 COCO 下载图片"。地址只出现在脚本的 docstring 里（`https://dl.fbaipublicfiles.com/LVIS/lvis_v1_train.json.zip` 等）。② **`openimages` 的图片数与实际使用的不一致**：总表写"19 类……共 7005 张"，正文写"18 类……6872 张"，实际进入合并的是 **7216 张**（summary 中 openimages 各子集之和为 5719+759+738=7216；raw 目录中的标注文件按修改时间可分为两批：00:3x 的 211 个是早一次下载的残留，12:4x 的 7005 个对应当前的 `manifest.json`）。③ `aicook` 只写了"Roboflow 上的 AICook 数据集"和 GitHub 仓库名，没有可访问的完整 URL；`vvrh5` 同样只给了仓库名。④ `eggdet` 的同一份内容有两个副本，许可互相矛盾（MIT 与 CC BY-NC 4.0）。执行者选用了 MIT 的副本，但这种许可冲突不在 1.1 的用户例外之内，需要补充说明或请用户确认。核对后符合要求的部分：hyunahko 的"许可未声明"和 web_raw_beef 的 CC 许可已在 1.1 例外中登记；`web_raw_beef_attribution.csv` 有 219 行，与输出数据集中的 219 张 web_raw_beef 图片逐一对应（差集为空），许可分布与 sources.md 一致，没有 ND 许可；12 行缺少作者，其中 11 行是 CC0 的 rawpixel 图片，1 行是 by-sa 的 Wikimedia 图片。没有发现使用 01 §2 D 组"不建议使用"的来源 |
| 1.2 | 通过 | `.venv/Scripts/python training/prepare_dataset.py --check-classes` 输出 `missing: []`，与预期一致。另外，本分支把第 7 类的 `zh` 和 `ingredient` 由"白菜"改为"卷心菜"，按 §1.4 应重跑 0.6。本审查员重跑了 0.4（输出 `33 True`）和 0.6（输出 `[]`），都通过，但本阶段还没有对应的证据文件 |
| 1.3 | 通过 | 执行总纲命令，输出 `train 40489 40489`、`val 4568 4568`、`test 4618 4618`。进一步按文件主干比对，三个子集中图片与标注的主干集合完全相同（对称差为 0），也与 summary.json 的 `split_files` 一致 |
| 1.4 | **不通过** | 执行总纲命令，输出 **`5 0`**，预期是 `0 0`。独立核实的结果：① 这 5 个确实是原始标注本身的坏框，不是适配器的换算错误。mendeley 有 4 个 VOC 框零宽或零高，或者在图外（例如 `xmin=xmax=641`，而图宽为 640），lvis 有 1 个框（`000000047372.txt`：`6 1 0.816653 0.2 0.220613`，中心在右边缘，一半在图外），与 `corrupt_by_source` 的 `{"lvis": 1, "mendeley": 4}` 一致。② 自写脚本扫描了输出数据集的 297,936 行标注，类别越界、字段数错误、坐标越界、零面积、超出图像边界的行数都是 0。③ Ultralytics 的 `labels/{train,val,test}.cache` 显示三个子集均为 `corrupt 0`、`missing 0`、`empty 0`。④ 自己计算了全部 50,188 张图（三个子集加 fridge_test）的 md5 和平均哈希：跨子集 md5 相同 0，平均哈希相同 0。**不通过的原因**：总纲字面预期是 `0 0`，而 `corrupt` 在本实现中表示"原始标注中被丢弃的坏框数"，这一口径与总纲 §4 任务 3 的字段定义"坐标越界或类别越界的标签数"、1.4 的预期都不一致，总纲和验收记录中也没有用户确认的口径说明。数据本身已经核实是干净的，只需要按"需要执行者处理的事项"第 2 条处理。另外，`cross_split_duplicates` 是在 md5 去重之后统计的，按实现方式它恒为 0，作为验收依据没有独立意义（见改动审阅） |
| 1.5 | 通过 | 执行总纲命令，输出 `True`。`training/data.yaml` 的 33 个 names 与 `classes.yaml` 顺序一致 |
| 1.6 | 通过 | 执行总纲命令，输出 `0`。这条命令只能说明 aicook 没有作为来源参与合并（它不在 `sources_used` 中）。因此另做了内容级核对：fridge_test 的 513 张图与 yolo 三个子集之间，md5 相同 0 张，平均哈希相同 0 张，可以排除 AICook 图片经由 vvrh5 等 Roboflow 来源间接混入的可能 |
| 1.7 | **不通过** | `training/reports/dataset/yolo/class_distribution.png` 已生成并入库，图中标注了每类的 train 框数，也画了 200 框阈值线。但 val 和 test 是在 **symlog 对数坐标上的堆叠条**，段长等于对数差，与框数不成比例，从图上**读不出、也比较不了**各类在 val、test 中的框数，不满足"图中能看出每一类在 train、val、test 中的框数"。举例：西红柿 val 有 2145 框，大蒜 val 只有 83 框，但图上大蒜的 val 段长约为西红柿的 3.5 倍（log10(379/296)=0.107，log10(31332/29187)=0.031）。用作论文附图时会误导读者 |
| 1.8 | **不通过** | 执行总纲命令，输出 `{'ginger': 55, 'tofu': 118}`，预期是 `{}`。与调用方告知的情况一致，需要等用户自拍照片（custom）加入后重新合并并复测。其余 31 类都不少于 200 框，最少的是牛肉 219、猪肉 284、大蒜 296、牛奶 298 |
| 1.10 | **不通过** | 已满足的部分：`training/datasets/fridge_test/summary.json` 的 `images` 为 `{"val": 513}`；有框的类别正好 15 个，与 `classes.yaml` 中 `sources.aicook` 声明的 15 类完全一致（用 `source_map(c,'aicook')` 比对结果为 `True`）；入库的副本 `training/reports/dataset/fridge_test/summary.json` 与本地版本除 `split_files` 外完全一致。**未满足的部分**：清单要求"在 `sources.md` 中记录各类图片数"，但 `sources.md` 的 aicook 一节只写了"每类 182–356 框"，这是框数范围，不是各类图片数。各类图片数（例如 tomato 304、chicken 305、apple 172……）没有写进 sources.md |
| 1.12 | 通过 | 执行总纲命令，输出 `256 257 0`。进一步核对：`seed` 为 42；ft 与 eval 的并集正好等于 fridge_test 的 513 个文件名，两半内部都没有重复，文件名都以 `aicook_` 开头。`git log --follow` 显示 `fridge_split.json` 只在 `5e3faf6` 提交过一次，之后没有改动。`build_dataset` 在划分文件已存在时会拒绝运行，有单元测试覆盖 |
| 1.13 | 通过 | `git ls-files "*.pt" "*.onnx" "*.pth" "training/datasets/*"` 无输出；`_local_secrets.py` 也没有被跟踪。`training/prepare_dataset.py`、`training/sources/`（4 个文件）、`training/data.yaml`、`training/data_fridge.yaml`、`training/reports/dataset/` 都已入库，工作区干净，`git status --ignored` 显示这些路径下没有被忽略的遗漏文件。另外发现 `runs/detect/...` 下有无关文件入库，不属于本项的判定范围，见改动审阅 |

## 改动审阅

审阅范围：`git diff master...HEAD`（共 90 个文件，其中包括阶段 0 的提交）。重点审阅的是阶段 1 自身的改动，即 `git diff stage-0-env...HEAD`，共 62 个文件。`core/`、`data/`、`database/`、`config.py`、`app.py` 在阶段 1 中没有改动。单元测试：`.venv/Scripts/python -m unittest discover -s tests` 结果为 `Ran 52 tests ... OK`。

### 严重

未发现问题。

### 一般

1. **无关的运行产物被提交入库**：`runs/detect/training/runs/dataset_smoke/args.yaml`、`results.csv`，在 `bf1c5f7` 中提交。这是过渡版数据集冒烟训练的 Ultralytics 输出，因为 `project=training/runs` 用了相对路径，被放到了仓库根目录的 `runs/` 下。`.gitignore` 只忽略了 `training/runs/`，没有忽略根目录的 `runs/`。同一目录下的 `weights/best.pt`、`last.pt` 只是因为 `*.pt` 规则才没有入库。这两个文件与阶段 1 的产出物无关，应该移出版本库，并在 `.gitignore` 中补上 `runs/`。
2. **Open Images 原始目录中混有早一次下载的残留，导致无法复现**：`training/download_openimages.py` 不清理旧的输出。第二次下载时加入了 `Cabbage`，被排除的图片集合随之变化，各类候选列表的洗牌结果也跟着变了，于是第一次下载的 211 张图片和标注留在了目录里，并全部进入了合并结果。按 sources.md 记录的命令重新下载只能得到 7005 张，复现不出现在的 7216 张。这些残留的标注是在没有 Cabbage 类时写的，图中如果有卷心菜，会漏标。建议二选一：删除残留后重新合并；或者在 sources.md 中如实记录 7216 张及原因，并在脚本中加入清理旧输出的逻辑。
3. **`cross_split_duplicates` 按实现方式恒为 0**：`_dedupe` 已经保证每个 md5 只保留一条记录，之后再统计"跨子集 md5 相同的图片数"必然得 0，所以 1.4 的后半项检查不到任何东西。本次审查用独立扫描补足了这项核对（结果为 0）。建议改为在写出之后，对输出目录中的文件重新计算 md5 和平均哈希，或者在 summary 中注明这个指标的含义。
4. **近义类别没有映射，造成同一种外观的标签互相矛盾**：mendeley 的 `Lemon`（sources.md 写明是绿色小青柠）映射成了 lemon，而 lvis 的 `lime`（401 框）、zenodo 的 `Lime`（1301 框）、vvrh5 的 `lime`（218 框）都没有映射，留在图中成为未标注的背景。另外，lvis 的 `mandarin orange`（196 框）、`clementine`（26 框）在 orange 类下没有映射，mendeley 的 `Green Banana`（583 框）在 banana 类下也没有映射。同一类外观的物体，有时被标为某一类，有时被当成背景，这会加重 1.9 中发现的漏标问题。建议在决定 1.9 的处理方式时一并考虑：映射这些类别，或者排除含有这些类别的图片。
5. **验收标准变更缺少用户书面确认的原文记录**：阶段 1 验收记录中两行"验收标准变更（用户决定）"改写了 1.1、1.6、1.10、1.11、1.12，以及 1.4、1.7、1.8 的路径。其中 1.10 由"自采不少于 300 张、7 个稀缺类各不少于 15 张"放宽为"AICook 513 张已转换"，变化幅度很大。阶段 0 的同类变更记录了"用户已于 2026-09-27 在对话中书面回复'确认'"，阶段 1 的记录只写了"用户决定"。审查员无法核实对话内容，建议在最终审查之前，由用户本人书面确认这些变更并记录在案。

### 建议

1. `training/data.yaml` 和 `data_fridge.yaml` 中的 `path` 是开发机上的绝对路径（`E:\paperdesign\...`）。阶段 2 在训练机上使用时需要重新生成或手动修改。如果在训练机上重新生成 fridge_test，会被"`fridge_split.json` 已存在"的保护拦截，需要用 `--split-json` 指向临时文件。建议提前写明数据集如何交付到训练机。
2. `data_fridge.yaml` 的 `train`、`val`、`test` 都指向 `images/val`。用它评估没有问题，但阶段 5 的 E5 微调必须另建一个只含 ft 半集的 yaml，避免误用后把 eval 半集带进训练。
3. Ultralytics 缓存中有 43 张训练图带有重复的标注行（mendeley 38、vvrh5 3、openimages 2），训练时 Ultralytics 会自动去重，但 summary 中的 `per_class` 框数因此略微偏高。建议在 `_write_record` 中去掉完全相同的框。
4. `training/normalize_photos.py` 即将用于处理用户自拍的照片：① 它接受 `.heic` 扩展名，但项目 venv 中的 PIL 没有 HEIC 插件，遇到 iPhone 原图会直接报错；② 默认 `--prefix fridge`，docstring 中写的是 labelImg，而总纲和 sources.md 要求用 `--prefix custom` 和 X-AnyLabeling，口径不一致，建议统一。
5. `web_raw_beef` 中保留了 1 张 Sketchfab 的 3D 渲染图（`raw_beef_0171.jpg`，by-nc）。sources.md 写明的复核标准会排除插画，这张图与标准不符，建议复核。
6. `crawl_openverse.py` 的 `fetch` 用 `except Exception: return None` 吞掉了所有异常，没有统计失败的原因和数量。`auto_label.py` 分批输出到同一目录时，`data.yaml` 中的注释只会保留最后一批的参数。这两处都不影响数据本身，建议补充日志。
7. `download_hyunahko.py` 在重新编码时丢弃了 EXIF，但没有按 EXIF 转正。如果原图带有旋转标记，而原始标注是按显示方向画的，框就会错位。建议抽查原始压缩包中是否有 Orientation≠1 的图片。本次审查扫描了输出数据集，所有图片都没有 Orientation≠1 的标记，但这只能说明 EXIF 已被去掉，不能排除错位。
8. 01 §7 第 5 步仍然写着"自采数据（custom）默认不进入训练集，整体作为独立测试集"，01 §5 写的是由适配器在读图时做 `exif_transpose`，都与总纲的新决定（custom 进训练集，由 `normalize_photos.py` 预先转正）不一致。总纲优先，但建议同步修改 01，避免以后误读。
9. sources.md 中 lvis 一行的许可只写了"代码 MIT；标注 CC BY 4.0"，没有说明图片按 COCO/Flickr 原始许可（其中包含 ND 许可）。爬取牛肉时以"可能构成演绎作品"为由排除了 ND，与此处的处理口径不一致，建议在论文中统一说明。
10. `prepare_dataset.py` 的 `--preview` 和 `--check-classes` 没有单元测试，建议补上。

## 整体结论

**中期不通过**

指定的 11 项中，1.2、1.3、1.5、1.6、1.12、1.13 通过；1.1、1.4、1.7、1.8、1.10 不通过。不通过的 5 项中，1.8 是已知的外部等待（缺少生姜、豆腐照片）；1.4 的数据本身已经核实干净，需要处理的是判定口径；1.1、1.7、1.10 都是记录或作图方面的问题，修改量不大。

还没有审查的项：1.9（等待用户决定）、1.11（等待自拍照片）。另外，加入 custom 来源重新合并之后，各子集的划分会整体变化（`_split` 的随机数状态会随生姜、豆腐的分桶一起变化），所以 **1.3–1.8 在最终审查时必须针对新数据集全部重新复核**，本报告中的通过结论只对当前这版十来源数据集有效。

## 需要执行者处理的事项

1. **1.1**：
   - 在 sources.md 的 `lvis_full` 一节补上下载地址（LVIS v1 标注的 URL 和 COCO 图片的来源）。
   - 修正 `openimages` 的图片数和类别数，使总表、正文与实际进入合并的数量一致，并处理 211 张残留图（见改动审阅"一般"第 2 条）。
   - 为 `aicook`、`vvrh5` 补上可访问的完整 URL。
   - 说明 `eggdet` 许可冲突的处理依据，或者请用户把它纳入 1.1 的例外。
2. **1.4**：二选一，并请用户书面确认：
   - (a) 在阶段 1 验收记录中写明 `corrupt` 表示"原始标注中被丢弃的坏框数"，列出 5 个坏框的明细，并把 1.4 的判定改为针对输出数据集（例如在 summary 中增加输出侧的统计字段，预期为 0，或者以 Ultralytics 扫描结果 `corrupt 0` 为证据）；
   - (b) 修改实现，使 `corrupt` 只统计输出数据集中的坏标签，原始坏框另用一个字段记录。

   无论选哪一种，都建议同时改进 `cross_split_duplicates` 的统计方式（"一般"第 3 条）。
3. **1.7**：重新绘制类别分布图，使 val 和 test 的框数可以读出。例如改为每类 train、val、test 三根并列的条形（对数坐标下仍然可比），或者在图上同时标注三个数字。
4. **1.8**：加入用户自拍的 custom 照片后，用总纲第 5 步的完整命令重新合并，复测得到 `{}`。如果仍然不达标，按"未通过怎么办"处理。如果改动了 `classes.yaml`，要按 §1.4 从 0.4 重新开始。
5. **1.10**：在 sources.md 的 aicook 一节写入 15 类各自的图片数，以 `fridge_test/summary.json` 的 `per_class_images.val` 为准。
6. **证据**：按 §1.2，在 `docs/acceptance/stage-1/` 下为每个清单项生成以编号开头的证据文件（命令类用 `Tee-Object` 保存输出），包括本阶段因卷心菜改名而重跑的 0.6。完成后勾选清单，并在验收记录中补上自查行。
7. **一般问题**：把 `runs/detect/...` 的两个文件移出版本库，并在 `.gitignore` 中加入 `runs/`。请用户书面确认阶段 1 的验收标准变更（"一般"第 5 条）。在决定 1.9 的处理方式时，一并考虑近义类别的标签矛盾（"一般"第 4 条）。
8. **合并前提**：阶段 1 合并回 master 之前，阶段 0 必须已通过最终审查，合并并打上 `stage-0-pass`（§1.6）。
