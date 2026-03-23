#!/usr/bin/env python3

import sys
import subprocess
import os
import tempfile
import shutil
from pathlib import Path

from tools import parse_package_spec
from registry import register


def get_git_repo_dir() -> Path:
    """获取 faiss-wheels git 仓库存储目录"""
    home = Path.home()
    return home / ".pip_git" / "faiss-wheels"


def clone_or_update_repo(git_dir: Path):
    """克隆或更新 faiss-wheels 仓库"""
    repo_url = "https://github.com/faiss-wheels/faiss-wheels.git"

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
    """根据版本号查找匹配的 tag。"""
    result = subprocess.run(
        ["git", "tag", "-l"],
        capture_output=True,
        text=True,
        check=True,
        cwd=git_dir,
    )
    tags = [tag.strip() for tag in result.stdout.splitlines() if tag.strip()]

    candidates = [
        version,
        f"v{version}",
    ]

    matching_tags = [tag for tag in tags if tag in candidates]
    if not matching_tags:
        # 兼容诸如 1.13.0.post1 / 1.13.0rc1 等前缀匹配情况
        prefix_candidates = [version, f"v{version}"]
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


def build_wheel(source_dir: Path, wheel_dir: str):
    """构建 wheel"""
    print(f"🔨 在 {source_dir} 中构建 wheel")
    env = os.environ.copy()
    env.setdefault("FAISS_GPU_SUPPORT", "OFF")
    subprocess.run(
        ["pip", "wheel", "--verbose", ".", "-w", wheel_dir],
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

    git_dir = get_git_repo_dir()
    clone_or_update_repo(git_dir)
    tag = find_matching_tag(git_dir, version)

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            tmp_source = Path(tmpdir) / "faiss-wheels"
            print(f"📋 复制源码到临时目录: {tmp_source}")
            shutil.copytree(git_dir, tmp_source, symlinks=True)

            checkout_version(tmp_source, tag)
            patch_pyproject_project_name(tmp_source, pkg_name)
            build_wheel(tmp_source, wheel_dir)
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
