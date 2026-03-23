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
