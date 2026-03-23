#!/bin/sh

# 用法说明
if [ "$#" -ne 2 ]; then
    echo "用法: $0 <url> <target_dir>"
    exit 1
fi

URL="$1"
DEST_DIR="$2"
TMP_TAR="$(mktemp /tmp/download.XXXXXX.tar.gz)"

# 下载
echo "📥 下载中: $URL"
wget -O "$TMP_TAR" "$URL"
if [ $? -ne 0 ]; then
    echo "❌ 下载失败: $URL"
    rm -f "$TMP_TAR"
    exit 1
fi

# 创建目标目录
mkdir -p "$DEST_DIR"

# 解压并去掉最上层目录
echo "📦 解压到: $DEST_DIR"
tar -xzf "$TMP_TAR" -C "$DEST_DIR" --strip-components=1
if [ $? -ne 0 ]; then
    echo "❌ 解压失败"
    rm -f "$TMP_TAR"
    exit 1
fi

# 清理
rm -f "$TMP_TAR"

echo "✅ 完成: $DEST_DIR"
