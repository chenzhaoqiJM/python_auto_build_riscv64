#!/usr/bin/env bash
# 公用环境加载器

# 获取当前脚本所在目录
SCRIPT_DIR_ENV_LOADER="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 定义模块脚本路径数组（注意顺序）
MODULE_SCRIPTS=(
    "$SCRIPT_DIR_ENV_LOADER/arrow_env.sh" "$SCRIPT_DIR_ENV_LOADER/av_env.sh" "$SCRIPT_DIR_ENV_LOADER/llvmlite_env.sh" \
    "$SCRIPT_DIR_ENV_LOADER/mujoco_env.sh" "$SCRIPT_DIR_ENV_LOADER/cyclonedds_env.sh" "$SCRIPT_DIR_ENV_LOADER/opencv_env.sh" \
    "$SCRIPT_DIR_ENV_LOADER/qt5_env.sh" "$SCRIPT_DIR_ENV_LOADER/qt6_env.sh" \
    "$SCRIPT_DIR_ENV_LOADER/pymupdf_env.sh" "$SCRIPT_DIR_ENV_LOADER/pemja_env.sh" "$SCRIPT_DIR_ENV_LOADER/faiss_env.sh" "$SCRIPT_DIR_ENV_LOADER/pynacl.sh" \
    "$SCRIPT_DIR_ENV_LOADER/stag_python_env.sh" \
    "$SCRIPT_DIR_ENV_LOADER/numpy_env.sh"
)

# 用户传入的包
PKG_ENV_LOADER="$1"

# 加载函数
load_env() {
    echo "[INFO] Activating $PKG_ENV_LOADER"
    for script in "${MODULE_SCRIPTS[@]}"; do
        if ! source "$script" activate "$PKG_ENV_LOADER"; then
            echo "⚠️ Failed to load env script: $script"
        fi
    done
}

# 卸载函数（逆序卸载）
unload_env() {
    echo "[INFO] Deactivating"
    for (( i=${#MODULE_SCRIPTS[@]}-1; i>=0; i-- )); do
        if ! source "${MODULE_SCRIPTS[i]}" deactivate; then
            echo "⚠️ Failed to unload env script: ${MODULE_SCRIPTS[i]}"
        fi
    done
}
