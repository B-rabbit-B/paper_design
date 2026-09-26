# -*- coding: utf-8 -*-
"""Training machine self-check for stage 0 (items 0.8 - 0.13 of the master plan).

Runs every check, prints the result, and writes an evidence file.
No dataset download is needed: the smoke test trains on a tiny synthetic
dataset, so it also works where the GitHub download CDN is unreachable.

Usage (from the project root, inside the venv):
    python training/check_env.py                 # training machine, GPU 0
    python training/check_env.py --device cpu    # dry run on a CPU-only machine

Output is ASCII-only on purpose, so it survives Windows PowerShell 5.1 pipes.
"""
import argparse
import os
import random
import shutil
import subprocess
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = os.path.join(ROOT, "models", "yolov8n.pt")
SMOKE_DIR = os.path.join(ROOT, "training", "datasets", "smoke")
RUNS_DIR = os.path.join(ROOT, "training", "runs")
EVIDENCE_NAME = "0.8-0.13-train-machine.txt"

LINES = []
RESULTS = []  # (item, passed, summary)


def log(text=""):
    print(text, flush=True)
    LINES.append(text)


def record(item, passed, summary):
    RESULTS.append((item, passed, summary))
    log(f"[{item}] {'PASS' if passed else 'FAIL'} - {summary}")
    log()


def run_cmd(cmd):
    """Run a command and return (returncode, combined output). Returncode is None if not found."""
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return None, f"command not found: {cmd[0]}"


def check_nvidia_smi(cpu_mode):
    log("== 0.8 nvidia-smi ==")
    code, out = run_cmd(["nvidia-smi"])
    log(out)
    if cpu_mode:
        record("0.8 nvidia-smi", True, "skipped in --device cpu mode")
    else:
        record("0.8 nvidia-smi", code == 0, "nvidia-smi ran" if code == 0 else "nvidia-smi failed or missing")


def check_torch(cpu_mode):
    log("== 0.8/0.9 torch ==")
    import torch
    cuda_ok = torch.cuda.is_available()
    log(f"torch.__version__      = {torch.__version__}")
    log(f"torch.version.cuda     = {torch.version.cuda}")
    log(f"torch.cuda.is_available = {cuda_ok}")
    if cuda_ok:
        log(f"device 0 name          = {torch.cuda.get_device_name(0)}")
    if cpu_mode:
        record("0.8/0.9 torch", True, f"torch {torch.__version__} (CUDA not required in cpu mode)")
    else:
        passed = cuda_ok and torch.version.cuda is not None
        record("0.8/0.9 torch", passed,
               f"CUDA {torch.version.cuda}, available={cuda_ok}" if passed
               else "CUDA build of torch not usable; reinstall torch from the CUDA index (plan 02 section 1)")


def check_ultralytics():
    log("== ultralytics version ==")
    import ultralytics
    ver = ultralytics.__version__
    major, minor = (int(x) for x in ver.split(".")[:2])
    log(f"ultralytics.__version__ = {ver}")
    record("ultralytics >= 8.3", (major, minor) >= (8, 3), ver)


def build_smoke_dataset():
    """8 train + 4 val images, 160x160, random colored boxes, a single class."""
    from PIL import Image, ImageDraw

    if os.path.isdir(SMOKE_DIR):
        shutil.rmtree(SMOKE_DIR)
    rng = random.Random(0)
    for split, count in (("train", 8), ("val", 4)):
        img_dir = os.path.join(SMOKE_DIR, "images", split)
        lbl_dir = os.path.join(SMOKE_DIR, "labels", split)
        os.makedirs(img_dir)
        os.makedirs(lbl_dir)
        for i in range(count):
            img = Image.new("RGB", (160, 160), (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
            draw = ImageDraw.Draw(img)
            labels = []
            for _ in range(rng.randint(1, 3)):
                w, h = rng.randint(20, 60), rng.randint(20, 60)
                x1, y1 = rng.randint(0, 160 - w), rng.randint(0, 160 - h)
                draw.rectangle([x1, y1, x1 + w, y1 + h],
                               fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
                labels.append(f"0 {(x1 + w / 2) / 160:.6f} {(y1 + h / 2) / 160:.6f} {w / 160:.6f} {h / 160:.6f}")
            img.save(os.path.join(img_dir, f"{split}_{i}.jpg"))
            with open(os.path.join(lbl_dir, f"{split}_{i}.txt"), "w", encoding="ascii") as f:
                f.write("\n".join(labels) + "\n")
    data_yaml = os.path.join(SMOKE_DIR, "smoke.yaml")
    with open(data_yaml, "w", encoding="ascii") as f:
        f.write(f"path: {SMOKE_DIR.replace(os.sep, '/')}\ntrain: images/train\nval: images/val\nnames:\n  0: box\n")
    return data_yaml


def check_smoke_train(device):
    log("== 0.10 smoke training (1 epoch, synthetic data) ==")
    if not os.path.exists(WEIGHTS):
        record("0.10 smoke train", False,
               f"{WEIGHTS} not found; run `python scripts/download_model.py` first")
        return
    try:
        from ultralytics import YOLO
        data_yaml = build_smoke_dataset()
        start = time.time()
        model = YOLO(WEIGHTS)
        model.train(data=data_yaml, epochs=1, imgsz=160, batch=4, workers=0, device=device,
                    project=RUNS_DIR, name="smoke", exist_ok=True, plots=False, verbose=False)
        elapsed = time.time() - start
        save_dir = getattr(getattr(model, "trainer", None), "save_dir", "unknown")
        record("0.10 smoke train", True, f"1 epoch on device={device} in {elapsed:.1f}s, saved to {save_dir}")
    except Exception:
        log(traceback.format_exc())
        record("0.10 smoke train", False, "training raised an exception (traceback above)")


def check_settings():
    log("== 0.11 ultralytics settings ==")
    from ultralytics import settings
    settings.update({"sync": False})
    value = settings["sync"]
    log(f"settings file = {getattr(settings, 'file', 'unknown')}")
    log(f"sync          = {value}")
    record("0.11 sync=False", value is False, f"sync = {value}")


def check_git():
    log("== 0.13 git log -1 ==")
    code, out = run_cmd(["git", "log", "-1", "--format=%H %ad", "--date=iso"])
    log(out)
    record("0.13 git log", code == 0, out if code == 0 else "git log failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", default="0", help="CUDA device index, or 'cpu' for a dry run (default: 0)")
    parser.add_argument("--out", default=os.path.join(ROOT, "docs", "acceptance", "stage-0"),
                        help="directory for the evidence file")
    args = parser.parse_args()
    cpu_mode = args.device.lower() == "cpu"

    log(f"check_env.py  time={time.strftime('%Y-%m-%d %H:%M:%S')}  device={args.device}")
    log(f"python={sys.version.split()[0]}  executable={sys.executable}")
    log()

    for check in (lambda: check_nvidia_smi(cpu_mode), lambda: check_torch(cpu_mode),
                  check_ultralytics, lambda: check_smoke_train(args.device), check_settings, check_git):
        try:
            check()
        except Exception:
            log(traceback.format_exc())
            record(getattr(check, "__name__", "check"), False, "unexpected exception (traceback above)")

    log("== SUMMARY ==")
    for item, passed, summary in RESULTS:
        log(f"{'PASS' if passed else 'FAIL'}  {item}: {summary}")
    all_passed = all(p for _, p, _ in RESULTS)
    log(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, EVIDENCE_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print(f"evidence written to {path}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
