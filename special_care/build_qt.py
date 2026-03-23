#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import os
import tempfile
from pathlib import Path
import time
import re

from tools import download_source_with_retry, extract_source
from registry import register

def patch_project(source_dir: Path):
    project_file = source_dir / "project.py"
    if not project_file.exists():
        print(f"❌ {project_file} not found")
        return

    print(f"🛠 Patching {project_file} ...")

    # 读取文件内容
    with open(project_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # 找到目标行，插入修改
        if line.strip() == "if tool == 'pep517':":
            new_lines.append("        self.confirm_license = True\n")
            new_lines.append(line)  # 保留原来的 if
        else:
            new_lines.append(line)

    # 写回文件
    with open(project_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✅ Patched {project_file} successfully.")


def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("pyqt5", "pyqt6")
def build_qt_func(package_spec, wheel_dir):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:

            # 没有whl，下载源码编译
            download_source_with_retry(package_spec, tmpdir)
            source_dir = extract_source(tmpdir)

            # 必要 patch
            patch_project(Path(source_dir))

            # 执行构建
            build_wheel(source_dir, wheel_dir)
            print("✅ Build complete.")

        except Exception as e:
            print(f"❌ Error during build: {e}", file=sys.stderr)
            sys.exit(1)