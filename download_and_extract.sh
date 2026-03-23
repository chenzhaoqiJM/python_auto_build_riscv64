#!/bin/sh

# 用法说明
if [ "$#" -ne 2 ]; then
    echo "用法: $0 <url> <target_dir>"
    exit 1
fi

URL="$1"
DEST_DIR="$2"

# 确保目标目录存在
sudo mkdir -p "$DEST_DIR"

# 下载文件（保持原始名字）
echo "📥 下载中: $URL"
if ! wget -P /tmp "$URL"; then
    echo "❌ 下载失败: $URL"
    exit 1
fi

# 提取文件名
FILENAME=$(basename "$URL")
TMP_TAR="/tmp/$FILENAME"

# 解压并去掉最上层目录
echo "📦 解压到: $DEST_DIR"
if ! sudo tar -xzf "$TMP_TAR" -C "$DEST_DIR" --strip-components=1; then
    echo "❌ 解压失败"
    rm -f "$TMP_TAR"
    exit 1
fi

# 清理
rm -f "$TMP_TAR"

echo "✅ 完成: $DEST_DIR"
