# scripts/：数据准备与维护脚本

一次性或偶尔运行的工具，不是系统运行时的一部分。先读根目录 `CLAUDE.md`。所有脚本都在项目根目录用 `.venv/Scripts/python scripts/<名字>.py` 运行。

| 脚本 | 作用 |
|---|---|
| `download_model.py` | 下载 COCO 预训练权重 `yolov8n.pt` 到 `models/`。github.com 的 CDN 在本网络被墙，脚本改走 Azure 直连 |
| `download_cfcd.py`、`merge_cfcd.py` | 下载《中国食物成分表》并合并进 `data/ingredients.json` |
| `download_western.py`、`integrate_western.py`、`translate_western.py` | 下载西餐和饮料菜谱、整合、用大模型翻译成中文 |
| `gen_recipes.py`（776 行，接近 800 行上限） | 生成 `data/recipes.json` |
| `audit_recipes.py` | 菜谱库数据质量审计，默认只报告不修改 |

## 约定

- 脚本要**幂等**：重复运行结果不变，不要在原数据上累加。
- 会改 `data/` 下文件的脚本，运行前先 `git status` 确认工作区干净，运行后看 `git diff --stat`。
- 数据集相关的脚本不在这里，在 `training/`。
- `gen_recipes.py` 已接近 800 行，要再加功能先拆。
