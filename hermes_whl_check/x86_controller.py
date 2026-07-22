#!/usr/bin/env python3
"""x86 Hermes controller for installed wheel smoke checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


QUEUE_STATES = ("pending", "testing", "passed", "failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_name(package: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", package).strip("_") or "package"


def item_id(package: str, python_version: str) -> str:
    return f"{safe_name(package)}-py{python_version.replace('.', '').replace('t', 't')}"


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


def list_pending_requests(host: str, remote_home_data_dir: str) -> list[str]:
    pending_dir = remote_queue_dir(remote_home_data_dir, "pending")
    command = f"find {remote_quote(pending_dir)} -maxdepth 1 -type f -name '*.json' -print 2>/dev/null | sort"
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


def write_remote_json(host: str, remote_path: str, data: dict) -> bool:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    command = f"cat > {remote_quote(remote_path)}.tmp && mv {remote_quote(remote_path)}.tmp {remote_quote(remote_path)}"
    proc = subprocess.run(["ssh", host, command], input=payload, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        print(f"⚠️  写远端 JSON 失败: {remote_path}\n{proc.stderr}", file=sys.stderr)
        return False
    return True


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


def cleanup_queue_entries(host: str, remote_home_data_dir: str, filename: str) -> None:
    for state in QUEUE_STATES:
        path = f"{remote_queue_dir(remote_home_data_dir, state)}/{filename}"
        ssh(host, f"rm -f {remote_quote(path)}", capture=True)


def expand_remote_home_dir(host: str, path: str) -> str:
    if path == "~" or path.startswith("~/"):
        proc = ssh(host, 'printf %s "$HOME"')
        if proc.returncode != 0 or not proc.stdout.strip():
            raise RuntimeError(f"无法解析远端 HOME: {proc.stderr}")
        return proc.stdout.strip() + path[1:]
    return path


def make_prompt(request: dict, local_install_log: Path, *, ssh_host: str = "") -> str:
    package = str(request.get("package", ""))
    python_version = str(request.get("python_version", ""))
    remote_repo_root = str(request.get("repo_root", ""))
    venv_python = str(request.get("venv_python", ""))
    venv_dir = str(request.get("venv_dir", ""))
    install_log = str(request.get("install_log", ""))
    ssh_target = ssh_host.strip() or "<HERMES_RISCV_HOST>"
    ssh_target_cmd = shlex.quote(ssh_target) if ssh_host.strip() else "<HERMES_RISCV_HOST>"
    quoted_python = shlex.quote(venv_python) if venv_python else "<venv_python>"
    remote_test_dir = f"{request.get('home_data_dir', '~/.python_auto_build_hermes_whl_check')}/tests/{item_id(package, python_version)}"

    return f"""# Hermes wheel 基础功能测试请求

请在 RISC-V 远端主机中检查已安装 wheel 的基本常用功能是否正常。

## 包信息

- package: {package}
- python_version: {python_version}
- remote_repo_root: {remote_repo_root}
- remote_venv_dir: {venv_dir}
- remote_venv_python: {venv_python}
- remote_install_log: {install_log}
- local_install_log: {local_install_log}
- remote_ssh_host: {ssh_target}

## 远端连接方式

你运行在 x86 controller 本机。所有远端命令都必须通过下面的 SSH 目标执行。

- 远端命令模板：`ssh {ssh_target_cmd} '<remote command>'`
- 已安装包的 Python：`{quoted_python}`

不要重新创建虚拟环境，不要重新安装该包，不要使用系统 Python 代替上面的 venv Python。

## 测试要求

1. 先阅读安装日志，确认安装的是 wheel 而不是源码构建。
2. 在远端 `{remote_test_dir}` 下写一个临时 Python 测试脚本。
3. 测试脚本应覆盖该包最基本、最常用、低副作用的功能：导入包、读取版本、创建核心对象或调用轻量函数。避免联网、GPU、大模型下载、长时间计算和破坏性写操作。
4. 使用下面形式执行测试：`ssh {ssh_target_cmd} {shlex.quote(f'{quoted_python} <remote_test_script>')}`。
5. 如果包名和 import 名不一致，请根据包元数据、常见约定或安装日志判断合理 import 名。
6. 测试结束后清理你创建的远端临时测试脚本或目录。

## 输出格式

只输出 JSON，不要输出代码围栏，不要输出额外解释。格式如下：

{{
  "status": "passed",
  "summary": "一句话总结测试结果",
  "details": "关键命令、检查点和失败堆栈；通过时写简要检查点"
}}

当基础功能不正常、测试脚本报错、无法确定 import 名、SSH 失败或日志显示安装异常时，status 使用 "failed"，summary 写清楚包名和主要失败原因。
"""


def run_hermes_api_command(args: argparse.Namespace, prompt_path: Path, log_path: Path, *, output_path: Path) -> int:
    script = """from pathlib import Path
from run_agent import AIAgent

prompt = Path({prompt!r}).read_text(encoding="utf-8")
agent = AIAgent(
    model={model!r},
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
)
result = agent.chat(prompt)
result_text = "" if result is None else str(result)
Path({output!r}).parent.mkdir(parents=True, exist_ok=True)
Path({output!r}).write_text(result_text.rstrip() + "\\n", encoding="utf-8")
print(result_text)
""".format(prompt=str(prompt_path), model=args.hermes_model, output=str(output_path))
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as script_file:
        script_file.write(script)
        script_path = Path(script_file.name)

    activate_path = str(Path(args.hermes_venv_activate).expanduser())
    command = f"source {shlex.quote(activate_path)} && python {shlex.quote(str(script_path))}"
    try:
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            proc = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=args.test_timeout,
                check=False,
            )
        return proc.returncode
    except subprocess.TimeoutExpired:
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            log.write(f"\n# timed_out_after: {args.test_timeout}\n")
        return 124
    finally:
        script_path.unlink(missing_ok=True)


def parse_hermes_result(output: str) -> dict:
    candidates = [output.strip()]
    candidates.extend(match.group(1).strip() for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL | re.IGNORECASE))
    brace_match = re.search(r"\{.*\}", output, re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0).strip())

    for candidate in candidates:
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        status = str(data.get("status", "")).strip().lower()
        if status not in {"passed", "failed"}:
            data["status"] = "failed"
            data["summary"] = data.get("summary") or f"Hermes 返回了未知状态: {status or '<empty>'}"
        else:
            data["status"] = status
            data["summary"] = str(data.get("summary", "")).strip() or status
        data["details"] = str(data.get("details", "")).strip()
        return data

    return {
        "status": "failed",
        "summary": "无法解析 Hermes 测试结果 JSON",
        "details": output.strip(),
    }


def append_failure_summary(args: argparse.Namespace, request: dict, result: dict, test_log: Path) -> None:
    log_path = args.home_dir / "logs" / "failed_whl_checks.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": now_iso(),
        "package": request.get("package", ""),
        "python_version": request.get("python_version", ""),
        "summary": result.get("summary", ""),
        "details": result.get("details", ""),
        "test_log": str(test_log),
        "install_log": request.get("local_install_log") or request.get("install_log", ""),
    }
    with log_path.open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")


def process_request(args: argparse.Namespace, remote_pending_path: str) -> None:
    request = read_remote_json(args.host, remote_pending_path)
    if not request:
        return

    package = str(request.get("package", Path(remote_pending_path).stem))
    python_version = str(request.get("python_version", ""))
    name = item_id(package, python_version)
    testing_path = move_remote_request(args.host, remote_pending_path, args.remote_home_data_dir, "testing")
    if not testing_path:
        return

    request["state"] = "testing"
    request["test_started_at"] = now_iso()
    write_remote_json(args.host, testing_path, request)

    local_pkg_dir = args.home_dir / "cache" / name
    local_pkg_dir.mkdir(parents=True, exist_ok=True)
    local_install_log = local_pkg_dir / "install.log"
    remote_install_log = str(request.get("install_log", ""))
    if remote_install_log:
        proc = scp_from(args.host, remote_install_log, local_install_log)
        if proc.returncode != 0:
            local_install_log.write_text(f"拉取远端安装日志失败:\n{proc.stderr}\n", encoding="utf-8")
    request["local_install_log"] = str(local_install_log)

    prompt_path = local_pkg_dir / "hermes_test_prompt.md"
    result_path = local_pkg_dir / "hermes_result.json"
    prompt_path.write_text(make_prompt(request, local_install_log, ssh_host=args.host), encoding="utf-8")

    test_log = args.home_dir / "logs" / f"{name}-test.log"
    test_log.parent.mkdir(parents=True, exist_ok=True)
    test_log.write_text(f"# started_at: {now_iso()}\n# command: hermes-api\n\n", encoding="utf-8", errors="replace")

    print(f"🧪 处理 wheel 测试请求: {package} Python {python_version}")
    exit_code = run_hermes_api_command(args, prompt_path, test_log, output_path=result_path)
    output = result_path.read_text(encoding="utf-8", errors="replace") if result_path.exists() else ""
    result = parse_hermes_result(output)
    if exit_code != 0 and result["status"] == "passed":
        result = {
            "status": "failed",
            "summary": f"hermes-api 退出码非 0: {exit_code}",
            "details": output,
        }

    final_state = "passed" if result["status"] == "passed" else "failed"
    request["state"] = final_state
    request["test_finished_at"] = now_iso()
    request["test_exit_code"] = exit_code
    request["local_prompt_path"] = str(prompt_path)
    request["local_test_log"] = str(test_log)
    request["hermes_result"] = result
    request["summary"] = result.get("summary", "")

    filename = Path(testing_path).name
    cleanup_queue_entries(args.host, args.remote_home_data_dir, filename)
    final_remote_path = f"{remote_queue_dir(args.remote_home_data_dir, final_state)}/{filename}"
    ssh(args.host, f"mkdir -p {remote_quote(remote_queue_dir(args.remote_home_data_dir, final_state))}")
    write_remote_json(args.host, final_remote_path, request)

    if final_state == "failed":
        append_failure_summary(args, request, result, test_log)

    print(f"✅ 已标记: {package} Python {python_version} -> {final_state}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="x86 PC Hermes wheel 测试控制器")
    parser.add_argument("--host", default=os.environ.get("HERMES_RISCV_HOST", ""), help="远端 SSH 主机，例如 bianbu@10.0.90.13")
    parser.add_argument(
        "--remote-home-data-dir",
        default=os.environ.get("HERMES_REMOTE_HOME_DATA_DIR", "~/.python_auto_build_hermes_whl_check"),
        help="远端 RISC-V worker 运行态目录",
    )
    parser.add_argument("--home-dir", type=Path, default=Path.home() / ".python_auto_build_hermes_whl_check")
    parser.add_argument("--hermes-venv-activate", default=os.environ.get("HERMES_VENV_ACTIVATE", "~/hermes_env/bin/activate"))
    parser.add_argument("--hermes-model", default=os.environ.get("HERMES_MODEL", "gpt-5.5"))
    parser.add_argument("--test-timeout", type=int, default=int(os.environ.get("HERMES_WHL_CHECK_TIMEOUT", "1800")))
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
    (args.home_dir / "logs").mkdir(parents=True, exist_ok=True)
    (args.home_dir / "cache").mkdir(parents=True, exist_ok=True)

    while True:
        pending = list_pending_requests(args.host, args.remote_home_data_dir)
        if not pending:
            print("⏳ 暂无 wheel 测试请求")
        for remote_pending_path in pending:
            process_request(args, remote_pending_path)

        if args.once:
            return 0
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
