# 阶段 1 审查报告（最终审查的第六次复审，r6）

- 审查时间：2026-10-16
- 分支：`stage-1-dataset`
- 被审查提交：`8e21739`
- 未提交改动：无
- 方式：没有重新合并数据集，没有运行 `init_db.py`，没有启动 Web。临时文件、抽样图都在 scratchpad。

## 进入条件

同 r5：符合总纲 §1.6 例外可审查阶段 1；合并前提仍未满足（无 `stage-0-pass` 标签，`docs/acceptance/stage-0/` 无训练机检查证据）。

## 验收清单逐项复核

| 编号 | 结论 | 依据 |
|---|---|---|
| 1.1 | 通过 | 署名清单与网图未变（r5 已核）；`sources.md` 中 r5 指出的"保留 169 张"旧数字已不存在（grep 无结果） |
| 1.2 | 通过 | 本轮未改 classes.yaml，r5 已验 |
| 1.3 | 通过 | 证据 `train 40891 / val 4619 / test 4577`，与 verify 输出的图片数一致；我另按标签目录独立数得框数 252252 / 23437 / 23958，与 `summary.json` 每类 0 处不符 |
| 1.4 | 通过 | 重跑 `verify_dataset.py training/datasets/yolo --against training/datasets/fridge_test`：`corrupt=0 unpaired=0 cross_split_md5=0 cross_split_ahash=0 cross_split_dhash=0 against_md5=0 against_ahash=0 against_dhash=0`，退出码 0，与证据一致。近重复详见下节 |
| 1.5 | 通过 | 证据 `True`，本轮 data.yaml 类别顺序未变（重新合并同一 classes.yaml） |
| 1.6 | 通过 | 证据 aicook 数 0，`against_*` 全为 0（上面重跑） |
| 1.7 | 通过 | 入库图与 `training/reports/dataset/yolo/class_distribution.png` md5 相同（`11cac8e4…`）；看图：图例 `150 (train threshold)`，三根条与框数标注齐全，牛肉 166、生姜 167、豆腐 200，数字与我独立重数一致，没有红字 |
| 1.8 | 通过 | 证据 `{}`；独立重数：牛肉 166、生姜 167、豆腐 200，其余更高（猪肉 284、牛奶 297）。余量：牛肉 16 框、豆腐刚好 200 |
| 1.9 | 通过 | 种子 2468（未用过）抽 20 张逐张看：**错框 0**；灰色 2 张（香蕉图里 3 个重叠的 banana 框，`train_openimages_08dd…`；LVIS 长颈鹿图里递给长颈鹿的小块生菜，框极小）；漏标 2 张（`train_openimages_1d8d…` 碗里的橘子、香蕉、葡萄等只标了胡萝卜；`test_zenodo_red-tomato-picture-id531101523` 满架西红柿只标了一个——这是测试集里的图）。错框 ≤ 1，通过。执行者种子 0 的记录（错框 0、漏标 0）格式齐全，样图文件名与最终数据集一致 |
| 1.10 | 通过 | 证据 `{'val': 513}`，本轮未改动 fridge_test |
| 1.11 | 通过（沿用 r5，内容未变） | 三份清单与署名清单未变（157 / 89 / 174），未重做抽样 |
| 1.12 | 通过 | 证据 `256 257 0`，未改动 |
| 1.13 | 通过 | 本轮 diff 只含代码、测试、文档、证据、样图；未发现权重、数据集、密钥入库；作者与提交信息沿用 r5 已核的规则 |

测试：`.venv/Scripts/python -m unittest discover -s tests` -> `Ran 95 tests ... OK`。

## 近重复处理的独立检查

用 r5 的独立算法（灰度图、Lanczos 缩放到 17x16 的 256 位差异哈希）对当前数据集 50087 张图重算，跨 split（val-train、test-train、val-test）的图对数：

| 距离阈值 | r5（提交 ce789a3） | r6（提交 8e21739） |
|---|---|---|
| ≤ 12 | 42 对 | **0 对** |
| ≤ 16 | 未算 | 7 对 |
| ≤ 20 | 492 对（r5 在项目自身哈希下的数） | 34 对（涉及 33 张 val/test 图：fishmarket 28、zenodo 5、eggdet 1） |

- r5 点名的 2 对 Open Images ID 同图：全数据集按文件名里的 16 位 ID 检查（openimages 与 zenodo，共 7059 个 ID），**跨 split 的 ID 为 0**。已解决。
- r5 的 42 对：在我的算法下 ≤12 已为 0，解决。
- **仍有的漏网**：把阈值放到 16–20，我的算法仍能找到 7～34 对跨 split 的图对。我把 4 对放大并排看：fishmarket 的 `Puti436`(val) 与 `Puti746`(train) 是同一条鱼同一姿势；`zenodo_tomato48`(test) 与 `tomato71`(train) 是同一束西红柿；`Mrigel60`(test) 与 `Mrigel1346`(train) 是同一条鱼；`eggdet_sample48`(val) 与 `sample49`(train) 是同一个蛋盒，只是摆放的蛋不同（连拍）。所以**仍有明确的同一照片跨 split**，数量很少（至多约 33 张 val/test 图，占 val+test 的约 0.4%），主要在 fishmarket。这与执行者在 `sources.md` 里写的"仍无法保证为 0，作为已知局限"一致。
- 代码：`group_key` 先去掉 `.rf.<hash>` 与 `_jpg/_png` 后缀，再匹配以 16 位十六进制开头的 ID，归为 `oid:<id>`，不分来源；`zenodo` 的文件名带 `_jpg.rf.` 后缀，openimages 不带，两者归一，测试覆盖。正则要求 ID 后是 `_` 或结尾，不会误吞更长的十六进制串。未发现新问题。副作用：任何其他来源若文件名恰以 16 位十六进制开头也会跨来源归组，影响可忽略。`near_pairs` 的分段（抽屉原理）原理对阈值 20 仍成立，测试里的分散位 `1 << (12*k+3)`（k<20）覆盖到 bit 231，仍在 256 位内，测试通过。
- 阈值 20 是否把无关图连成大片：分组数 38446（r5 为 39529），最大组仍是 608 张视频帧，未变；训练 / 验证 / 测试比例 81.4% / 9.2% / 9.1%，无失衡。没有看到连成大片的迹象。

## 改动审阅

范围：`git diff 37822c2..HEAD`。代码改动只有 `training/prepare_dataset.py`（阈值与 `group_key`，12 行）和 `tests/test_prepare_dataset.py`，其余是文档、证据、样图、`summary.json`，均可追溯到用户选择的方案 a。`sources.md`、`training/CLAUDE.md`、总纲 1.4 条文与验收记录行都已同步，验收记录引用用户的选择 "a"，未改动验收标准的实质（阈值是实现细节，1.4 的命令输出仍是 0）。未触碰 `core/`、`database/`、`app.py`。

### 严重
无。

### 一般
1. 近重复仍未归零（见上，≤16 为 7 对，≤20 为 34 对，肉眼确认是同一照片）。1.4 按总纲命令通过；影响只是鱼等类的 val/test 指标略偏乐观，论文需写入已知局限（`sources.md` 已写）。不阻断。

### 建议
1. 豆腐训练框数恰为 200、牛肉 166，阶段 2 前不要再继续排除网图，否则牛肉逼近 150。
2. 论文里沿用 r5 的建议：网图来源灰色约 14%、验证与测试里稀缺类别样本极少（牛肉 20 / 21，豆腐 29 / 39，生姜 38 / 22 框）。
3. 1.9 抽检中测试集里的西红柿图只标一个果（Zenodo 类漏标），属多来源数据的已知漏标局限。

## 整体结论

**通过**

1.1–1.13 按总纲当前标准全部通过。r5 点名的 42 对和 2 对 Open Images ID 同图已解决（独立重算 ≤12 为 0 对，ID 同图跨 split 为 0）；仍有少量（≤16：7 对，≤20：34 对）肉眼确认的同照片跨 split，属已登记的已知局限，不阻断。

**注意**：仍不能合并回 master 打 `stage-1-pass`：阶段 0 训练机检查未做，`stage-0-pass` 不存在。

## 需要执行者处理的事项

1. 无阻断项。
2. 合并前提（用户需要做）：在训练机运行 `python training/check_env.py`，输出放入 `docs/acceptance/stage-0/`，阶段 0 通过最终审查并合并、打 `stage-0-pass`，之后才能合并阶段 1（先 0 后 1）。

## 关于阶段 0 训练机检查的记录

**记录清楚。** 总纲 §1.6 例外表、阶段 0 验收记录（0.8–0.11、0.13 未勾，训练开始前补做）、阶段 1 的进入条件与验收记录均明确写明；核实状态与记录一致：`docs/acceptance/stage-0/` 无训练机证据，无最终审查报告，`git tag -l "stage-*"` 无 `stage-0-pass`。
