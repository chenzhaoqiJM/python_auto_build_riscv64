#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

# === 配置项 ===
PIP_CACHE_DIR = Path(os.path.expanduser("~/.cache/pip/wheels"))
WHEELS_REPAIR_DIR = Path(os.path.expanduser("~/wheels_repair"))
RECORD_FILE = Path(os.path.expanduser("~/.upload_whl_log.txt"))
PYPI_REPO = "gitlab"

# 保证目录存在
PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

def find_built_wheels():
    print("🔍 Searching for built wheels in pip cache...")
    whls = list(PIP_CACHE_DIR.rglob("*.whl"))
    whls = [w for w in whls if w.is_file()]
    if not whls:
        print("⚠️  No .whl files found.")
    return whls

def try_auditwheel_repair(whl_path: Path) -> Path:
    print(f"🛠️  Trying auditwheel repair: {whl_path.name}")
    try:
        subprocess.run([
            "auditwheel", "repair",
            "--no-update-tags",
            "--disable-isa-ext-check",
            str(whl_path),
            "-w", str(WHEELS_REPAIR_DIR)
        ], check=True)
        # 返回生成的文件路径
        repaired_whls = list(WHEELS_REPAIR_DIR.glob(f"*{whl_path.stem}*.whl"))
        if repaired_whls:
            print(f"✅ auditwheel repair succeeded: {repaired_whls[0].name}")
            return repaired_whls[0]
        else:
            raise FileNotFoundError("No repaired .whl file found")
    except Exception as e:
        print(f"❌ auditwheel repair failed: {e}")
        # 直接复制原始文件
        fallback_path = WHEELS_REPAIR_DIR / whl_path.name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path

def upload_whl(whl_path: Path):
    print(f"🚀 Uploading {whl_path.name} to PyPI repo: {PYPI_REPO}")
    subprocess.run([
        "twine", "upload", "-r", PYPI_REPO, str(whl_path)
    ], check=True)
    with open(RECORD_FILE, "a") as f:
        f.write(f"{datetime.now()} {whl_path.name}\n")

def clean_dirs():
    print("🧹 Cleaning pip cache and repaired wheels directories...")
    shutil.rmtree(PIP_CACHE_DIR, ignore_errors=True)
    shutil.rmtree(WHEELS_REPAIR_DIR, ignore_errors=True)
    PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

def main():
    whl_files = find_built_wheels()
    for whl in whl_files:
        try:
            final_whl = try_auditwheel_repair(whl)
            upload_whl(final_whl)
        except subprocess.CalledProcessError:
            print(f"⚠️  Upload failed for {whl.name}")
        except Exception as e:
            print(f"⚠️  Unexpected error for {whl.name}: {e}")
    clean_dirs()

if __name__ == "__main__":
    main()
