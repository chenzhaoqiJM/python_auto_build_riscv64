#!/bin/bash
set -e  # 如果任何命令失败则退出
set -u  # 使用未定义变量时报错

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 安装系统 deb 依赖..."
bash "$SCRIPT_DIR/sys_deb_deps.sh"

echo "🔧 安装扩展依赖..."
bash "$SCRIPT_DIR/sys_other_deps.sh"