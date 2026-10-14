# data/：营养库与菜谱库的种子数据

先读根目录 `CLAUDE.md`。

| 文件 | 条数 | 说明 |
|---|---|---|
| `ingredients.json` | 995 | 营养库：每种食材一条，含主名、别名（`aliases`）、营养成分 |
| `recipes.json` | 1038 | 菜谱库，由 `scripts/gen_recipes.py` 生成（输入：`recipes_base.json`、`data_sources/cookbook_kg_entities.json` 等） |
| `recipes_base.json` | 64 | 家常菜原始种子，是 `gen_recipes.py` 的输入，保证重复生成结果不变 |

## 约定

- **不要手工改 `recipes.json`**：它由脚本生成，重新生成会覆盖手工修改。要改菜谱，改 `recipes_base.json` 或对应脚本，再生成。
- `ingredients.json` 是由 `scripts/merge_cfcd.py` 把《中国食物成分表》合并进来的，来源数据在 `data_sources/`。手工改单条（比如补别名）可以，但要保持 JSON 格式（缩进 2 空格、数组每项一行），方便看 diff。
- 补别名的原因通常是 33 类的 `ingredient` 字段没命中：例如"鸡肉"是"鸡"条目的别名，"鱼"是"草鱼"条目的别名。改完执行 `python database/init_db.py`，再重跑总纲 0.5、0.6。
- 这些文件体积不小，改动后用 `git diff --stat` 先看一下范围，不要误改整份。
