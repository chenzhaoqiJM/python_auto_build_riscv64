#!/usr/bin/env python3
import os
import re
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
PIP_CACHE_DIR = os.getenv("PIP_CACHE_DIR", "~/.cache/pip/wheels")
PIP_CACHE_DIR = Path(os.path.expanduser(PIP_CACHE_DIR))
UV_CACHE_DIR = Path(os.path.expanduser("~/.cache/uv"))
WHEELS_REPAIR_DIR = os.getenv("WHEELS_REPAIR_DIR", "~/wheels_repair")
WHEELS_REPAIR_DIR = Path(os.path.expanduser(WHEELS_REPAIR_DIR))

RECORD_FILE = Path(os.path.expanduser("~/.upload_whl_log.txt"))
PYPI_REPO = "gitlab"
UPLOAD_TIMEOUT_SECONDS = int(os.getenv("UPLOAD_TIMEOUT_SECONDS", "1800"))

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
    THE_BUILD_PACKAGE_NAME=THE_BUILD_PACKAGE_NAME.split("/")[-1]


def canonicalize_package_name(name: str) -> str:
    """按 Python 包名规则统一 ``-``、``_`` 和 ``.``。"""
    return re.sub(r"[-_.]+", "-", name).lower()

def find_built_wheels():
    print("🔍 Searching for built wheels in pip cache...")
    whls_pip = list(PIP_CACHE_DIR.rglob("*.whl"))
    # whls_uv = list(UV_CACHE_DIR.rglob("*.whl"))
    whls_uv = []

    new_whls = []
    for w in whls_pip + whls_uv:
        if w.is_file():
            new_whls.append(w)
    whls = new_whls

    if not whls:
        print(f"⚠️  No .whl files found. try scaning {str(WHEEL_CACHE_DIR)}")

        if str(WHEEL_CACHE_DIR) != '.' and str(WHEEL_CACHE_DIR) != '':
            FROM_WHEEL_CACHE_FLAG = True
            _tmp_whls = list(WHEEL_CACHE_DIR.rglob("*.whl"))
            _tmp_whls = [w for w in _tmp_whls if w.is_file()]
            target_name = canonicalize_package_name(
                THE_BUILD_PACKAGE_NAME.split("==", 1)[0]
            )

            for _whl_file in _tmp_whls:
                wheel_name = canonicalize_package_name(
                    _whl_file.name.split("-", 1)[0]
                )
                if target_name and wheel_name == target_name:
                    whls.append(_whl_file)
                    print(f"✅ find the relevant pkg: {_whl_file}")
                    break

    print("📦 Found wheel files:")
    for w in whls:
        print(f"  - {w.resolve()}")
    return whls

def try_auditwheel_repair(whl_path: Path) -> Path:

    whl_name = whl_path.name

    print(f"🛠️  Trying auditwheel repair: {str(whl_path)}")

    # 检查 wheel 名称是否包含跳过关键字
    if any(keyword in whl_name for keyword in SKIP_KEYWORDS):
        print(f"⚠️  Skipping auditwheel repair for wheel with skip-tag: {whl_name}")
        fallback_path = WHEELS_REPAIR_DIR / whl_name
        shutil.copy2(whl_path, fallback_path)
        print(f"📋 Copied original wheel to: {fallback_path}")
        return fallback_path

    try:
        exclude_libs = ['libglib*.so.*', 'libgobject*.so.*', 'libgio*.so.*', 'libgdk*.so*', 'libgmodule*.so*']

        if FROM_SOURCE_FLAG == "1":
            cmd = [
                "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR), "--disable-isa-ext-check", "--plat", AUDITWHEEL_PLAT_DEF
            ]
        else:
            if sys.version_info.major == 3 and sys.version_info.minor <= 12:
                cmd = [
                    "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR), "--disable-isa-ext-check",
                ]
            else:
                cmd = [
                    "auditwheel", "repair", str(whl_path), "-w", str(WHEELS_REPAIR_DIR), "--disable-isa-ext-check", "--plat", AUDITWHEEL_PLAT_DEF
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

def is_gitlab_project_81_pypirc() -> bool:
    pypirc_path = Path(os.path.expanduser("~/.pypirc"))
    if not pypirc_path.is_file():
        return False

    try:
        content = pypirc_path.read_text()
    except Exception as e:
        print(f"⚠️  Failed to read {pypirc_path}: {e}")
        return False

    return (
        "[gitlab]" in content
        and "git.spacemit.com/api/v4/projects/81/packages/pypi" in content
    )

def upload_whl(whl_path: Path):
    if 'none-any' in str(whl_path.name):
        print("none-any 包，不上传")
        return
    if (not is_gitlab_project_81_pypirc()) and ('abi3' in whl_path.name or 'none' in whl_path.name) and sys.version_info[:2] > (3, 12):
        print(f"检测到 abi3 包 或 none 包，且当前 Python 版本为 {sys.version_info.major}.{sys.version_info.minor}，跳过上传: {whl_path.name}")
        return
    print(f"🚀 Uploading {whl_path.name} to PyPI repo: {PYPI_REPO}")
    env = os.environ.copy()
    env.setdefault("TWINE_NON_INTERACTIVE", "1")
    subprocess.run([
        "twine", "upload", "-r", PYPI_REPO, str(whl_path)
    ], check=True, timeout=UPLOAD_TIMEOUT_SECONDS, env=env)
    with open(RECORD_FILE, "a") as f:
        f.write(f"{datetime.now()} {whl_path.name}\n")

def clean_dirs():
    print("🧹 Cleaning pip cache and repaired wheels directories...")
    shutil.rmtree(PIP_CACHE_DIR, ignore_errors=True)
    shutil.rmtree(WHEELS_REPAIR_DIR, ignore_errors=True)
    PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

def main():
    shutil.rmtree(WHEELS_REPAIR_DIR, ignore_errors=True)
    WHEELS_REPAIR_DIR.mkdir(parents=True, exist_ok=True)

    whl_files = find_built_wheels()
    if not whl_files:
        clean_dirs()
        if THE_BUILD_PACKAGE_NAME:
            print(f"❌ No wheel found for package: {THE_BUILD_PACKAGE_NAME}")
            return 1
        print("ℹ️ No target package specified; cache cleanup only")
        return 0

    for whl in whl_files:
        try:
            # 打包动态库
            final_whl = try_auditwheel_repair(whl)

            # 修复动态库
            final_whl2 = process_whl_rpath(str(final_whl), skip_tag=SKIP_KEYWORDS)
            if final_whl2 is None:
                final_whl2 = final_whl

            # 修复 abi 3
            final_whl3 = patch_whl_to_abi3(final_whl2)
            if final_whl3 is None:
                final_whl3 = final_whl2

            upload_whl(Path(final_whl3))
            # shutil.copy2(final_whl3, '/home/zqpi/')
        except subprocess.TimeoutExpired:
            print(f"⏰ Upload timed out after {UPLOAD_TIMEOUT_SECONDS}s for {whl.name}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Upload failed for {whl.name}")
        except Exception as e:
            print(f"⚠️  Unexpected error for {whl.name}: {e}")
    clean_dirs()
    return 0

if __name__ == "__main__":
    sys.exit(main())
