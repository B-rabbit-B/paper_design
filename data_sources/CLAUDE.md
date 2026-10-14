# data_sources/：营养库、菜谱库的原始外部数据

这些是脚本的**输入**，不是系统运行时读取的数据。先读根目录 `CLAUDE.md`。

| 路径 | 内容 | 谁用 |
|---|---|---|
| `cfcd/` | 《中国食物成分表（第 6 版）》JSON，61 个分类文件加血糖生成指数文件（来源 Sanotsu/china-food-composition-data） | `scripts/download_cfcd.py` 下载，`scripts/merge_cfcd.py` 合并进 `data/ingredients.json` |
| `themealdb/` | 西餐菜谱（TheMealDB）与无酒精饮料（TheCocktailDB） | `scripts/download_western.py` 下载，`scripts/integrate_western.py` 整合 |
| `cookbook_kg_entities.json` | CookBook-KG 知识图谱里的 199 道中式真实菜谱 | `scripts/gen_recipes.py` 读取，生成 `data/recipes.json` |

## 约定

- 不要手工改这里的文件，它们是下载下来的原始数据；需要变化就改对应脚本。
- 重新下载前先确认联网和来源仍可用；来源和许可要写进论文的"数据来源"一节，不要用来源不明的数据。
- 这里的文件很多（60 多个），不要整个目录读进上下文，需要时按文件名取。
