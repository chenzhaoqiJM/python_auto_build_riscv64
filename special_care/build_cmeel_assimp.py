#!/usr/bin/env python3

import sys
import subprocess
import os
import tempfile
import shutil
from pathlib import Path

from tools import has_whl_in_gitlab_with_retry, parse_package_spec
from registry import register

def get_git_repo_dir():
    """获取 git 仓库存储目录"""
    home = Path.home()
    git_dir = home / ".pip_git" / "cmeel-assimp"
    return git_dir

def clone_or_update_repo(git_dir: Path):
    """克隆或更新 git 仓库"""
    repo_url = "https://github.com/cmake-wheel/cmeel-assimp.git"

    if git_dir.exists():
        print(f"📂 仓库已存在: {git_dir}")
        print("🔄 更新仓库...")
        subprocess.run(["git", "fetch", "--all", "--tags"], check=True, cwd=git_dir)
    else:
        print(f"📥 克隆仓库到: {git_dir}")
        git_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(git_dir)], check=True)
        print("🔄 初始化子模块...")
        subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True, cwd=git_dir)

def find_matching_tag(git_dir: Path, version: str):
    """
    根据版本号查找匹配的 tag
    例如: 版本 6.0.2 -> tag v6.0.2.c0
    """
    # 获取所有 tags
    result = subprocess.run(
        ["git", "tag", "-l"],
        capture_output=True,
        text=True,
        check=True,
        cwd=git_dir
    )

    tags = result.stdout.strip().split('\n')

    # 查找匹配的 tag (格式: v{version}.c*)
    pattern = f"v{version}."
    matching_tags = [tag for tag in tags if tag.startswith(pattern)]

    if not matching_tags:
        raise ValueError(f"❌ 未找到版本 {version} 对应的 tag (期望格式: v{version}.c*)")

    # 如果有多个匹配，选择最新的（按字母序最大）
    selected_tag = sorted(matching_tags)[-1]
    print(f"✅ 找到匹配的 tag: {selected_tag}")
    return selected_tag

def checkout_version(git_dir: Path, tag: str):
    """切换到指定的 tag"""
    print(f"🔀 切换到 tag: {tag}")
    subprocess.run(["git", "checkout", tag], check=True, cwd=git_dir)
    print("🔄 更新子模块...")
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True, cwd=git_dir)

def build_wheel(source_dir: Path, wheel_dir: str):
    """构建 wheel"""
    print(f"🔨 在 {source_dir} 中构建 wheel")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
        check=True,
        cwd=source_dir
    )

@register("cmeel-assimp")
def build_cmeel_assimp_func(package_spec: str, wheel_dir: str):
    """
    构建 cmeel-assimp

    Args:
        package_spec: 包规格，如 "cmeel-assimp==6.0.2"
        wheel_dir: wheel 输出目录
    """
    pkg_name, version = parse_package_spec(package_spec)

    if not version:
        raise ValueError("❌ 必须指定版本号，例如: cmeel-assimp==6.0.2")

    print(f"📦 开始构建 {pkg_name} {version}")

    # 获取 git 仓库目录
    git_dir = get_git_repo_dir()

    # 克隆或更新仓库
    clone_or_update_repo(git_dir)

    # 查找匹配的 tag
    tag = find_matching_tag(git_dir, version)

    # 切换到对应版本
    checkout_version(git_dir, tag)

    # 使用临时目录进行构建
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # 复制源码到临时目录
            tmp_source = Path(tmpdir) / "cmeel-assimp"
            print(f"📋 复制源码到临时目录: {tmp_source}")
            shutil.copytree(git_dir, tmp_source, symlinks=True)

            # 构建 wheel
            build_wheel(tmp_source, wheel_dir)
            print("✅ 构建完成")

        except Exception as e:
            print(f"❌ 构建过程中出错: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: build_cmeel_assimp.py <package_spec> [<wheel_dir>]", file=sys.stderr)
        sys.exit(1)

    package_spec = sys.argv[1]
    wheel_dir = sys.argv[2] if len(sys.argv) >= 3 else os.getcwd()

    build_cmeel_assimp_func(package_spec, wheel_dir)
