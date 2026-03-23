#!/bin/bash
set -e


# 当前脚本所在目录（支持相对路径执行）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 加载公共函数
source "$SCRIPT_DIR/../common_func.sh"

# 调用检查函数
check_build_version

ensure_uv
uv python install $BUILD_FOR_VERSION

echo "开始构建 Python $BUILD_FOR_VERSION ..."
# 下面继续构建逻辑


UPLOAD_SCRIPT="$SCRIPT_DIR/../common_py/00upload_with_repair.py"

# 可配置字段
export PIP_CACHE_DIR="$HOME/.cache/pip/wheels_stag_uv_$BUILD_FOR_VERSION"
BUILD_TMPDIR="$HOME/.mytmp/stag_uv_$BUILD_FOR_VERSION"
VENV_NAME="tmpbuild_stag_uv_$BUILD_FOR_VERSION"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
DIST_DIR="$HOME/pyenvs/store"

WHEEL_CACHE_DIR="$HOME/wheels/stag"

mkdir -p "$BUILD_TMPDIR" "$WHEEL_CACHE_DIR" "$DIST_DIR"

export WHEEL_CACHE_DIR_PY="$WHEEL_CACHE_DIR"
export TMPDIR="$BUILD_TMPDIR"

export CMAKE_ARGS="-Wno-error -DWITH_GTK=OFF -DWITH_QT=ON -DWITH_GTK_2_X=OFF"

export CI_BUILD=1 

export MAKEFLAGS='-j8'
export NINJAFLAGS='-j8'

# 添加 Qt lib 路径到 LD_LIBRARY_PATH（防重复）
if [[ ":$LD_LIBRARY_PATH:" != *":/opt/Qt5.15.16/lib:"* ]]; then
    export LD_LIBRARY_PATH=/opt/Qt5.15.16/lib:$LD_LIBRARY_PATH
fi

# 添加 Qt bin 路径到 PATH（防重复）
if [[ ":$PATH:" != *":/opt/Qt5.15.16/bin:"* ]]; then
    export PATH=/opt/Qt5.15.16/bin:$PATH
fi

# 设置 QTDIR 变量
export QTDIR=/opt/Qt5.15.16

# 打印确认
echo "LD_LIBRARY_PATH = $LD_LIBRARY_PATH"
echo "LLVM_CONFIG = $LLVM_CONFIG"

# git dir
TARGET_DIR="$HOME/ck/stag-python"
TAGS=("v1.1.1" "v1.1.0" "v1.0.2" "v1.0.1" "v1.0.0")  # 这里列出所有需要构建的 tag

# 创建上级目录（如果不存在）
mkdir -p "$(dirname "$TARGET_DIR")"


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
    pip install --verbose setuptools wheel build twine auditwheel numpy tomli-w

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


for tag in "${TAGS[@]}"; do

    cd "$SCRIPT_DIR"

    echo "🔖 Processing tag: $tag"

    echo "🗑️  Removing $VENV_DIR"
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
    rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

    rm -rf "$HOME/ck"
    # 创建上级目录（如果不存在）
    mkdir -p "$(dirname "$TARGET_DIR")"


    cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    # 克隆仓库到指定目录（递归包含子模块）
    git clone --recursive https://github.com/ManfredStoiber/stag-python "$TARGET_DIR"

    # 如果克隆成功，则进入该目录
    if [ $? -eq 0 ]; then
        cd "$TARGET_DIR" || exit 1
        git checkout $tag
    else
        echo "Git clone failed."
        exit 1
    fi

    sleep 4

    pip wheel . --verbose --wheel-dir="$WHEEL_CACHE_DIR"

    if [ -f "$UPLOAD_SCRIPT" ]; then
        echo "🚀 Running upload_built_wheels.py..."
        python "$UPLOAD_SCRIPT"
    else
        echo "⚠️  upload_built_wheels.py not found in $SCRIPT_DIR"
    fi

    deactivate

    sleep 3

    echo "🗑️  Removing $VENV_DIR"
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
    rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

done

rm -rf "$HOME/ck" 
echo "✅ Done All."
