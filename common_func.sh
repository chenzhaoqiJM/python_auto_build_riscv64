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

# 校验解释器的 Python 主次版本和构建 ABI（常规 GIL / free-threaded）。
python_matches_build_version() {
    _python_executable="$1"
    _requested_version="$2"

    [ -x "$_python_executable" ] || return 1
    "$_python_executable" - "$_requested_version" <<'PY'
import sys
import sysconfig

requested = sys.argv[1]
expected_free_threaded = requested.endswith("t")
expected_version = requested.removesuffix("t")
actual_version = f"{sys.version_info.major}.{sys.version_info.minor}"
actual_free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

if (actual_version, actual_free_threaded) != (expected_version, expected_free_threaded):
    actual = f"{actual_version}{'t' if actual_free_threaded else ''}"
    print(
        f"❌ Python ABI mismatch: requested {requested}, got {actual} "
        f"from {sys.executable}",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
}

# uv 对不带 variant 的 3.14 请求可能选择补丁版本更高的 3.14t。
# 使用 uv 创建的精确可执行文件名，确保 3.14 和 3.14t 不会互相替代。
select_uv_build_python() {
    _uv_python_bin_dir=$(uv python dir --bin)
    _uv_python_executable="$_uv_python_bin_dir/python$BUILD_FOR_VERSION"

    if ! python_matches_build_version "$_uv_python_executable" "$BUILD_FOR_VERSION"; then
        _uv_install_request="$BUILD_FOR_VERSION"
        case "$BUILD_FOR_VERSION" in
            *t) ;;
            *)
                # An unqualified request such as 3.14 can match 3.14t. Pick the
                # newest concrete non-variant CPython version instead.
                _uv_regular_version=$(
                    uv python list "$BUILD_FOR_VERSION" --all-versions 2>/dev/null |
                        awk '
                            $1 ~ /^cpython-/ && index($1, "+") == 0 {
                                version = $1
                                sub(/^cpython-/, "", version)
                                sub(/-.*/, "", version)
                                print version
                                exit
                            }
                        '
                )
                if [ -n "$_uv_regular_version" ]; then
                    _uv_install_request="$_uv_regular_version"
                fi
                ;;
        esac
        uv python install "$_uv_install_request"
    fi

    if ! python_matches_build_version "$_uv_python_executable" "$BUILD_FOR_VERSION"; then
        echo "❌ uv 未提供匹配 BUILD_FOR_VERSION=$BUILD_FOR_VERSION 的解释器: $_uv_python_executable" >&2
        echo "   请用 'uv python list --only-installed' 检查常规版与 free-threaded 版是否均已正确安装。" >&2
        return 1
    fi

    UV_BUILD_PYTHON="$_uv_python_executable"
    export UV_BUILD_PYTHON
    echo "✅ Selected exact Python interpreter: $UV_BUILD_PYTHON"
}

# 错误 ABI 的虚拟环境缓存可安全重建，避免目录名与实际解释器不一致。
remove_mismatched_venv_cache() {
    _cached_venv="$1"
    [ -d "$_cached_venv" ] || return 0

    if python_matches_build_version "$_cached_venv/bin/python" "$BUILD_FOR_VERSION"; then
        return 0
    fi

    case "$_cached_venv" in
        "$HOME/pyenvs/store/"?*) ;;
        *)
            echo "❌ Refusing to remove unexpected virtualenv cache path: $_cached_venv" >&2
            return 1
            ;;
    esac

    echo "🧹 Removing mismatched virtualenv cache: $_cached_venv"
    rm -rf -- "$_cached_venv"
}

# 判断包名（或源码目录名）是否属于需要外部 Qt 的 Python Qt 绑定。
is_qt_binding_package() {
    _qt_package_name=$(basename "${1%/}" | tr '[:upper:]_' '[:lower:]-')
    case "$_qt_package_name" in
        pyqt5*|pyqt6*|pyside2*|pyside6*|pyside-setup*|pyside-pyside*) return 0 ;;
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
