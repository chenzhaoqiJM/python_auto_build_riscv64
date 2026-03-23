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

# =============================== 需要构建的版本
TO_BUILD_VERSIONS=("2.7.1" "2.7.0" "2.6.0" "2.5.1" "2.5.0" "2.4.1" "2.4.0")

# =============================== 构建变量
export PYTORCH_BUILD_NUMBER=0
export PKG_NAME="torch"

# =============================== 下载源码
DOWNLOAD_SRC_SH="$SCRIPT_DIR/../download_extract_user.sh"

SOURCE_TARGET_DIR=$HOME/whl_build/pytorch

## 下载源码
if [ ! -d "$SOURCE_TARGET_DIR" ]; then
    $DOWNLOAD_SRC_SH "https://archive.spacemit.com/ros2/prebuilt/source_code/pytorch.tar.gz" $SOURCE_TARGET_DIR
else
    echo "📦 $SOURCE_TARGET_DIR 已存在，跳过下载和解压"
fi

# =============================== 上传脚本相关
UPLOAD_SCRIPT="$SCRIPT_DIR/04torch_upload.py" 
CHECK_EXIST_SCRIPT="$SCRIPT_DIR/../special_care/check_whl_exist.py" 

# =============================== 构建环境相关
export PIP_CACHE_DIR="$HOME/.cache/pip/wheels_${PKG_NAME}_uv_$BUILD_FOR_VERSION"
BUILD_TMPDIR="$HOME/.mytmp/${PKG_NAME}_uv_$BUILD_FOR_VERSION"
VENV_NAME="build_${PKG_NAME}_uv_$BUILD_FOR_VERSION"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
WHEEL_CACHE_DIR="$HOME/.mywheels/${PKG_NAME}_uv_$BUILD_FOR_VERSION"
DIST_DIR="$HOME/pyenvs/store"

mkdir -p "$BUILD_TMPDIR" "$WHEEL_CACHE_DIR" "$DIST_DIR"

export WHEEL_CACHE_DIR_PY="$WHEEL_CACHE_DIR"
export TMPDIR="$BUILD_TMPDIR"


# =============================== 加载环境变量
source "$SCRIPT_DIR/../env_common.sh"

# 打印确认
echo "LD_LIBRARY_PATH = $LD_LIBRARY_PATH"
echo "LLVM_CONFIG = $LLVM_CONFIG"

export USE_CUDA=0
export USE_DISTRIBUTED=0
export USE_MKLDNN=0

# =============================== 创建可复用的虚拟环境
## 清理旧虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo "🧹 Removing old virtualenv at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

## 创建或还原虚拟环境
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

## 设置环境变量
export PYTHONPATH="$VENV_DIR/lib/python$BUILD_FOR_VERSION/site-packages"

# =============================== 执行逐版本构建
for version in "${TO_BUILD_VERSIONS[@]}"; do

    echo "🔨 Building wheel for $PKG_NAME==$version ..."

    ## 查看是否有 whl 包
    set +e 
    python3 $CHECK_EXIST_SCRIPT "$PKG_NAME==$version"
    if [ $? -eq 0 ]; then
        echo "已有 wheel $PKG_NAME==$version"
        continue
    else
        echo "需要构建"
    fi
    set -e

    ## 这个环境变量决定 whl 包名里面的版本
    export PYTORCH_BUILD_VERSION=$version

    ## 比较 2.7.0, 低版本需要开启这个环境变量
    if [ "$(printf '%s\n%s\n' "$version" "2.7.0" | sort -V | head -n1)" = "$version" ] && [ "$version" != "2.7.0" ]; then
        export USE_SYSTEM_SLEEF=ON
        export CMAKE_POLICY_VERSION_MINIMUM=3.5
    else
        unset USE_SYSTEM_SLEEF  # 或者保持默认
    fi

    echo "Building version $version (USE_SYSTEM_SLEEF=${USE_SYSTEM_SLEEF:-OFF})"

    ## 检查源码目录是否存在
    if [[ ! -d "$SOURCE_TARGET_DIR" ]]; then
        echo "❌ ERROR: 源码目录不存在: $SOURCE_TARGET_DIR"
        exit 1
    fi

    cd "$SOURCE_TARGET_DIR" || { echo "❌ ERROR: 无法进入目录 $SOURCE_TARGET_DIR"; exit 1; }

    ## 清理旧的 build 目录
    if [[ -d build ]]; then
        echo "🧹 清理旧的 build 目录..."
        rm -rf build || { echo "❌ ERROR: 无法删除 build 目录"; exit 1; }
    fi

    echo "🧹 清理未跟踪的文件和目录..."
    git clean -fdx || { echo "❌ ERROR: git clean 失败"; exit 1; }


    ## 切换到指定版本
    echo "📌 切换到 PyTorch v$PYTORCH_BUILD_VERSION ..."
    if ! git checkout -f "v$PYTORCH_BUILD_VERSION"; then
        echo "❌ ERROR: 切换到版本 v$PYTORCH_BUILD_VERSION 失败"
        exit 1
    fi

    ## 更新子模块
    echo "🔄 更新子模块 ..."
    if ! git submodule update --init --recursive; then
        echo "❌ ERROR: 子模块更新失败，可重复执行脚本，或手动执行git submodule update --init --recursive"
        exit 1
    fi

    echo "✅ 初始化完成，准备开始构建 PyTorch v$PYTORCH_BUILD_VERSION"


    cd $SCRIPT_DIR || { echo "❌ ERROR: 无法进入目录 $SCRIPT_DIR"; exit 1; }

    rm -rf "$VENV_DIR" || echo "⚠️ Failed Remove $VENV_DIR"

    ## 复制虚拟环境
    cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"

    ## 再次激活虚拟环境，刷新
    source "$VENV_DIR/bin/activate"

    ## 存在，则进入该目录
    if [ -d "$SOURCE_TARGET_DIR" ]; then
        cd "$SOURCE_TARGET_DIR"
    else
        echo "Error no torch project dir !"
        exit 1
    fi

    ## 安装构建依赖
    pip install -r requirements.txt

    sleep 4

    rm -rf "$WHEEL_CACHE_DIR" || echo "⚠️ Failed Remove $WHEEL_CACHE_DIR"

    ## 执行构建，不创建隔离的虚拟环境
    pip wheel . --verbose --wheel-dir="$WHEEL_CACHE_DIR" --no-build-isolation

    ## 执行上传流程
    echo "📦 上传构建的 wheel"
    if [ -f "$UPLOAD_SCRIPT" ]; then
        echo "🚀 Running upload_built_wheels.py for $PACKAGE_NAME"
        if ! python "$UPLOAD_SCRIPT"; then
            echo "⚠️ Failed to run upload_built_wheels.py for $PACKAGE_NAME"
        fi
    else
        echo "⚠️ upload_built_wheels.py not found in $SCRIPT_DIR"
    fi

    ## 注销环境
    deactivate

    sleep 3

    echo "🗑️  Removing $VENV_DIR"
    rm -rf "$PIP_CACHE_DIR" || echo "❌ Failed to remove $PIP_CACHE_DIR"
    rm -rf "$BUILD_TMPDIR" || echo "❌ Failed to remove $BUILD_TMPDIR"
    rm -rf "$VENV_DIR" || echo "⚠️ Failed Remove $VENV_DIR"
    rm -rf "$WHEEL_CACHE_DIR" || echo "⚠️ Failed Remove $WHEEL_CACHE_DIR"

done

echo "✅ Done All"
