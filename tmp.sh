#!/bin/bash

# 获取 Python 版本号 (只取主次版本号，比如 3.12, 3.13)
PYTHON_VERSION=$(/usr/bin/python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

case "$PYTHON_VERSION" in
    "3.12")
        EXT_PREFIX="ext"   # Python 3.12 用 ext
        ;;
    "3.13")
        EXT_PREFIX="ext3"  # Python 3.13 用 ext3
        ;;
    *)
        echo "❌ 不支持的 Python 版本: $PYTHON_VERSION"
        exit 1
        ;;
esac

echo "✅ 当前 Python 版本: $PYTHON_VERSION (使用目录: $EXT_PREFIX)"

# 解压操作（若目录已存在则跳过）
function download_and_extract {
    local url=$1
    local dest=$2
    if [ ! -d "$dest" ]; then
        ./download_and_extract.sh "$url" "$dest"
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


BASE_URL="https://archive.spacemit.com/ros2/prebuilt/$EXT_PREFIX"

download_and_extract $BASE_URL/Qt5.15.16.tar.gz /opt/Qt5.15.16

### download_targz_all URL路径 tar文件的前缀名 /opt/ext下的解压子文件夹名

# arrow
download_targz_all "$BASE_URL/arrow" apache-arrow arrow

# ffmpeg
download_targz_all "$BASE_URL/ffmpeg" ffmpeg ffmpeg

# # mujoco
download_targz_all "$BASE_URL/mujoco" mujoco mujoco
