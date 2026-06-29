#!/bin/bash
set -e  # 如果任何命令失败则退出
set -u  # 使用未定义变量时报错

# 获取 glibc 版本号（只取主次版本号，如 2.39、2.41）
GLIBC_VERSION=$(ldd --version 2>&1 \
    | grep -oE '[0-9]+\.[0-9]+' \
    | head -n1)

case "$GLIBC_VERSION" in
    "2.39")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential python3-requests patchelf python3-sphinx
            python3-routes
        )
        ;;
    "2.41")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential python3-requests patchelf python3-sphinx
            python3-routes
        )
        ;;
    "2.42")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential python3-requests patchelf python3-sphinx
            python3-routes
        )
        ;;
    "2.43")
        BUILD_DEPS=(
            python3 python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
            libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev libncursesw5-dev libgdbm-dev
            libnss3-dev liblzma-dev swig autoconf automake libtool libopenblas-dev libfreetype6-dev liblcms2-dev libwebp-dev
            tcl-dev tk-dev libharfbuzz-dev libfribidi-dev libxcb1-dev clang lld ninja-build libxml2-dev libxslt1-dev
            curl libjpeg-dev libhdf5-dev gfortran python3-bs4 cmake pkg-config build-essential python3-requests patchelf python3-sphinx
            python3-routes
        )
        ;;
    *)
        echo "❌ 不支持的 glibc 版本: $GLIBC_VERSION"
        exit 1
        ;;
esac

echo "🔄 更新 apt 源并安装构建依赖..."
sudo apt update
if sudo apt install -y --allow-downgrades "${BUILD_DEPS[@]}"; then
    echo "✅ 所有构建依赖安装成功"
else
    echo "❌ 构建依赖安装失败"
    exit 1
fi



SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CPUINFO_CONTENT="$(cat /proc/cpuinfo)"

if grep -q "model name.*Spacemit(R) X60" <<< "$CPUINFO_CONTENT"; then
    CPU_VARIANT="K1"
    EXTRA_INDEX_URL="https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple"
    SOURCE_FILE="$SCRIPT_DIR/pypirc.txt"
elif grep -q "model name.*Spacemit(R) X100\|model name.*Spacemit(R) A100" <<< "$CPUINFO_CONTENT"; then
    CPU_VARIANT="K3"
    EXTRA_INDEX_URL="https://git.spacemit.com/api/v4/projects/81/packages/pypi/simple"
    SOURCE_FILE="$SCRIPT_DIR/pypirc_k3.txt"
    echo "📋 K3 detected, overwriting $SCRIPT_DIR/pypirc.txt with $SOURCE_FILE"
    cp "$SOURCE_FILE" "$SCRIPT_DIR/pypirc.txt"
else
    echo "❌ 无法识别 CPU 型号，默认使用 K1 PyPI 源配置, 请确保你使用的是 Bianbu2.2/Bianbu2.3/Bianbu3.0 版本的镜像"
    CPU_VARIANT="X86"
    EXTRA_INDEX_URL="https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple"
    SOURCE_FILE="$SCRIPT_DIR/pypirc.txt"
fi

echo "✅ 检测到 CPU 平台: $CPU_VARIANT"


# 获取 glibc 版本号（只取主次版本号，如 2.39、2.41）
GLIBC_VERSION=$(ldd --version 2>&1 \
    | grep -oE '[0-9]+\.[0-9]+' \
    | head -n1)

case "$GLIBC_VERSION" in
    "2.39")
        ;;
    "2.41")
        ;;
    "2.42")
        ;;
    "2.43")
        ;;
    *)
        echo "❌ 不支持的 glibc 版本: $GLIBC_VERSION"
        exit 1
        ;;
esac

source "$SCRIPT_DIR/common_compiler_setup.sh"
ensure_gcc_14

sleep 1


echo "✅ Python deb 依赖安装完成"

pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip config set global.extra-index-url "$EXTRA_INDEX_URL"

# 支持uv
curl -LsSf https://astral.sh/uv/install.sh | sh

PYPIRC_PATH="$HOME/.pypirc"

# 如果目标文件存在则删除
if [ -f "$PYPIRC_PATH" ]; then
    echo "🧹 Removing existing $PYPIRC_PATH"
    rm -f "$PYPIRC_PATH"
fi

# 复制新的 pypirc 文件
echo "📋 Copying $SOURCE_FILE to $PYPIRC_PATH"
cp "$SOURCE_FILE" "$PYPIRC_PATH"

sleep 3


# 安装 rust 工具 ------------------------------------------------------------------------------
echo "📥 安装 Rust 工具链..."
# -y 自动确认安装
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

echo "🔁 加载 Rust 环境变量..."
source "$HOME/.cargo/env"

echo "⏫ 更新 Rust 工具链..."
rustup update

echo "✅ Rust 安装完成"

# 可选：输出版本验证
echo ""
echo "🧪 Python 版本：$(python3 --version)"
echo "🧪 Rust 版本：$(rustc --version)"
echo "🧪 Cargo 版本：$(cargo --version)"


