#!/bin/bash
set -e

# 当前脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载公共函数
source "$SCRIPT_DIR/../common_func.sh"

# 调用检查函数
check_build_version

ensure_uv
uv python install "$BUILD_FOR_VERSION"

echo "开始构建 Python $BUILD_FOR_VERSION ..."
# 下面继续构建逻辑

# 可配置字段
export PIP_CACHE_DIR="$HOME/.cache/pip/wheels_hp_uv_$BUILD_FOR_VERSION"
export UV_CACHE_DIR="$HOME/.cache/uv_hp_$BUILD_FOR_VERSION"
export XDG_CACHE_HOME="$HOME/.cache_hp_uv_$BUILD_FOR_VERSION"
export WHEELS_REPAIR_DIR="$HOME/.mywheel_repair/hp_uv_$BUILD_FOR_VERSION"
BUILD_TMPDIR="$HOME/.mytmp/hp_uv_$BUILD_FOR_VERSION"
export CARGO_HOME="$BUILD_TMPDIR/cargo-home"
PIP_BUILD_TRACKER_DIR="$BUILD_TMPDIR/pip-build-tracker"
VENV_NAME="hp_uv_$BUILD_FOR_VERSION"
VENV_DIR="$HOME/pyenvs/$VENV_NAME"
DIST_DIR="$HOME/pyenvs/store"
WHEEL_CACHE_DIR="$HOME/.mywheels/hp_uv_$BUILD_FOR_VERSION"
export WHEEL_CACHE_DIR_PY="$WHEEL_CACHE_DIR"
PACKAGE_LIST="$SCRIPT_DIR/hp_pkgs.txt"
FAILED_LIST="$SCRIPT_DIR/failed_hp_$BUILD_FOR_VERSION.log"

UPLOAD_SCRIPT="$SCRIPT_DIR/../common_py/00upload_with_repair.py"
SPECIAL_BUILDER_SCRIPT="$SCRIPT_DIR/../special_care/special_builder.py"
DEPENDENCY_PLAN_SCRIPT="$SCRIPT_DIR/../common_py/dependency_plan.py"
UPDATE_LIBS_SH="$SCRIPT_DIR/../update_libs.sh"

# 单包构建超时（默认24小时）
BUILD_TIMEOUT_SECONDS=$((24 * 60 * 60))
UPLOAD_TIMEOUT_SECONDS=${UPLOAD_TIMEOUT_SECONDS:-3600}

if ! command -v timeout >/dev/null 2>&1; then
    echo "❌ 'timeout' command not found. Please install coreutils."
    exit 1
fi

record_failed() {
    local package_name="$1"

    if grep -Fqx -- "$package_name" "$FAILED_LIST" 2>/dev/null; then
        return 0
    fi
    if ! echo "$package_name" >> "$FAILED_LIST"; then
        echo "⚠️ Failed to write failed package to $FAILED_LIST: $package_name"
    fi
}

run_upload_script() {
    local package_name="$1"

    if [ -f "$UPLOAD_SCRIPT" ]; then
        echo "🚀 Running upload script for $package_name"
        if ! timeout --foreground --kill-after=60s "${UPLOAD_TIMEOUT_SECONDS}s" python "$UPLOAD_SCRIPT"; then
            echo "⚠️ Upload script failed or timed out after ${UPLOAD_TIMEOUT_SECONDS}s for $package_name"
            record_failed "$package_name"
            return 1
        fi
    else
        echo "⚠️  Upload script not found: $UPLOAD_SCRIPT"
        return 1
    fi
}

# 创建必要目录
mkdir -p "$BUILD_TMPDIR" "$PIP_BUILD_TRACKER_DIR" "$WHEEL_CACHE_DIR" "$DIST_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME" "$CARGO_HOME"

# 编译相关参数
export TMPDIR="$BUILD_TMPDIR"
export PIP_BUILD_TRACKER="$PIP_BUILD_TRACKER_DIR"
export PYTHONPATH="$VENV_DIR/lib/python$BUILD_FOR_VERSION/site-packages"
echo "&&&- set PYTHONPATH to: $PYTHONPATH"
echo "&&&- set CARGO_HOME to: $CARGO_HOME"

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
    uv venv "$VENV_DIR" --python="$BUILD_FOR_VERSION"

    source "$VENV_DIR/bin/activate"
    echo "⬆️  Installing pip & build tools..."
    uv pip install --upgrade pip
    deactivate
    source "$VENV_DIR/bin/activate"
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
            rm -rf "${BUILD_TMPDIR:?}"/* || echo "❌ Failed to remove build tmp"
            mkdir -p "$BUILD_TMPDIR" "$PIP_BUILD_TRACKER_DIR" "$WHEEL_CACHE_DIR" "$DIST_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME" "$CARGO_HOME"
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
    rm -rf "${BUILD_TMPDIR:?}"/* || echo "❌ Failed to remove build tmp"
    mkdir -p "$BUILD_TMPDIR" "$PIP_BUILD_TRACKER_DIR" "$WHEEL_CACHE_DIR" "$DIST_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME" "$CARGO_HOME"
fi

RESOLVER_PYTHON="$DIST_DIR/$VENV_NAME/bin/python"

cleanup_package_workspace() {
    if command -v deactivate &>/dev/null; then
        deactivate || true
    fi
    rm -rf "$VENV_DIR" || echo "❌ Failed to remove venv"
    rm -rf "${BUILD_TMPDIR:?}"/* || echo "❌ Failed to remove build tmp"
    rm -rf "${WHEEL_CACHE_DIR:?}"/* || echo "❌ Failed to clean wheel cache"
    mkdir -p "$BUILD_TMPDIR" "$PIP_BUILD_TRACKER_DIR" "$WHEEL_CACHE_DIR" "$DIST_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME" "$CARGO_HOME"
}

build_with_special_python() {
    echo "⚙️  Checking for special build path for $PACKAGE_NAME"

    timeout --foreground --kill-after=60s "${BUILD_TIMEOUT_SECONDS}s" \
        python3 "$SPECIAL_BUILDER_SCRIPT" "$PACKAGE_NAME" "$WHEEL_CACHE_DIR"
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        echo "✅ Special build complete for $PACKAGE_NAME"
        return 0
    elif [[ $exit_code -eq 101 ]]; then
        return 101
    elif [[ $exit_code -eq 100 ]]; then
        echo "ℹ️  $PACKAGE_NAME not handled specially, fallback to generic build"
        return 100
    elif [[ $exit_code -eq 124 ]]; then
        echo "⏰ Timeout (>24h), skip package: $PACKAGE_NAME"
        return 124
    fi

    echo "❌ Special builder failed: $PACKAGE_NAME"
    return 1
}

build_generic_package() {
    # Runtime dependencies are resolved and built as independent queue items.
    # This keeps every dependency under its own dynamic_env/special_care setup.
    find "$CARGO_HOME" -type f \( -name '.package-cache' -o -name '*.lock' \) -delete 2>/dev/null || true

    timeout --foreground --kill-after=60s "${BUILD_TIMEOUT_SECONDS}s" \
        pip wheel --verbose --no-deps --no-binary "${PACKAGE_NAME%%==*}" \
        --wheel-dir="$WHEEL_CACHE_DIR" "$PACKAGE_NAME"
    local build_exit_code=$?

    if [[ $build_exit_code -eq 124 ]]; then
        echo "⏰ Timeout (>24h), skip package: $PACKAGE_NAME"
        return 124
    elif [[ $build_exit_code -ne 0 ]]; then
        echo "❌ Failed: $PACKAGE_NAME"
        return 1
    fi
    return 0
}

process_package() {
    local package_spec="$1"
    local exit_code build_result upload_result
    PACKAGE_NAME="$package_spec"

    echo "🔁 Processing $PACKAGE_NAME"

    # Use the cached target interpreter for this read-only probe. This avoids
    # copying a build environment for packages that official PyPI already serves.
    if timeout --foreground --kill-after=30s 600s \
        env -u PYTHONPATH "$RESOLVER_PYTHON" "$DEPENDENCY_PLAN_SCRIPT" \
        official-wheel "$PACKAGE_NAME"; then
        echo "⏭️  Skipping $PACKAGE_NAME (official PyPI has an installable wheel)"
        return 0
    fi

    echo "🧹 Cleaning tmp build and venv..."
    cleanup_package_workspace

    echo "📂 Copying venv..."
    cp -r "$DIST_DIR/$VENV_NAME" "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    source "$ENV_LOADER_SH" "$PACKAGE_NAME"
    load_env
    echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
    echo "🔨 Building wheel for $PACKAGE_NAME ..."

    set +e
    build_with_special_python
    exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        echo "📦 $PACKAGE_NAME handled specially"
    elif [[ $exit_code -eq 101 ]]; then
        echo "⏭️  Skipping $PACKAGE_NAME (target platform wheel already exists)"
        set -e
        deactivate || true
        unload_env
        return 0
    elif [[ $exit_code -eq 100 ]]; then
        echo "build_generic_package starting........"
        build_generic_package
        build_result=$?
        if [[ $build_result -ne 0 ]]; then
            set -e
            deactivate || true
            unload_env
            return "$build_result"
        fi
    else
        set -e
        deactivate || true
        unload_env
        return "$exit_code"
    fi
    set -e

    export THE_BUILD_PACKAGE_NAME="${PACKAGE_NAME%%==*}"
    export UPLOAD_CURRENT_TARGET_ONLY=1
    upload_result=0
    run_upload_script "$PACKAGE_NAME" || upload_result=$?

    deactivate || true
    sleep 2
    unload_env

    if [[ $upload_result -ne 0 ]]; then
        return "$upload_result"
    fi
    echo "✅ Done for $PACKAGE_NAME"
    echo "-------------------------------------------------------------------"
    return 0
}

# 无限循环处理包
while true; do
    echo "⏳ Starting new round at $(date)"
    if ! : > "$FAILED_LIST"; then
        echo "⚠️ Failed to clear failed list: $FAILED_LIST"
    fi

    if [ ! -f "$PACKAGE_LIST" ]; then
        echo "❌ File not found: $PACKAGE_LIST"
        exit 1
    fi

    declare -A PACKAGE_RESULTS=()

    while IFS= read -r REQUESTED_PACKAGE || [[ -n "$REQUESTED_PACKAGE" ]]; do
        REQUESTED_PACKAGE=$(echo "$REQUESTED_PACKAGE" | xargs)
        if [ -z "$REQUESTED_PACKAGE" ] || [[ "$REQUESTED_PACKAGE" == \#* ]]; then
            continue
        fi

        echo "🔎 Resolving dependency closure for $REQUESTED_PACKAGE"
        PLAN_OUTPUT=""
        if ! PLAN_OUTPUT=$(env -u PYTHONPATH "$RESOLVER_PYTHON" \
            "$DEPENDENCY_PLAN_SCRIPT" resolve "$REQUESTED_PACKAGE"); then
            echo "❌ Failed to resolve dependency closure: $REQUESTED_PACKAGE"
            record_failed "$REQUESTED_PACKAGE"
            continue
        fi
        if [[ -z "$PLAN_OUTPUT" ]]; then
            echo "❌ Empty dependency plan: $REQUESTED_PACKAGE"
            record_failed "$REQUESTED_PACKAGE"
            continue
        fi

        mapfile -t BUILD_PLAN <<< "$PLAN_OUTPUT"
        ROOT_FAILED=0
        LAST_PLAN_INDEX=$((${#BUILD_PLAN[@]} - 1))

        for PLAN_INDEX in "${!BUILD_PLAN[@]}"; do
            PACKAGE_NAME="${BUILD_PLAN[$PLAN_INDEX]}"
            if [[ -z "$PACKAGE_NAME" ]]; then
                continue
            fi

            if [[ $PLAN_INDEX -eq $LAST_PLAN_INDEX && $ROOT_FAILED -ne 0 ]]; then
                echo "⏭️  Not completing $REQUESTED_PACKAGE because a dependency failed"
                break
            fi

            if [[ "${PACKAGE_RESULTS[$PACKAGE_NAME]:-}" == "success" ]]; then
                echo "⏭️  Already satisfied in this round: $PACKAGE_NAME"
                continue
            elif [[ "${PACKAGE_RESULTS[$PACKAGE_NAME]:-}" == "failed" ]]; then
                echo "❌ Dependency already failed in this round: $PACKAGE_NAME"
                ROOT_FAILED=1
                continue
            fi

            if process_package "$PACKAGE_NAME"; then
                PACKAGE_RESULTS["$PACKAGE_NAME"]="success"
            else
                PACKAGE_RESULTS["$PACKAGE_NAME"]="failed"
                ROOT_FAILED=1
                record_failed "$PACKAGE_NAME"
            fi
        done

        if [[ $ROOT_FAILED -ne 0 ]]; then
            record_failed "$REQUESTED_PACKAGE"
        else
            echo "✅ Dependency closure complete for $REQUESTED_PACKAGE"
        fi
    done < "$PACKAGE_LIST"

    echo "🎉 Round finished at $(date)"
    if [ -s "$FAILED_LIST" ]; then
        echo "❗ Some packages failed:"
        cat "$FAILED_LIST" || echo "⚠️ Failed to read failed list: $FAILED_LIST"
    else
        echo "✅ All packages installed successfully!"
    fi

    # 更新第三方库
    echo "🔄 Updating third-party libraries..."
    (
        flock 200
        bash "$UPDATE_LIBS_SH"
    ) 200>"$HOME/.python_auto_build_update_libs.lock" || echo "⚠️ Failed to update libs"

    echo "🕒 Sleeping for 2 hours..."
    sleep 7200
done
