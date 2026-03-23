#!/bin/bash
set -e

# 检查是否提供了至少一个包名
if [ $# -lt 1 ]; then
    echo "❗ Usage: $0 <package_name1> [package_name2] [...]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 加载公共函数
source "$SCRIPT_DIR/../common_func.sh"

# 调用检查函数
check_build_version

echo "开始构建 Python $BUILD_FOR_VERSION ..."
# 下面继续构建逻辑

UPLOAD_SCRIPT="$SCRIPT_DIR/../common_py/00upload_with_repair.py"
FAILED_LIST="$SCRIPT_DIR/failed_s.log"
SPECIAL_BUILDER_SCRIPT="$SCRIPT_DIR/../special_care/special_builder.py"
NO_DEPS_SCRIPT="$SCRIPT_DIR/../common_py/check_no_deps.py"

# 可配置字段
BUILD_TMPDIR="$HOME/mytmpversion_single"
VENV_NAME="tmpbuild_version_single"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
DIST_DIR="$HOME/pyenvs/store"
WHEEL_CACHE_DIR="$HOME/wheels/version_single"

mkdir -p "$BUILD_TMPDIR" "$WHEEL_CACHE_DIR" "$DIST_DIR"

export TMPDIR="$BUILD_TMPDIR"
export PYTHONPATH="$VENV_DIR/lib/python$BUILD_FOR_VERSION/site-packages"
echo "&&&- set PYTHONPATH to: $PYTHONPATH"

# 动态环境变量
ENV_LOADER_SH="$SCRIPT_DIR/../dynamic_env/env_loader.sh"

# 加载公共环境变量
source "$SCRIPT_DIR/../env_common.sh"

# 打印确认
echo "LD_LIBRARY_PATH = $LD_LIBRARY_PATH"
echo "LLVM_CONFIG = $LLVM_CONFIG"

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
    python3 -m venv --copies "$VENV_DIR"

    source "$VENV_DIR/bin/activate"
    echo "⬆️  Installing pip & build tools..."
    pip install --upgrade pip
    pip install --upgrade --verbose setuptools wheel build twine auditwheel 
    pip install --verbose --prefer-binary numpy maturin scipy pyelftools pybind11 Cython

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


for PACKAGE in "$@"; do
    echo "🔁 Processing package: $PACKAGE"
    echo "🧹 Cleaning tmp build and venv..."
    command -v deactivate &>/dev/null && deactivate || true
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
    rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

    # 执行 00get_pkg_version.py 获取版本列表
    echo "🔄 Running 00get_pkg_version.py for $PACKAGE..."
    if ! python3 "$SCRIPT_DIR/00get_pkg_version.py" "$PACKAGE"; then
        echo "❌ Failed to get versions for $PACKAGE"
        continue
    fi

    VERSION_FILE="$SCRIPT_DIR/${PACKAGE}.log"
    if [ ! -f "$VERSION_FILE" ]; then
        echo "⚠️ Version file for $PACKAGE not found. Skipping."
        continue
    fi

    while IFS= read -r PACKAGE_VERSION_NAME || [[ -n "$PACKAGE_VERSION_NAME" ]]; do
        PACKAGE_VERSION_NAME=$(echo "$PACKAGE_VERSION_NAME" | xargs)
        if [ -z "$PACKAGE_VERSION_NAME" ]; then
            continue
        fi

        PACKAGE_WITH_VERSION="$PACKAGE==$PACKAGE_VERSION_NAME"
        echo "🔁 Processing $PACKAGE_WITH_VERSION"

        # 加载动态环境变量
        source "$ENV_LOADER_SH" "$PACKAGE_WITH_VERSION"
        load_env
        echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"

        echo "🧹 Cleaning tmp build and venv..."
        command -v deactivate &>/dev/null && deactivate || true
        rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
        rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
        rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

        echo "📂 Copying venv..."
        cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"
        source "$VENV_DIR/bin/activate"

        echo "🔨 Building wheel for $PACKAGE_WITH_VERSION ..."

        build_with_special_python() {
            echo "⚙️  Checking for special build path for $PACKAGE_WITH_VERSION"

            python3 "$SPECIAL_BUILDER_SCRIPT" "$PACKAGE_WITH_VERSION" "$WHEEL_CACHE_DIR"
            exit_code=$?
            
            if [[ $exit_code -eq 0 ]]; then
                echo "✅ Special build complete for $PACKAGE_WITH_VERSION"
                return 0
            elif [[ $exit_code -eq 100 ]]; then
                echo "ℹ️  $PACKAGE_WITH_VERSION not handled specially, fallback to generic build"
                return 100
            else
                echo "❌ Special builder failed: $PACKAGE_WITH_VERSION"
                echo "$PACKAGE_WITH_VERSION" >> "$FAILED_LIST"
                deactivate || true
                return 1
            fi
        }

        build_generic_package() {

            NO_DEPS=$(python3 "$NO_DEPS_SCRIPT" "$PACKAGE_NAME")
            echo "⚙️  Extra pip flags: $NO_DEPS"

            if ! pip wheel --verbose $NO_DEPS --wheel-dir="$WHEEL_CACHE_DIR" "$PACKAGE_WITH_VERSION"; then
                echo "❌ Failed: $PACKAGE_WITH_VERSION"
                echo "$PACKAGE_WITH_VERSION" >> "$FAILED_LIST"
                deactivate || true
                return 1
            fi
            return 0
        }

        # func select ---------------------------------------------
        set +e  # 临时关闭 set -e

        build_with_special_python
        exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            echo "📦 $PACKAGE_WITH_VERSION handled specially"
        elif [[ $exit_code -eq 100 ]]; then
            echo "build_generic_package starting........"
            build_generic_package
            build_result=$?

            if [[ $build_result -ne 0 ]]; then
                set -e
                unload_env
                continue  
            fi
        else
            set -e
            unload_env
            continue
        fi

        set -e
        # func select ---------------------------------------------

        if [ -f "$UPLOAD_SCRIPT" ]; then
            echo "🚀 Running upload script for $PACKAGE_WITH_VERSION"
            python "$UPLOAD_SCRIPT"
        else
            echo "⚠️  Upload script not found: $UPLOAD_SCRIPT"
        fi

        deactivate || true
        sleep 2
        unload_env
        echo "✅ Done for $PACKAGE_WITH_VERSION"
        echo "-------------------------------------------------------------------"
    done < "$VERSION_FILE"

    rm -f "$VERSION_FILE"
    echo "🗑️ Removed version file for $PACKAGE: $VERSION_FILE"
    echo "✅ All done for $PACKAGE!"
    echo "============================================="
done
