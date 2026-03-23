#!/usr/bin/env python3

import sys
import subprocess
import tarfile
import os
import tempfile
from pathlib import Path
import time
import re
# 插入通用脚本路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "common_py"))
sys.path.insert(0, parent_dir)

from download_whl_sdist import download_sdist
from check_whl import has_whl_in_gitlab

# 拆分包名和版本
def parse_package_spec(package_spec: str):
    if "==" in package_spec:
        name, version = package_spec.split("==", 1)
        return name.strip(), version.strip()
    return package_spec.strip(), None

# 下载源码
def download_source(package_spec, download_dir):
    print(f"📦 Downloading source for {package_spec}")
    pkg, ver = parse_package_spec(package_spec)
    save_path, ver = download_sdist(pkg, version=ver, dest_dir=download_dir)
    return save_path, ver

def download_source_with_retry(package_spec, download_dir, max_retries=5, delay=3):
    for attempt in range(1, max_retries + 1):
        try:
            save_path, ver = download_source(package_spec, download_dir)
            return save_path, ver
        except Exception as e:
            print(f"⚠️ 下载失败（第 {attempt} 次）：{e}")
            if attempt < max_retries:
                print(f"⏳ {delay} 秒后重试...")
                time.sleep(delay)
            else:
                print("❌ 已重试 {max_retries} 次仍失败，放弃。")
                raise

def has_whl_in_gitlab_with_retry(package_spec, max_retries=5, delay=3):
    pkg, ver = parse_package_spec(package_spec)
    for attempt in range(1, max_retries + 1):
        try:
            return has_whl_in_gitlab(package_name=pkg, version=ver)
        except Exception as e:
            print(f"⚠️ GitLab 查询失败（第 {attempt} 次）：{e}")
            if attempt < max_retries:
                print(f"⏳ {delay} 秒后重试...")
                time.sleep(delay)
            else:
                print("❌ GitLab 查询重试 {max_retries} 次仍失败，放弃。")
                raise

# 提取源码
def extract_source(download_dir):
    for file in os.listdir(download_dir):
        if file.endswith(".tar.gz"):
            path = os.path.join(download_dir, file)
            with tarfile.open(path, "r:gz") as tar:
                tar.extractall(path=download_dir)
                top_level = next(
                    (name.split('/')[0] for name in tar.getnames() if "/" in name),
                    None
                )
                if not top_level:
                    raise RuntimeError("Failed to detect top-level directory in tar.gz")
                return os.path.join(download_dir, top_level)
    raise FileNotFoundError("No .tar.gz source archive found in download dir.")

def get_glibc_version() -> tuple[int, int]:
    """返回 glibc 主版本和次版本，例如 2.39 -> (2, 39)"""
    try:
        out = subprocess.check_output(["ldd", "--version"], text=True)
        # 通常第一行形如 "ldd (Ubuntu GLIBC 2.39-0ubuntu3) 2.39"
        m = re.search(r" (\d+)\.(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 0, 0  # 默认未知版本