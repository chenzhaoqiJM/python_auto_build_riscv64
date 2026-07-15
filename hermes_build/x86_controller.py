#!/usr/bin/env python3
"""x86 PC hermes-api controller。

职责：通过 SSH 读取远端失败请求，准备 hermes 修复上下文，通过 hermes-api 修复，
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


def make_prompt(request: dict, local_log: Path, experience_dir: Path, *, ssh_host: str = "") -> str:
    package = request.get("package", "")
    repo_root = request.get("repo_root", "")
    python_version = str(request.get("python_version", "")).strip()
    ssh_target = ssh_host.strip() or "<HERMES_RISCV_HOST>"
    ssh_target_cmd = shlex.quote(ssh_target) if ssh_host.strip() else "<HERMES_RISCV_HOST>"
    remote_repo_cmd = shlex.quote(str(repo_root)) if repo_root else "<remote_repo_root>"
    build_for_version_value = python_version or "<失败请求中的 python_version>"
    build_for_version_export = (
        f"export BUILD_FOR_VERSION={shlex.quote(build_for_version_value)}"
        if python_version
        else "export BUILD_FOR_VERSION=<失败请求中的 python_version>"
    )
    remote_build_command = (
        f"cd {remote_repo_cmd} && export SAVE_FINAL_WHL_TO_HOME=0 && "
        f"{build_for_version_export} && "
        "~/python_auto_build_riscv64/build_most_common/build_from_src.sh <package_path>"
    )
    remote_build_example = f"ssh {ssh_target_cmd} {shlex.quote(remote_build_command)}"
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
- remote_ssh_host: {ssh_target}

## 远端连接方式

你运行在 x86 controller 本机。所有读取远端仓库、远端日志、远端源码目录和执行构建验证的命令，都必须通过 controller 提供的 SSH 目标执行。

- 远端命令模板：`ssh {ssh_target_cmd} '<remote command>'`
- 远端拷贝模板：`scp {ssh_target_cmd}:<remote_path> <local_path>`

不要只使用裸 IP，不要自行猜用户名或切换账号。如果遇到 host key 或权限错误，记录完整 SSH 错误并退出非 0，不要把未验证结果写成成功。

## 要求

1. 先阅读失败日志，判断根因。
2. 不要动构建脚本仓库。
3. 需要验证时，通过上面的 SSH 目标在远端运行 build_from_src.sh。
4. 修复成功后，把经验写入本地 experience markdown。
5. 如果 30 分钟内无果，退出非 0，让 controller 标记 permanent_failed。

## 修复时的注意事项

1. 如果某包是因为其依赖包构建失败导致的，尝试修复依赖包，不要去掉主包的依赖项去绕过问题，如果需要修改主包的依赖项，必须确保修改是安全和必要的。
2. 如果需要在远程用户目录下放文件，放在 ~/hermes_temp/ 下，避免污染用户项目目录, 修复结束后清理。

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
4. 如果需要源码修改、补丁或优化，只在该解压目录中修改，保留原始压缩包以便随时回退。
5. 构建前设置环境变量：`export SAVE_FINAL_WHL_TO_HOME=0`。
6. 设置 `BUILD_FOR_VERSION` 为失败请求里的 Python 版本 `{build_for_version_value}`：`{build_for_version_export}`。不要默认写成 3.12。
7. 使用脚本 `~/python_auto_build_riscv64/build_most_common/build_from_src.sh` 构建， 用法：`~/python_auto_build_riscv64/build_most_common/build_from_src.sh <package_path>`。

远端验证命令示例：

`{remote_build_example}`

## 后处理流程

修复完成或者判定修复失败后，需要清理远端临时构建目录，避免占用磁盘空间，以及确保修复时的编译进程已经结束。
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


def make_experience_prompt(request: dict, status: str, local_log: Path, repair_log: Path, experience_path: Path) -> str:
    package = request.get("package", "")
    return f"""# Hermes RISC-V wheel 修复经验整理

请阅读本次构建失败日志和 hermes 修复日志，输出可直接保存的 Markdown 修复经验。
controller 会把你的回复写入 `{experience_path}`，所以只输出 Markdown 正文，不要代码围栏。

## 上下文

- package: {package}
- python_version: {request.get('python_version', '')}
- arch: {request.get('arch', 'riscv64')}
- status: {status}
- remote_repo_root: {request.get('repo_root', '')}
- failed_build_log: {local_log}
- repair_log: {repair_log}
- experience_path: {experience_path}

## 必须包含

- 根因判断
- 实际修改或尝试
- 验证命令和结果
- 可复用经验
- 如果状态不是 fixed，写清楚卡点和后续建议
"""


def write_experience_from_hermes(
    args: argparse.Namespace,
    request: dict,
    status: str,
    local_log: Path,
    repair_log: Path,
    experience_path: Path,
    prompt_path: Path,
    draft_path: Path,
) -> bool:
    write_experience(experience_path, request, status, repair_log)
    prompt_path.write_text(make_experience_prompt(request, status, local_log, repair_log, experience_path), encoding="utf-8")
    exit_code = run_hermes_api_command(args, prompt_path, repair_log, output_path=draft_path)
    if exit_code != 0 or not draft_path.exists():
        return False

    text = draft_path.read_text(encoding="utf-8").strip()
    if not text:
        return False
    experience_path.parent.mkdir(parents=True, exist_ok=True)
    experience_path.write_text(text + "\n", encoding="utf-8")
    return True


def run_hermes_api_command(args: argparse.Namespace, prompt_path: Path, repair_log: Path, *, output_path: Path | None = None) -> int:
    script = """from pathlib import Path
from run_agent import AIAgent

prompt = Path({prompt!r}).read_text(encoding="utf-8")
output_path = {output!r}
agent = AIAgent(
    model={model!r},
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
)
result = agent.chat(prompt)
result_text = "" if result is None else str(result)
if output_path:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(result_text.rstrip() + "\\n", encoding="utf-8")
print(result_text)
""".format(prompt=str(prompt_path), output=str(output_path) if output_path else None, model=args.hermes_model)
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


def run_repair_command(args: argparse.Namespace, prompt_path: Path, repair_log: Path) -> int:
    repair_log.parent.mkdir(parents=True, exist_ok=True)
    repair_log.write_text(f"# started_at: {now_iso()}\n# command: hermes-api\n\n", encoding="utf-8", errors="replace")
    exit_code = run_hermes_api_command(args, prompt_path, repair_log)
    with repair_log.open("a", encoding="utf-8", errors="replace") as log:
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
    prompt_path.write_text(make_prompt(request, local_log, experience_dir, ssh_host=args.host), encoding="utf-8")

    repair_log = args.home_dir / "logs" / f"{name}-repair.log"
    print(f"🔧 处理失败请求: {package}")
    exit_code = run_repair_command(args, prompt_path, repair_log)

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

    experience_path = experience_dir / f"{name}.md"
    write_experience_from_hermes(
        args,
        request,
        final_state,
        local_log,
        repair_log,
        experience_path,
        local_pkg_dir / "experience_prompt.md",
        local_pkg_dir / "experience_draft.md",
    )
    print(f"✅ 已标记: {package} -> {final_state}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="x86 PC hermes-api 修复控制器")
    parser.add_argument("--host", default=os.environ.get("HERMES_RISCV_HOST", ""), help="远端 SSH 主机，例如 bianbu@10.0.90.13")
    parser.add_argument(
        "--remote-home-data-dir",
        default=os.environ.get("HERMES_REMOTE_HOME_DATA_DIR", "~/.python_auto_build_hermes"),
        help="远端运行态目录",
    )
    parser.add_argument("--home-dir", type=Path, default=Path.home() / ".python_auto_build_hermes")
    parser.add_argument("--repair-timeout", type=int, default=int(os.environ.get("HERMES_REPAIR_TIMEOUT", "1800")))
    parser.add_argument("--hermes-venv-activate", default=os.environ.get("HERMES_VENV_ACTIVATE", "~/hermes_env/bin/activate"))
    parser.add_argument("--hermes-model", default=os.environ.get("HERMES_MODEL", "gpt-5.5"))
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
