#!/usr/bin/env python3

import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tools import parse_package_spec
from registry import register


LEGACY_REPO_URL = "https://github.com/faiss-wheels/faiss-wheels.git"
UPSTREAM_REPO_URL = "https://github.com/facebookresearch/faiss.git"
UPSTREAM_WHEEL_VERSION = (1, 14, 2)


def uses_upstream_repo(version: str) -> bool:
    """从 1.14.2 开始，wheel 构建配置由 Faiss 上游仓库维护。"""
    normalized_version = version.removeprefix("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", normalized_version)
    if not match:
        raise ValueError(f"❌ 无法解析 faiss-cpu 版本号: {version}")
    return tuple(int(part) for part in match.groups()) >= UPSTREAM_WHEEL_VERSION


def get_git_repo_dir(repo_name: str) -> Path:
    """获取指定 git 仓库的缓存目录。"""
    home = Path.home()
    build_for_version = os.environ.get("BUILD_FOR_VERSION", "default")
    return home / f".pip_git_hp_{build_for_version}" / repo_name


def clone_or_update_repo(git_dir: Path, repo_url: str):
    """克隆或更新构建源码仓库。"""
    if git_dir.exists():
        print(f"📂 仓库已存在: {git_dir}")
        print("🔄 更新仓库...")
        subprocess.run(["git", "pull"], check=True, cwd=git_dir)
        subprocess.run(["git", "fetch", "--all", "--tags"], check=True, cwd=git_dir)
    else:
        print(f"📥 克隆仓库到: {git_dir}")
        git_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--recursive", repo_url, str(git_dir)], check=True)


def find_matching_tag(git_dir: Path, version: str) -> str:
    """根据版本号查找匹配的 tag，版本号可带 ``v`` 前缀。"""
    result = subprocess.run(
        ["git", "tag", "-l"],
        capture_output=True,
        text=True,
        check=True,
        cwd=git_dir,
    )
    tags = [tag.strip() for tag in result.stdout.splitlines() if tag.strip()]

    normalized_version = version.removeprefix("v")
    candidates = [normalized_version, f"v{normalized_version}"]

    matching_tags = [tag for tag in tags if tag in candidates]
    if not matching_tags:
        # 兼容诸如 1.13.0.post1 / 1.13.0rc1 等前缀匹配情况
        prefix_candidates = candidates
        matching_tags = [
            tag for tag in tags
            if any(tag.startswith(prefix) for prefix in prefix_candidates)
        ]

    if not matching_tags:
        raise ValueError(f"❌ 未找到版本 {version} 对应的 tag")

    selected_tag = sorted(matching_tags)[-1]
    print(f"✅ 找到匹配的 tag: {selected_tag}")
    return selected_tag


def checkout_version(source_dir: Path, tag: str):
    """切换到指定 tag 并更新子模块"""
    print(f"🔀 切换到 tag: {tag}")
    subprocess.run(["git", "checkout", "-f", tag], check=True, cwd=source_dir)
    print("🔄 更新子模块...")
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True, cwd=source_dir)


def patch_pyproject_project_name(source_dir: Path, package_name: str):
    """确保 pyproject.toml 中项目名与目标包名一致。"""
    pyproject = source_dir / "pyproject.toml"
    if not pyproject.exists():
        raise FileNotFoundError(f"❌ 未找到 {pyproject}")

    text = pyproject.read_text(encoding="utf-8")
    old = 'name = "faiss-cpu"'
    new = f'name = "{package_name}"'

    if old not in text:
        if new in text:
            print(f"ℹ️ pyproject.toml 中项目名已是 {package_name}")
            return
        raise RuntimeError("❌ pyproject.toml 中未找到 name = \"faiss-cpu\"，无法自动替换")

    pyproject.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"✅ 已更新 pyproject.toml 项目名为 {package_name}")


def build_wheel(source_dir: Path, wheel_dir: str, use_upstream: bool):
    """构建 wheel"""
    print(f"🔨 在 {source_dir} 中构建 wheel")
    env = os.environ.copy()
    env.setdefault("FAISS_GPU_SUPPORT", "OFF")
    command = ["pip", "wheel", "--verbose"]
    if use_upstream and platform.machine() == "riscv64":
        print("ℹ️ riscv64 上禁用 LTO，避免 RVV 对象链接失败")
        command.extend(
            ["--config-settings", "cmake.define.FAISS_USE_LTO=OFF"]
        )
    command.extend([".", "-w", wheel_dir])
    subprocess.run(
        command,
        check=True,
        cwd=source_dir,
        env=env,
    )


@register("faiss-cpu")
def build_faiss_cpu_func(package_spec: str, wheel_dir: str):
    """构建 faiss-cpu。"""
    pkg_name, version = parse_package_spec(package_spec)

    if not version:
        raise ValueError("❌ 必须指定版本号，例如: faiss-cpu==1.13.0")

    print(f"📦 开始构建 {pkg_name} {version}")

    use_upstream = uses_upstream_repo(version)
    repo_name = "faiss" if use_upstream else "faiss-wheels"
    repo_url = UPSTREAM_REPO_URL if use_upstream else LEGACY_REPO_URL
    print(f"📚 使用源码仓库: {repo_url}")

    git_dir = get_git_repo_dir(repo_name)
    clone_or_update_repo(git_dir, repo_url)
    tag = find_matching_tag(git_dir, version)

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            tmp_source = Path(tmpdir) / repo_name
            print(f"📋 复制源码到临时目录: {tmp_source}")
            shutil.copytree(git_dir, tmp_source, symlinks=True)

            checkout_version(tmp_source, tag)
            patch_pyproject_project_name(tmp_source, pkg_name)
            build_wheel(tmp_source, wheel_dir, use_upstream)
            print("✅ 构建完成")

        except Exception as e:
            print(f"❌ 构建过程中出错: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: build_faiss_cpu.py <package_spec> [<wheel_dir>]", file=sys.stderr)
        sys.exit(1)

    package_spec = sys.argv[1]
    wheel_dir = sys.argv[2] if len(sys.argv) >= 3 else os.getcwd()

    build_faiss_cpu_func(package_spec, wheel_dir)
