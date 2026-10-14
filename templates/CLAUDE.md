# templates/：Jinja2 页面模板

服务端渲染，由 `app.py` 的路由返回。先读根目录 `CLAUDE.md`。

页面：`home`、`index`（识别页）、`daily`、`week`、`library`、`market`、`profile`、`login`、`register`、`error`。

## 约定

- **没有基础模板继承**（没有 `{% extends %}`），每个页面都重复导航栏和头部。改导航要同步改所有页面，或者趁阶段 3、4 改页面时顺手抽出 `base.html`，不要单独为此重构。
- 链接一律用 `url_for(...)`，静态文件用 `url_for('static', filename=...)`，不要写死路径。
- 样式在 `static/style.css`，不要写大段内联样式。
- 识别页（`index.html`）是阶段 3 的主要改动对象：结果表要显示食材名、数量、最高置信度，并提供**可编辑的克数输入框**（03 §B 的人工兜底），引擎标识要区分自训练模型和 COCO 兜底。
- 用户输入显示时依赖 Jinja2 的自动转义，不要随意加 `|safe`。
- 单个模板不超过 800 行（现在最长 `daily.html` 478 行）。

## 怎么验证

启动应用后用浏览器看页面，截图作为总纲验收证据（参考 `docs/acceptance/stage-0/0.7-*.png`）。
