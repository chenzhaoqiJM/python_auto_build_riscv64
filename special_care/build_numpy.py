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
from registry import register, version_check


# 修改部分源码
def patch_project(source_dir: Path, version_num="1.26.4"):
    """
    Patch pyproject.toml so that setuptools version pin
    like setuptools==59.2.0 is replaced with setuptools<70.0.0
    """
    pyproject = source_dir / "pyproject.toml"
    if not pyproject.exists():
        print("⚠️ No pyproject.toml found, skip patch.")
        return

    text = pyproject.read_text(encoding="utf-8")

    # 用正则替换 setuptools==任意版本号
    new_text = re.sub(
        r'setuptools==[0-9]+\.[0-9]+(\.[0-9]+)?',
        'setuptools<70.0.0',
        text
    )

    if text != new_text:
        pyproject.write_text(new_text, encoding="utf-8")
        print("✅ Patched setuptools requirement to <70.0.0")
    else:
        print("ℹ️ No setuptools==X.Y.Z found, nothing changed.")



def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("numpy")
def build_numpy_func(package_spec, wheel_dir):
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

            # 必要 patch
            patch_project(Path(source_dir), version_num)

            # 执行构建
            build_wheel(source_dir, wheel_dir)
            print("✅ Build complete.")

        except Exception as e:
            print(f"❌ Error during build: {e}", file=sys.stderr)
            sys.exit(1)

@version_check("numpy")
def check_numpy_version(package_spec, wheel_dir):
    split_list = package_spec.split("==")
    if len(split_list) > 1:
        version_num = split_list[-1]
    else:
        version_num = "2.3.2"

    py_version = sys.version_info
    if py_version.minor<=10:
        return False

    if Version(version_num) >= Version("1.26.0"):
        return False
    else:
        return True
