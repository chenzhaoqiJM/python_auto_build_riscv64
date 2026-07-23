#!/usr/bin/env python3
"""RISC-V wheel install worker for Hermes smoke checks."""

from __future__ import annotations

import argparse
import html.parser
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INDEX_URL = "https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple"
DEFAULT_PYTHON_VERSIONS = ("3.12", "3.13", "3.14")
QUEUE_STATES = ("pending", "testing", "passed", "failed")
DONE_STATES = {"passed", "failed", "skipped", "install_failed", "test_timeout"}


class SimpleIndexParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_name(package: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", package).strip("_") or "package"


def normalize_package_name(package: str) -> str:
    return re.sub(r"[-_.]+", "-", package).lower()


def item_id(package: str, python_version: str) -> str:
    return f"{safe_name(package)}-py{python_version.replace('.', '').replace('t', 't')}"


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_packages(path: Path) -> list[str]:
    packages: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        package = line.strip()
        if not package or package.startswith("#"):
            continue
        packages.append(package)
    return packages


def state_path(base_dir: Path, package: str, python_version: str) -> Path:
    return base_dir / "state" / "packages" / f"{item_id(package, python_version)}.json"


def read_state(base_dir: Path, package: str, python_version: str) -> str | None:
    data = read_json(state_path(base_dir, package, python_version))
    if not data:
        return None
    state = data.get("state")
    return str(state) if state else None


def write_state(base_dir: Path, package: str, python_version: str, state: str, **extra: object) -> None:
    data = {
        "package": package,
        "python_version": python_version,
        "state": state,
        "updated_at": now_iso(),
        **extra,
    }
    atomic_write_json(state_path(base_dir, package, python_version), data)


def queue_path(base_dir: Path, state: str, package: str, python_version: str) -> Path:
    return base_dir / "queue" / state / f"{item_id(package, python_version)}.json"


def remove_old_queue_entries(base_dir: Path, package: str, python_version: str) -> None:
    for state in QUEUE_STATES:
        path = queue_path(base_dir, state, package, python_version)
        path.unlink(missing_ok=True)


def ensure_dirs(base_dir: Path) -> None:
    for rel in (
        "queue/pending",
        "queue/testing",
        "queue/passed",
        "queue/failed",
        "state/packages",
        "logs",
        "venvs",
    ):
        (base_dir / rel).mkdir(parents=True, exist_ok=True)


def package_simple_url(index_url: str, package: str) -> str:
    base = index_url.rstrip("/")
    normalized = urllib.parse.quote(normalize_package_name(package), safe="")
    return f"{base}/{normalized}/"


def wheel_filenames_from_simple_html(index_url: str, html_text: str) -> list[str]:
    parser = SimpleIndexParser()
    parser.feed(html_text)
    filenames: list[str] = []
    for href in parser.hrefs:
        parsed = urllib.parse.urlparse(urllib.parse.urljoin(index_url, href))
        filename = urllib.parse.unquote(Path(parsed.path).name)
        if filename.endswith(".whl"):
            filenames.append(filename)
    return filenames


def split_wheel_tags(filename: str) -> tuple[str, str, str] | None:
    if not filename.endswith(".whl"):
        return None
    stem = filename[:-4]
    parts = stem.split("-")
    if len(parts) < 5:
        return None
    return parts[-3], parts[-2], parts[-1]


def wheel_matches_python_version(filename: str, python_version: str) -> bool:
    tags = split_wheel_tags(filename)
    if not tags:
        return False

    py_tag, abi_tag, platform_tag = tags
    cp_tag = "cp" + python_version.replace(".", "").replace("t", "t")
    py_tags = py_tag.split(".")
    abi_tags = abi_tag.split(".")
    platform_tags = platform_tag.split(".")

    python_ok = cp_tag in py_tags or "py3" in py_tags
    abi_ok = "none" in abi_tags or "abi3" in abi_tags or cp_tag in abi_tags
    platform_ok = "any" in platform_tags or any("riscv64" in tag for tag in platform_tags)
    return python_ok and abi_ok and platform_ok


def check_wheel_available(package: str, python_version: str, index_url: str, *, timeout: int = 30) -> bool:
    url = package_simple_url(index_url, package)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        html_text = response.read().decode("utf-8", errors="replace")
    filenames = wheel_filenames_from_simple_html(url, html_text)
    return any(wheel_matches_python_version(filename, python_version) for filename in filenames)


def run_logged(
    cmd: list[str],
    log_path: Path,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n# started_at: {now_iso()}\n# command: {' '.join(cmd)}\n\n")
        log.flush()
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
            )
            log.write(f"\n# finished_at: {now_iso()}\n# exit_code: {proc.returncode}\n")
            return proc.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\n# timed_out_at: {now_iso()}\n# timeout: {timeout}\n")
            return 124


def run_logged_shell(
    command: str,
    log_path: Path,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n# started_at: {now_iso()}\n# command: {command}\n\n")
        log.flush()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                cwd=cwd,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
            )
            log.write(f"\n# finished_at: {now_iso()}\n# exit_code: {proc.returncode}\n")
            return proc.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\n# timed_out_at: {now_iso()}\n# timeout: {timeout}\n")
            return 124


def refresh_package_list(repo_root: Path, package_fetch_python: str, refresh_log: Path) -> int:
    script = repo_root / "build_pypi" / "00get_spacemit_pkgs.py"
    return run_logged([package_fetch_python, str(script)], refresh_log, cwd=repo_root / "build_pypi")


def make_test_request(
    *,
    repo_root: Path,
    base_dir: Path,
    package: str,
    python_version: str,
    venv_dir: Path,
    install_log: Path,
    index_url: str,
) -> dict:
    return {
        "package": package,
        "package_spec": package,
        "python_version": python_version,
        "arch": "riscv64",
        "repo_root": str(repo_root),
        "home_data_dir": str(base_dir),
        "venv_dir": str(venv_dir),
        "venv_python": str(venv_dir / "bin" / "python"),
        "install_log": str(install_log),
        "index_url": index_url,
        "state": "pending",
        "created_at": now_iso(),
    }


def create_and_install_package(args: argparse.Namespace, package: str, python_version: str, venv_dir: Path, install_log: Path) -> int:
    install_log.parent.mkdir(parents=True, exist_ok=True)
    install_log.write_text(
        f"# package: {package}\n# python_version: {python_version}\n# index_url: {args.index_url}\n",
        encoding="utf-8",
        errors="replace",
    )

    env = os.environ.copy()
    env["UV_INDEX_URL"] = args.index_url
    if args.extra_index_url:
        env["UV_EXTRA_INDEX_URL"] = args.extra_index_url

    venv_code = run_logged(["uv", "venv", str(venv_dir), f"--python={python_version}"], install_log, env=env, timeout=args.install_timeout)
    if venv_code != 0:
        return venv_code

    activate_script = shlex.quote(str(venv_dir / "bin" / "activate"))
    upgrade_pip_code = run_logged_shell(
        f"source {activate_script} && uv pip install pip -U && deactivate",
        install_log,
        env=env,
        timeout=args.install_timeout,
    )
    if upgrade_pip_code != 0:
        return upgrade_pip_code

    install_cmd = ["pip", "install", "--index-url", args.index_url, "--only-binary=:all:"]
    if args.extra_index_url:
        install_cmd.extend(["--extra-index-url", args.extra_index_url])
    install_cmd.append(package)
    install_command = " ".join(shlex.quote(str(part)) for part in install_cmd)
    return run_logged_shell(
        f"source {activate_script} && {install_command}",
        install_log,
        env=env,
        timeout=args.install_timeout,
    )


def cleanup_venv(venv_dir: Path) -> None:
    if not venv_dir.exists():
        return
    subprocess.run(["rm", "-rf", str(venv_dir)], check=False)


def wait_for_test_result(base_dir: Path, package: str, python_version: str, interval: int, timeout: int) -> tuple[str, dict]:
    started = time.monotonic()
    while True:
        for state in ("passed", "failed"):
            path = queue_path(base_dir, state, package, python_version)
            if path.exists():
                return state, read_json(path) or {}

        if timeout > 0 and time.monotonic() - started >= timeout:
            return "test_timeout", {"summary": f"等待 Hermes 测试结果超时: {timeout}s"}

        print(f"⏳ 等待 x86 Hermes 测试: {package} Python {python_version}", flush=True)
        time.sleep(interval)


def process_package_version(args: argparse.Namespace, package: str, python_version: str, index: int, total: int) -> None:
    current_state = read_state(args.home_dir, package, python_version)
    if current_state in DONE_STATES and not args.retry_failed:
        print(f"⏭️  跳过已完成 [{index}/{total}]: {package} Python {python_version} ({current_state})")
        return

    print(f"==============================\n📦 检查 [{index}/{total}]: {package} Python {python_version}\n==============================")
    remove_old_queue_entries(args.home_dir, package, python_version)

    venv_dir = args.home_dir / "venvs" / item_id(package, python_version)
    install_log = args.home_dir / "logs" / safe_name(package) / python_version / "install.log"
    cleanup_venv(venv_dir)

    try:
        has_wheel = check_wheel_available(package, python_version, args.index_url, timeout=args.index_timeout)
    except Exception as exc:  # noqa: BLE001 - keep batch worker moving with explicit state.
        write_state(args.home_dir, package, python_version, "failed", index=index, error=f"查询 wheel 失败: {exc}")
        print(f"❌ 查询 wheel 失败: {package} Python {python_version}: {exc}")
        return

    if not has_wheel:
        write_state(args.home_dir, package, python_version, "skipped", index=index, reason="no_compatible_wheel")
        print(f"⏭️  无兼容 wheel，跳过: {package} Python {python_version}")
        return

    write_state(args.home_dir, package, python_version, "installing", index=index, venv_dir=str(venv_dir), install_log=str(install_log))
    install_code = create_and_install_package(args, package, python_version, venv_dir, install_log)
    if install_code != 0:
        cleanup_venv(venv_dir)
        write_state(
            args.home_dir,
            package,
            python_version,
            "install_failed",
            index=index,
            exit_code=install_code,
            install_log=str(install_log),
        )
        print(f"❌ 安装失败: {package} Python {python_version}, log: {install_log}")
        return

    request = make_test_request(
        repo_root=args.repo_root,
        base_dir=args.home_dir,
        package=package,
        python_version=python_version,
        venv_dir=venv_dir,
        install_log=install_log,
        index_url=args.index_url,
    )
    atomic_write_json(queue_path(args.home_dir, "pending", package, python_version), request)
    write_state(args.home_dir, package, python_version, "pending_test", index=index, venv_dir=str(venv_dir), install_log=str(install_log))
    print(f"🧪 已写入测试请求: {queue_path(args.home_dir, 'pending', package, python_version)}")

    final_state, result = wait_for_test_result(args.home_dir, package, python_version, args.wait_interval, args.wait_timeout)
    cleanup_venv(venv_dir)
    write_state(
        args.home_dir,
        package,
        python_version,
        final_state,
        index=index,
        venv_dir=str(venv_dir),
        install_log=str(install_log),
        summary=result.get("summary", ""),
    )
    print(f"➡️  Hermes 测试结果: {package} Python {python_version} -> {final_state}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RISC-V 端 Spacemit PyPI wheel 基础功能测试 worker")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home-dir", type=Path, default=Path.home() / ".python_auto_build_hermes_whl_check")
    parser.add_argument("--package-list", type=Path, default=None)
    parser.add_argument("--python-versions", nargs="+", default=list(DEFAULT_PYTHON_VERSIONS))
    parser.add_argument("--index-url", default=os.environ.get("WHL_CHECK_INDEX_URL", DEFAULT_INDEX_URL))
    parser.add_argument("--extra-index-url", default=os.environ.get("WHL_CHECK_EXTRA_INDEX_URL", ""))
    parser.add_argument("--package-fetch-python", default=os.environ.get("WHL_CHECK_PACKAGE_FETCH_PYTHON", "python3"))
    parser.add_argument("--no-refresh-package-list", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个包，0 表示不限制")
    parser.add_argument("--index-timeout", type=int, default=30)
    parser.add_argument("--install-timeout", type=int, default=1800)
    parser.add_argument("--wait-interval", type=int, default=60)
    parser.add_argument("--wait-timeout", type=int, default=0, help="等待 Hermes 结果超时秒数，0 表示一直等待")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.repo_root = args.repo_root.expanduser().resolve()
    args.home_dir = args.home_dir.expanduser().resolve()
    ensure_dirs(args.home_dir)

    package_list = args.package_list or args.repo_root / "build_pypi" / "packages_spacemit.log"
    if not args.no_refresh_package_list:
        refresh_log = args.home_dir / "logs" / "refresh_packages.log"
        print("🔄 Running build_pypi/00get_spacemit_pkgs.py to get package names...")
        refresh_code = refresh_package_list(args.repo_root, args.package_fetch_python, refresh_log)
        if refresh_code != 0:
            print(f"❌ 获取包列表失败: {refresh_log}", file=sys.stderr)
            return refresh_code

    if not package_list.exists():
        print(f"❌ 包列表不存在: {package_list}", file=sys.stderr)
        return 1

    packages = read_packages(package_list)
    if args.limit > 0:
        packages = packages[: args.limit]
    if not packages:
        print(f"❌ 包列表为空: {package_list}", file=sys.stderr)
        return 1

    total = len(packages) * len(args.python_versions)
    current = 0
    print(f"📦 共 {len(packages)} 个包，Python 版本: {', '.join(args.python_versions)}")
    print(f"📂 运行态目录: {args.home_dir}")
    for package in packages:
        for python_version in args.python_versions:
            current += 1
            process_package_version(args, package, python_version, current, total)

    print("🎉 wheel 检查队列处理完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
