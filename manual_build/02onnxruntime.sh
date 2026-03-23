#!/bin/bash
## 需要指定 ONNXRUNTIME_TARGET_DIR 和 tag
set -e
export CMAKE_ARGS="-DCMAKE_CXX_FLAGS='-march=rv64gcv' -DCMAKE_C_FLAGS='-march=rv64gcv'"

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

# git dir
ONNXRUNTIME_TARGET_DIR=/root/whls/onnxruntime
ONNX_TAG=v1.24.3

export PIP_CACHE_DIR="$HOME/.cache/pip/wheels_onnxruntime_uv_$BUILD_FOR_VERSION"
export TMPDIR="$HOME/.mytmp/onnxruntime_uv_$BUILD_FOR_VERSION"
mkdir -p $TMPDIR
# 虚拟环境目录
VENV_DIR="$HOME/pyenvs/build_onnxruntime_uv_$BUILD_FOR_VERSION"

# 删除旧虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo "🧹 Removing old virtualenv at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

# 创建新虚拟环境
echo "📦 Creating new virtualenv at $VENV_DIR"
uv venv "$VENV_DIR" --python=$BUILD_FOR_VERSION

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 安装构建相关工具
echo "⬆️  Installing pip & build tools..."
uv pip install --upgrade pip
deactivate
source "$VENV_DIR/bin/activate"
pip install --verbose setuptools wheel build twine numpy cmake==3.30.0

deactivate

# 再次激活虚拟环境，刷新cmake版本
source "$VENV_DIR/bin/activate"

# 执行 cmake --version 并打印输出
echo "CMake version info:"
cmake --version

# 设置环境变量
export PYTHONPATH="$VENV_DIR/lib/python3.12/site-packages"

# 存在，则进入该目录
if [ -d "$ONNXRUNTIME_TARGET_DIR" ]; then
    cd "$ONNXRUNTIME_TARGET_DIR"
else
    echo "Error no onnxruntime project dir !"
    exit 1
fi

# 检查 tag 是否存在
if git rev-parse -q --verify "refs/tags/$ONNX_TAG" >/dev/null; then
    git checkout "$ONNX_TAG"
else
    echo "Error: Git tag '$ONNX_TAG' does not exist!"
    exit 1
fi

sleep 4

./build.sh --config Release --parallel --compile_no_warning_as_error --skip_submodule_sync --enable_pybind --build_wheel

rm -rf "~/mytmpstg" || echo "❌ Failed to remove mytmpstg"

deactivate

sleep 3

echo "🗑️  Removing $VENV_DIR"
rm -rf "$VENV_DIR" || echo "⚠️ Failed Remove $VENV_DIR"

echo "✅ Done.请检查并上传whl包"
