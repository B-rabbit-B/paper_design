# .claude/：Claude Code 的项目配置

目前只有 `agents/stage-supervisor.md`：独立的阶段审查代理。先读根目录 `CLAUDE.md`。

## 约定

- 审查代理是**只读的验收员**：不替执行者补做工作，不修改数据集、清单、证据文件，只写审查报告到 `docs/acceptance/stage-N/`。
- 审查报告写入的文件名：最终审查 `supervisor-report.md`，中期 `supervisor-report-interim.md`；已存在时加 `-r2`、`-r3`，**不覆盖**。
- 改这份代理说明会改变验收的严格程度，要先告诉用户，并在总纲里记录。
- 不要把 API Key 或 `_local_secrets.py` 的内容写进这里。
