# Hermes Wheel 基础功能检查

此目录用于检查 Spacemit PyPI 源上已有 wheel 包在 RISC-V Python `3.12`、`3.13`、`3.14` 下是否能安装并通过基础常用功能测试。

运行态数据默认放在双方各自的：

```text
$HOME/.python_auto_build_hermes_whl_check/
```

## RISC-V worker

在 RISC-V 机器仓库根目录运行：

```bash
cd /path/to/python_auto_build_riscv64
python3 hermes_whl_check/remote_worker.py
```

worker 会：

- 调用 `build_pypi/00get_spacemit_pkgs.py` 生成 `build_pypi/packages_spacemit.log`
- 依次检查 `3.12`、`3.13`、`3.14`
- 先读取 simple index，若没有兼容 wheel 则标记 `skipped`
- 用 `uv venv <venv> --python=<version>` 创建单包单版本临时 venv
- 激活 venv 后用 `uv pip install pip -U` 更新 pip
- 重新激活 venv 后使用普通 `pip install --only-binary=:all:` 安装包
- 安装成功后写入 `queue/pending/*.json` 等待 x86 Hermes controller
- 收到 `passed` 或 `failed` 后删除该包对应 venv，避免残留

常用参数：

```bash
python3 hermes_whl_check/remote_worker.py --limit 10
python3 hermes_whl_check/remote_worker.py --python-versions 3.12 3.13 3.14
python3 hermes_whl_check/remote_worker.py --no-refresh-package-list
```

默认源：

```text
https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple
```

可通过环境变量覆盖：

```bash
export WHL_CHECK_INDEX_URL=https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple
export WHL_CHECK_EXTRA_INDEX_URL=
```

## x86 Hermes controller

在 x86 PC 仓库根目录运行：

```bash
cd /path/to/python_auto_build_riscv64
export HERMES_RISCV_HOST=bianbu@10.0.90.13
export HERMES_REMOTE_HOME_DATA_DIR=/home/bianbu/.python_auto_build_hermes_whl_check
export HERMES_VENV_ACTIVATE=~/hermes_env/bin/activate
export HERMES_MODEL=gpt-5.5
python3 hermes_whl_check/x86_controller.py
```

controller 会：

- 通过 SSH 读取远端 `queue/pending/*.json`
- 拉取远端安装日志到本地 cache
- 调用 hermes-api，让 Hermes 在远端已有 venv 内写并运行基础功能测试
- 根据 Hermes JSON 输出标记远端 `queue/passed` 或 `queue/failed`
- 对失败项追加本地日志：

```text
$HOME/.python_auto_build_hermes_whl_check/logs/failed_whl_checks.log
```

只处理一轮：

```bash
python3 hermes_whl_check/x86_controller.py --once
```

## 目录结构

RISC-V 端：

```text
$HOME/.python_auto_build_hermes_whl_check/
  queue/{pending,testing,passed,failed}/
  state/packages/
  logs/<package>/<python-version>/install.log
  venvs/
```

x86 端：

```text
$HOME/.python_auto_build_hermes_whl_check/
  cache/<package>-py<version>/
    install.log
    hermes_test_prompt.md
    hermes_result.json
  logs/
    <package>-py<version>-test.log
    failed_whl_checks.log
```

## 注意

- worker 只用现有 wheel，`--only-binary=:all:` 会避免源码构建。
- 没有对应 Python 版本 wheel 的包会跳过，不会创建 venv。
- 每个包单版本测试完成后都会删除对应 venv。
- 不要在未运行 RISC-V worker 和 x86 controller 的情况下声称包功能测试通过。
