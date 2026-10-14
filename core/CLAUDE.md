# core/：业务逻辑层

被 `app.py` 的路由调用，本身不含路由、不碰模板。先读根目录 `CLAUDE.md`。

## 模块

| 分组 | 文件 | 作用 |
|---|---|---|
| 识别 | `recognizer.py` | 食材识别：本地 YOLO 兜底 + 视觉大模型。**阶段 3 要按 03 §B1–B3 重写成自训练模型为主路径** |
| 识别 | `food_classes.py` | 加载、校验 `training/classes.yaml`，33 类的唯一入口（训练侧与运行侧共用） |
| 营养 | `nutrition.py` | 食材营养查询与多食材汇总 |
| 推荐 | `recommender.py`、`diet_advisor.py`、`health_goal.py` | 食谱推荐、搭配与禁忌、健康目标 |
| 用户 | `health_profile.py`、`health_report.py`、`achievements.py` | BMI/基础代谢、体检单解析、成就徽章 |
| 每日 | `daily.py`（307 行，最大）、`meal_photo.py`、`produce.py`、`market.py` | 一日规划、餐食照片估热、买菜照片评估、应季推荐 |
| 大模型 | `llm.py` | 统一调用大模型（DeepSeek）；**没配 key 或失败时返回 `None`，调用方必须降级到本地规则** |

## 约定

- 单个文件不超过 800 行；新模块优先新建文件，不往 `daily.py` 里堆。
- 新写的识别、检测代码把"调用模型、读写文件、联网"放进适配层，核心逻辑不直接依赖 Flask、sqlite3、requests，这样能单测。`llm.py`、`recognizer.py` 目前直接用 requests 和 YOLO，是已知的耦合，阶段 3 改造时一并拆。
- **大模型和 YOLO 的输出都不能直接当真**：要能降级、能让用户在页面上修改（根目录 `CLAUDE.md` 的"模型输出必须有第二来源或人工兜底"）。`meal_photo.py`、`produce.py`、`health_report.py` 的结果都只作参考，不是诊断。
- 类别名只从 `food_classes.py` 取，不要在别处再写一份常量表（原来 `config.CLASS_TO_INGREDIENT` 按 03 §B8 要删掉）。

## 改完怎么验证

- `.venv/Scripts/python -m unittest discover -s tests`。
- 改了 `food_classes.py` 或 `training/classes.yaml`：重跑总纲 0.4、0.6，并重新合并数据集。
