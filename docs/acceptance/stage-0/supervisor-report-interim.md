# 阶段 0 审查报告（中期）

- 审查时间：2026-09-26 18:38 至 18:55（+08:00）
- 分支：`stage-0-env`（`git rev-parse --abbrev-ref HEAD` 输出 `stage-0-env`）
- 被审查提交：`82915ca39a402aed2fc377669c4f4cd884ebf8a0`（阶段0：环境与骨架（开发机部分））。`git log --oneline master..HEAD` 只有这一个提交。master 为 `eddad01`，与分支的 merge-base 相同，master 上只有基线提交。
- 未提交改动：无。审查开始时和结束时执行 `git status --short`，都没有输出。被忽略的文件与审查开始时相同，也是 `.venv/`、`models/`、`database/nutrition.db`、`training/datasets/`、`training/runs/`、`__pycache__/`、`.claude/settings.local.json`。
- 审查范围：调用方指定的 0.1、0.2、0.3、0.4、0.5、0.6、0.7、0.12、0.11（开发机部分），以及 `git diff master...stage-0-env` 的全部改动。另外审阅了 `training/check_env.py` 的代码。
- 审查依据：分支上的 `docs/plan/总纲-分阶段实施与验收.md`。该文件在本分支中被修改过，见改动审阅"一般-2"。
- 审查员执行过的、会改变状态的操作：
  1. 按总纲 0.5 的要求执行了 `python database/init_db.py`。它重建了 `database/nutrition.db` 中的 ingredients 表和 recipes 表，该文件已被 gitignore，修改时间为 18:40:01。重建前库中只有这两张表，没有用户数据。
  2. 按 0.7 的要求启动了 Web 应用，检查完后已经停止。
  - 没有运行 `training/check_env.py`。它会删除并重建 `training/datasets/smoke`，改写 ultralytics 的 settings.json，并且默认在仓库里写出证据文件，所以只做了代码审阅和 AST 语法解析。
  - 临时文件都放在 scratchpad 的 `supervisor\` 目录下，包括 `app-stdout.txt`、`app-stderr.txt`、`page_*.html`。

## 进入条件

结论：满足（中期审查范围内）。

- 阶段 0 没有前置标签要求（总纲 §2 中阶段 0 的进入条件为"无"）。`git tag -l "stage-*"` 无输出，与此一致。
- 仓库已初始化，基线提交 `eddad01` 已导入原项目代码与规划文档。`stage-0-env` 从 master 切出，merge-base 等于 master，符合 §1.3。
- "已读完 00–03"和"训练机能开机联网"这两条无法在本机核实，不影响本次中期审查。

## 验收清单逐项复核

所有命令都在项目根目录执行，设置了 `PYTHONIOENCODING=utf-8`，使用 `.venv/Scripts/python`。

| 编号 | 结论 | 依据（实际执行的命令与关键输出，或核对的证据文件） |
|---|---|---|
| 0.1 | 通过 | 执行 `python -c "import flask, yaml, ultralytics; print(ultralytics.__version__)"`，输出 `8.4.163`，满足 ≥ 8.3。补充检查：flask 3.1.3，PyYAML 6.0.3，`pip check` 输出 `No broken requirements found.`。证据 `0.1-deps.txt` 的内容是 `8.4.163`，与实际一致。 |
| 0.2 | 通过 | 执行 `python -c "import torch; print(torch.__version__)"`，输出 `2.14.0+cpu`。补充检查：torchvision 为 `0.29.0+cpu`，`torch.version.cuda` 为 `None`，numpy 2.5.2，没有版本冲突。证据 `0.2-torch.txt` 与实际一致。 |
| 0.3 | 通过 | 执行 `python -c "from ultralytics import YOLO; print(YOLO('models/yolov8n.pt').names[46])"`，输出 `banana`。`models/yolov8n.pt` 大小为 6,549,796 字节，未被 git 跟踪。证据 `0.3-yolo-names.txt` 与实际一致。另见改动审阅"一般-1"：系统自身的识别器并不读取这个位置。 |
| 0.4 | 通过 | 执行总纲命令，输出 `33 True`。补充检查：用脚本把 `training/classes.yaml` 与 01 §1 的 33 行表格逐行比对，id 顺序、name、zh、unit、default_weight_g 全部一致（牛奶那一行的差异只是表格写成"piece（按盒/杯）"引起的解析差异）。chicken 和 fish 的 `ingredient` 分别写成 `鸡肉` 和 `鱼`，通过别名命中，符合 01 §6 的方案 (b)。证据 `0.4-classes.txt` 与实际一致。 |
| 0.5 | 通过 | 执行 `python database/init_db.py`，输出"数据库初始化完成：食材 995 条，菜谱 1038 条"，退出码 0。重建前后执行别名检查命令，输出都是 `True True`，`鸡肉` 指向"鸡"，`鱼` 指向"草鱼"。`ingredients.json` 的差异只涉及这两个别名，没有其他条目使用 `鸡肉` 或 `鱼` 作为主名或别名，`recipes.json` 中也没有食材名为这两个词。证据 `0.5-init-db.txt` 与实际一致。 |
| 0.6 | 通过 | 执行总纲命令，输出 `[]`。证据 `0.6-validate.txt` 与实际一致。另外执行 `python -m unittest discover -s tests -v`，15 个测试全部通过，与 `0.4-0.6-unittest.txt` 一致。 |
| 0.7 | 通过 | 用总纲命令 `python -c "from app import app; app.run(host='127.0.0.1', port=5000, use_reloader=False)"` 在后台启动，产生两个进程：venv 启动器 PID 21132 和解释器 PID 27132。用 curl 访问三个页面：`/` 返回 200、8554 字节，标题"知食分子"；`/recipes` 返回 200、13322 字节，标题"知食分子"；`/daily` 返回 200、26239 字节，标题"一日饮食规划 · 知食分子"。三个字节数与 `0.7-pages.txt` 完全相同。页面引用的 `/static/style.css`、`manifest.json`、`icon-192.png` 都返回 200，页面中没有错误页标记。服务端 stdout 和 stderr 中 Traceback 数为 0，显示 `Debug mode: off`。结束后用 `Stop-Process` 停止了两个进程，5000 端口已经没有连接，也没有残留的应用进程。三张截图 `0.7-home.png`、`0.7-recipes.png`、`0.7-daily.png` 都是 929×861 的 PNG，查看了 `0.7-recipes.png`，页面渲染正常。以上是按清单规定的检查方式得出的结论。这三个 GET 页面没有覆盖到识别功能，识别功能的问题见"一般-1"。 |
| 0.11（开发机部分） | 通过 | 执行 `.venv/Scripts/yolo settings`，输出中 `"sync": false`，全文与 `0.11-dev-settings.txt` 逐字一致，设置文件路径为 `C:\Users\Administrator\AppData\Roaming\Ultralytics\settings.json`。训练机部分未审查。 |
| 0.12 | 通过 | 在已提交的 `82915ca` 上执行 `git ls-files "*.pt" "*.onnx" "*.pth" "training/datasets/*"`，无输出。按审查员规程扩展为加上 `"_local_secrets.py"` 后，同样无输出。补充检查：在 136 个被跟踪文件中查找 db、zip、jpg、bin、safetensors、runs/、weights/ 等可疑类型，没有命中。本分支新增的二进制文件只有 3 张证据截图。在 diff 中搜索密钥，只找到 ultralytics 设置里为空的 `api_key` 字段。证据 `0.12-git-ls-files.txt` 是提交前在 `git add -A` 状态下生成的，结论与复核一致。 |

### 未审查（等待训练机）

| 编号 | 状态 | 说明 |
|---|---|---|
| 0.8 | 未审查（等待训练机） | 需要 RTX 4060 训练机上 `training/check_env.py` 生成的证据文件。 |
| 0.9 | 未审查（等待训练机） | 同上。 |
| 0.10 | 未审查（等待训练机） | 同上。 |
| 0.11（训练机部分） | 未审查（等待训练机） | 同上。 |
| 0.13 | 未审查（等待训练机） | 同上。另外，验收记录中"交付给训练机的提交号"目前还是"（交付时填写）"。 |

## 改动审阅

`git diff master...stage-0-env --stat` 显示改动了 23 个文件，新增 708 行，删除 38 行。所有改动都能在分支版总纲的阶段 0 任务和产出物清单中找到对应，没有越界修改，也没有无关的重构。没有权重、数据集或密钥被提交。测试存在，15 个测试全部通过。

### 严重

未发现问题。

### 一般

**一般-1：权重的新下载位置与现有识别器的配置冲突，属于"与已有代码冲突"，由本分支引入，已复现**

- 本分支把 `scripts/download_model.py` 的输出改成了 `<项目根>/models/yolov8n.pt`。但 `config.py:66` 仍然是 `YOLO_MODEL = "yolov8n.pt"`，这是相对于启动目录的路径，也就是指向项目根下的 `yolov8n.pt`。`core/recognizer.py:28-31` 会先检查 `os.path.exists(config.YOLO_MODEL)`，文件不存在时报"模型文件不存在：yolov8n.pt，请先运行 download_model.py 下载"。
- 复现方法：执行 `IngredientRecognizer()._load_model()`，抛出 `RuntimeError: 模型文件不存在：yolov8n.pt，请先运行 download_model.py 下载`，而此时 `models/yolov8n.pt` 是存在的。`recognize()` 会吞掉异常并返回 `[]`（`recognizer.py:57-58`），所以原系统 `/recognize`（食谱页上的"拍照识别食材"）的 YOLO 本地兜底路径会静默地识别不到任何东西。而且报错信息给出的办法，也就是运行 download_model.py，已经解决不了问题。`README.md:24` 仍然写着 `yolov8n.pt` 放在项目根目录。
- 在基线版本中，`download_model.py` 的 `OUT="yolov8n.pt"` 与 config 是一致的。在本机上，基线时项目根目录本来就没有这个权重，原项目 `E:\workspace\nutrition_system` 里也没有，所以本机上可以观察到的行为和改动前一样。但按文档流程重新搭建环境时，识别路径已经走不通了。阶段 0 任务 2 的名称就是"COCO 兜底权重"，0.3 只验证了 ultralytics 能按显式路径加载这个文件，没有验证系统本身会用到它。03 §B8 把 `YOLO_MODEL` 和 `YOLO_FALLBACK_MODEL` 改到 `models/` 的工作排在阶段 3，但本分支先移动了文件，没有同步修改使用它的地方。

**一般-2：阶段 0 的验收标准本身是在被审查的分支里修改的**

- 本分支改动了总纲，涉及 0.7（启动命令由 `python app.py` 改为关闭重载器、非 debug 模式）、0.8 到 0.10（由直接执行命令改为运行 `check_env.py`，0.10 由 coco8、imgsz=640 改为 8+4 张合成图、imgsz=160、batch=4）、0.11、0.13（由"`git log -1` 一致"改为"提交号等于交付时记录的号"），另外还改了 §1.1、§1.3、§1.5、§9 的流程规则，并新增了审查员自己的定义文件 `.claude/agents/stage-supervisor.md`。
- 修改理由在文中写明了：GitHub 下载 CDN 访问不了，重载器会残留子进程。调用方给出的审查参数也与分支版本一致，所以本次按分支版本审查。但这些修改相当于执行者在同一分支里改了衡量自己的标准。尤其是 0.10 的冒烟训练被削弱了：imgsz=160 不会检验 640 分辨率下的显存，这部分到阶段 2 才会覆盖。按 §1.1 的精神，这类修改应当由用户或导师书面确认。

**一般-3：`check_env.py` 在 `--device cpu` 模式下会生成一份"OVERALL: PASS"、文件名与正式证据相同的文件**

- 在 cpu 模式下，`[0.8 nvidia-smi]` 和 `[0.8/0.9 torch]` 都直接记为 PASS，只注明 skipped（`check_env.py:58-59`、`73-74`），所以 OVERALL 可能是 PASS。证据默认写入 `docs/acceptance/stage-0/0.8-0.13-train-machine.txt`，与训练机的正式证据同名。总纲把文件最后一行的 `OVERALL: PASS` 定义为总结论，因此一次开发机上的试运行就能产生一份看起来通过的正式证据，也可能覆盖真正的证据。虽然文件头部会写 `device=cpu`，也不会有 CUDA 设备名，最终审查时能识别出来，但这个设计对证据的可靠性不利。

**一般-4：`check_env.py` 的自动通过条件没有完全覆盖总纲的判定标准**

- 0.8：总纲要求"设备名是 RTX 4060"，脚本只要求 `nvidia-smi` 退出码为 0，并且 `torch.cuda.is_available()` 为真、`torch.version.cuda` 不为 None。设备名只是打印出来（`check_env.py:61`、`76`），没有做判断。所以 `OVERALL: PASS` 不等于 0.8 已经满足，还需要人工核对设备名。
- 0.13：PASS 只说明 `git log` 执行成功（`check_env.py:157`），并没有和交付时的提交号比对。按总纲，这一步由人工比对，可以接受。但脚本没有输出当前分支，也没有输出 `git status --porcelain`。如果采用"拷贝整个文件夹"的交付方式，而开发机上当时有未提交的改动，这些改动会被一起带过去，而提交号仍然相同。也就是说，提交号相同不能证明"代码一致"。
- 其他方面，脚本逻辑基本可靠：
  - 0.10 使用 `device="0"`。如果 CUDA 不可用，ultralytics 会直接报错，而不会悄悄退回 CPU，所以 PASS 可以说明确实在 GPU 上完成了训练。
  - 脚本有 `if __name__ == "__main__":` 守卫，`workers=0`，适合 Windows。
  - 数据集和训练输出分别在已被 gitignore 的 `training/datasets/smoke` 和 `training/runs/smoke` 下。
  - 每一项检查都包在 try/except 中，一项出错不会中断其余检查，最后一定会写出证据文件。
  - 各检查项的标签与总纲引用的 `[0.8 nvidia-smi]`、`[0.8/0.9 torch]`、`[0.10 smoke train]`、`[0.11 sync=False]`、`[0.13 git log]` 一致。
  - 本机 `training/runs/smoke/results.csv` 中有执行者 18:31:46 至 18:31:58 在 CPU 上训练 1 个 epoch 的结果，与总纲中"约 15 秒、通过"的说法相符。

### 建议

1. **`check_env.py`：sync 设置的时机**。`check_settings` 排在冒烟训练之后（`check_env.py:172-173`）。在新机器上，训练时 sync 还是默认值 True，这与 02 §1 第 5 步"训练前关闭联网行为"的意图相反。遥测是异步发送的，风险较低，但建议把设置步骤移到训练之前。另外，`settings["sync"]` 是在 update 之后立即从内存中读取的，几乎一定成立。建议从 settings.json 重新读一次，确认写入成功。
2. **`check_env.py`：非 ASCII 路径**。`smoke.yaml` 以 `encoding="ascii"` 写入，并且里面包含绝对路径（`check_env.py:117-118`）。如果训练机上仓库路径含有中文，比如 `D:\毕设\...`，写入时会抛出 UnicodeEncodeError，导致 0.10 记为 FAIL。已用最小片段验证 ascii 编码中文路径会抛出这个异常。建议改用 utf-8，或者在总纲里注明仓库路径只能用 ASCII 字符。
3. **`check_env.py`：只在 GPU 上才会走到的代码**。CPU 试运行覆盖不到以下几处：nvidia-smi 和 CUDA 的判定、选择 `device=0`、ultralytics 的 AMP 检查。在 8.4.163 版本中，CUDA 下的 AMP 检查（`ultralytics/utils/checks.py:1017-1028`）会从 GitHub release 把 `yolo26n.pt` 下载到 weights_dir，而总纲自己说这个 CDN 访问不了。下载失败时，`safe_download` 会重试，然后抛出 `ConnectionError`，`check_amp` 会捕获它，提示"AMP checks skipped"，训练继续进行，所以不会导致失败，但可能多花几分钟。因此，总纲中"开发机已经用 --device cpu 预先跑过一遍……说明脚本本身没有问题"的说法说得过满了。这次 CPU 试运行的输出也没有作为证据保存下来。
4. **`check_env.py`：出错时的项目名**。主循环用 `getattr(check, "__name__")` 作为出错项的名称。nvidia-smi、torch、smoke train 这三项是用 lambda 包装的，如果出现意外异常，会记成 `[<lambda>] FAIL`，看不出是哪个编号。例如 nvidia-smi 卡住时，`run_cmd` 没有捕获 `subprocess.TimeoutExpired`。OVERALL 仍然是 FAIL，结论不会错，只是无法追溯到具体编号。
5. **ultralytics 目录设置**。`0.11-dev-settings.txt` 显示 `weights_dir` 为 `E:\paperdesign\weights`，`runs_dir` 为 `E:\paperdesign\runs`，这两个目录都不在 `.gitignore` 中，只有 `*.pt` 会被忽略。`check_env.py` 显式指定了 `project=training/runs`，目前没有问题。但以后如果不带 `project=` 直接使用 yolo CLI，训练产物会落到仓库根目录下，而且不会被忽略。
6. **`core/food_classes.py` 的异常类型**。docstring 说文件不合法时抛出 ValueError，但有几种情况实际抛出的是 TypeError 或 AttributeError：条目不是字典、id 类型混用、`default_weight_g` 是字符串、yaml 顶层是列表。影响不大。另外，03 §B1 写的"validate 非空时在 app 启动时打印警告"尚未实现，这部分属于阶段 3 的 app 接入，这里只是提醒。
7. **测试**。`test_names_follow_id_order` 基本是同义反复，因为 names 本身就是由 list 生成的。`test_every_ingredient_resolves` 用的是从 JSON 构建的索引，而不是数据库；数据库这条路径由 0.6 的命令覆盖。
8. **验收记录的写法**。结论栏写的是"开发机部分自查通过，待训练机"，而 §1.3 第 3 步要求结论栏先写"待审查"。这是措辞问题。
9. **`classes.yaml` 的 sources**。目前只填了 `custom`，文件中已经注明原因，等阶段 1 查清各数据集真实的类名后再填。在那之前，`source_map` 对公开数据源返回 `{}`。阶段 1 运行 prepare_dataset 之前必须补齐。
10. **`download_model.py` 的写入方式**（原有问题，不是本分支引入的）。下载时边下边写，直接写到最终路径。如果下载中断，会留下一个不完整的 `models/yolov8n.pt`，而它能通过 `os.path.exists` 检查。

## 整体结论

中期不通过

说明：本次指定的 9 项（0.1 到 0.7、0.11 开发机部分、0.12）我都独立重新执行过，全部通过，证据文件与实际结果一致。不通过的原因来自改动审阅："一般-1"是本分支引入的、已复现的与已有代码的冲突，即权重移到了 `models/`，但识别器仍然在项目根目录找它。按审查规程中"与已有代码冲突"属于明显缺陷，并且结论要保守，所以本次中期结论为不通过。

还没有审查的项：0.8、0.9、0.10、0.11 的训练机部分、0.13（等待训练机）。中期审查不能代替最终审查。

## 需要执行者处理的事项

**必须处理（重新做中期审查或最终审查之前）**

1. **一般-1**：两种方式任选一种。
   - (a) 在本阶段把 `config.YOLO_MODEL` 改为基于 `_BASE_DIR` 的 `models/yolov8n.pt` 绝对路径，方向与 03 §B8 一致；同时更新总纲阶段 0 产出物中对 `config.py` 的描述，以及 `README.md:24` 中的说明。修改后复测：`IngredientRecognizer()._load_model()` 能成功加载，并重跑 0.7。
   - (b) 由用户书面确认把这个问题推迟到阶段 3，并在验收记录的备注中写明"阶段 0 至 3 之间，/recognize 的 YOLO 兜底不可用"这一已知限制。

**应在把代码交给训练机之前处理**

原因：0.13 要求证据与交付时的提交绑定，交付之后再改代码，就要重新交付、重新运行自检脚本。

2. **一般-3**：cpu 模式不应产生 PASS 结论。可以把跳过的项记为 SKIP、最后写 `OVERALL: DRY-RUN`，或者改用其他文件名，或者在 cpu 模式下拒绝使用默认的 `--out`。
3. **一般-4**：
   - 0.8 增加对设备名包含 "4060" 的判断。
   - 0.13 额外输出 `git rev-parse --abbrev-ref HEAD` 和 `git status --porcelain`，并把"工作区干净"纳入通过条件。可以考虑支持 `--expect-commit <hash>`，由脚本自动比对提交号。
4. 建议一并处理"建议"中的第 1 至 4 条：sync 设置移到训练之前并从磁盘回读；smoke.yaml 改用 utf-8 写入；在总纲中修正"CPU 试运行说明脚本没有问题"的表述；出错项使用正确的编号作为名称。

**需要用户确认**

5. **一般-2**：请用户或导师确认本分支对总纲阶段 0 验收标准和流程规则的修改（0.7、0.8 到 0.10、0.11、0.13，§1.1、§1.3、§1.5、§9，以及新增的审查员定义），并在验收记录的备注中留下确认记录。
