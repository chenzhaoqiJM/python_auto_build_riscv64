#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import os
import tempfile
from pathlib import Path
import time
import re

import shutil
from tools import download_source_with_retry, extract_source
from registry import register

# 修改部分源码
def patch_project(source_dir: Path):
    glfw_dir = source_dir / "glfw"
    if not glfw_dir.exists():
        raise FileNotFoundError(f"❌ 未找到 {glfw_dir}，确认源码目录是否正确")

    # 要创建的子目录
    subdirs = ["wayland", "x11"]

    # 系统 libglfw 路径
    system_lib = Path("/usr/lib/riscv64-linux-gnu/libglfw.so")
    if not system_lib.exists():
        raise FileNotFoundError(f"❌ 系统库不存在: {system_lib}")

    for sub in subdirs:
        target_dir = glfw_dir / sub
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / "libglfw.so"
        shutil.copy(system_lib, target_file)
        print(f"✅ 已复制 {system_lib} -> {target_file}")


def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("glfw")
def build_glfw_func(package_spec, wheel_dir):
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

