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
def patch_project(source_dir: Path, version_num="3.10.1"):
    versioneer_path = source_dir / "versioneer.py"
    limit_version = "3.8.4"
    if versioneer_path.exists():
        try:
            if Version(version_num) <= Version(limit_version):
                text = versioneer_path.read_text(encoding="utf-8")
                new_text = text.replace("SafeConfigParser", "ConfigParser")
                versioneer_path.write_text(new_text, encoding="utf-8")
                print(f"✅ Patched {versioneer_path}")
        except Exception as e:
            print(f"⚠️ Failed to patch versioneer.py: {e}")

        # 2. 修改 setupext.py 里的 configure 调用
    setupext_path = source_dir / "setupext.py"
    if setupext_path.exists() and  Version(version_num) <= Version(limit_version):
        try:
            text = setupext_path.read_text(encoding="utf-8")
            # 找到 subprocess.check_call(["./configure", ...]) 这行
            if "./configure" in text:
                new_text = text.replace(
                    '"./configure",',
                    '"./configure", "--build=riscv64-unknown-linux-gnu",'
                )
                setupext_path.write_text(new_text, encoding="utf-8")
                print(f"✅ Patched {setupext_path} (added --build)")
            # new_text = text.replace("./configure", "ConfigParser")
            # versioneer_path.write_text(new_text, encoding="utf-8")

        except Exception as e:
            print(f"⚠️ Failed to patch setupext.py: {e}")

def build_wheel(source_dir, wheel_dir):
    print(f"🔨 Building wheel in {source_dir}")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("matplotlib")
def build_matplotlib_func(package_spec, wheel_dir):
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

@version_check("matplotlib")
def check_matplotlib_version(package_spec, wheel_dir):
    split_list = package_spec.split("==")
    if len(split_list) > 1:
        version_num = split_list[-1]
    else:
        version_num = "3.10.6"

    # py_version = sys.version_info
    # if py_version.minor<=10:
    #     return False
    if Version(version_num) >= Version("3.9.0"):
        return False
    else:
        return True