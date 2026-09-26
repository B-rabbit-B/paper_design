# 阶段 0 审查报告（中期，第二轮）

- 审查时间：2026-09-26 18:57 至 19:05（+08:00）
- 分支：`stage-0-env`（`git rev-parse --abbrev-ref HEAD` 输出 `stage-0-env`）
- 被审查提交：`db006b1062a392f0ba618005e6ddc18bdbb629df`（阶段0：按第一轮中期审查意见修复）
  - `git log --oneline master..HEAD` 列出 `db006b1`、`82915ca` 两个提交，HEAD 就是 `db006b1`。
  - 本轮主要审阅 `git diff 82915ca..db006b1` 的改动，共 8 个文件，新增 287 行，删除 73 行。
- 未提交改动：无。审查开始时和结束时执行 `git status --short`，都没有输出。
- 第一轮报告 `supervisor-report-interim.md` 已原样提交：
  - 文件修改时间是 18:51:41，也就是我第一轮最后一次编辑的时间，早于 `db006b1` 的提交时间 18:55:48。
  - 文件共 127 行，与 diff 中新增的行数一致，关键行（如 `recognizer.py:57-58`）与我写的内容相同。
  - 本轮没有改动它。
- 审查依据：分支上的 `docs/plan/总纲-分阶段实施与验收.md`，第一轮报告，调用方给出的第二轮审查范围。
- 审查员执行过的、会改变状态的操作：
  - 启动并停止了 Web 应用（0.7）。
  - 按调用方授权执行了 `python training/check_env.py --device cpu`。它的副作用都在预期范围内：
    - 重建了 `training/datasets/smoke` 和 `training/runs/smoke`，改写了 `training/runs/check_env-cpu-dryrun.txt`，这三处都被 git 忽略。执行者此前生成的试跑报告，我先复制到 scratchpad 留存，再运行。
    - 重写了 ultralytics 的 `settings.json`，但前后 md5 都是 `ab5e8d63…`，内容没有变。
  - 本轮没有执行 `database/init_db.py`，理由见"未改动项的影响评估"。
  - 所有临时文件都在 scratchpad 的 `supervisor\r2\` 下，包括突变测试用的小目录树、非 ASCII 路径测试目录、应用日志、页面快照和试跑控制台输出。
  - 模拟测试时，我用 importlib 加载 `check_env.py`，因此在仓库中生成了 `training/__pycache__/check_env.cpython-312.pyc`（19:01:43，被 git 忽略）。这是我自己产生的缓存，已经删除。删除后，`git status --short --ignored` 列出的条目与审查开始时相同，另外只多了本报告。

## 进入条件

与第一轮相同，结论仍为满足：

- 阶段 0 没有前置标签要求，`git tag -l "stage-*"` 无输出。
- 分支从 master 的 `eddad01` 切出。

## 第一轮问题逐条复核

| 第一轮问题 | 结论 | 依据 |
|---|---|---|
| **一般-1** `config.YOLO_MODEL` 与下载路径不一致 | 已解决 | 见下方"一般-1 复核" |
| **一般-3** cpu 模式会产生 PASS，并写入正式证据的文件名 | 已解决 | 见下方"check_env.py 复核" |
| **一般-4** 0.8 没有判断设备名；0.13 没有检查工作区状态 | 已解决 | 见下方"check_env.py 复核" |
| 建议 1：sync 的设置顺序和回读 | 顺序已解决；回读未做，但影响可以忽略 | `CHECKS` 中 `0.11 sync=False` 已排在 `0.10 smoke train` 之前（`check_env.py:190-197`）。值仍然是 update 后从内存读出的。不过试跑后我用 `yolo settings` 从磁盘读取，显示 `"sync": false`，设置文件的 md5 也没有变，说明确实写入了磁盘。 |
| 建议 2：smoke.yaml 的编码 | 已解决，并实测通过 | yaml 和标签文件都改为 utf-8 写入（`check_env.py:140-145`）。我在 scratchpad 下建了一个名为"非ASCII路径测试"的目录，调用脚本自己的 `build_smoke_dataset()` 在其中生成数据集，然后在 CPU 上训练 1 个 epoch，训练正常完成，`train ok`。 |
| 建议 3：AMP 说明，以及"CPU 试跑说明脚本没有问题"的说法 | 部分解决 | 脚本的 docstring（`check_env.py:16-18`）已经说明 CUDA 下 AMP 检查会尝试下载模型，超时后跳过，不会导致失败。总纲把原来的说法改成了"冒烟训练能够完成，说明脚本本身可用"，并注明试跑报告不能用作证据。但总纲里仍然没有提到"CPU 试跑覆盖不到 GPU 专属的代码路径"和"AMP 检查可能多等几分钟"，用户在训练机上看到长时间等待时，从总纲里找不到解释。见新建议 N4。 |
| 建议 4：lambda 标签 | 已解决 | 改为使用 `CHECKS = [(编号, 函数), …]`，出现意外异常时按编号记 FAIL（`check_env.py:216-221`）。 |
| **一般-2** 验收标准和流程规则是在本分支中修改的 | 仍然待用户书面确认 | 见下方"一般-2 复核"。审查员不能替用户认定已经确认。 |

### 一般-1 复核（实测）

1. **从项目根目录以外启动**。在 scratchpad 的 `supervisor\r2` 目录下启动 Python，把 `E:\paperdesign` 加入 `sys.path`，然后执行：
   - `config.YOLO_MODEL` 为 `E:\paperdesign\models\yolov8n.pt`，是绝对路径，文件存在。当前目录下没有 `yolov8n.pt`。
   - `IngredientRecognizer()._load_model()` 加载成功，`ckpt_path = E:\paperdesign\models\yolov8n.pt`，`names[46] = banana`。
   - 用加载出的模型对 ultralytics 自带的 `bus.jpg` 做推理，得到 6 个框（bus、person、stop sign），说明模型可以正常推理。
   - `recognize(bus.jpg)` 返回 `[]`。这是正常结果：图中没有 `CLASS_TO_INGREDIENT` 里的食物类别，不是因为权重没找到。
   - 运行结束后，该目录中没有生成任何文件。
2. **`tests/test_model_path.py` 能否拦住路径不一致（突变测试）**。在 scratchpad 里建了几棵最小目录树，每棵只包含 `config.py`、`scripts/download_model.py` 和本轮的测试文件，分别放入不同版本的 config.py 和 download_model.py，然后运行 `unittest`：

   | config.py / download_model.py 的来源 | 结果 |
   |---|---|
   | master 基线，两处都是相对路径 `yolov8n.pt` | `test_yolo_model_is_absolute` FAIL |
   | `82915ca`，即第一轮发现问题时的状态 | 2 个测试都 FAIL，其中 `'…\models\yolov8n.pt' != 'yolov8n.pt'` |
   | 人为改成 `os.path.join(_BASE_DIR, "yolov8n.pt")`，是绝对路径但目录不对 | `test_download_target_matches_config` FAIL |
   | `db006b1` | 2 个测试都 OK |

   结论：这个测试能拦住"下载位置与配置不一致"和"配置使用相对路径"这两类问题。测试加载 `download_model.py` 时只执行模块顶层代码，`main()` 有 `__main__` 守卫，所以不会联网。
3. `README.md` 中关于权重位置的两处说明已经改为 `models/yolov8n.pt`。总纲的产出物清单也同步写明了 `config.py` 的这项修改和新增的测试文件。

### check_env.py 复核（通读新代码，实际试跑，并用模拟对象测试分支逻辑）

**cpu 试跑**

执行 `python training/check_env.py --device cpu`，退出码为 0。报告写到 `training/runs/check_env-cpu-dryrun.txt`，结果如下：

- 文件头部带有 `(DRY RUN - not valid as training machine evidence)`。
- `[0.8 nvidia-smi] SKIP`，`[0.8/0.9 torch] SKIP`。
- `ultralytics >= 8.3`、`0.11 sync=False`、`0.10 smoke train`（CPU，2.6 秒）、`0.13 git` 都是 PASS。`0.13 git` 这一项显示 `stage-0-env @ db006b1…; working tree clean`。
- 最后一行是 `OVERALL: DRY-RUN OK (cpu mode; GPU checks skipped; not acceptance evidence)`。
- 控制台中只有两条 "Slow image access" 的 WARNING，没有报错、没有 Traceback，也没有下载。
- 试跑之后：
  - `git status --short` 无输出。
  - `git status --short --ignored` 列出的条目与试跑前相同。
  - `docs/acceptance/stage-0/0.8-0.13-train-machine.txt` 不存在。
  - 仓库根目录下没有生成 `weights/` 或 `runs/`。

**GPU 专属分支的模拟测试**

我把 `check_env.py` 作为模块加载，替换掉 `torch` 和 `run_cmd`，分别测试以下情况：

- `check_torch`：
  - 设备名为 "NVIDIA GeForce RTX 4060 Laptop GPU" 时判 PASS。
  - 设备名为 "NVIDIA GeForce RTX 3060" 时判 FAIL，提示为 `device 0 is 'NVIDIA GeForce RTX 3060', expected an RTX 4060`。
  - CUDA 不可用时判 FAIL。
- `check_git`：
  - porcelain 输出只有本脚本自己的证据文件（`?? docs/acceptance/stage-0/0.8-0.13-train-machine.txt`）时，判 PASS，显示 working tree clean。
  - porcelain 输出中再多一行 ` M config.py` 时，判 FAIL，提示有 1 处未提交改动。

**与总纲的一致性**

- 总纲 0.13 已改为要求"提交号相同，并且显示 `working tree clean`"，标签从 `[0.13 git log]` 改成了 `[0.13 git]`，与脚本一致。
- 0.8、0.10、0.11 的标签没有变。
- 在正式模式下，文件最后一行仍然是 `OVERALL: PASS/FAIL`。

### 一般-2 复核（只核对备注）

总纲阶段 0 验收记录的备注中写了以下内容：

- 第一轮结论和修复情况。
- 修改依据：0.7、0.8–0.10、0.13 的改写来自"用户 2026-09-26 批准的阶段 0 执行计划第 6、8 步"；§1.1、§1.3、§1.5、§9 的分支与审查规则来自用户同日的指示。
- 结尾写明"以上依据待用户确认"。

备注写得基本清楚，但有两处没有列出：0.11 判定方式的改写（改为以证据文件和自检项为准），以及新增的审查员定义文件 `.claude/agents/stage-supervisor.md`（后者可以理解为包含在 §1.5 中）。

**本项继续列为"待用户书面确认"。** 我看不到对话记录，无法核实上述依据，也不能认定已经确认。在最终审查之前，需要用户本人在总纲中留下确认记录，例如把备注里的"待用户确认"改为由用户签注的确认说明。

## 验收清单逐项复核（本轮重新执行的项）

所有命令都在项目根目录执行，设置了 `PYTHONIOENCODING=utf-8`，使用 `.venv/Scripts/python`。

| 编号 | 结论 | 依据（实际执行的命令与关键输出，或核对的证据文件） |
|---|---|---|
| 0.3 | 通过 | 执行总纲命令，输出 `banana`。补充检查：执行 `YOLO(config.YOLO_MODEL).names[46]`，同样输出 `banana`。证据 `0.3-yolo-names.txt` 与实际一致。 |
| 0.7 | 通过 | 用总纲命令在后台启动应用，启动前确认 5000 端口空闲，产生启动器 PID 27324 和解释器 PID 20336。用 curl 访问：`/` 返回 200、8554 字节，标题"知食分子"；`/recipes` 返回 200、13322 字节；`/daily` 返回 200、26239 字节，标题"一日饮食规划 · 知食分子"。三个字节数与第一轮和 `0.7-pages.txt` 完全相同。`style.css`、`manifest.json`、`icon-192.png` 都返回 200，页面中没有错误页标记。服务端日志中 Traceback 数为 0，显示 `Debug mode: off`。结束后用 `Stop-Process` 停止了两个进程，5000 端口已经没有连接，也没有残留的应用进程。 |
| 0.12 | 通过 | 在 `db006b1` 上执行 `git ls-files "*.pt" "*.onnx" "*.pth" "training/datasets/*" "_local_secrets.py"`，无输出。本轮新增的被跟踪文件只有 `tests/test_model_path.py` 和第一轮审查报告。证据 `0.12-git-ls-files.txt` 已更新为 18:55:35 的检查结果，结论一致。 |
| 单元测试 | 通过 | 执行 `python -m unittest discover -s tests -v`，`Ran 17 tests`，结果 `OK`，其中新增了 `test_model_path` 的 2 个测试。与 `0.4-0.6-unittest.txt` 一致。 |

### 未改动项的影响评估

本轮的 diff 只涉及 `README.md`、`config.py`、`tests/test_model_path.py`、`training/check_env.py`、总纲和证据文件。其中 `config.py` 只改了 `YOLO_MODEL` 一行，全仓只有 `core/recognizer.py` 使用这个配置项。

| 编号 | 是否受影响 | 理由与本轮核对 |
|---|---|---|
| 0.1 | 不受影响 | `requirements.txt` 没有变，本轮也没有执行任何 pip 操作，结果只取决于 venv 中已装的包。我仍然用只读方式重跑了一次，输出 `8.4.163`，与之前相同。 |
| 0.2 | 不受影响 | 理由同 0.1。重跑输出 `2.14.0+cpu`。 |
| 0.4 | 不受影响 | 它依赖 `training/classes.yaml`、`core/food_classes.py` 和 `config.YOLO_CLASSES_YAML`，这些都没有改。重跑输出 `33 True`。 |
| 0.5 | 不受影响，不需要重新灌库 | `data/ingredients.json`、`database/db.py`、`database/init_db.py` 和 config 中的 `DB_PATH`、`INGREDIENTS_JSON` 都没有改。`nutrition.db` 的修改时间仍然是我第一轮灌库时的 18:40:01。`init_db.py` 会改变数据库状态，总纲 §1.4 也不要求因为这类改动重跑，所以本轮没有执行它，只重跑了只读的别名检查，输出 `True True`。 |
| 0.6 | 不受影响 | 依赖与 0.4、0.5 相同。重跑输出 `[]`。 |
| 0.11（开发机部分） | 不受影响 | `check_env.py` 试跑时会写入 `sync=False`，但设置文件的 md5 前后相同。试跑之后执行 `yolo settings`，输出与 `0.11-dev-settings.txt` 逐字一致（比较时去掉了行尾的 CR）。 |

### 仍未审查（等待训练机）

0.8、0.9、0.10、0.11（训练机部分）、0.13。

## 改动审阅（82915ca..db006b1）

所有改动都能对应到第一轮提出的问题，没有越界修改。没有权重、数据集或密钥被提交。

### 严重

未发现问题。

### 一般

未发现问题。

### 建议（本轮新发现，或第一轮遗留的问题）

- **N1 总纲排错表中的一条建议不准确**。新增的"0.8 报设备名不是 RTX 4060"一行写着"或者用 `--device` 参数指定 4060 对应的编号"。但 `check_torch` 读取设备名时固定使用 `torch.cuda.get_device_name(0)`（`check_env.py:81`），与 `--device` 无关。如果 4060 不是 0 号设备，改用 `--device 1` 后 0.8/0.9 仍然会判 FAIL，只有设置 `CUDA_VISIBLE_DEVICES` 才有效。建议让脚本按 `--device` 指定的编号读取设备名，或者删掉排错表中的这半句。
- **N2 `--out` 指向其他盘符时 0.13 会误判 FAIL**。`check_git` 用 `os.path.relpath(report_path, ROOT)` 计算相对路径（`check_env.py:176`）。在 Windows 上，如果两者不在同一个盘符，会抛出 `ValueError: path is on mount 'D:', start on mount 'E:'`（已实测），主循环会把它记为 `0.13 git FAIL (unexpected exception)`。总纲并没有要求使用 `--out`，所以影响很小。
- **N3 拷贝整个文件夹交付时，可能因为换行符差异被判为"工作区不干净"**。开发机的 `core.autocrlf=true`，在 138 个被跟踪文件中，有 119 个在工作区是 CRLF、在索引中是 LF。如果训练机的 git 设置为 `core.autocrlf=false`，拷贝过去后执行 `git status`，这些文件可能都显示为已修改，0.13 就会判 FAIL。这属于偏保守的误报，不会放过真正的问题。但排错表中"按输出列出的文件逐个查明来源"的处理办法，面对上百个文件时并不实用。建议在总纲中补充说明：优先用 bundle 方式交付，或者确认训练机上 `core.autocrlf` 的设置，出现这种情况时用 `git checkout -- .` 恢复。
- **N4 总纲缺少关于 AMP 的说明**。见上文"建议 3"。建议在 0.10 或排错表中补充一句：GPU 上的 AMP 检查会尝试下载 `yolo26n.pt`，访问不了时会在超时后跳过，这不是故障。
- **N5 权重路径的第三份副本没有被测试覆盖**。`check_env.py:32` 的 `WEIGHTS` 是另外单独写死的 `models/yolov8n.pt`，没有引用 `config`，`test_model_path.py` 也没有覆盖它。以后如果只改 config，自检脚本仍然会检查旧位置。建议在测试中加一条断言，或者让脚本改为读取 config。另外，按 03 §B8，阶段 3 会把 `YOLO_MODEL` 改成 `best.pt`，届时这个测试需要随之调整。
- **N6 0.7 的证据生成于 config 修改之前**。`0.7-pages.txt` 和三张截图是第一轮之前生成的。本轮我在修改后的代码上重跑，结果完全相同，所以结论不受影响。执行者可以视需要更新证据中的时间。
- 第一轮报告中的建议 5 到 10，本轮没有处理，仍然只是建议。它们是：ultralytics 的 weights_dir 和 runs_dir 不在 .gitignore 中；food_classes 的异常类型；测试中存在同义反复；验收记录结论栏的写法；classes.yaml 的 sources 要在阶段 1 补齐；download_model.py 下载中断会留下不完整的文件。

## 整体结论

中期通过

说明：

- 第一轮导致"中期不通过"的一般-1 已经修复，并经过实测和突变测试验证。
- 一般-3 和一般-4 已经修复，并经过实际试跑和模拟测试验证。
- 本轮重跑的 0.3、0.7、0.12 和 17 个单元测试全部通过。0.1、0.2、0.4、0.5、0.6、0.11（开发机部分）不受本轮改动影响，只读重跑的结果也与之前一致。
- 没有发现严重或一般级别的新问题。

这是中期结论，不能代替最终审查。以下项目仍未审查：0.8、0.9、0.10、0.11（训练机部分）、0.13，都在等训练机。

## 需要执行者处理的事项

**最终审查之前必须完成**

1. **一般-2**：由用户本人书面确认验收标准和流程规则的修改，并在总纲的验收记录中留下确认记录。审查员不会替用户认定已经确认。备注中建议补上 0.11 的改写和审查员定义文件这两项。
2. **交付顺序**：如果要处理下面的 N1 到 N5，请在把代码交给训练机之前完成并提交，然后在验收记录中填写"交付给训练机的提交号"。0.13 会用这个提交号核对，交付之后再改代码，就需要重新交付并重新运行自检脚本。

**建议处理（不影响本轮结论）**

3. N1 到 N6，以及第一轮遗留的建议 5 到 10。
