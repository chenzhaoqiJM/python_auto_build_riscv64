# Hermes 远程构建闭环

此目录放 RISC-V 远端构建 worker 和 x86 PC hermes controller。脚本放仓库，运行态数据放双方各自的 `$HOME/.python_auto_build_hermes/`。

## 架构

```text
RISC-V remote_worker.py
  -> 逐包调用 build_most_common/build_one.sh
  -> 失败写 $HOME 队列和日志
  -> 等 x86 标记 fixed / permanent_failed

x86 x86_controller.py
  -> SSH 读取远端失败请求
  -> 生成 hermes 修复提示
  -> 调用 hermes-api
  -> 标记 fixed / permanent_failed
```

## RISC-V 远端运行

```bash
cd /path/to/python_auto_build_riscv64
export BUILD_FOR_VERSION=3.12
python3 hermes_build/remote_worker.py
```

默认读取：

```text
build_pypi/top_pypi_package_names.txt
```

远端运行态目录：

```text
$HOME/.python_auto_build_hermes/
  queue/{failed,repairing,fixed,permanent_failed}/
  state/packages/
  logs/<package>/
  src/
```

## x86 PC 运行

```bash
cd /path/to/python_auto_build_riscv64
export HERMES_RISCV_HOST=bianbu@10.0.90.13
export HERMES_REMOTE_HOME_DATA_DIR=/home/bianbu/.python_auto_build_hermes
export HERMES_VENV_ACTIVATE=~/hermes_env/bin/activate
export HERMES_MODEL=gpt-5.5
python3 hermes_build/x86_controller.py
```

controller 固定使用 hermes-api，会从 `HERMES_VENV_ACTIVATE` 指定的虚拟环境加载 `run_agent.AIAgent`。

x86 运行态目录：

```text
$HOME/.python_auto_build_hermes/
  cache/failed_requests/<package>/
    hermes_prompt.md
    experience_prompt.md
    experience_draft.md
  logs/<package>-repair.log
  experience/<package>.md
```

每轮修复结束后，controller 会再调用一次 hermes-api，根据构建日志和修复日志生成真实经验摘要；生成失败时才保留占位模板。

## 只处理一轮

```bash
python3 hermes_build/x86_controller.py --once
```

## 注意

- 第一版只做串行闭环，不做 HTTP 服务、数据库、并发构建。
- 远端 worker 不直接依赖 hermes，只通过文件队列等待结果。
- x86 controller 用 SSH/SCP 访问远端，要求免密 SSH 或手动可登录；修复侧固定调用本地 hermes-api。
- `build_from_src.sh` 支持外部传入 `PACKAGE_NAME_REAL`，不传时按源码目录名兜底。
