#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import shutil
import argparse

# 获取当前文件的目录（hp_build），再拼接到上一级（即项目根目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(current_dir)
sys.path.insert(0, parent_dir)

from fix_whl.fix_whl_rpath import process_whl_rpath

# 定义跳过关键字列表
SKIP_KEYWORDS = ["none", "cmake", "pyqt", "PyQt"]  # 可以随时扩展

# === 配置项 ===
WHEELS_REPAIR_DIR = Path(os.path.expanduser("~/wheels_repair_dir"))
RECORD_FILE = Path(os.path.expanduser("~/.upload_whl_log.txt"))
PYPI_REPO = "gitlab"

# 保证目录存在
WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

FROM_SOURCE_FLAG = os.environ.get("FROM_SOURCE_FLAG")
AUDITWHEEL_PLAT_DEF = os.environ.get("AUDITWHEEL_PLAT_DEF")

# whl 的存储和路径
WHEEL_CACHE_DIR = os.environ.get("WHEEL_CACHE_DIR_PY", "")
WHEEL_CACHE_DIR = Path(os.path.expanduser(WHEEL_CACHE_DIR))
FROM_WHEEL_CACHE_FLAG = False


def find_built_wheels(wheel_dir: Path):
    print(f"🔍 Searching for built wheels in: {wheel_dir}")
    whls = list(wheel_dir.rglob("*.whl"))

    if not whls:
        print(f"⚠️  No .whl files found. try scanning {str(WHEEL_CACHE_DIR)}")

    return whls


def try_auditwheel_repair(whl_path: Path) -> Path:
    whl_name = whl_path.name
    print(f"🛠️  Trying auditwheel repair: {whl_name}")

    # 检查 wheel 名称是否包含跳过关键字
    if any(keyword in whl_name for keyword in SKIP_KEYWORDS):
        print(f"⚠️  Skipping auditwheel repair for wheel with skip-tag: {whl_name}")
        fallback_path = WHEELS_REPAIR_DIR / whl_name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path

    try:
        exclude_libs = [
            'libglib*.so.*', 'libgobject*.so.*', 'libgio*.so.*', 'libX11*.so.*', 'libGLX*.so.*',
            'libGL*.so.*', 'libGLdispatch*.so.*', 'libxcb*.so.*', 'libXau*.so.*', 'libqwayland*.so.*',
            'libXdmcp*.so.*', 'libX*.so*', 'libgdk*.so*', 'libgio*.so*', 'libgmodule*.so*',
            'libgtk*.so*', 'libwayland*.so.*'
        ]

        cmd = [
            "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR)
        ]

        # 检查 Python 版本并决定是否添加 --no-update-tags
        if sys.version_info.major == 3 and sys.version_info.minor <= 12 and FROM_SOURCE_FLAG != "1":
            print(f"🔧 Detected Python {sys.version_info.major}.{sys.version_info.minor} <= 3.12, adding --no-update-tags")
            cmd.append("--no-update-tags")
        else:
            print(f"ℹ️  Detected Python {sys.version_info.major}.{sys.version_info.minor} > 3.12, not adding --no-update-tags")

        for lib in exclude_libs:
            cmd += ["--exclude", lib]

        before_files = set(WHEELS_REPAIR_DIR.glob("*.whl"))

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("❌ auditwheel repair failed!")
            print(f"   Command: {e.cmd}")
            print(f"   Return code: {e.returncode}")
            if e.stdout:
                print(f"   --- STDOUT ---\n{e.stdout}")
            if e.stderr:
                print(f"   --- STDERR ---\n{e.stderr}")
            # 这里 fallback
            fallback_path = WHEELS_REPAIR_DIR / whl_path.name
            shutil.copy2(whl_path, fallback_path)
            print(f"📋 Copied original wheel to: {fallback_path}")
            return fallback_path
        # subprocess.run(cmd, check=True)
        after_files = set(WHEELS_REPAIR_DIR.glob("*.whl"))

        new_files = list(after_files - before_files)

        print(f"生成的修复文件：{new_files}")

        if new_files:
            repaired_whl = new_files[0]
            print(f"✅ auditwheel repair succeeded: {repaired_whl.name}")
            return repaired_whl
        else:
            raise FileNotFoundError("No repaired .whl generate")

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
    shutil.rmtree(WHEELS_REPAIR_DIR, ignore_errors=True)
    WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Repair and upload wheels")
    parser.add_argument(
        "--wheel-dir",
        type=str,
        default="~/.cache/pip/wheels",
        help="Directory containing built wheel files"
    )
    args = parser.parse_args()

    clean_dirs

    wheel_dir = Path(os.path.expanduser(args.wheel_dir))

    whl_files = find_built_wheels(wheel_dir)
    for whl in whl_files:
        print()
        print(f"###开始处理{str(whl)}")
        try:
            final_whl = try_auditwheel_repair(whl)
            final_whl2 = process_whl_rpath(str(final_whl), skip_tag=SKIP_KEYWORDS)
            if final_whl2 is None:
                final_whl2 = final_whl

            upload_whl(Path(final_whl2))

        except subprocess.CalledProcessError:
            print(f"⚠️  Upload failed for {whl.name}")
        except Exception as e:
            print(f"⚠️  Unexpected error for {whl.name}: {e}")

    clean_dirs()


if __name__ == "__main__":
    main()
