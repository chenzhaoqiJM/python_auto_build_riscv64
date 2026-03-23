#!/bin/bash
set -e

# 检查是否传入至少一个路径
if [ $# -eq 0 ]; then
    echo "❌ 错误: 你必须传入至少一个源码路径作为参数，例如："
    echo "    ./test.sh /home/bianbu/scipy"
    exit 1
fi

# 检查 SAVE_FINAL_WHL_TO_HOME 环境变量
if [ -z "${SAVE_FINAL_WHL_TO_HOME+x}" ]; then
    echo "❌ 错误: 必须设置环境变量 SAVE_FINAL_WHL_TO_HOME"
    echo "    export SAVE_FINAL_WHL_TO_HOME=1  # 将构建好的 whl 保存到 HOME 目录（验证阶段）"
    echo "    export SAVE_FINAL_WHL_TO_HOME=0  # 上传到 spacemit pypi"
    exit 1
fi

if [ "$SAVE_FINAL_WHL_TO_HOME" != "0" ] && [ "$SAVE_FINAL_WHL_TO_HOME" != "1" ]; then
    echo "❌ 错误: SAVE_FINAL_WHL_TO_HOME 只允许设置为 0 或 1"
    echo "    当前值: '$SAVE_FINAL_WHL_TO_HOME'"
    echo "    export SAVE_FINAL_WHL_TO_HOME=1  # 将构建好的 whl 保存到 HOME 目录（验证阶段）"
    echo "    export SAVE_FINAL_WHL_TO_HOME=0  # 上传到 spacemit pypi"
    exit 1
fi

export SAVE_FINAL_WHL_TO_HOME

# 当前脚本所在目录（支持相对路径执行）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置uv环境
# 加载公共函数
source "$SCRIPT_DIR/../common_func.sh"

# 调用检查函数
check_build_version

ensure_uv
uv python install $BUILD_FOR_VERSION

echo "开始构建 Python $BUILD_FOR_VERSION ..."
# 下面继续构建逻辑


UPLOAD_SCRIPT="$SCRIPT_DIR/../common_py/01upload_with_repair_src.py"  # 用于缓存虚拟环境上传（第一次）
SPECIAL_BUILDER_SCRIPT="$SCRIPT_DIR/../special_care/special_builder.py"
NO_DEPS_SCRIPT="$SCRIPT_DIR/../common_py/check_no_deps.py"

# 可配置字段
export PIP_CACHE_DIR="$HOME/.cache/pip/wheels_build_from_src_uv_$BUILD_FOR_VERSION"
export WHEELS_REPAIR_DIR="$HOME/.mywheel_repair/build_from_src_uv_$BUILD_FOR_VERSION"
BUILD_TMPDIR="$HOME/.mytmp/build_from_src_uv_$BUILD_FOR_VERSION"
VENV_NAME="build_from_src_uv_$BUILD_FOR_VERSION"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
DIST_DIR="$HOME/pyenvs/store"
WHEEL_CACHE_DIR="$HOME/.mywheels/build_from_src_uv_$BUILD_FOR_VERSION"

mkdir -p "$BUILD_TMPDIR" "$WHEEL_CACHE_DIR" "$DIST_DIR"

rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

# 环境变量
export WHEEL_CACHE_DIR_PY="$WHEEL_CACHE_DIR"
export TMPDIR="$BUILD_TMPDIR"

export PYTHONPATH="$VENV_DIR/lib/python$BUILD_FOR_VERSION/site-packages"

ENV_LOADER_SH="$SCRIPT_DIR/../dynamic_env/env_loader.sh"

# 加载公共环境变量
source "$SCRIPT_DIR/../env_common.sh"

# 打印确认
echo "LD_LIBRARY_PATH = $LD_LIBRARY_PATH"
echo "LLVM_CONFIG = $LLVM_CONFIG"


# ✅ 可选清空旧日志
> "$SCRIPT_DIR/failed_test.log"

# 清理旧虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo "🧹 Removing old virtualenv at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

# 创建或还原虚拟环境
if [ -d "$DIST_DIR/$VENV_NAME" ]; then
    echo "✅ Cached virtualenv ready at $DIST_DIR"
else
    echo "📦 Creating new virtualenv at $VENV_DIR"
    uv venv "$VENV_DIR" --python=$BUILD_FOR_VERSION

    source "$VENV_DIR/bin/activate"
    echo "⬆️  Installing pip & build tools..."
    uv pip install --upgrade pip
    deactivate
    source "$VENV_DIR/bin/activate"
    pip install --upgrade setuptools wheel build twine auditwheel
    pip install numpy maturin scipy pyelftools pybind11 Cython nanobind

    REQUIRED_PKGS=("setuptools" "wheel" "build" "twine" "auditwheel")
    for pkg in "${REQUIRED_PKGS[@]}"; do
        if python -m pip show "$pkg" >/dev/null 2>&1; then
            echo "[OK] $pkg is installed"
        else
            echo "❌ [ERROR] $pkg is NOT installed"
            deactivate
            sleep 2
            echo "Removing tmp..........."
            rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
            rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
            exit 1
        fi
    done

    echo "✅ All required packages are installed."

    if [ -f "$UPLOAD_SCRIPT" ]; then
        echo "🚀 Running upload script..."
        python "$UPLOAD_SCRIPT"
    else
        echo "⚠️  Upload script not found: $UPLOAD_SCRIPT"
    fi

    deactivate
    sleep 2
    cp -r "$VENV_DIR" "$DIST_DIR"

    echo "🧹 Cleaning tmp build and venv..."
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
    rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"
fi

# 遍历每个传入的包名
for PACKAGE_SOURCE_PATH in "$@"; do
    echo "=============================="
    echo "🔧 准备构建: $PACKAGE_SOURCE_PATH"
    echo "=============================="

    # 清除历史残留
    echo "🧹 Cleaning tmp build and venv..."
    command -v deactivate &>/dev/null && deactivate || true
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
    rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

    # 去除尾部斜杠，防止 basename 为空
    PACKAGE_SOURCE_PATH="${PACKAGE_SOURCE_PATH%/}"

    # 拷贝源码
    BASENAME_1="$(basename "$PACKAGE_SOURCE_PATH")"

    TMP_SOURCE_DIR="$TMPDIR/$BASENAME_1"
    cp -ra "$PACKAGE_SOURCE_PATH" "$TMPDIR/"

    # 拷贝虚拟环境
    cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    # 动态环境变量
    source "$ENV_LOADER_SH" "$PACKAGE_NAME_REAL"
    load_env
    echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"

    echo "🔨 Building wheel for $PACKAGE_SOURCE_PATH ..."

    # 直接构建
    build_generic_package() {

        NO_DEPS=$(python3 "$NO_DEPS_SCRIPT" "$PACKAGE_SOURCE_PATH")
        echo "⚙️  Extra pip flags: $NO_DEPS"


        cd "$TMP_SOURCE_DIR" || { echo "❌ ERROR: 无法进入目录 $TMP_SOURCE_DIR"; exit 1; }

        if ! pip wheel . --verbose $NO_DEPS --wheel-dir="$WHEEL_CACHE_DIR" ; then
            echo "❌ Failed: $PACKAGE_SOURCE_PATH"
            echo "$PACKAGE_SOURCE_PATH" >> "$SCRIPT_DIR/failed_test.log"
            deactivate || true
            return 1
        fi
        return 0
    }

    # func select ---------------------------------------------
    set +e  # 临时关闭 set -e

    build_generic_package

    build_result=$?

    if [[ $build_result -ne 0 ]]; then
        set -e
        unload_env
        continue
    fi

    set -e
    # func select ---------------------------------------------

    export THE_BUILD_PACKAGE_NAME=$PACKAGE_SOURCE_PATH

    echo "📦 上传构建的 wheel"
    if [ -f "$UPLOAD_SCRIPT" ]; then
        echo "🚀 Running upload_built_wheels.py for $PACKAGE_SOURCE_PATH"
        if ! python "$UPLOAD_SCRIPT"; then
            echo "⚠️ Failed to run upload_built_wheels.py for $PACKAGE_SOURCE_PATH"
        fi
    else
        echo "⚠️ upload_built_wheels.py not found in $SCRIPT_DIR"
    fi

    # 清除环境
    deactivate || true
    sleep 2
    echo "🧹 Cleaning tmp build and venv..."
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"


    echo "✅ Done: $PACKAGE_SOURCE_PATH"
    unload_env
    echo "---------------------------------------------"
done

if [ -s "$SCRIPT_DIR/failed_test.log" ]; then
    echo "❌ 以下包构建失败："
    cat "$SCRIPT_DIR/failed_test.log"
else
    echo "🎉 所有包均构建成功！"
fi
