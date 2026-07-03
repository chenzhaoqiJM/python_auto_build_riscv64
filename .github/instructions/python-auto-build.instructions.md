---
description: "Use when editing python_auto_build scripts, Python build helpers, shell automation, dynamic_env modules, special_care builders, wheel repair or upload logic. Covers concise project coding conventions for RISC-V Python wheel automation."
name: "python_auto_build 项目编程规范"
applyTo: ["**/*.py", "**/*.sh", "**/*.md"]
---

# python_auto_build 项目编程规范

本项目用于在 Bianbu Linux / riscv64 环境下自动化构建、修复、测试并上传 Python wheel 包。修改时优先保持脚本简单、可直接在目标环境执行、便于排障。

## 通用原则

- 优先做最小改动，避免引入不必要的框架、抽象层或新依赖。
- 保持现有目录职责：通用逻辑放 `common_py/`、包特殊构建放 `special_care/`、动态环境放 `dynamic_env/`、需要特殊处理的包的可自动构建的包的脚本放 `build_*`。
- 修改构建流程时必须考虑 `BUILD_FOR_VERSION`，支持 `3.9` 到 `3.14t` 的现有版本约定。
- 不要硬编码个人本地路径；确需缓存或临时目录时沿用 `$HOME/.cache*`、`$HOME/.mytmp*`、`$HOME/pyenvs*` 等现有模式。
- 涉及上传、删除、覆盖包等高风险操作时，保留清晰日志并避免静默失败。

## Shell 脚本约定

- 新增 Bash 脚本优先使用 `#!/bin/bash` 与 `set -e`；需要 POSIX sh 时才使用 `#!/usr/bin/env sh`。
- 路径基于脚本目录计算：`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`，避免依赖当前工作目录。
- 复用 `common_func.sh`、`env_common.sh`、`dynamic_env/env_loader.sh`，不要复制已有函数。
- 变量引用默认加双引号；包名、路径、版本号都按可能包含特殊字符处理。
- 动态环境必须成对考虑 `load_env` / `unload_env`，避免污染后续包构建。

## Python 代码约定

- Python 脚本保持标准库优先；只有现有项目已经依赖或确有必要时才新增第三方依赖。
- 通用能力写成小函数，包级特殊逻辑写在 `special_care/build_<pkg>.py`，并通过 `registry.py` 的装饰器注册。
- 网络下载、GitLab 查询、上传等不稳定操作应有重试或明确错误输出。
- 解析包名时兼容 `name` 和 `name==version` 两种形式，避免破坏版本构建脚本。
- 日志保持可读，沿用项目中中文说明和 emoji 状态提示风格即可；错误信息要包含包名或关键路径。

## Wheel 与构建兼容性

- 修改 wheel 修复逻辑时，优先保持 manylinux 标签、rpath、`.libs` 处理和 abi3/free-threading 兼容性。
- 涉及 glibc、RISC-V、RVV、Qt、OpenCV、Arrow、FFmpeg、MuJoCo、CycloneDDS、Faiss 等环境时，优先通过 `dynamic_env/` 增量配置。
- 新增特殊包构建时先检查是否已有 whl、是否需要源码 patch、是否需要额外系统库。

## 验证建议

- 修改 Python 文件后，至少运行语法检查或目标脚本的轻量入口检查。
- 修改 Shell 脚本后，至少运行 `bash -n` 检查语法；能在目标环境执行时再做实际构建验证。
- 不要在未确认目标 riscv64/Bianbu 环境的情况下声称构建成功。

## 后期维护

- 新增规范时优先追加到对应小节，保持条目短句化。
- 如果某条规则只适用于单个包，请写到对应 `special_care/build_<pkg>.py` 附近的注释或 README，而不是放进本文件。