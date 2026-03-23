#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import os
import tempfile
from pathlib import Path
import time
import re

from tools import download_source_with_retry, extract_source, get_glibc_version
from registry import register

# 修改部分源码
def patch_project(source_dir: Path):
    cmake_file = source_dir / "CMakeLists.txt"

    text = cmake_file.read_text()

    # 条件移除 FREE_THREADED
    major, minor = get_glibc_version()
    if (major, minor) <= (2, 39):
        text, n = re.subn(r"\bFREE_THREADED\b", "", text)
        if n > 0:
            print(f"✅ glibc {major}.{minor} ≤ 2.39，已移除 FREE_THREADED")
        else:
            print("⚠️ 没找到 FREE_THREADED，无需移除")
    else:
        print(f"ℹ️ glibc {major}.{minor} > 2.39，保留 FREE_THREADED")

    # === 2. 强制打开 ONNX_USE_PROTOBUF_SHARED_LIBS ===
    text, n = re.subn(
        r'option\(\s*ONNX_USE_PROTOBUF_SHARED_LIBS\s+"[^"]*"\s+OFF\s*\)',
        'option(ONNX_USE_PROTOBUF_SHARED_LIBS "Build ONNX using protobuf shared library." ON)',
        text
    )

    if n > 0:
        print("✅ 已将 ONNX_USE_PROTOBUF_SHARED_LIBS 设置为 ON")
    else:
        print("⚠️ 未找到 ONNX_USE_PROTOBUF_SHARED_LIBS 选项（可能已是 ON 或结构变化）")

    cmake_file.write_text(text)



def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("onnx")
def build_onnx_func(package_spec, wheel_dir):
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

