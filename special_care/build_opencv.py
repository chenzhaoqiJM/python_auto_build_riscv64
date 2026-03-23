#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import os
import tempfile
from pathlib import Path
import time
import re
from packaging.version import Version

from tools import download_source_with_retry, extract_source
from registry import register

# 要写入的 pyproject.toml 内容
NEW_PYPROJECT_CONTENT = """[build-system]
requires = [
  "numpy>=2.0.0;  python_version>='3.9'",
  "packaging",
  "pip",
  "scikit-build>=0.14.0",
  "setuptools==59.2.0; python_version<'3.12'",
  "setuptools<70.0.0; python_version>='3.12'",
]
"""

NEW_PYPROJECT_CONTENT_LOW = """[build-system]
requires = [
  "numpy==1.26.2",
  "packaging",
  "pip",
  "scikit-build>=0.14.0",
  "setuptools==59.2.0; python_version<'3.12'",
  "setuptools<70.0.0; python_version>='3.12'",
]
"""


# 修改部分源码
def patch_project(source_dir: Path, version_num="4.12.0.88"):
    version_py_path = source_dir / "cv2/version.py"

    if not version_py_path.exists():
        print(f"❌ version.py not found in {source_dir}")
        sys.exit(1)

    print(f"🛠 Patching {version_py_path}")

    # 修改 version.py 内容
    with open(version_py_path, "r") as f:
        content = f.read()

    new_content = []
    for line in content.splitlines():
        if line.startswith("ci_build = "):
            new_content.append("ci_build = True")
        else:
            new_content.append(line)

    with open(version_py_path, "w") as f:
        f.write("\n".join(new_content) + "\n")

    # setup_py_path = source_dir / "setup.py"  # 假设 setup.py 在 source_dir 下
    # 修改 setup.py 中 libqxcb -> lib*
    # if setup_py_path.exists():
    #     print(f"🛠 Patching {setup_py_path} for libqxcb -> lib*")
    #     with open(setup_py_path, "r") as f:
    #         setup_content = f.read()

    #     # 替换
    #     setup_content = setup_content.replace("libqxcb", ".*")

    #     with open(setup_py_path, "w") as f:
    #         f.write(setup_content)
    # else:
    #     print(f"⚠️ setup.py not found in {source_dir}, skipping libqxcb patch")


    # 检查并修改 pyproject.toml
    pyproject_path = source_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            if Version(version_num) <= Version("4.10.0.84"):

                py_version = sys.version_info
                if py_version.minor>11:
                    if Version(version_num) == Version("4.10.0.84") or Version(version_num) == Version("4.10.0.82"):
                        print(f"📝 Replacing pyproject.toml (opencv {version_num})")
                        backup_path = pyproject_path.with_suffix(".toml.bak")
                        pyproject_path.rename(backup_path)  # 备份
                        with open(pyproject_path, "w", encoding="utf-8") as f:
                            f.write(NEW_PYPROJECT_CONTENT)
                    else:
                        print(f"📝 Replacing pyproject.toml OLD (opencv {version_num})")
                        backup_path = pyproject_path.with_suffix(".toml.bak")
                        pyproject_path.rename(backup_path)  # 备份
                        with open(pyproject_path, "w", encoding="utf-8") as f:
                            f.write(NEW_PYPROJECT_CONTENT_LOW)


                # 同时修改 patchQtPlugins
                patch_qt_plugins = source_dir / "patches" / "patchQtPlugins"
                if patch_qt_plugins.exists():
                    print(f"🛠 Patching {patch_qt_plugins}")
                    with open(patch_qt_plugins, "r", encoding="utf-8") as f:
                        patch_content = f.read()
                    # 用正则替换 Qt5.15.xx -> Qt5.15.16
                    patch_content_new = re.sub(
                        r"Qt5\.15\.\d+",
                        "Qt5.15.16",
                        patch_content
                    )
                    if patch_content != patch_content_new:
                        with open(patch_qt_plugins, "w", encoding="utf-8") as f:
                            f.write(patch_content_new)
                        print("✅ Replaced Qt5.15.x with Qt5.15.16")
                    else:
                        print("ℹ️ No Qt5.15.x pattern found in patchQtPlugins")

            else:
                # python3.14之后的支持
                if sys.version_info >= (3, 14):
                    if Version(version_num) == Version("4.12.0.88"):
                        text = pyproject_path.read_text(encoding="utf-8")
                        pattern = r'"numpy==2\.1\.3;\s*python_version==\'3\.13\'",'
                        replacement = (
                            '"numpy==2.1.3; python_version==\'3.13\'",\n'
                            '  "numpy==2.3.5; python_version>=\'3.14\'",'
                        )

                        new_text, count = re.subn(pattern, replacement, text)

                        if count != 1:
                            raise RuntimeError("Failed to patch pyproject.toml: pattern not found or ambiguous")

                        pyproject_path.write_text(new_text, encoding="utf-8")
                        print("pyproject.toml patched for 4.12.0.88 of Python >= 3.14")

        except Exception as e:
            print(f"⚠️ Failed to patch pyproject.toml: {e}")

def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("opencv-python", "opencv-contrib-python", "opencv-python-headless", "opencv-contrib-python-headless")
def build_opencv_func(package_spec, wheel_dir):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # 没有whl，下载源码编译
            save_path, ver_ret = download_source_with_retry(package_spec, tmpdir)
            source_dir = extract_source(tmpdir)

            split_list = package_spec.split("==")
            if len(split_list) > 1:
                version_num = split_list[-1]
            else:
                version_num = ver_ret
                print(f"获取到最新版本: {ver_ret}")

            # 必要 patch
            patch_project(Path(source_dir), version_num)

            # 执行构建
            build_wheel(source_dir, wheel_dir)
            print("✅ Build complete.")

        except Exception as e:
            print(f"❌ Error during build: {e}", file=sys.stderr)
            sys.exit(1)
