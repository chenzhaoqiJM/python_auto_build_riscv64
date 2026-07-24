#!/usr/bin/env python3

import base64
import csv
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from hashlib import sha256
from pathlib import Path

from registry import register
from tools import get_glibc_version, parse_package_spec


REPO_ARCHIVE_URL = "https://github.com/asg017/sqlite-vec/archive/refs/tags/v{version}.tar.gz"
SQLITE_AMALGAMATION_URL = "https://www.sqlite.org/2024/sqlite-amalgamation-3450300.zip"
SQLITE_AMALGAMATION_DIR = "sqlite-amalgamation-3450300"


def _skip_existing_wheel_lookup_for_sqlite_vec():
    main_module = sys.modules.get("__main__")
    if main_module is None or not hasattr(main_module, "has_whl_in_gitlab_with_retry"):
        return

    original = main_module.has_whl_in_gitlab_with_retry
    if getattr(original, "_sqlite_vec_wrapped", False):
        return

    def wrapped(package_spec, *args, **kwargs):
        name, _ = parse_package_spec(package_spec)
        if name == "sqlite-vec":
            print("ℹ️ sqlite-vec 特殊构建总是下载新源码，跳过 GitLab wheel 预检查")
            return False, []
        return original(package_spec, *args, **kwargs)

    wrapped._sqlite_vec_wrapped = True
    main_module.has_whl_in_gitlab_with_retry = wrapped


_skip_existing_wheel_lookup_for_sqlite_vec()


def _run(cmd, cwd=None):
    print(f"🔧 Running: {' '.join(str(x) for x in cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def _download(url: str, target: Path):
    cmd = [
        "curl",
        "-fL",
        "--retry",
        "5",
        "--retry-delay",
        "3",
        "--retry-all-errors",
        "--connect-timeout",
        "20",
        "--max-time",
        "180",
        "-o",
        str(target),
        url,
    ]
    last_error = None
    for attempt in range(1, 4):
        try:
            _run(cmd)
            return
        except subprocess.CalledProcessError as e:
            last_error = e
            if attempt < 3:
                print(f"⚠️ 下载失败（第 {attempt} 次），3 秒后重试: {url}")
                time.sleep(3)
    raise last_error


def _download_source(version: str, tmpdir: Path) -> Path:
    archive = tmpdir / f"sqlite-vec-{version}.tar.gz"
    url = REPO_ARCHIVE_URL.format(version=version)
    _download(url, archive)

    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(tmpdir)

    source_dir = tmpdir / f"sqlite-vec-{version}"
    if not source_dir.is_dir():
        raise FileNotFoundError(f"❌ 未找到解压后的源码目录: {source_dir}")
    return source_dir


def _platform_tag() -> str:
    env_tag = os.environ.get("AUDITWHEEL_PLAT_DEF")
    if env_tag:
        return env_tag

    major, minor = get_glibc_version()
    if major == 0:
        raise RuntimeError("❌ 无法检测 glibc 版本，不能生成 manylinux wheel tag")
    return f"manylinux_{major}_{minor}_{os.uname().machine}"


def _vendor_sqlite(source_dir: Path):
    vendor_dir = source_dir / "vendor"
    if (vendor_dir / "sqlite3ext.h").exists():
        return

    archive = source_dir / "sqlite-amalgamation.zip"
    _download(SQLITE_AMALGAMATION_URL, archive)

    with zipfile.ZipFile(archive) as zf:
        zf.extractall(source_dir)

    extracted_dir = source_dir / SQLITE_AMALGAMATION_DIR
    if not extracted_dir.is_dir():
        raise FileNotFoundError(f"❌ 未找到 SQLite 解压目录: {extracted_dir}")

    vendor_dir.mkdir(exist_ok=True)
    for item in extracted_dir.iterdir():
        if item.is_file():
            shutil.move(str(item), vendor_dir / item.name)

    shutil.rmtree(extracted_dir)
    archive.unlink(missing_ok=True)


def _build_loadable(source_dir: Path) -> Path:
    _vendor_sqlite(source_dir)

    platform_dir = source_dir / "dist" / "linux-riscv64"
    _run(["make", "prefix=dist/linux-riscv64", "loadable"], cwd=source_dir)

    loadable = platform_dir / "vec0.so"
    if not loadable.exists():
        raise FileNotFoundError(f"❌ 未找到编译产物: {loadable}")
    return loadable


def _record_row(path: str, data: bytes) -> list[str]:
    digest = base64.urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode()
    return [path, f"sha256={digest}", str(len(data))]


def _build_init_py(source_dir: Path, version: str) -> bytes:
    extra_init = (source_dir / "bindings" / "python" / "extra_init.py").read_text()
    init_py = f'''
from os import path
import sqlite3

__version__ = "{version}"
__version_info__ = tuple(__version__.split("."))

def loadable_path():
  """ Returns the full path to the sqlite-vec loadable SQLite extension bundled with this package """

  loadable_path = path.join(path.dirname(__file__), "vec0")
  return path.normpath(loadable_path)

def load(conn: sqlite3.Connection)  -> None:
  """ Load the sqlite-vec SQLite extension into the given database connection. """

  conn.load_extension(loadable_path())

{extra_init}
'''.lstrip()
    return init_py.encode()


def _write_wheel(source_dir: Path, loadable: Path, version: str, wheel_dir: Path) -> Path:
    wheel_dir.mkdir(parents=True, exist_ok=True)

    dist_name = "sqlite_vec"
    package_name = "sqlite_vec"
    dist_info = f"{dist_name}-{version}.dist-info"
    wheel_tag = f"py3-none-{_platform_tag()}"
    wheel_path = wheel_dir / f"{dist_name}-{version}-{wheel_tag}.whl"

    files = {
        f"{package_name}/__init__.py": _build_init_py(source_dir, version),
        f"{package_name}/vec0.so": loadable.read_bytes(),
        f"{dist_info}/METADATA": f"""Metadata-Version: 2.1
Name: sqlite-vec
Version: {version}
Home-page: https://alexgarcia.xyz/sqlite-vec
Author: Alex Garcia
License: MIT OR Apache-2.0
Summary: A vector search SQLite extension.
Description-Content-Type: text/markdown

sqlite-vec {version} for riscv64
""".encode(),
        f"{dist_info}/WHEEL": f"""Wheel-Version: 1.0
Generator: python_auto_build_riscv64 build_sqlite_vec.py
Root-Is-Purelib: false
Tag: {wheel_tag}
""".encode(),
        f"{dist_info}/top_level.txt": b"sqlite_vec\n",
    }

    record_path = f"{dist_info}/RECORD"
    rows = [_record_row(path, data) for path, data in files.items()]
    rows.append([record_path, "", ""])
    record_buf = io.StringIO()
    csv.writer(record_buf, lineterminator="\n").writerows(rows)
    files[record_path] = record_buf.getvalue().encode()

    if wheel_path.exists():
        wheel_path.unlink()
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for archive_name, data in files.items():
            info = zipfile.ZipInfo(archive_name)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

    return wheel_path


def _copy_to_pip_cache(wheel_path: Path):
    pip_cache_dir = os.environ.get("PIP_CACHE_DIR")
    if not pip_cache_dir:
        return

    target_dir = Path(os.path.expanduser(pip_cache_dir)) / "sqlite-vec"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / wheel_path.name
    shutil.copy2(wheel_path, target)
    print(f"📦 Copied wheel to pip cache: {target}")


def build_wheel(package_spec: str, wheel_dir: str):
    name, version = parse_package_spec(package_spec)
    if name != "sqlite-vec":
        raise RuntimeError(f"❌ build_sqlite_vec 收到不支持的包: {package_spec}")
    if not version:
        raise RuntimeError("❌ sqlite-vec 特殊构建需要显式版本，例如 sqlite-vec==0.1.8")

    with tempfile.TemporaryDirectory(prefix="sqlite-vec-build-") as tmp:
        tmpdir = Path(tmp)
        source_dir = _download_source(version, tmpdir)

        source_version = (source_dir / "VERSION").read_text().strip()
        if source_version != version:
            raise RuntimeError(f"❌ 源码 VERSION={source_version}，期望 {version}")

        loadable = _build_loadable(source_dir)
        wheel_path = _write_wheel(source_dir, loadable, version, Path(wheel_dir))
        _copy_to_pip_cache(wheel_path)
        print(f"✅ sqlite-vec wheel build complete: {wheel_path}")


@register("sqlite-vec")
def build_sqlite_vec_func(package_spec, wheel_dir):
    try:
        build_wheel(package_spec, wheel_dir)
    except Exception as e:
        print(f"❌ Error during sqlite-vec build: {e}", file=sys.stderr)
        sys.exit(1)
