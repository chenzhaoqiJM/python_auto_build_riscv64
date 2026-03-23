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

# 修改部分源码
def patch_project(source_dir: Path):

    cmake_file = source_dir / "CMakeLists.txt"

    text = cmake_file.read_text()

    # 只处理 CMAKE_CXX_FLAGS 的设置行：去掉 -flto 并追加 -fPIC
    def repl(m):
        # 去掉 -flto
        flags = f"{m.group(2)} {m.group(3)}".replace("  ", " ").strip()
        # 确保有 -fPIC
        if "-fPIC" not in flags:
            flags = f"{flags} -fPIC"
        return f'{m.group(1)}"{flags}"'

    text = re.sub(
        r'(set\(CMAKE_CXX_FLAGS.*)"([^"]*?)\s*-flto\s*([^"]*?)"',
        repl,
        text
    )

    cmake_file.write_text(text)

    print("✅ 已修改 CMakeLists.txt，去掉 -flto 并加上 -fPIC：\n")
    # print(text)


def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("mmcif")
def build_mmcif_func(package_spec, wheel_dir):
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

