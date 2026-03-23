#!/usr/bin/env python3

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from registry import register


REPO_URL = "https://github.com/ManfredStoiber/stag-python"


def _run(cmd, cwd=None):
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=cwd)


def _ensure_env(var_name: str) -> str:
    value = os.environ.get(var_name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


def _get_tag(package_spec: str):
    _, _, version = package_spec.partition("==")
    version = version.strip()
    if not version:
        raise RuntimeError("stag-python special build requires an explicit version, e.g. stag-python==1.1.1")
    return f"v{version}" if not version.startswith("v") else version


@register("stag-python")
def build_stag_python_func(package_spec, wheel_dir):
    build_for_version = _ensure_env("BUILD_FOR_VERSION")

    target_root = Path.home() / "ck"
    target_dir = target_root / "stag-python"
    wheel_dir_path = Path(wheel_dir)
    wheel_dir_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"stag_uv_{build_for_version}_") as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["TMPDIR"] = str(tmp_path)

        tag = _get_tag(package_spec)
        print(f"🔖 Processing tag: {tag}")

        if target_root.exists():
            shutil.rmtree(target_root)
        target_root.mkdir(parents=True, exist_ok=True)

        _run(["git", "clone", "--recursive", REPO_URL, str(target_dir)])
        _run(["git", "checkout", tag], cwd=target_dir)

        try:
            _run(["pip", "wheel", ".", "--verbose", "--wheel-dir", str(wheel_dir_path)], cwd=target_dir)
        finally:
            if target_root.exists():
                shutil.rmtree(target_root)

    print(f"✅ stag-python build complete for Python {build_for_version}")