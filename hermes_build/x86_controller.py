#!/usr/bin/env python3
"""x86 PC hermes controller。

职责：通过 SSH 读取远端失败请求，准备 hermes 修复上下文，执行可配置修复命令，
根据结果标记 fixed/permanent_failed。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path


QUEUE_STATES = ("failed", "repairing", "fixed", "permanent_failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_name(package: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", package).strip("_") or "package"


def run_local(cmd: list[str], *, timeout: int | None = None, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=capture, timeout=timeout, check=False)


def ssh(host: str, command: str, *, timeout: int | None = None, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return run_local(["ssh", host, command], timeout=timeout, capture=capture)


def scp_from(host: str, remote_path: str, local_path: Path) -> subprocess.CompletedProcess[str]:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    return run_local(["scp", f"{host}:{remote_path}", str(local_path)])


def remote_quote(path: str | Path) -> str:
    return shlex.quote(str(path))


def remote_queue_dir(remote_home_data_dir: str, state: str) -> str:
    return f"{remote_home_data_dir}/queue/{state}"


def list_failed_requests(host: str, remote_home_data_dir: str) -> list[str]:
    failed_dir = remote_queue_dir(remote_home_data_dir, "failed")
    command = f"find {remote_quote(failed_dir)} -maxdepth 1 -type f -name '*.json' -print 2>/dev/null | sort"
    proc = ssh(host, command)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def read_remote_json(host: str, remote_path: str) -> dict | None:
    proc = ssh(host, f"cat {remote_quote(remote_path)}")
    if proc.returncode != 0:
        print(f"⚠️  读取远端请求失败: {remote_path}\n{proc.stderr}", file=sys.stderr)
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"⚠️  JSON 解析失败: {remote_path}: {exc}", file=sys.stderr)
        return None


def move_remote_request(host: str, src: str, remote_home_data_dir: str, state: str) -> str | None:
    dst = f"{remote_queue_dir(remote_home_data_dir, state)}/{Path(src).name}"
    command = " && ".join(
        [
            f"mkdir -p {remote_quote(remote_queue_dir(remote_home_data_dir, state))}",
            f"mv {remote_quote(src)} {remote_quote(dst)}",
        ]
    )
    proc = ssh(host, command)
    if proc.returncode != 0:
        print(f"⚠️  移动远端请求失败: {src} -> {dst}\n{proc.stderr}", file=sys.stderr)
        return None
    return dst


def write_remote_json(host: str, remote_path: str, data: dict) -> bool:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    command = f"cat > {remote_quote(remote_path)}.tmp && mv {remote_quote(remote_path)}.tmp {remote_quote(remote_path)}"
    proc = subprocess.run(["ssh", host, command], input=payload, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        print(f"⚠️  写远端 JSON 失败: {remote_path}\n{proc.stderr}", file=sys.stderr)
        return False
    return True


def cleanup_queue_entries(host: str, remote_home_data_dir: str, filename: str) -> None:
    for state in QUEUE_STATES:
        path = f"{remote_queue_dir(remote_home_data_dir, state)}/{filename}"
        ssh(host, f"rm -f {remote_quote(path)}", capture=True)


def expand_remote_home_dir(host: str, path: str) -> str:
    if path == "~" or path.startswith("~/"):
        proc = ssh(host, 'printf %s "$HOME"')
        if proc.returncode != 0 or not proc.stdout.strip():
            raise RuntimeError(f"无法解析远端 HOME: {proc.stderr}")
        home = proc.stdout.strip()
        return home + path[1:]
    return path


def make_prompt(request: dict, local_log: Path, experience_dir: Path) -> str:
    package = request.get("package", "")
    repo_root = request.get("repo_root", "")
    python_version = request.get("python_version", "")
    return f"""# Hermes RISC-V wheel 修复请求

请修复 RISC-V 远端 Python wheel 构建失败，并在远端验证。

## 包信息

- package: {package}
- python_version: {python_version}
- arch: {request.get('arch', 'riscv64')}
- remote_repo_root: {repo_root}
- build_script: {request.get('build_script', '')}
- src_build_script: {request.get('src_build_script', '')}
- local_failed_log: {local_log}
- local_experience_dir: {experience_dir}

## 要求

1. 先阅读失败日志，判断根因。
2. 不要动构建脚本仓库。
3. 需要验证时，在远端运行 build_from_src.sh。
4. 修复成功后，把经验写入本地 experience markdown。
5. 如果 30 分钟内无果，退出非 0，让 controller 标记 permanent_failed。


## 修复时下载源码包

使用远程脚本 `~/python_auto_build_riscv64/common_py/download_whl_sdist.py` 下载用户指定包。

常见用法：

- 下载最新源码包：`python3 ~/python_auto_build_riscv64/common_py/download_whl_sdist.py lintrunner`
- 下载指定版本：`python3 ~/python_auto_build_riscv64/common_py/download_whl_sdist.py numpy 1.26.0`
- 指定目录和文件名：`python3 ~/python_auto_build_riscv64/common_py/download_whl_sdist.py flask --dest ./downloads --filename flask-src.tar.gz`

下载目录应选择远程临时工作目录，避免污染用户项目目录。

## 修复时构建流程

1. 在远程主机创建临时构建目录。
2. 下载用户指定包的源码包到该临时目录。
3. 使用 `tar xzf` 解压源码包到临时目录。
4. 如果用户要求源码修改、补丁或优化，只在该解压目录中修改，保留原始压缩包以便随时回退。
5. 构建前设置环境变量：`SAVE_FINAL_WHL_TO_HOME=0`。
6. 设置 `BUILD_FOR_VERSION`为 3.12
7. 使用脚本 `~/python_auto_build_riscv64/build_most_common/build_from_src.sh` 构建， 用法：`~/python_auto_build_riscv64/build_most_common/build_from_src.sh <package_path>`。
"""


def write_experience(path: Path, request: dict, status: str, repair_log: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    package = request.get("package", "")
    text = f"""# {package} RISC-V wheel 修复记录

- 包名：{package}
- Python 版本：{request.get('python_version', '')}
- 架构：{request.get('arch', 'riscv64')}
- 状态：{status}
- 远端仓库：{request.get('repo_root', '')}
- 原始日志：{request.get('log_path', '')}
- 本地修复日志：{repair_log}
- 记录时间：{now_iso()}

## 处理说明

请根据 `{repair_log}` 补充根因、修改文件、验证命令和可复用经验。
"""
    path.write_text(text, encoding="utf-8")


def run_hermes_api_command(args: argparse.Namespace, prompt_path: Path, repair_log: Path) -> int:
    script = """from pathlib import Path
from run_agent import AIAgent

prompt = Path({prompt!r}).read_text(encoding="utf-8")
agent = AIAgent(
    model={model!r},
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
)
print(agent.chat(prompt))
""".format(prompt=str(prompt_path), model=args.hermes_model)
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as script_file:
        script_file.write(script)
        script_path = Path(script_file.name)

    activate_path = str(Path(args.hermes_venv_activate).expanduser())
    command = f"source {shlex.quote(activate_path)} && python {shlex.quote(str(script_path))}"
    try:
        with repair_log.open("a", encoding="utf-8", errors="replace") as log:
            proc = subprocess.run(command, shell=True, executable="/bin/bash", text=True, stdout=log, stderr=subprocess.STDOUT, timeout=args.repair_timeout, check=False)
        return proc.returncode
    except subprocess.TimeoutExpired:
        with repair_log.open("a", encoding="utf-8", errors="replace") as log:
            log.write(f"\n# timed_out_after: {args.repair_timeout}\n")
        return 124
    finally:
        script_path.unlink(missing_ok=True)


def run_repair_command(args: argparse.Namespace, request: dict, prompt_path: Path, repair_log: Path) -> int:
    package = str(request.get("package", ""))
    command_template = args.repair_command or os.environ.get("HERMES_REPAIR_COMMAND", "")
    if not command_template:
        print(f"📝 未配置修复命令，已生成提示文件: {prompt_path}")
        print("   设置 HERMES_REPAIR_COMMAND 后可自动修复；本次将标记 permanent_failed。")
        return 125

    values = {
        "prompt": str(prompt_path),
        "package": package,
        "host": args.host,
        "remote_repo": args.remote_repo,
        "remote_home_data_dir": args.remote_home_data_dir,
        "repair_log": str(repair_log),
    }
    command = command_template.format(**values)
    repair_log.parent.mkdir(parents=True, exist_ok=True)
    with repair_log.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"# started_at: {now_iso()}\n# command: {command}\n\n")
        log.flush()
        exit_code = 124
        try:
            if command_template == "hermes-api":
                exit_code = run_hermes_api_command(args, prompt_path, repair_log)
            else:
                proc = subprocess.run(command, shell=True, text=True, stdout=log, stderr=subprocess.STDOUT, timeout=args.repair_timeout, check=False)
                exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            log.write(f"\n# timed_out_after: {args.repair_timeout}\n")
        finally:
            cleanup_template = args.session_cleanup_command or os.environ.get("HERMES_SESSION_CLEANUP_COMMAND", "")
            if cleanup_template:
                cleanup_command = cleanup_template.format(**values)
                log.write(f"\n# cleanup_started_at: {now_iso()}\n# cleanup_command: {cleanup_command}\n")
                log.flush()
                cleanup_proc = subprocess.run(cleanup_command, shell=True, text=True, stdout=log, stderr=subprocess.STDOUT, check=False)
                log.write(f"# cleanup_exit_code: {cleanup_proc.returncode}\n")
            log.write(f"\n# finished_at: {now_iso()}\n# exit_code: {exit_code}\n")
        return exit_code


def process_request(args: argparse.Namespace, remote_failed_path: str) -> None:
    request = read_remote_json(args.host, remote_failed_path)
    if not request:
        return

    package = str(request.get("package", Path(remote_failed_path).stem))
    name = safe_name(package)
    repairing_path = move_remote_request(args.host, remote_failed_path, args.remote_home_data_dir, "repairing")
    if not repairing_path:
        return

    request["state"] = "repairing"
    request["repair_started_at"] = now_iso()
    write_remote_json(args.host, repairing_path, request)

    local_pkg_dir = args.home_dir / "cache" / "failed_requests" / name
    local_log = local_pkg_dir / "build.log"
    remote_log = str(request.get("log_path", ""))
    if remote_log:
        proc = scp_from(args.host, remote_log, local_log)
        if proc.returncode != 0:
            local_log.write_text(f"拉取远端日志失败:\n{proc.stderr}\n", encoding="utf-8")

    prompt_path = local_pkg_dir / "hermes_prompt.md"
    experience_dir = args.home_dir / "experience"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(make_prompt(request, local_log, experience_dir), encoding="utf-8")

    repair_log = args.home_dir / "logs" / f"{name}-repair.log"
    print(f"🔧 处理失败请求: {package}")
    exit_code = run_repair_command(args, request, prompt_path, repair_log)

    final_state = "fixed" if exit_code == 0 else "permanent_failed"
    request["state"] = final_state
    request["repair_finished_at"] = now_iso()
    request["repair_exit_code"] = exit_code
    request["local_prompt_path"] = str(prompt_path)
    request["local_repair_log"] = str(repair_log)

    filename = Path(repairing_path).name
    cleanup_queue_entries(args.host, args.remote_home_data_dir, filename)
    final_remote_path = f"{remote_queue_dir(args.remote_home_data_dir, final_state)}/{filename}"
    ssh(args.host, f"mkdir -p {remote_quote(remote_queue_dir(args.remote_home_data_dir, final_state))}")
    write_remote_json(args.host, final_remote_path, request)

    write_experience(experience_dir / f"{name}.md", request, final_state, repair_log)
    print(f"✅ 已标记: {package} -> {final_state}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="x86 PC hermes 修复控制器")
    parser.add_argument("--host", default=os.environ.get("HERMES_RISCV_HOST", ""), help="远端 SSH 主机，例如 bianbu@10.0.90.13")
    parser.add_argument("--remote-repo", default=os.environ.get("HERMES_RISCV_REPO", ""), help="远端仓库路径")
    parser.add_argument(
        "--remote-home-data-dir",
        default=os.environ.get("HERMES_REMOTE_HOME_DATA_DIR", "~/.python_auto_build_hermes"),
        help="远端运行态目录",
    )
    parser.add_argument("--home-dir", type=Path, default=Path.home() / ".python_auto_build_hermes")
    parser.add_argument("--repair-timeout", type=int, default=int(os.environ.get("HERMES_REPAIR_TIMEOUT", "1800")))
    parser.add_argument("--repair-command", default=os.environ.get("HERMES_REPAIR_COMMAND", ""))
    parser.add_argument("--hermes-venv-activate", default=os.environ.get("HERMES_VENV_ACTIVATE", "~/hermes_env/bin/activate"))
    parser.add_argument("--hermes-model", default=os.environ.get("HERMES_MODEL", "gpt-5.5"))
    parser.add_argument("--session-cleanup-command", default=os.environ.get("HERMES_SESSION_CLEANUP_COMMAND", ""))
    parser.add_argument("--poll-interval", type=int, default=60)
    parser.add_argument("--once", action="store_true", help="只扫描处理一轮")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.host:
        print("❌ 请设置 HERMES_RISCV_HOST 或传入 --host", file=sys.stderr)
        return 1

    try:
        args.remote_home_data_dir = expand_remote_home_dir(args.host, args.remote_home_data_dir)
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    args.home_dir = args.home_dir.expanduser().resolve()
    args.home_dir.mkdir(parents=True, exist_ok=True)
    (args.home_dir / "logs").mkdir(parents=True, exist_ok=True)

    while True:
        failed = list_failed_requests(args.host, args.remote_home_data_dir)
        if not failed:
            print("⏳ 暂无失败请求")
        for remote_failed_path in failed:
            process_request(args, remote_failed_path)

        if args.once:
            return 0
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
