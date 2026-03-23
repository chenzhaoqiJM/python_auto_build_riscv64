#!/bin/bash
set -e  # 如果任何命令失败则退出
set -u  # 使用未定义变量时报错

UPDATE_LIB_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


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
        "$UPDATE_LIB_SCRIPT_DIR/download_and_extract.sh" "$url" "$dest"
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

download_targz_all "$BASE_URL/faiss" faiss faiss


echo "✅ 第三方库下载完成"


