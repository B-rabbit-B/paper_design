# database/：SQLite 数据层

`db.py`（约 290 行）：建表、灌入种子数据、查询营养库与菜谱库；`init_db.py`：初始化入口。先读根目录 `CLAUDE.md`。

## 表

- 种子表（每次初始化都**删除重建**）：`ingredients`（营养库）、`recipes`（菜谱库），数据来自 `data/*.json`。
- 用户表（`CREATE TABLE IF NOT EXISTS`，不会被重建）：`users`、`user_profile`、`daily_log`。
- 阶段 4 会新增 `meal_item`（见 03 §B4）；新增表必须写成 `IF NOT EXISTS`，不能靠删库重建。

## 常用命令（项目根目录、用 `.venv/Scripts/python`）

```bash
python database/init_db.py     # 预期输出：食材 995 条，菜谱 1038 条（数字随 data/ 变化）
```

## 约定

- **改了 `data/ingredients.json` 必须重新运行 `init_db.py`**，否则运行中的库还是旧的；同时重跑总纲 0.5、0.6（类别能否命中营养库）。
- `nutrition.db` 不入库（已 gitignore），**用户数据（`users`、`user_profile`、`daily_log`）只在这个文件里，丢了无法恢复**。答辩前和做破坏性改动前先备份它。
- 密码用 `werkzeug.security` 的哈希存储，不要明文。
- 食材的主名和别名都会进查询索引（`load_ingredients` 以它们为键），加别名时先确认没有别的食材已经用了同一个名字，否则会互相覆盖。0.6 只检查 33 类能不能命中，不检查重名。
