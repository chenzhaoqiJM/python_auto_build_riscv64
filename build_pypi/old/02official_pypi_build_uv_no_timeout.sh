#!/bin/bash
set -e

# 当前脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 加载公共函数
source "$SCRIPT_DIR/../common_func.sh"

# 调用检查函数
check_build_version

ensure_uv
uv python install $BUILD_FOR_VERSION

echo "开始构建 Python $BUILD_FOR_VERSION ..."
# 下面继续构建逻辑

# 可配置字段
export PIP_CACHE_DIR="$HOME/.cache/pip/wheels_auto_uv_$BUILD_FOR_VERSION"
export WHEELS_REPAIR_DIR="$HOME/.mywheel_repair/auto_uv_$BUILD_FOR_VERSION"
BUILD_TMPDIR="$HOME/.mytmp/auto_uv_$BUILD_FOR_VERSION"
VENV_NAME="tmpbuild_auto_uv_$BUILD_FOR_VERSION"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
DIST_DIR="$HOME/pyenvs/store"
WHEEL_CACHE_DIR="$HOME/.mywheels/auto_uv_$BUILD_FOR_VERSION"
PACKAGE_LIST="$SCRIPT_DIR/top_pypi_package_names.txt"
FAILED_LIST="$SCRIPT_DIR/failed_$BUILD_FOR_VERSION.log"
UPLOAD_SCRIPT="$SCRIPT_DIR/../common_py/00upload_with_repair.py"
SKIP_LIST="$SCRIPT_DIR/../common_py/skip_pkgs.txt"
SPECIAL_BUILDER_SCRIPT="$SCRIPT_DIR/../special_care/special_builder.py"
NO_DEPS_SCRIPT="$SCRIPT_DIR/../common_py/check_no_deps.py"
FETCH_VERSION_SCRIPT="$SCRIPT_DIR/../common_py/02get_latest_version.py"

UPDATE_LIBS_SH="$SCRIPT_DIR/../update_libs.sh"


# 创建必要目录
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


if [ ! -f "$PACKAGE_LIST" ]; then
    echo "❌ File not found: $PACKAGE_LIST"
    exit 1
fi

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
    uv venv "$VENV_DIR" --python=$BUILD_FOR_VERSION

    source "$VENV_DIR/bin/activate"
    echo "⬆️  Installing pip & build tools..."
    uv pip install --upgrade pip
    deactivate
    source "$VENV_DIR/bin/activate"
    pip install --upgrade --verbose setuptools wheel build twine auditwheel
    pip install --verbose --prefer-binary numpy maturin scipy pyelftools pybind11 Cython beautifulsoup4 lxml

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


# 无限循环处理包
while true; do
    echo "⏳ Starting new round at $(date)"

    # 清空失败记录
    > "$FAILED_LIST"

    while IFS= read -r PACKAGE_NAME || [[ -n "$PACKAGE_NAME" ]]; do
        PACKAGE_NAME=$(echo "$PACKAGE_NAME" | xargs)
        if [ -z "$PACKAGE_NAME" ]; then
            continue
        fi

        PACKAGE_NAME=$(python3 "$FETCH_VERSION_SCRIPT" "$PACKAGE_NAME")

        # if [ -f "$SKIP_LIST" ] && grep -Fxq "$PACKAGE_NAME" "$SKIP_LIST"; then
        #     echo "⏭️  Skipping $PACKAGE_NAME (in skip list)"
        #     echo "---------------------------------------------"
        #     continue
        # fi

        if [ -f "$SKIP_LIST" ]; then
            while read -r pattern; do
                case "$PACKAGE_NAME" in
                    $pattern)
                        echo "⏭️  Skipping $PACKAGE_NAME (in skip list)"
                        echo "---------------------------------------------"
                        continue 2
                        ;;
                esac
            done < "$SKIP_LIST"
        fi

        echo "🔁 Processing $PACKAGE_NAME"

        echo "Removing tmp..........."
        command -v deactivate &>/dev/null && deactivate || true
        rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
        rm -rf "$BUILD_TMPDIR"/* || echo "❌ Failed to remove build tmp"
        rm -rf "$WHEEL_CACHE_DIR"/* || echo "❌ Failed to clean wheel cache"

        echo "📂 Copying venv..."
        cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"
        source "$VENV_DIR/bin/activate"

        # 加载动态环境变量
        source "$ENV_LOADER_SH" "$PACKAGE_NAME"
        load_env
        echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"

        # 特殊构建路径
        build_with_special_python() {
            echo "⚙️  Checking for special build path for $PACKAGE_NAME"

            python3 "$SPECIAL_BUILDER_SCRIPT" "$PACKAGE_NAME" "$WHEEL_CACHE_DIR"
            exit_code=$?

            if [[ $exit_code -eq 0 ]]; then
                echo "✅ Special build complete for $PACKAGE_NAME"
                return 0
            elif [[ $exit_code -eq 100 ]]; then
                echo "ℹ️  $PACKAGE_NAME not handled specially, fallback to generic build"
                return 100
            else
                echo "❌ Special builder failed: $PACKAGE_NAME"
                echo "$PACKAGE_NAME" >> "$FAILED_LIST"
                deactivate || true
                return 1
            fi
        }

        build_generic_package() {

            NO_DEPS=$(python3 "$NO_DEPS_SCRIPT" "$PACKAGE_NAME")
            echo "⚙️  Extra pip flags: $NO_DEPS"

            if ! pip wheel --verbose $NO_DEPS --wheel-dir="$WHEEL_CACHE_DIR" "$PACKAGE_NAME"; then
                echo "❌ Failed: $PACKAGE_NAME"
                echo "$PACKAGE_NAME" >> "$FAILED_LIST"
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
            echo "📦 $PACKAGE_NAME handled specially"
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

        # 调用上传脚本（如果存在）
        if [ -f "$UPLOAD_SCRIPT" ]; then
            echo "🚀 Running upload script for $PACKAGE_NAME"
            python "$UPLOAD_SCRIPT"
        else
            echo "⚠️  Upload script not found: $UPLOAD_SCRIPT"
        fi

        deactivate || true
        sleep 2
        unload_env
        echo "✅ Done for $PACKAGE_NAME"
        echo "---------------------------------------------"
    done < "$PACKAGE_LIST"

    echo "🎉 All done!"
    if [ -s "$FAILED_LIST" ]; then
        echo "❗ Some packages failed:"
        cat "$FAILED_LIST"
    else
        echo "✅ All packages built and processed successfully!"
    fi

    # 更新第三方库
    echo "🔄 Updating third-party libraries..."
    bash "$UPDATE_LIBS_SH" || echo "⚠️ Failed to update libs"

    echo "🕒 Sleeping for 4 hours..."
    sleep 14400
done