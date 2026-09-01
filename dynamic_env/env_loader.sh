#!/usr/bin/env bash
# 公用环境加载器

# 获取当前脚本所在目录。qt.sh 支持从 Bash 和 zsh source，
# 因此这里不能在 zsh 中继续使用 BASH_SOURCE 定位。
if [[ -n "${BASH_VERSION:-}" ]]; then
    ENV_LOADER_FILE="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
    ENV_LOADER_FILE="${(%):-%N}"
else
    echo "❌ 动态环境加载器仅支持 Bash 或 zsh"
    return 1 2>/dev/null || exit 1
fi
SCRIPT_DIR_ENV_LOADER="$(cd "$(dirname "$ENV_LOADER_FILE")" && pwd)"
unset ENV_LOADER_FILE

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
    local i script
    for (( i=${#MODULE_SCRIPTS[@]}; i>=1; i-- )); do
        if [[ -n "${ZSH_VERSION:-}" ]]; then
            script="${MODULE_SCRIPTS[i]}"
        else
            script="${MODULE_SCRIPTS[i-1]}"
        fi
        if ! source "$script" deactivate; then
            echo "⚠️ Failed to unload env script: $script"
        fi
    done
}
