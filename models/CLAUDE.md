# models/：模型权重目录

先读根目录 `CLAUDE.md`。

| 文件 | 来源 | 入库 |
|---|---|---|
| `yolov8n.pt` | COCO 预训练兜底权重，`python scripts/download_model.py` 下载 | **否**（`*.pt` 已 gitignore） |
| `best.pt`、`best.onnx` | 阶段 2 在训练机训练后拷回，自训练的部署模型 | **否** |
| `model_card.json` | 阶段 2 的 `evaluate.py --update-card` 产出：数据集版本、指标、训练参数 | **是**（`.gitignore` 里专门放行） |

## 约定

- 权重和数据集一样不入库（总纲 0.12、1.13 的检查命令会查）。权重丢了无法恢复，答辩前备份 `best.pt`。
- `config.YOLO_MODEL` 是指向 `models/yolov8n.pt` 的绝对路径，`tests/test_model_path.py` 保证下载脚本和识别器指向同一处，改位置时两边一起改。
- 部署模型要有模型卡，论文里的指标以模型卡为准。
