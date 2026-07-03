#!/usr/bin/env python3
"""RISC-V 远端构建 worker。

职责：逐包运行 build_one.sh；失败时写入 $HOME 队列和日志；等待 x86 controller
标记 fixed/permanent_failed 后继续下一个包。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_DONE = {"success", "fixed", "permanent_failed", "skipped"}
QUEUE_STATES = ("failed", "repairing", "fixed", "permanent_failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_name(package: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", package).strip("_") or "package"


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_packages(path: Path) -> list[str]:
    packages: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        packages.append(item)
    return packages


def package_state_path(base_dir: Path, package: str) -> Path:
    return base_dir / "state" / "packages" / f"{safe_name(package)}.json"


def read_state(base_dir: Path, package: str) -> str | None:
    path = package_state_path(base_dir, package)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("state")
    except json.JSONDecodeError:
        return None


def write_state(base_dir: Path, package: str, state: str, **extra: object) -> None:
    data = {"package": package, "state": state, "updated_at": now_iso(), **extra}
    atomic_write_json(package_state_path(base_dir, package), data)


def queue_path(base_dir: Path, state: str, package: str) -> Path:
    return base_dir / "queue" / state / f"{safe_name(package)}.json"


def remove_old_queue_entries(base_dir: Path, package: str) -> None:
    for state in QUEUE_STATES:
        path = queue_path(base_dir, state, package)
        if path.exists():
            path.unlink()


def wait_for_repair_result(base_dir: Path, package: str, interval: int) -> str:
    fixed = queue_path(base_dir, "fixed", package)
    failed = queue_path(base_dir, "permanent_failed", package)
    while True:
        if fixed.exists():
            return "fixed"
        if failed.exists():
            return "permanent_failed"
        print(f"⏳ 等待 x86 hermes 处理: {package}", flush=True)
        time.sleep(interval)


def run_build(repo_root: Path, package: str, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    script = repo_root / "build_most_common" / "build_one.sh"
    env = os.environ.copy()
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"# package: {package}\n# started_at: {now_iso()}\n# command: {script} {package}\n\n")
        log.flush()
        proc = subprocess.run(
            [str(script), package],
            cwd=repo_root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        log.write(f"\n# finished_at: {now_iso()}\n# exit_code: {proc.returncode}\n")
        return proc.returncode


def build_request(repo_root: Path, base_dir: Path, package: str, log_path: Path, attempt: int) -> dict:
    return {
        "package": package,
        "package_spec": package,
        "python_version": os.environ.get("BUILD_FOR_VERSION", ""),
        "arch": "riscv64",
        "repo_root": str(repo_root),
        "build_script": "build_most_common/build_one.sh",
        "src_build_script": "build_most_common/build_from_src.sh",
        "log_path": str(log_path),
        "state": "failed",
        "attempt": attempt,
        "created_at": now_iso(),
        "remote_home_data_dir": str(base_dir),
    }


def ensure_dirs(base_dir: Path) -> None:
    for rel in (
        "queue/failed",
        "queue/repairing",
        "queue/fixed",
        "queue/permanent_failed",
        "state/packages",
        "logs",
        "src",
        "locks",
    ):
        (base_dir / rel).mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RISC-V 远端逐包构建 worker")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--package-list", type=Path, default=None)
    parser.add_argument("--home-dir", type=Path, default=Path.home() / ".python_auto_build_hermes")
    parser.add_argument("--wait-interval", type=int, default=60)
    parser.add_argument("--retry-failed", action="store_true", help="重新尝试已失败/已完成的包")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    package_list = args.package_list or repo_root / "build_pypi" / "top_pypi_package_names.txt"
    base_dir = args.home_dir.expanduser().resolve()
    ensure_dirs(base_dir)

    if not package_list.exists():
        print(f"❌ 包列表不存在: {package_list}", file=sys.stderr)
        return 1

    packages = read_packages(package_list)
    if not packages:
        print(f"❌ 包列表为空: {package_list}", file=sys.stderr)
        return 1

    print(f"📦 共 {len(packages)} 个包，运行态目录: {base_dir}")
    for index, package in enumerate(packages, start=1):
        current_state = read_state(base_dir, package)
        if current_state in STATE_DONE and not args.retry_failed:
            print(f"⏭️  跳过已完成包 [{index}/{len(packages)}]: {package} ({current_state})")
            continue

        print(f"==============================\n🔧 构建 [{index}/{len(packages)}]: {package}\n==============================")
        remove_old_queue_entries(base_dir, package)
        attempt = 1
        log_path = base_dir / "logs" / safe_name(package) / f"attempt-{attempt}-build.log"
        write_state(base_dir, package, "building", index=index, log_path=str(log_path))

        exit_code = run_build(repo_root, package, log_path)
        if exit_code == 0:
            write_state(base_dir, package, "success", index=index, exit_code=exit_code, log_path=str(log_path))
            print(f"✅ 构建成功: {package}")
            continue

        request = build_request(repo_root, base_dir, package, log_path, attempt)
        atomic_write_json(queue_path(base_dir, "failed", package), request)
        write_state(base_dir, package, "failed", index=index, exit_code=exit_code, log_path=str(log_path))
        print(f"❌ 构建失败，已写入请求: {queue_path(base_dir, 'failed', package)}")

        result = wait_for_repair_result(base_dir, package, args.wait_interval)
        write_state(base_dir, package, result, index=index, log_path=str(log_path))
        print(f"➡️  hermes 处理结果: {package} -> {result}")

    print("🎉 remote_worker 队列处理完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
