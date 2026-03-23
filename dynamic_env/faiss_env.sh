#!/usr/bin/env bash
# faiss_env.sh
# 用法: source faiss_env.sh <action> <package>

# 要设置的组件

# 维护激活状态
: "${_faiss_ENV_ACTIVE:=0}"

# 根据包名选择 faiss 安装路径
get_faiss_prefix_by_pkg() {
    local pkg="$1"
    if [ -z "$pkg" ]; then
        echo "Usage: get_faiss_prefix_by_pkg <package>"
        return 1
    fi

    # 拆分包名
    IFS='=' read -r name _ version <<< "$pkg"

    # 默认版本
    local default_version="1.12.0"

    # 如果不是 faiss 或版本缺失，使用默认版本
    if [[ "$name" != faiss* ]] || [ -z "$version" ]; then
        version="$default_version"
    fi

    local install_prefix="/opt/ext/faiss/faiss-v$version"
    echo "$install_prefix"
}

if [[ "$1" == "activate" ]]; then

    if [[ "$2" != faiss* ]]; then
        echo "[faissEnv] Skip: package '$2' is not faiss, no environment change"
        return 0
    fi

    pkg="$2"
    faiss_INSTALL_PREFIX=$(get_faiss_prefix_by_pkg "$pkg")

    if [[ -z "$faiss_INSTALL_PREFIX" ]]; then
        echo "[faissEnv] No faiss path configured for package: $pkg"
        _faiss_ENV_ACTIVE=0
        return 0
    fi

    if [[ "$_faiss_ENV_ACTIVE" -eq 1 ]]; then
        echo "[faissEnv] Warning: faiss environment already active, skipping activate"
        return 0
    fi

    echo "[faissEnv] Activating for package: $pkg" DIR TO $faiss_INSTALL_PREFIX
    export _faiss_ENV_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${faiss_INSTALL_PREFIX}/lib:${LD_LIBRARY_PATH}"

    export FAISS_ENABLE_GPU=False
    export FAISS_INSTALL_PREFIX=$faiss_INSTALL_PREFIX

    _faiss_ENV_ACTIVE=1

elif [[ "$1" == "deactivate" ]]; then
    if [[ "$_faiss_ENV_ACTIVE" -eq 0 ]]; then
        echo "[faissEnv] faiss environment not active, skipping deactivate"
        return 0
    fi

    echo "[faissEnv] Restoring environment"
    if [[ -n "${_faiss_ENV_OLD_LD_LIBRARY_PATH:-}" ]]; then
        export LD_LIBRARY_PATH="$_faiss_ENV_OLD_LD_LIBRARY_PATH"
        unset _faiss_ENV_OLD_LD_LIBRARY_PATH
    fi

    unset FAISS_ENABLE_GPU
    unset FAISS_INSTALL_PREFIX

    _faiss_ENV_ACTIVE=0
    echo faissEnv UNSET OK, Now LD_LIBRARY_PATH == $LD_LIBRARY_PATH

else
    echo "Usage: source faiss_env.sh activate <package>"
    echo "       source faiss_env.sh deactivate"
fi
