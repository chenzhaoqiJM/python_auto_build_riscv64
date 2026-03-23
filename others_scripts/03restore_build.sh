#!/bin/bash
set -e
# 当前脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPLOAD_SCRIPT="$SCRIPT_DIR/00upload_with_repair.py"

# 可配置字段
BUILD_TMPDIR="$HOME/mytmpauto_quick"
VENV_NAME="tmpbuild_quick"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
DIST_DIR="$HOME/pyenvs/store"
WHEEL_CACHE_DIR="$HOME/wheels/quick"

PACKAGE_LIST_FILE="packages_to_delete.txt"
SKIP_LIST_FILE="skip_pkgs.txt"

# 编译相关参数
export CMAKE_ARGS="-DCMAKE_CXX_FLAGS='-march=rv64gcv' -DCMAKE_C_FLAGS='-march=rv64gcv'"
export LLVM_CONFIG=/usr/bin/llvm-config-15
export TMPDIR="$BUILD_TMPDIR"
export PYODIDE=1

# 创建必要目录
mkdir -p "$BUILD_TMPDIR" "$WHEEL_CACHE_DIR" "$DIST_DIR"

# 清理旧虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo "🧹 Removing old virtualenv at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

# 检查缓存虚拟环境
if [ -d "$DIST_DIR/$VENV_NAME" ]; then
    echo "✅ Cached virtualenv ready at $DIST_DIR"
else
    echo "📦 Creating new virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"

    source "$VENV_DIR/bin/activate"
    echo "⬆️  Installing pip & build tools..."
    pip install --upgrade pip
    pip install --verbose setuptools wheel build twine auditwheel numpy maturin scipy

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

    echo "Removing tmp..........."
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
fi

# 检查 packages_all.txt 是否存在
if [ ! -f "$SCRIPT_DIR/$PACKAGE_LIST_FILE" ]; then
    echo "⚠️ $PACKAGE_LIST_FILE not found. Exiting."
    exit 1
fi

# 检查 skip_pkgs.txt 是否存在
if [ -f "$SCRIPT_DIR/$SKIP_LIST_FILE" ]; then
    skip_pkgs=$(<"$SCRIPT_DIR/$SKIP_LIST_FILE")  # 读取跳过的包名
else
    skip_pkgs=()  # 如果没有 skip_pkgs.txt，则不跳过任何包
fi

# 读取包名并遍历
while IFS= read -r package; do
    # 检查当前包是否在 skip_pkgs.txt 中
    if echo "$skip_pkgs" | grep -qw "$package"; then
        echo "⏭️ Skipping package: $package"
        continue  # 跳过当前包
    fi

    echo "🔁 Processing package: $package"

    # 获取虚拟环境
    echo "📂 Copying venv..."
    cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    # 安装工具和指定版本的包
    echo "🔨 Building wheel for $package"
    
    rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

    if ! pip wheel --verbose --wheel-dir="$WHEEL_CACHE_DIR" "$package"; then
        echo "⚠️ Failed to install $package" >> "$SCRIPT_DIR/failed.log"

        deactivate
        sleep 2
        echo "Removing tmp..........."
        rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
        rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
        continue  # 如果安装失败，跳过当前包并继续处理下一个包
    fi

    # 执行上传脚本
    if [ -f "$UPLOAD_SCRIPT" ]; then
        echo "🚀 Running upload_built_wheels.py for $package"
        if ! python "$UPLOAD_SCRIPT"; then
            echo "⚠️ Failed to run upload_built_wheels.py for $package" >> "$SCRIPT_DIR/failed.log"
        fi
    else
        echo "⚠️ upload_built_wheels.py not found in $SCRIPT_DIR" >> "$SCRIPT_DIR/failed.log"
    fi

    deactivate
    sleep 2

    echo "✅ Done for $package"

    echo "Removing tmp..........."
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
    echo "---------------------------------------------"

done < "$SCRIPT_DIR/$PACKAGE_LIST_FILE"

echo "🎉 All done!"
