#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

# 获取当前文件的目录（hp_build），再拼接到上一级（即项目根目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(current_dir)
sys.path.insert(0, parent_dir)

from fix_whl.fix_whl_rpath import process_whl_rpath
from fix_whl.fix_whl_name import patch_whl_to_abi3
# 定义跳过关键字列表
SKIP_KEYWORDS = ["none", "cmake", "pyqt", "PyQt"]  # 可以随时扩展
# === 配置项 ===
SAVE_FINAL_WHL_TO_HOME = os.environ.get("SAVE_FINAL_WHL_TO_HOME", "0") == "1"

PIP_CACHE_DIR = os.getenv("PIP_CACHE_DIR", "~/.cache/pip/wheels")
PIP_CACHE_DIR = Path(os.path.expanduser(PIP_CACHE_DIR))
WHEELS_REPAIR_DIR = os.getenv("WHEELS_REPAIR_DIR", "~/wheels_repair")
WHEELS_REPAIR_DIR = Path(os.path.expanduser(WHEELS_REPAIR_DIR))
RECORD_FILE = Path(os.path.expanduser("~/.upload_whl_log.txt"))
PYPI_REPO = "gitlab"

# 保证目录存在
PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

FROM_SOURCE_FLAG = os.environ.get("FROM_SOURCE_FLAG")
AUDITWHEEL_PLAT_DEF = os.environ.get("AUDITWHEEL_PLAT_DEF")

# whl 的存储和路径
WHEEL_CACHE_DIR = os.environ.get("WHEEL_CACHE_DIR_PY", "")
WHEEL_CACHE_DIR = Path(os.path.expanduser(WHEEL_CACHE_DIR))
FROM_WHEEL_CACHE_FLAG=False

# 包名或者源码路径
THE_BUILD_PACKAGE_NAME = os.environ.get("THE_BUILD_PACKAGE_NAME", "")
THE_BUILD_PACKAGE_NAME = os.path.expanduser(THE_BUILD_PACKAGE_NAME)
if THE_BUILD_PACKAGE_NAME != "" and "/" in THE_BUILD_PACKAGE_NAME:
    # 先移除末尾的斜杠，再进行分割
    THE_BUILD_PACKAGE_NAME = THE_BUILD_PACKAGE_NAME.rstrip('/').split('/')[-1]

def find_built_wheels():
    print("🔍 Searching for built wheels in pip cache...")
    whls = list(PIP_CACHE_DIR.rglob("*.whl"))
    whls = [w for w in whls if w.is_file()]

    if len(whls) == 0:
        # 只获取 .whl 文件，且文件名不包含 "none"
        files = [
            f for f in WHEEL_CACHE_DIR.iterdir()
            if f.is_file() and f.suffix == ".whl" and "none" not in f.name.lower()
        ]

        # 去掉与 whls 中同名的文件
        existing_names = {w.name for w in whls}
        files = [f for f in files if f.name not in existing_names]

        # 按创建时间排序（新→旧）
        files_sorted = sorted(files, key=lambda f: f.stat().st_ctime, reverse=True)

        # 取最近的两个
        latest_two = files_sorted[:2]

        whls = whls + latest_two

    return whls

def try_auditwheel_repair(whl_path: Path) -> Path:
    print(f"🛠️  Trying auditwheel repair: {str(whl_path)}")

    # 判断是否带有 none 字段（可按需更精确）
    # if "none" in whl_path.name:
    #     print(f"⚠️  Skipping auditwheel repair for wheel with 'none' tag: {whl_path.name}")
    #     fallback_path = WHEELS_REPAIR_DIR / whl_path.name
    #     shutil.copy2(whl_path, fallback_path)
    #     print(f"📋 Copied original wheel to: {fallback_path}")
    #     return fallback_path
    whl_name = whl_path.name
    if any(keyword in whl_name for keyword in SKIP_KEYWORDS):
        print(f"⚠️  Skipping auditwheel repair for wheel with skip-tag: {whl_name}")
        fallback_path = WHEELS_REPAIR_DIR / whl_name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path

    try:
        pkg_name=(str(whl_path.name).split("-"))[0]

        if "torch" in pkg_name and pkg_name != "torch":
            exclude_libs = [
                'libc10.so', 'libtorch*.so', 'libbackend_with_compiler.so', 'libjitbackend_test.so'
            ]
        elif "cyclonedds" in pkg_name:
            exclude_libs = ["libssl*", "libcrypto*"]
        else:
            exclude_libs = [
                # 'libgtk*.so*'
            ]

        if FROM_SOURCE_FLAG == "1":
            cmd = [
                "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR), "--disable-isa-ext-check", "--plat", AUDITWHEEL_PLAT_DEF
            ]
        else:
            cmd = [
                "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR), "--disable-isa-ext-check",
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

        # subprocess.run(cmd, check=True)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"auditwheel failed:\n{result.stderr}")

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
    PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

def main():
    whl_files = find_built_wheels()
    for whl in whl_files:
        try:
            final_whl = try_auditwheel_repair(whl)

            process_whl_rpath(str(final_whl))

            final_whl2 = process_whl_rpath(str(final_whl), skip_tag=SKIP_KEYWORDS)
            if final_whl2 is None:
                final_whl2 = final_whl

            # === 可选：保存最终 whl 到用户 HOME 目录 ===
            if SAVE_FINAL_WHL_TO_HOME:
                home_dir = Path.home()
                dst = home_dir / final_whl2.name
                shutil.copy2(final_whl2, dst)
                print(f"📦 Final wheel saved to HOME: {dst}")

            else:
                final_whl3 = patch_whl_to_abi3(final_whl2)
                if final_whl3 is None:
                    final_whl3 = final_whl2

                upload_whl(Path(final_whl3))

            print("分割线----------------------------------------\n")
        except subprocess.CalledProcessError:
            print(f"⚠️  Upload failed for {whl.name}")
        except Exception as e:
            print(f"⚠️  Unexpected error for {whl.name}: {e}")
    clean_dirs()

if __name__ == "__main__":
    main()
