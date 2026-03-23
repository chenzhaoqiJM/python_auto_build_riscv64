#!/usr/bin/env python3

import sys
import subprocess
import os
import tempfile
from pathlib import Path
import re

from tools import download_source_with_retry, extract_source
from registry import register


def patch_setup_py(source_dir: str):
    """修复 setup.py 中 spawn() 调用的 dry_run 参数问题。
    新版 setuptools 的 distutils.spawn.spawn() 不再接受 dry_run 关键字参数。
    """
    setup_py = os.path.join(source_dir, "setup.py")
    if not os.path.exists(setup_py):
        raise FileNotFoundError(f"❌ 未找到 {setup_py}")

    with open(setup_py, "r") as f:
        content = f.read()

    # spawn(cmd, dry_run=dry_run) -> spawn(cmd)
    patched = content.replace("spawn(cmd, dry_run=dry_run)", "spawn(cmd)")

    if patched == content:
        print("⚠️  未找到需要 patch 的 spawn 调用，可能已修复或版本不同")
        return

    with open(setup_py, "w") as f:
        f.write(patched)

    print("✅ 已 patch setup.py: 移除 spawn() 的 dry_run 参数")


def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )


@register("llvmlite")
def build_llvmlite_func(package_spec, wheel_dir):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # 下载源码
            download_source_with_retry(package_spec, tmpdir)
            source_dir = extract_source(tmpdir)

            # patch setup.py
            patch_setup_py(source_dir)

            # 执行构建
            build_wheel(source_dir, wheel_dir)
            print("✅ Build complete.")

        except Exception as e:
            print(f"❌ Error during build: {e}", file=sys.stderr)
            sys.exit(1)
