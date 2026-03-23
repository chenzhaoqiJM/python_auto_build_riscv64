#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import os
import tempfile
from pathlib import Path
import time
import re
import json

from tools import download_source_with_retry, extract_source
from registry import register

# 修改部分源码
def patch_project(source_dir: Path):
    """
    Patch curl-cffi project to support riscv64 by adding riscv64 config entry.
    """
    config_file = source_dir / "libs.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Cannot find {config_file}")

    # 读取 JSON
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 检查是否已有 riscv64
    if any(item.get("machine") == "riscv64" for item in data):
        print("riscv64 already supported, skip patch.")
        return

    # 构造 riscv64 的配置（使用系统 libcurl）
    riscv64_entry = {
        "system": "Linux",
        "machine": "riscv64",
        "pointer_size": 64,
        "libdir": "",
        "sysname": "linux",
        "link_type": "static",
        "libc": "gnu",
        "so_name": "libcurl-impersonate.so",
        "so_arch": "riscv64"
    }


    # 插入到列表末尾
    data.append(riscv64_entry)

    # 写回文件
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print("Patched architectures.json with riscv64 entry ✅")




def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("curl-cffi")
def build_curl_cffi_func(package_spec, wheel_dir):
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

