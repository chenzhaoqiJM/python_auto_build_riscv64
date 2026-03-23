#!/bin/bash
set -e  # 如果任何命令失败则退出
set -u  # 使用未定义变量时报错

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


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


set +e  # 临时关闭 set -e
sudo apt remove -y python3-numpy python3-scipy
set -e

GCC_MAJOR=$(gcc -dumpfullversion | cut -d. -f1)

if [ "$GCC_MAJOR" -lt 14 ]; then
    echo "当前 GCC 版本为 $GCC_MAJOR，小于 14，开始安装 gcc-14 和 g++-14..."

    sudo apt install -y gcc-14 g++-14

    # 设置 update-alternatives
    sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100
    sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 100
    sudo update-alternatives --set gcc /usr/bin/gcc-14
    sudo update-alternatives --set g++ /usr/bin/g++-14

    sudo update-alternatives --install /usr/bin/riscv64-linux-gnu-gcc riscv64-linux-gnu-gcc /usr/bin/riscv64-linux-gnu-gcc-14 100
    sudo update-alternatives --install /usr/bin/riscv64-linux-gnu-g++ riscv64-linux-gnu-g++ /usr/bin/riscv64-linux-gnu-g++-14 100
    sudo update-alternatives --set riscv64-linux-gnu-gcc /usr/bin/riscv64-linux-gnu-gcc-14
    sudo update-alternatives --set riscv64-linux-gnu-g++ /usr/bin/riscv64-linux-gnu-g++-14

    echo "✅ GCC/G++ 已切换为 14"
else
    echo "✅ 当前 GCC 版本为 $GCC_MAJOR，已满足 ≥ 14，无需切换"
fi

sleep 1

# Qt 字体支持（避免重复复制）
if [ ! -d "/usr/share/fonts/dejavu" ]; then
    sudo mkdir -p /usr/share/fonts
    sudo cp -r /usr/share/fonts/truetype/dejavu /usr/share/fonts/dejavu
fi

echo "✅ Python deb 依赖安装完成"

pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip config set global.extra-index-url https://git.spacemit.com/api/v4/projects/33/packages/pypi/simple

# 支持uv
curl -LsSf https://astral.sh/uv/install.sh | sh

PYPIRC_PATH="$HOME/.pypirc"
SOURCE_FILE="$SCRIPT_DIR/pypirc.txt"

# 如果目标文件存在则删除
if [ -f "$PYPIRC_PATH" ]; then
    echo "🧹 Removing existing $PYPIRC_PATH"
    rm -f "$PYPIRC_PATH"
fi

# 复制新的 pypirc 文件
echo "📋 Copying $SOURCE_FILE to $PYPIRC_PATH"
cp "$SOURCE_FILE" "$PYPIRC_PATH"

sleep 3

# 下载第三方库 ------------------------------------------------------------------------------------------------
# 获取 glibc 版本号（只取主次版本号，如 2.39、2.41）
GLIBC_VERSION=$(ldd --version 2>&1 \
    | grep -oE '[0-9]+\.[0-9]+' \
    | head -n1)

case "$GLIBC_VERSION" in
    "2.39")
        EXT_PREFIX="bianbu24"
        ;;
    "2.41")
        EXT_PREFIX="bianbu25"
        ;;
    "2.42")
        EXT_PREFIX="bianbu26-pre"
        ;;
    *)
        echo "❌ 不支持的 glibc 版本: $GLIBC_VERSION"
        exit 1
        ;;
esac

echo "✅ 当前 glibc 版本: $GLIBC_VERSION (使用目录: $EXT_PREFIX)"

# 解压操作（若目录已存在则跳过）
function download_and_extract {
    local url=$1
    local dest=$2
    if [ ! -d "$dest" ]; then
        "$SCRIPT_DIR/download_and_extract.sh" "$url" "$dest"
    else
        echo "📦 $dest 已存在，跳过下载和解压"
    fi
}

download_targz_all() {
    local base_url="$1"
    local prefix_name="$2"
    local opt_sub_dir_name="$3"

    # 获取文件列表
    local files=$(curl -s "$base_url/" | grep -oE "${prefix_name}-[^\\\"]+\.tar\.gz" | sort -u)

    echo "Found files:"
    echo "$files"

    for f in $files; do
        # 去掉 .tar.gz 得到目录名
        local dirname="${f%.tar.gz}"
        local dest="/opt/ext/$opt_sub_dir_name/$dirname"
        echo "Downloading and extracting $f to $dest"
        download_and_extract "$base_url/$f" "$dest"
    done
}


BASE_URL="https://archive.spacemit.com/ros2/prebuilt_libs/$EXT_PREFIX/opt/ext"

set +e  # 临时关闭 set -e
download_and_extract $BASE_URL/qt_xcb/Qt5.15.16.tar.gz /opt/Qt5.15.16
download_and_extract $BASE_URL/qt_xcb/Qt5.15.18.tar.gz /opt/Qt5.15.18

### download_targz_all URL路径 tar文件的前缀名 /opt/ext下的解压子文件夹名

# arrow
download_targz_all "$BASE_URL/arrow" apache-arrow arrow

# ffmpeg
download_targz_all "$BASE_URL/ffmpeg" ffmpeg ffmpeg

# # mujoco
download_targz_all "$BASE_URL/mujoco" mujoco mujoco

# # mujoco
download_targz_all "$BASE_URL/cyclonedds" cyclonedds cyclonedds

echo "✅ 第三方库下载完成"
set -e

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
