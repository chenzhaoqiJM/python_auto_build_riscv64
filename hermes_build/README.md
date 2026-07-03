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
  -> 执行 HERMES_REPAIR_COMMAND
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
python3 hermes_build/x86_controller.py
```

默认只生成 hermes prompt，并把请求标为 `permanent_failed`。要自动修复，需要设置 `HERMES_REPAIR_COMMAND`。

示例：

```bash
export HERMES_REPAIR_COMMAND='hermes < {prompt}'
python3 hermes_build/x86_controller.py
```

如果 hermes 每次执行都会留下会话，可配置修复结束后的清理命令。
当前 Hermes CLI 支持 `sessions prune/delete`，不支持按包名 `session clear --package`：

```bash
export HERMES_SESSION_CLEANUP_COMMAND='hermes sessions prune --older-than 1 --source cli --yes'
```

该命令会在每个包的修复命令结束后执行；即使修复失败或超时，也会尝试清理。若需要精确删除单个会话，请先通过 `hermes sessions list` 获取 session_id，再使用 `hermes sessions delete --yes <session_id>`。

`HERMES_REPAIR_COMMAND` 可用变量：

```text
{prompt}                本地 hermes 提示文件
{package}               包名
{host}                  远端 SSH 主机
{remote_repo}           远端仓库路径
{remote_home_data_dir}  远端运行态目录
{repair_log}            本地修复日志路径
```

`HERMES_SESSION_CLEANUP_COMMAND` 使用同一组变量。

x86 运行态目录：

```text
$HOME/.python_auto_build_hermes/
  cache/failed_requests/<package>/
  logs/<package>-repair.log
  experience/<package>.md
```

## 只处理一轮

```bash
python3 hermes_build/x86_controller.py --once
```

## 注意

- 第一版只做串行闭环，不做 HTTP 服务、数据库、并发构建。
- 远端 worker 不直接依赖 hermes，只通过文件队列等待结果。
- x86 controller 用 SSH/SCP 访问远端，要求免密 SSH 或手动可登录。
- `build_from_src.sh` 支持外部传入 `PACKAGE_NAME_REAL`，不传时按源码目录名兜底。
