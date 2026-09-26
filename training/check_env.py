# -*- coding: utf-8 -*-
"""Training machine self-check for stage 0 (items 0.8 - 0.13 of the master plan).

Runs every check, prints the result, and writes an evidence file.
No dataset download is needed: the smoke test trains on a tiny synthetic
dataset, so it also works where the GitHub download CDN is unreachable.

Usage (from the project root, inside the venv):
    python training/check_env.py                 # training machine, GPU 0 -> official evidence
    python training/check_env.py --device cpu    # dry run on a CPU-only machine (NOT evidence)

In --device cpu mode the GPU checks are marked SKIP, the summary says DRY-RUN,
and the report goes to training/runs/ (git-ignored) instead of docs/acceptance/,
so a dry run can never be mistaken for, or block, the real evidence.

Note: on a CUDA device ultralytics runs an AMP check that tries to download a
small model. If GitHub is unreachable it is skipped after a timeout; this can
add a few minutes but does not fail the smoke test.

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
EVIDENCE_DIR = os.path.join(ROOT, "docs", "acceptance", "stage-0")
EVIDENCE_NAME = "0.8-0.13-train-machine.txt"
DRY_RUN_NAME = "check_env-cpu-dryrun.txt"
EXPECTED_GPU = "4060"

LINES = []
RESULTS = []  # (item, status, summary); status is PASS / FAIL / SKIP


def log(text=""):
    print(text, flush=True)
    LINES.append(text)


def record(item, status, summary):
    RESULTS.append((item, status, summary))
    log(f"[{item}] {status} - {summary}")
    log()


def run_cmd(cmd):
    """Run a command and return (returncode, combined output). Returncode is None if not found."""
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        # rstrip only: leading spaces are meaningful in `git status --porcelain` output
        return p.returncode, (p.stdout + p.stderr).rstrip()
    except FileNotFoundError:
        return None, f"command not found: {cmd[0]}"


def check_nvidia_smi(ctx):
    log("== 0.8 nvidia-smi ==")
    code, out = run_cmd(["nvidia-smi"])
    log(out)
    if ctx["cpu_mode"]:
        record("0.8 nvidia-smi", "SKIP", "not required in --device cpu dry run")
    else:
        record("0.8 nvidia-smi", "PASS" if code == 0 else "FAIL",
               "nvidia-smi ran" if code == 0 else "nvidia-smi failed or missing")


def check_torch(ctx):
    log("== 0.8/0.9 torch ==")
    import torch
    cuda_ok = torch.cuda.is_available()
    name = torch.cuda.get_device_name(0) if cuda_ok else None
    log(f"torch.__version__       = {torch.__version__}")
    log(f"torch.version.cuda      = {torch.version.cuda}")
    log(f"torch.cuda.is_available = {cuda_ok}")
    log(f"device 0 name           = {name}")
    if ctx["cpu_mode"]:
        record("0.8/0.9 torch", "SKIP", f"torch {torch.__version__}; CUDA not required in --device cpu dry run")
    elif not (cuda_ok and torch.version.cuda is not None):
        record("0.8/0.9 torch", "FAIL",
               "CUDA build of torch not usable; reinstall torch from the CUDA index (plan 02 section 1)")
    elif EXPECTED_GPU not in name:
        record("0.8/0.9 torch", "FAIL", f"device 0 is '{name}', expected an RTX {EXPECTED_GPU}")
    else:
        record("0.8/0.9 torch", "PASS", f"CUDA {torch.version.cuda}, device '{name}'")


def check_ultralytics(ctx):
    log("== ultralytics version ==")
    import ultralytics
    ver = ultralytics.__version__
    major, minor = (int(x) for x in ver.split(".")[:2])
    log(f"ultralytics.__version__ = {ver}")
    record("ultralytics >= 8.3", "PASS" if (major, minor) >= (8, 3) else "FAIL", ver)


def check_settings(ctx):
    """Runs before the smoke training so that training already happens with sync disabled."""
    log("== 0.11 ultralytics settings ==")
    from ultralytics import settings
    settings.update({"sync": False})
    value = settings["sync"]
    log(f"settings file = {getattr(settings, 'file', 'unknown')}")
    log(f"sync          = {value}")
    record("0.11 sync=False", "PASS" if value is False else "FAIL", f"sync = {value}")


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
            with open(os.path.join(lbl_dir, f"{split}_{i}.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(labels) + "\n")
    data_yaml = os.path.join(SMOKE_DIR, "smoke.yaml")
    # utf-8, so a project path containing non-ASCII characters still works
    with open(data_yaml, "w", encoding="utf-8") as f:
        f.write(f"path: {SMOKE_DIR.replace(os.sep, '/')}\ntrain: images/train\nval: images/val\nnames:\n  0: box\n")
    return data_yaml


def check_smoke_train(ctx):
    log("== 0.10 smoke training (1 epoch, synthetic data) ==")
    device = ctx["device"]
    if not os.path.exists(WEIGHTS):
        record("0.10 smoke train", "FAIL", f"{WEIGHTS} not found; run `python scripts/download_model.py` first")
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
        record("0.10 smoke train", "PASS", f"1 epoch on device={device} in {elapsed:.1f}s, saved to {save_dir}")
    except Exception:
        log(traceback.format_exc())
        record("0.10 smoke train", "FAIL", "training raised an exception (traceback above)")


def check_git(ctx):
    log("== 0.13 git ==")
    _, branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    code, head = run_cmd(["git", "log", "-1", "--format=%H %ad", "--date=iso"])
    _, porcelain = run_cmd(["git", "status", "--porcelain"])
    # The evidence file of a previous run is the only change this script itself may leave behind.
    own = os.path.relpath(ctx["report_path"], ROOT).replace(os.sep, "/")
    dirty = [line for line in porcelain.splitlines() if line.strip() and not line.endswith(own)]
    log(f"branch = {branch}")
    log(f"HEAD   = {head}")
    log("git status --porcelain (excluding this script's own report):")
    log("\n".join(dirty) if dirty else "(clean)")
    if code != 0:
        record("0.13 git", "FAIL", "git log failed")
    elif dirty:
        record("0.13 git", "FAIL", f"working tree has {len(dirty)} uncommitted change(s); the code must match the delivered commit")
    else:
        record("0.13 git", "PASS", f"{branch} @ {head}; working tree clean")


CHECKS = [
    ("0.8 nvidia-smi", check_nvidia_smi),
    ("0.8/0.9 torch", check_torch),
    ("ultralytics >= 8.3", check_ultralytics),
    ("0.11 sync=False", check_settings),
    ("0.10 smoke train", check_smoke_train),
    ("0.13 git", check_git),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", default="0", help="CUDA device index, or 'cpu' for a dry run (default: 0)")
    parser.add_argument("--out", default=None,
                        help="directory for the report (default: docs/acceptance/stage-0, or training/runs in cpu mode)")
    args = parser.parse_args()
    cpu_mode = args.device.lower() == "cpu"
    out_dir = args.out or (RUNS_DIR if cpu_mode else EVIDENCE_DIR)
    report_path = os.path.join(out_dir, DRY_RUN_NAME if cpu_mode else EVIDENCE_NAME)
    ctx = {"device": args.device, "cpu_mode": cpu_mode, "report_path": report_path}

    log(f"check_env.py  time={time.strftime('%Y-%m-%d %H:%M:%S')}  device={args.device}"
        + ("  (DRY RUN - not valid as training machine evidence)" if cpu_mode else ""))
    log(f"python={sys.version.split()[0]}  executable={sys.executable}")
    log()

    for item, check in CHECKS:
        try:
            check(ctx)
        except Exception:
            log(traceback.format_exc())
            record(item, "FAIL", "unexpected exception (traceback above)")

    log("== SUMMARY ==")
    for item, status, summary in RESULTS:
        log(f"{status}  {item}: {summary}")
    failed = any(status == "FAIL" for _, status, _ in RESULTS)
    if cpu_mode:
        log(f"OVERALL: DRY-RUN {'FAIL' if failed else 'OK'} (cpu mode; GPU checks skipped; not acceptance evidence)")
    else:
        log(f"OVERALL: {'FAIL' if failed else 'PASS'}")

    os.makedirs(out_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print(f"report written to {report_path}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
