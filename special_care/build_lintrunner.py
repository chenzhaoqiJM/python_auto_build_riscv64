#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import zipfile
import os
import shutil
import tempfile
from pathlib import Path

from tools import download_source_with_retry, extract_source
from registry import register

def patch_pyproject(pyproject_path):
    print(f"🛠 Patching {pyproject_path}")
    lines = pyproject_path.read_text().splitlines()
    in_build_system = False
    new_lines = []

    for line in lines:
        if line.strip() == "[build-system]":
            in_build_system = True
            new_lines.append(line)
            continue
        if in_build_system and line.strip().startswith("requires"):
            new_lines.append('requires = ["maturin>=0.12,<0.15"]')
            in_build_system = False  # 只改一次
            continue
        new_lines.append(line)

    pyproject_path.write_text("\n".join(new_lines))

def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel","--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("lintrunner")
def build_lintrunner_func(package_spec, wheel_dir):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:

            # 没有whl，下载源码编译
            download_source_with_retry(package_spec, tmpdir)
            source_dir = extract_source(tmpdir)

            pyproject_path = Path(source_dir) / "pyproject.toml"
            if not pyproject_path.exists():
                print(f"❌ pyproject.toml not found in {source_dir}")
                sys.exit(1)

            patch_pyproject(pyproject_path)
            build_wheel(source_dir, wheel_dir)
            print("✅ Build complete. You can now run your upload script.")
        except Exception as e:
            print(f"❌ Error during lintrunner build: {e}", file=sys.stderr)
            sys.exit(1)

# 可作为主程序或被其他脚本调用
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_lintrunner.py lintrunner [<wheel_dir>]", file=sys.stderr)
        sys.exit(1)

    package_spec = sys.argv[1]
    wheel_dir = sys.argv[2] if len(sys.argv) >= 3 else os.getcwd()

    build_lintrunner_func(package_spec, wheel_dir)
