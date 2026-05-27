#!/bin/bash
set -e

# RealSense pyrealsense2 wheel build script.
# Usage:
#   BUILD_FOR_VERSION=3.14 ./05realsense.sh <librealsense_git_url> <version>
# Example:
#   BUILD_FOR_VERSION=3.14 ./05realsense.sh https://github.com/IntelRealSense/librealsense.git 2.57.7

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=/dev/null
source "$ROOT_DIR/common_func.sh"
# shellcheck source=/dev/null
source "$ROOT_DIR/env_common.sh"

detect_auditwheel_plat() {
    local arch glibc_ver glibc_maj glibc_min ldd_first_line

    arch="$(uname -m)"
    if command -v getconf >/dev/null 2>&1; then
        glibc_ver="$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}')"
    fi

    if [ -z "${glibc_ver:-}" ] && command -v ldd >/dev/null 2>&1; then
        ldd_first_line="$(ldd --version 2>&1 | head -n 1)"
        glibc_ver="$(printf '%s\n' "$ldd_first_line" | grep -oE '[0-9]+\.[0-9]+' | tail -n 1)"
    fi

    if [ -z "${glibc_ver:-}" ]; then
        echo "❌ 无法通过 getconf/ldd 检测 glibc 版本。"
        exit 1
    fi

    glibc_maj="${glibc_ver%%.*}"
    glibc_min="${glibc_ver#*.}"
    glibc_min="${glibc_min%%.*}"
    printf 'manylinux_%s_%s_%s\n' "$glibc_maj" "$glibc_min" "$arch"
}

check_build_version
ensure_uv
uv python install "$BUILD_FOR_VERSION"

if [ $# -lt 2 ]; then
    echo "❌ 用法: BUILD_FOR_VERSION=3.14 $0 <librealsense_git_url> <version>"
    echo "示例: BUILD_FOR_VERSION=3.14 $0 https://github.com/IntelRealSense/librealsense.git 2.57.7"
    exit 1
fi

REPO_URL="$1"
REALSENSE_VERSION="$2"
REPO_NAME="$(basename "$REPO_URL" .git)"
SRC_PARENT="${REALSENSE_SRC_PARENT:-$HOME}"
SRC_DIR="${REALSENSE_SRC_DIR:-$SRC_PARENT/$REPO_NAME}"
PY_VER_NODOT="${BUILD_FOR_VERSION//./}"
VENV_DIR="${REALSENSE_VENV_DIR:-$HOME/pyenvs/realsense_build_${PY_VER_NODOT}}"
BUILD_DIR="$SRC_DIR/build"
FIX_WHL_SCRIPT="$ROOT_DIR/common_py/fix_whl/fix_whl_rpath.py"
AUDITWHEEL_PLAT_DEF="$(detect_auditwheel_plat)"
export AUDITWHEEL_PLAT_DEF

export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$HOME/.cache/pip/realsense_${PY_VER_NODOT}}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$HOME/.cache/uv_realsense_${PY_VER_NODOT}}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache_realsense_${PY_VER_NODOT}}"
export TMPDIR="${TMPDIR:-$HOME/.mytmp/realsense_${PY_VER_NODOT}}"
export PIP_BUILD_TRACKER="${PIP_BUILD_TRACKER:-$TMPDIR/pip-build-tracker}"

mkdir -p "$SRC_PARENT" "$PIP_CACHE_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME" "$TMPDIR" "$PIP_BUILD_TRACKER"

echo "=============================="
echo "🔧 RealSense wheel build"
echo "Repo    : $REPO_URL"
echo "Version : $REALSENSE_VERSION"
echo "Python  : $BUILD_FOR_VERSION"
echo "Source  : $SRC_DIR"
echo "Venv    : $VENV_DIR"
echo "Plat    : ${AUDITWHEEL_PLAT_DEF:-auto}"
echo "=============================="

prepare_source() {
    if [ -d "$SRC_DIR/.git" ]; then
        echo "📥 Updating source with git pull: $SRC_DIR"
        git -C "$SRC_DIR" remote set-url origin "$REPO_URL"
        git -C "$SRC_DIR" fetch --tags origin
        git -C "$SRC_DIR" pull --ff-only || true
    else
        echo "📥 Cloning source: $REPO_URL -> $SRC_DIR"
        rm -rf "$SRC_DIR"
        git clone "$REPO_URL" "$SRC_DIR"
        git -C "$SRC_DIR" fetch --tags origin
    fi

    cd "$SRC_DIR"
    if git rev-parse --verify --quiet "v$REALSENSE_VERSION" >/dev/null; then
        git checkout "v$REALSENSE_VERSION"
    elif git rev-parse --verify --quiet "$REALSENSE_VERSION" >/dev/null; then
        git checkout "$REALSENSE_VERSION"
    elif git ls-remote --exit-code --heads origin "$REALSENSE_VERSION" >/dev/null 2>&1; then
        git checkout "$REALSENSE_VERSION"
        git pull --ff-only origin "$REALSENSE_VERSION"
    else
        echo "⚠️ 未找到 v$REALSENSE_VERSION / $REALSENSE_VERSION tag 或分支，继续使用当前分支构建。"
    fi
}

prepare_venv() {
    echo "🐍 Preparing Python build env"
    rm -rf "$VENV_DIR"
    uv venv "$VENV_DIR" --python="$BUILD_FOR_VERSION"
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    uv pip install pip -U
    deactivate
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    pip install -U setuptools wheel build hatchling auditwheel twine pyelftools
}

build_realsense() {
    echo "🏗️ Building librealsense"
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    cmake .. \
        -DBUILD_EXAMPLES=true \
        -DCMAKE_INSTALL_PREFIX=./install_v4l2 \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_PYTHON_BINDINGS=ON
    cmake --build . -- -j"$(nproc)"
    cmake --install .
}

prepare_python_package() {
    echo "📦 Preparing pyrealsense2 package files"
    cd "$SRC_DIR"
    mkdir -p wrappers/python/pyrealsense2
    cp build/Release/pyr* wrappers/python/pyrealsense2/
    cp build/third-party/pybind11/pybind11/_version.py wrappers/python/pyrealsense2/
    sed -i "s/__version__ = \"[^\"]*\"/__version__ = \"$REALSENSE_VERSION\"/" wrappers/python/pyrealsense2/_version.py
}

build_and_upload_wheel() {
    echo "🛞 Building, repairing and uploading wheel"
    cd "$SRC_DIR/wrappers/python"
    rm -rf build dist wheelhouse
    python -m build .

    local input_wheel
    input_wheel="$(find dist -maxdepth 1 -type f -name "pyrealsense2-${REALSENSE_VERSION}-*.whl" | head -n 1)"
    if [ -z "$input_wheel" ]; then
        echo "❌ 未找到构建出的 pyrealsense2-${REALSENSE_VERSION}-*.whl"
        exit 1
    fi

    auditwheel repair "$input_wheel" --plat "$AUDITWHEEL_PLAT_DEF"

    local repaired_wheel
    repaired_wheel="$(find wheelhouse -maxdepth 1 -type f -name "pyrealsense2-${REALSENSE_VERSION}-*.whl" | head -n 1)"
    if [ -z "$repaired_wheel" ]; then
        echo "❌ auditwheel repair 后未找到 wheelhouse 中的 wheel"
        exit 1
    fi

    if [ -f "$FIX_WHL_SCRIPT" ]; then
        python "$FIX_WHL_SCRIPT" "$repaired_wheel"
    else
        echo "⚠️ 未找到 fix_whl_rpath.py，跳过 rpath 修复: $FIX_WHL_SCRIPT"
    fi

    twine upload -r gitlab "$repaired_wheel"
}

prepare_source
prepare_venv
build_realsense
prepare_python_package
build_and_upload_wheel

deactivate || true
echo "✅ RealSense pyrealsense2 $REALSENSE_VERSION for Python $BUILD_FOR_VERSION build finished."