#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

# 获取当前文件的目录（hp_build），再拼接到上一级（即项目根目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "common_py/fix_whl"))
sys.path.insert(0, parent_dir)

from fix_whl_rpath import process_whl_rpath

pkg_name = os.environ.get("PKG_NAME", 'torchvision')

pip_cache_dir = os.environ.get("WHEEL_CACHE_DIR_PY")

PIP_CACHE_DIR = Path(os.path.expanduser(pip_cache_dir))

# === 配置项 ===
WHEELS_REPAIR_DIR = Path(os.path.expanduser(f"~/wheels_repair/build_{pkg_name}"))
RECORD_FILE = Path(os.path.expanduser("~/.upload_whl_log.txt"))
PYPI_REPO = "gitlab"

# 保证目录存在
PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

def find_built_wheels():
    print(f"🔍 Searching for built wheels in pip cache {PIP_CACHE_DIR}...")
    whls = list(PIP_CACHE_DIR.rglob("*.whl"))
    whls = [w for w in whls if w.is_file()]
    if not whls:
        print("⚠️  No .whl files found.")
    return whls

def try_auditwheel_repair(whl_path: Path) -> Path:
    print(f"🛠️  Trying auditwheel repair: {whl_path.name}")

    # 判断是否带有 none 字段（可按需更精确）
    if "none" in whl_path.name:
        print(f"⚠️  Skipping auditwheel repair for wheel with 'none' tag: {whl_path.name}")
        fallback_path = WHEELS_REPAIR_DIR / whl_path.name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path

    try:
        if pkg_name == "torchvision":
            exclude_libs = [
                'libc10.so', 'libtorch.so', 'libtorch_cpu.so', 'libtorch_python.so'
            ]

        elif (pkg_name == "torchaudio"):
            exclude_libs = [
                'libc10.so', 'libtorch.so', 'libtorch_cpu.so', 'libtorch_python.so',
                'libtorchaudio.so', 'libtorchaudio_sox.so', 'libtorio_ffmpeg.so',
                'libsox.so'
            ]

        else:
            torch_main_version = os.environ.get("PYTORCH_BUILD_VERSION", "2.8.0")
            torch_main_version = float(torch_main_version[:-2])

            if torch_main_version < 2.7:
                exclude_libs = [
                    'libtorch.so', 'libtorch_cpu.so', 'libc10.so',
                    'libbackend_with_compiler.so', 'libjitbackend_test.so'
                ]
            else:
                exclude_libs = []

        cmd = [
            "auditwheel", "repair",
            str(whl_path),
            "-w", str(WHEELS_REPAIR_DIR),
            "--disable-isa-ext-check",
        ]

        # 检查 Python 版本并决定是否添加 --no-update-tags
        if sys.version_info.major == 3 and sys.version_info.minor <= 12:
            print(f"🔧 Detected Python {sys.version_info.major}.{sys.version_info.minor} <= 3.12, adding --no-update-tags")
            cmd.append("--no-update-tags")
        else:
            print(f"ℹ️  Detected Python {sys.version_info.major}.{sys.version_info.minor} > 3.12, not adding --no-update-tags")

        for lib in exclude_libs:
            cmd += ["--exclude", lib]

        # 获取 repair 目录之前的文件列表
        before_files = set(WHEELS_REPAIR_DIR.glob("*.whl"))

        subprocess.run(cmd, check=True)

        # 获取 repair 目录之后的文件列表
        after_files = set(WHEELS_REPAIR_DIR.glob("*.whl"))
        new_files = list(after_files - before_files)

        if new_files:
            repaired_whl = new_files[0]
            print(f"✅ auditwheel repair succeeded: {repaired_whl.name}")
            return repaired_whl
        else:
            raise FileNotFoundError("No repaired .whl file found")

    except Exception as e:
        print(f"❌ auditwheel repair failed: {e}")
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

def main():
    whl_files = find_built_wheels()
    for whl in whl_files:

        if pkg_name not in str(whl.name):
            print("跳过处理........", str(whl.name))
            continue
        else:
            try:
                final_whl = try_auditwheel_repair(whl)
                process_whl_rpath(str(final_whl))
                upload_whl(final_whl)
            except subprocess.CalledProcessError:
                print(f"⚠️  Upload failed for {whl.name}")
            except Exception as e:
                print(f"⚠️  Unexpected error for {whl.name}: {e}")
    clean_dirs()

if __name__ == "__main__":
    main()
