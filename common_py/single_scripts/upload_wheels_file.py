#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

from ../fix_whl.fix_whl_rpath import process_whl_rpath

# 定义跳过关键字列表
SKIP_KEYWORDS = ["none", "cmake", "pyqt", "PyQt"]  # 可以随时扩展

# === 配置项 ===
WHEELS_REPAIR_DIR = Path(os.path.expanduser("~/wheels_repair"))
RECORD_FILE = Path(os.path.expanduser("~/.upload_whl_log.txt"))
PYPI_REPO = "gitlab"

# 保证目录存在
WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

FROM_SOURCE_FLAG = os.environ.get("FROM_SOURCE_FLAG")
AUDITWHEEL_PLAT_DEF = os.environ.get("AUDITWHEEL_PLAT_DEF")

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
        exclude_libs = []

        if FROM_SOURCE_FLAG == "1":
            cmd = [
                "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR),
                "--disable-isa-ext-check", "--plat", AUDITWHEEL_PLAT_DEF
            ]
        else:
            cmd = [
                "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR),
                "--disable-isa-ext-check",
            ]

        # 检查 Python 版本并决定是否添加 --no-update-tags
        if sys.version_info.major == 3 and sys.version_info.minor <= 12 and FROM_SOURCE_FLAG != "1":
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

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_whl.py <path_to_wheel>")
        sys.exit(1)

    whl_path = Path(sys.argv[1]).expanduser().resolve()
    if not whl_path.exists() or not whl_path.suffix.endswith(".whl"):
        print(f"❌ Invalid wheel path: {whl_path}")
        sys.exit(1)

    try:
        final_whl = try_auditwheel_repair(whl_path)

        final_whl2 = process_whl_rpath(str(final_whl), skip_tag=SKIP_KEYWORDS)

        if final_whl2 is None:
            final_whl2 = final_whl

        upload_whl(Path(final_whl2))
    except subprocess.CalledProcessError:
        print(f"⚠️  Upload failed for {whl_path.name}")
    except Exception as e:
        print(f"⚠️  Unexpected error for {whl_path.name}: {e}")

if __name__ == "__main__":
    main()
