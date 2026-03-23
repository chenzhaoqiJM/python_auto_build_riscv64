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

# 插入通用脚本路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "common_py"))
sys.path.insert(0, parent_dir)

from check_no_deps_func import get_no_deps_flag

def build_wheel(package_spec, source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")

    no_deps_flag = get_no_deps_flag(package_spec)

    cmd = ["pip", "wheel", "--verbose"]
    if no_deps_flag:  # 只有非空才添加
        cmd.append(no_deps_flag)
    cmd.extend([".", "-w", wheel_dir])

    subprocess.run(
        cmd,
        check=True,
        cwd=source_dir
    )

def build_all_func(package_spec, wheel_dir):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:

            # 没有whl，下载源码编译
            download_source_with_retry(package_spec, tmpdir)
            source_dir = extract_source(tmpdir)            

            # 执行构建
            build_wheel(package_spec, source_dir, wheel_dir)
            print("✅ Build complete.")

        except Exception as e:
            print(f"❌ Error during build: {e}", file=sys.stderr)
            sys.exit(1)

