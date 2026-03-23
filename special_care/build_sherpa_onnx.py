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

    # === 1. 强制打开 SHERPA_ONNX_ENABLE_SPACEMIT ===
    text, n = re.subn(
        r'option\(\s*SHERPA_ONNX_ENABLE_SPACEMIT\s+"[^"]*"\s+OFF\s*\)',
        'option(SHERPA_ONNX_ENABLE_SPACEMIT "Whether to build for SpacemiT CPUs" ON)',
        text
    )
    if n > 0:
        print("✅ 已将 SHERPA_ONNX_ENABLE_SPACEMIT 设置为 ON")
    else:
        print("⚠️ 未找到 SHERPA_ONNX_ENABLE_SPACEMIT 选项")

    cmake_file.write_text(text)




def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("sherpa-onnx", "sherpa_onnx")
def build_sherpa_onnx_func(package_spec, wheel_dir):
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

