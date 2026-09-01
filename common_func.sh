#!/usr/bin/env sh

check_build_version() {
    if [ -z "$BUILD_FOR_VERSION" ]; then
        echo "错误: 请先设置 BUILD_FOR_VERSION 环境变量，例如:"
        echo "export BUILD_FOR_VERSION=3.12"
        echo "  或者 3.9, 3.10, 3.11, 3.13, 3.13t, 3.14, 3.14t 等 Python 版本号"
        exit 1
    fi

    case "$BUILD_FOR_VERSION" in
        3.9|3.10|3.11|3.12|3.13|3.13t|3.14t|3.14) ;;
        *)
            echo "错误: BUILD_FOR_VERSION 只能是 3.9、3.10、3.11、3.12、3.13、3.13t、3.14、3.14t"
            exit 1
            ;;
    esac
}

ensure_uv() {
    if ! command -v uv >/dev/null 2>&1; then
        echo "⚠️ 未检测到 uv，正在安装..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # uv 默认安装到 ~/.local/bin
        if [ -f "$HOME/.local/bin/env" ]; then
            echo "✅ 载入 uv 环境..."
            # shellcheck source=/dev/null
            . "$HOME/.local/bin/env"
        else
            echo "❌ 没有找到 $HOME/.local/bin/env，请确认 uv 是否正确安装。"
        fi
    else
        echo "✅ 已检测到 uv: $(command -v uv)"
    fi
}

# 判断包名（或源码目录名）是否属于需要外部 Qt 的 Python Qt 绑定。
is_qt_binding_package() {
    _qt_package_name=$(basename "${1%/}" | tr '[:upper:]_' '[:lower:]-')
    case "$_qt_package_name" in
        pyqt5*|pyqt6*|pyside2*|pyside6*|pyside-setup*) return 0 ;;
        *) return 1 ;;
    esac
}

# Qt 绑定必须显式指定本次构建使用的 Qt，避免编译和 wheel 修复使用不同版本。
require_qt_install_prefix_for_package() {
    if ! is_qt_binding_package "$1"; then
        return 0
    fi

    if [ -z "${QT_INSTALL_PREFIX:-}" ]; then
        echo "❌ 错误: 构建 $1 必须设置环境变量 QT_INSTALL_PREFIX"
        echo "    例如: export QT_INSTALL_PREFIX=/opt/Qt6.9.2"
        return 1
    fi

    if [ ! -d "$QT_INSTALL_PREFIX" ]; then
        echo "❌ 错误: QT_INSTALL_PREFIX 目录不存在: $QT_INSTALL_PREFIX"
        return 1
    fi

    if [ ! -d "$QT_INSTALL_PREFIX/lib" ]; then
        echo "❌ 错误: Qt lib 目录不存在: $QT_INSTALL_PREFIX/lib"
        return 1
    fi

    export QT_INSTALL_PREFIX
    echo "✅ $1 使用 Qt 路径: $QT_INSTALL_PREFIX"
}


# 判断是否为 Python 3.13t / 3.14t（free-threading）
is_python_t_interpreter() {
    python3 - <<'PY'
import sys

# 仅关心 3.13 / 3.14
if sys.version_info < (3, 13):
    print("no")
    raise SystemExit

# Python 3.13+ free-threading 官方接口
if hasattr(sys, "_is_gil_enabled"):
    print("yes" if not sys._is_gil_enabled() else "no")
else:
    print("no")
PY
}
