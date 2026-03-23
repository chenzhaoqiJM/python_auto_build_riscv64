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
